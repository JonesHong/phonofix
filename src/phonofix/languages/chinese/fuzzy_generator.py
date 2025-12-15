"""
中文模糊變體生成器

負責為專有名詞自動生成可能的拼寫錯誤變體（同音字/近音字）。

注意：此模組使用延遲導入 (Lazy Import) 機制，
僅在實際使用中文功能時才會載入 Pinyin2Hanzi 和 hanziconv。
"""

from __future__ import annotations

from phonofix.backend import ChinesePhoneticBackend, get_chinese_backend
from phonofix.core.protocols.fuzzy import FuzzyGeneratorProtocol

from .config import ChinesePhoneticConfig
from .utils import ChinesePhoneticUtils

# =============================================================================
# 延遲導入 Pinyin2Hanzi 和 hanziconv
# =============================================================================

_pinyin2hanzi_dag = None
_pinyin2hanzi_params_class = None
_hanziconv = None
_imports_checked = False


def _get_pinyin2hanzi():
    """延遲載入 Pinyin2Hanzi 模組"""
    global _pinyin2hanzi_dag, _pinyin2hanzi_params_class, _imports_checked

    if _imports_checked and _pinyin2hanzi_dag is not None:
        return _pinyin2hanzi_params_class, _pinyin2hanzi_dag

    try:
        from Pinyin2Hanzi import DefaultDagParams, dag
        _pinyin2hanzi_params_class = DefaultDagParams
        _pinyin2hanzi_dag = dag
        _imports_checked = True
        return _pinyin2hanzi_params_class, _pinyin2hanzi_dag
    except ImportError:
        _imports_checked = True
        from phonofix.languages.chinese import CHINESE_INSTALL_HINT
        raise ImportError(CHINESE_INSTALL_HINT)


def _get_hanziconv():
    """延遲載入 hanziconv 模組"""
    global _hanziconv, _imports_checked

    if _imports_checked and _hanziconv is not None:
        return _hanziconv

    try:
        from hanziconv import HanziConv
        _hanziconv = HanziConv
        _imports_checked = True
        return _hanziconv
    except ImportError:
        _imports_checked = True
        from phonofix.languages.chinese import CHINESE_INSTALL_HINT
        raise ImportError(CHINESE_INSTALL_HINT)


class ChineseFuzzyGenerator(FuzzyGeneratorProtocol):
    """
    中文模糊變體生成器

    功能:
    - 根據輸入的專有名詞，生成其可能的發音變體
    - 利用 Pinyin2Hanzi 庫反查同音字
    - 考慮聲母/韻母的模糊音規則 (如 z/zh, in/ing)
    - 用於擴充修正器的比對目標，提高召回率
    """

    def __init__(
        self,
        config=None,
        backend: ChinesePhoneticBackend | None = None,
        *,
        enable_representative_variants: bool = False,
        max_phonetic_states: int = 600,
    ):
        """
        初始化中文模糊變體生成器。

        Args:
            config: 拼音設定（未提供則使用預設 ChinesePhoneticConfig）
            backend: 可選 backend（未提供則取得中文 backend 單例）
            enable_representative_variants: 是否啟用代表字變體（較昂貴，預設關閉）
            max_phonetic_states: 變體展開狀態上限（避免爆炸）

        注意：
        - Pinyin2Hanzi/hanziconv 只在需要「代表字」功能時才會被實際 import
        """
        self.config = config or ChinesePhoneticConfig
        self._backend = backend or get_chinese_backend()
        self.utils = ChinesePhoneticUtils(config=self.config, backend=self._backend)
        self.enable_representative_variants = enable_representative_variants
        self.max_phonetic_states = max(50, int(max_phonetic_states))
        self._dag_params = None  # 延遲初始化

    def _pinyin_string(self, text: str) -> str:
        """取得文本的拼音字串（委派給 backend 快取）。"""
        return self._backend.to_phonetic(text)

    @property
    def dag_params(self):
        """延遲初始化 DAG 參數"""
        if self._dag_params is None:
            DefaultDagParams, _ = _get_pinyin2hanzi()
            self._dag_params = DefaultDagParams()
        return self._dag_params

    def _pinyin_to_chars(self, pinyin_str, max_chars=2):
        """
        將拼音轉換為可能的漢字 (同音字反查)

        使用 Pinyin2Hanzi 庫的 DAG (有向無環圖) 演算法找出最可能的漢字。

        Args:
            pinyin_str: 拼音字串 (如 "zhong")
            max_chars: 最多返回幾個候選字

        Returns:
            List[str]: 候選漢字列表 (繁體)
            範例: "zhong" -> ["中", "重"]
        """
        # 延遲載入
        _, dag = _get_pinyin2hanzi()
        HanziConv = _get_hanziconv()

        # 使用 DAG 演算法查詢拼音對應的漢字路徑
        result = dag(self.dag_params, [pinyin_str], path_num=max_chars)
        chars = []
        if result:
            for item in result:
                # 將簡體結果轉換為繁體
                # item.path[0] 是最可能的單字
                chars.append(HanziConv.toTraditional(item.path[0]))
        # 若查無結果，返回原始拼音
        return chars if chars else [pinyin_str]

    def _get_char_variations(self, char):
        """
        取得單個漢字的所有模糊音變體

        流程:
        1. 取得漢字的標準拼音
        2. 生成該拼音的所有模糊變體 (如 z -> zh, in -> ing)
        3. 將模糊拼音反查回代表性漢字

        Args:
            char: 輸入漢字 (如 "中")

        Returns:
            List[Dict]: 變體列表，每個元素包含 {"pinyin": 拼音, "char": 代表字}
            範例: "中" (zhong) ->
            [
                {"pinyin": "zhong", "char": "中"},
                {"pinyin": "zong", "char": "宗"}  (假設 z/zh 模糊)
            ]
        """
        base_pinyin = self._pinyin_string(char)
        # 非中文字符直接返回原樣
        if not base_pinyin or not ('\u4e00' <= char <= '\u9fff'):
            return [{"pinyin": char, "char": char}]

        # 生成所有可能的模糊拼音
        potential_pinyins = self.utils.generate_fuzzy_pinyin_variants(
            base_pinyin, bidirectional=True
        )

        options = []
        for p in potential_pinyins:
            if p == base_pinyin:
                # 原始拼音對應原始字符
                options.append({"pinyin": p, "char": char, "changes": 0})
            else:
                if not self.enable_representative_variants:
                    continue

                # 模糊拼音需要反查一個代表字，以便後續組合成詞
                # 這裡只取第一個最可能的字作為代表
                candidate_chars = self._pinyin_to_chars(p)
                repr_char = candidate_chars[0]
                if '\u4e00' <= repr_char <= '\u9fff':
                    options.append({"pinyin": p, "char": repr_char, "changes": 1})
        return options

    def _generate_char_combinations(self, char_options_list, *, max_results: int):
        """
        生成所有字符變體的排列組合

        Args:
            char_options_list: 每個位置的字符變體列表
            範例: [
                [{"char": "台", "pinyin": "tai"}],
                [{"char": "積", "pinyin": "ji"}, {"char": "基", "pinyin": "ji"}]
            ]

        Returns:
            List[str]: 組合後的詞彙列表
            範例: ["台積", "台基"]
        """
        # 以「拼音字串」為 key 做 beam search：邊生成邊去重，避免笛卡兒積爆炸。
        # state: pinyin_key -> (surface_word, change_count)
        states: dict[str, tuple[str, int]] = {"": ("", 0)}

        for options in char_options_list:
            next_states: dict[str, tuple[str, int]] = {}
            for p_prefix, (w_prefix, c_prefix) in states.items():
                for opt in options:
                    p_new = p_prefix + opt["pinyin"]
                    w_new = w_prefix + opt["char"]
                    c_new = c_prefix + int(opt.get("changes", 0) or 0)

                    existing = next_states.get(p_new)
                    if existing is None:
                        next_states[p_new] = (w_new, c_new)
                        continue

                    # 同一 phonetic key 下保留「變更更少」的 representative；若相同則取字典序穩定結果
                    if c_new < existing[1] or (c_new == existing[1] and w_new < existing[0]):
                        next_states[p_new] = (w_new, c_new)

            # 控制狀態數量（依變更數/長度/字典序做穩定裁剪）
            if len(next_states) > self.max_phonetic_states:
                ranked = sorted(
                    next_states.items(),
                    key=lambda kv: (kv[1][1], len(kv[1][0]), kv[1][0], kv[0]),
                )
                next_states = dict(ranked[: self.max_phonetic_states])

            states = next_states

        # 依更少變更優先輸出，並限制結果數量
        ranked_final = sorted(
            states.values(),
            key=lambda v: (v[1], len(v[0]), v[0]),
        )
        words = [w for (w, _) in ranked_final if w]
        return words[:max_results]

    def _add_sticky_phrase_aliases(self, term, aliases):
        """
        添加黏音/懶音短語別名

        整句對整句的特例，處理如 "不知道" -> "不道" 這種非單字對應的變體。

        Args:
            term: 原始詞彙
            aliases: 當前別名列表 (會被直接修改)

        Returns:
            None
        """
        if term in self.config.STICKY_PHRASE_MAP:
            # 取得目前已有的變體文字，避免重複
            alias_texts = [a if isinstance(a, str) else a.get("text", "") for a in aliases]

            for sticky in self.config.STICKY_PHRASE_MAP[term]:
                if sticky not in alias_texts:
                    # 黏音通常沒有標準拼音對應，或拼音不重要，故只存文字
                    # 若 aliases 是字串列表，直接 append
                    # 若 aliases 是 dict 列表 (舊版邏輯)，則 append dict
                    # 這裡配合 generate_fuzzy_variants 返回字串列表的邏輯
                    aliases.append(sticky)

    def generate_variants(self, term: str, max_variants: int = 30):
        """
        為輸入詞彙生成模糊變體列表

        Args:
            term: 輸入詞彙 (canonical)
            max_variants: 最多返回幾個變體（不包含原詞）

        Returns:
            List[str]: 變體列表（不包含原詞）
        """
        if not term:
            return []

        variants: list[str] = []

        # 1) 黏音/懶音 (整詞特例) 永遠保留（不依賴代表字功能）
        self._add_sticky_phrase_aliases(term, variants)

        # 2) 字級別代表字變體（可選，預設關閉）
        if self.enable_representative_variants:
            char_options_list = []
            for char in term:
                options = self._get_char_variations(char)
                # 若某字無可用選項，回退為原字（避免整詞被丟棄）
                if not options:
                    options = [{"pinyin": self._pinyin_string(char), "char": char, "changes": 0}]
                char_options_list.append(options)

            # 生成階段就以拼音 key 去重並裁剪，避免爆炸
            combinations = self._generate_char_combinations(
                char_options_list,
                max_results=max_variants + 10,  # 留一點空間給 sticky variants
            )
            variants.extend(combinations)

        # 3) 最終整理（移除原詞、去重、穩定排序）
        unique_aliases = sorted({a for a in variants if a and a != term})
        return unique_aliases[:max_variants]

    def filter_homophones(self, term_list):
        """
        過濾同音詞

        輸入一個詞彙列表,將「去聲調拼音」完全相同的詞進行過濾
        只保留第一個出現的詞。這在處理大量相似詞彙時很有用，
        可以避免詞典過度膨脹。

        Args:
            term_list: 詞彙列表 (如 ["測試", "側試", "策試"])

        Returns:
            dict: {
                "kept": [...],      # 保留的詞 (如 ["測試"])
                "filtered": [...]   # 過濾掉的同音詞 (如 ["側試", "策試"])
            }
        """
        kept = []
        filtered = []
        seen_pinyins = set()

        for term in term_list:
            # 取得去聲調拼音 (如 "測試" -> "ceshi")
            pinyin_str = self._pinyin_string(term)

            if pinyin_str in seen_pinyins:
                # 拼音已存在,歸類為過濾掉的
                filtered.append(term)
            else:
                # 新拼音,保留
                kept.append(term)
                seen_pinyins.add(pinyin_str)

        return {"kept": kept, "filtered": filtered}

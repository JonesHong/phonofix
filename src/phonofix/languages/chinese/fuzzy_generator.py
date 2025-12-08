"""
中文模糊變體生成器（重構版）

負責為專有名詞自動生成可能的 ASR 錯誤變體 (同音字/近音字)。

重構內容：
- 繼承 BaseFuzzyGenerator 抽象基類
- 實現統一的 phonetic_transform, generate_phonetic_variants, phonetic_to_text 接口
- 保留所有現有功能，向後兼容

注意：此模組使用延遲導入 (Lazy Import) 機制，
僅在實際使用中文功能時才會載入 Pinyin2Hanzi 和 hanziconv。

安裝中文支援:
    pip install "phonofix[chinese]"
"""

import itertools
from typing import List
from .config import ChinesePhoneticConfig
from .utils import ChinesePhoneticUtils
from phonofix.utils.logger import get_logger
from phonofix.utils.cache import cached_method
from phonofix.core.fuzzy_generator_interface import (
    BaseFuzzyGenerator,
    PhoneticVariant,
    VariantSource,
    convert_to_simple_list,
)


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
        from phonofix.utils.lazy_imports import CHINESE_INSTALL_HINT
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
        from phonofix.utils.lazy_imports import CHINESE_INSTALL_HINT
        raise ImportError(CHINESE_INSTALL_HINT)


class ChineseFuzzyGenerator(BaseFuzzyGenerator):
    """
    中文模糊變體生成器（重構版 - 繼承 BaseFuzzyGenerator）

    功能:
    - 根據輸入的專有名詞，生成其可能的發音變體
    - 利用 Pinyin2Hanzi 庫反查同音字
    - 考慮聲母/韻母的模糊音規則 (如 z/zh, in/ing)
    - 用於擴充修正器的比對目標，提高召回率

    重構特性：
    - 實現 BaseFuzzyGenerator 的抽象方法
    - 統一的 phonetic_transform (文字 → Pinyin)
    - 統一的 generate_phonetic_variants (Pinyin → 模糊 Pinyin)
    - 統一的 phonetic_to_text (Pinyin → 漢字)
    - 保留所有現有方法，向後兼容
    """

    def __init__(self, config=None):
        super().__init__(config)  # 調用父類初始化
        self.config = config or ChinesePhoneticConfig
        self.utils = ChinesePhoneticUtils(config=self.config)
        self._dag_params = None  # 延遲初始化
        self._logger = get_logger("fuzzy.chinese")

    @property
    def dag_params(self):
        """延遲初始化 DAG 參數"""
        if self._dag_params is None:
            DefaultDagParams, _ = _get_pinyin2hanzi()
            self._dag_params = DefaultDagParams()
        return self._dag_params

    # ========== 實現 BaseFuzzyGenerator 抽象方法 ==========

    @cached_method(maxsize=1000)
    def phonetic_transform(self, term: str) -> str:
        """
        文字 → Pinyin (Task 7.3: 添加 LRU 緩存)

        將中文詞彙轉換為拼音表示（無聲調）

        Args:
            term: 輸入詞彙（如 "台北"）

        Returns:
            str: Pinyin 字串（如 "taibei"）

        範例：
            >>> generator = ChineseFuzzyGenerator()
            >>> pinyin = generator.phonetic_transform("台北")
            >>> print(pinyin)
            taibei
        """
        return self.utils.get_pinyin_string(term)

    @cached_method(maxsize=1000)
    def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
        """
        Pinyin → 模糊 Pinyin 變體 (Task 7.3: 添加 LRU 緩存)

        應用聲母/韻母混淆規則生成 Pinyin 變體

        Args:
            phonetic_key: 標準 Pinyin（如 "taibei"）

        Returns:
            List[str]: 模糊 Pinyin 列表

        範例：
            >>> generator = ChineseFuzzyGenerator()
            >>> variants = generator.generate_phonetic_variants("zhong")
            >>> print(variants)
            ['zhong', 'zong', 'zhung', 'zung']  # z/zh, o/u 混淆
        """
        return self.utils.generate_fuzzy_pinyin_variants(
            phonetic_key,
            bidirectional=True
        )

    def phonetic_to_text(self, phonetic_key: str) -> str:
        """
        Pinyin → 漢字（反查代表字）

        將 Pinyin 轉換回漢字，用於顯示

        Args:
            phonetic_key: Pinyin 字串

        Returns:
            str: 代表性漢字

        範例：
            >>> generator = ChineseFuzzyGenerator()
            >>> char = generator.phonetic_to_text("zhong")
            >>> print(char)
            中
        """
        # 使用 _pinyin_to_chars 方法反查漢字
        chars = self._pinyin_to_chars(phonetic_key, max_chars=1)
        return chars[0] if chars else phonetic_key

    def apply_hardcoded_rules(self, term: str) -> List[str]:
        """
        應用硬編碼規則（黏音/懶音）

        處理整詞級別的特殊變體，如 "不知道" → "不道"

        Args:
            term: 輸入詞彙

        Returns:
            List[str]: 硬編碼變體列表

        範例：
            >>> generator = ChineseFuzzyGenerator()
            >>> variants = generator.apply_hardcoded_rules("不知道")
            >>> print(variants)
            ['不道', '不曉得']
        """
        hardcoded = []

        if term in self.config.STICKY_PHRASE_MAP:
            hardcoded.extend(self.config.STICKY_PHRASE_MAP[term])

        return hardcoded

    # ========== 原有私有方法（保留） ==========

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
        base_pinyin = self.utils.get_pinyin_string(char)
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
                options.append({"pinyin": p, "char": char})
            else:
                # 模糊拼音需要反查一個代表字，以便後續組合成詞
                # 這裡只取第一個最可能的字作為代表
                candidate_chars = self._pinyin_to_chars(p)
                repr_char = candidate_chars[0]
                if '\u4e00' <= repr_char <= '\u9fff':
                    options.append({"pinyin": p, "char": repr_char})
        return options

    def _generate_char_combinations(self, char_options_list):
        """
        生成所有字符變體的排列組合（優化版：提前去重+動態上限）

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
        seen_pinyins = set()
        combinations = []

        # 動態設定上限（根據詞長）
        word_len = len(char_options_list)
        MAX_COMBOS = min(300, 100 * word_len)

        # 使用 itertools.product 進行笛卡兒積組合
        for i, combo in enumerate(itertools.product(*char_options_list)):
            # 達到上限時截斷
            if i >= MAX_COMBOS:
                self._logger.warning(
                    f"達到組合上限 {MAX_COMBOS}（詞長 {word_len}），截斷變體生成"
                )
                break

            # 提前計算拼音並去重（優化：避免無效組合）
            pinyin = "".join([item["pinyin"] for item in combo])
            if pinyin in seen_pinyins:
                continue

            word = "".join([item["char"] for item in combo])
            combinations.append(word)
            seen_pinyins.add(pinyin)

        return combinations

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

    def _prepare_final_alias_list(self, term, aliases):
        """
        準備最終的別名列表

        去重、排序,並將原詞放在第一位

        Args:
            term: 原始詞彙
            aliases: 別名列表 (字串列表)

        Returns:
            list: 最終的別名列表 (原詞在首位)
        """
        # 移除原詞 (稍後加回第一位) 並去重
        unique_aliases = set(aliases)
        if term in unique_aliases:
            unique_aliases.remove(term)
            
        sorted_aliases = sorted(list(unique_aliases))

        # 原詞放在第一位
        return [term] + sorted_aliases

    def generate_variants(self, term, max_variants=None, return_phonetic_variants=False):
        """
        為輸入詞彙生成模糊變體列表（重構版 - 向後兼容）

        支援三種輸入模式:
        1. 單一詞彙 (str): 返回該詞彙的變體列表 (List[str])
        2. 詞彙列表 (List[str]): 返回詞典 (Dict[str, List[str]])
        3. 單一詞彙 + return_phonetic_variants=True: 返回 PhoneticVariant 列表

        重構說明：
        - 現在可以使用父類的統一流程（通過 super().generate_variants）
        - 也保留了舊的字級組合邏輯（通過 _generate_variants_legacy）
        - 默認使用舊邏輯以保持向後兼容

        Args:
            term: 輸入詞彙 (str) 或 詞彙列表 (List[str])
            max_variants: 最大變體數量（None 表示不限制）
            return_phonetic_variants: 是否返回 PhoneticVariant 列表（新格式）

        Returns:
            List[str] or Dict[str, List[str]] or List[PhoneticVariant]: 視參數而定
        """
        # 模式 2: 處理詞彙列表
        if isinstance(term, list):
            result = {}
            for t in term:
                result[t] = self.generate_variants(
                    t,
                    max_variants=max_variants,
                    return_phonetic_variants=return_phonetic_variants
                )
            return result

        # 模式 3: 使用新的父類統一流程（返回 PhoneticVariant）
        if return_phonetic_variants:
            return super().generate_variants(
                term,
                max_variants=max_variants or 100,
                include_hardcoded=True
            )

        # 模式 1: 使用舊邏輯（向後兼容，返回 List[str]）
        final_variants = self._generate_variants_legacy(term)

        # 應用 max_variants 限制
        if max_variants is not None and len(final_variants) > max_variants:
            # 保留原詞（在第一位）+ 限制數量的變體
            if final_variants[0] == term:
                final_variants = [term] + final_variants[1:max_variants+1]
            else:
                final_variants = final_variants[:max_variants]

        return final_variants

    def _generate_variants_legacy(self, term):
        """
        舊版變體生成邏輯（保留以維持向後兼容）

        工作流程：
        1. 字級變體生成
        2. 字符組合
        3. 黏音/懶音規則
        4. 去重與排序

        Args:
            term: 輸入詞彙

        Returns:
            List[str]: 變體列表（原詞在首位）
        """
        # 1. 對詞彙中的每個字，生成其模糊音變體 (字級別)
        char_options_list = []
        for char in term:
            char_options_list.append(self._get_char_variations(char))

        # 2. 組合所有字的變體，產生新的詞彙 (詞級別)
        variants = self._generate_char_combinations(char_options_list)

        # 3. 處理黏音/懶音 (整詞特例)
        self._add_sticky_phrase_aliases(term, variants)

        # 4. 最終整理 (去重、排序、原詞置頂)
        final_variants = self._prepare_final_alias_list(term, variants)

        return final_variants

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
            pinyin_str = self.utils.get_pinyin_string(term)

            if pinyin_str in seen_pinyins:
                # 拼音已存在,歸類為過濾掉的
                filtered.append(term)
            else:
                # 新拼音,保留
                kept.append(term)
                seen_pinyins.add(pinyin_str)

        return {"kept": kept, "filtered": filtered}

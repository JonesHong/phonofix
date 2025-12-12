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
            phonetic_key, bidirectional=True
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
        return chars if chars else [pinyin_str]

    def _get_char_variations(self, char):
        """
        取得單個漢字的所有模糊音變體

        保證返回列表的第一個元素是原始字元。
        """
        base_pinyin = self.utils.get_pinyin_string(char)
        if not base_pinyin or not ("\u4e00" <= char <= "\u9fff"):
            return [{"pinyin": char, "char": char}]

        # 準備結果列表，預先加入原始字元
        options = [{"pinyin": base_pinyin, "char": char}]
        seen = {(base_pinyin, char)}

        # 生成所有可能的模糊拼音
        potential_pinyins = self.utils.generate_fuzzy_pinyin_variants(
            base_pinyin, bidirectional=True
        )

        for p in potential_pinyins:
            candidate_chars = self._pinyin_to_chars(p, max_chars=3)

            for c in candidate_chars:
                if "\u4e00" <= c <= "\u9fff":
                    if (p, c) not in seen:
                        options.append({"pinyin": p, "char": c})
                        seen.add((p, c))

        return options

    def _generate_char_combinations(self, char_options_list):
        """
        生成所有字符變體的排列組合 (優先生成變更較少的組合)
        """
        # 使用 dict 計算拼音出現次數，允許保留少量同音詞 (如: 台北車站 vs 太北車站)
        # 這樣可以確保 "保留一拼音不同的" 需求，即保留至少一個同音變體
        seen_pinyins = {}
        combinations = []

        word_len = len(char_options_list)
        MAX_COMBOS = 1000

        indices_list = [list(range(len(opts))) for opts in char_options_list]

        for diff_count in range(word_len + 1):
            if len(combinations) >= MAX_COMBOS:
                break

            for positions_to_change in itertools.combinations(
                range(word_len), diff_count
            ):
                if len(combinations) >= MAX_COMBOS:
                    break

                current_iterables = []
                valid_combo = True
                for i in range(word_len):
                    if i in positions_to_change:
                        if len(indices_list[i]) > 1:
                            current_iterables.append(indices_list[i][1:])
                        else:
                            valid_combo = False
                            break
                    else:
                        current_iterables.append([0])

                if not valid_combo:
                    continue

                for indices in itertools.product(*current_iterables):
                    if len(combinations) >= MAX_COMBOS:
                        break

                    current_combo = []
                    current_pinyin_parts = []

                    for i, idx in enumerate(indices):
                        item = char_options_list[i][idx]
                        current_combo.append(item["char"])
                        current_pinyin_parts.append(item["pinyin"])

                    pinyin = "".join(current_pinyin_parts)

                    # 檢查該拼音是否已達到保留上限 (例如保留 2 個: 1 個原詞 + 1 個變體)
                    count = seen_pinyins.get(pinyin, 0)
                    if count >= 2:
                        continue

                    word = "".join(current_combo)
                    combinations.append(word)
                    seen_pinyins[pinyin] = count + 1

        return combinations

    def generate_variants(self, term, max_variants=None, include_hardcoded=True):
        """
        為輸入詞彙生成模糊變體列表 (覆寫父類方法)

        中文特化實作：
        採用「逐字變體組合」策略，而非整詞拼音變換。
        1. 將詞彙拆解為單字
        2. 生成每個單字的同音/近音字
        3. 排列組合生成候選詞
        4.轉換為 PhoneticVariant 物件並評分

        Args:
            term: 輸入詞彙 (str) 或 詞彙列表 (List[str])
            max_variants: 最大變體數量（None 表示不限制，默認 100）
            include_hardcoded: 是否包含硬編碼規則（默認 True）

        Returns:
            List[PhoneticVariant] or Dict[str, List[PhoneticVariant]]: 視輸入類型而定
        """
        # 處理詞彙列表輸入
        if isinstance(term, list):
            result = {}
            for t in term:
                result[t] = self.generate_variants(
                    t, max_variants=max_variants, include_hardcoded=include_hardcoded
                )
            return result

        # 單一詞彙處理
        max_v = max_variants or 100
        variants = self._process_single_term(term, max_v, include_hardcoded)

        return variants

    def _process_single_term(self, term, max_variants, include_hardcoded):
        """處理單一詞彙的變體生成"""
        variants = []
        base_phonetic = self.phonetic_transform(term)

        # 1. 逐字生成選項
        char_options_list = []
        for char in term:
            options = self._get_char_variations(char)
            char_options_list.append(options)

        # 2. 排列組合生成候選詞文字 (List[str])
        candidate_words = self._generate_char_combinations(char_options_list)

        # 3. 轉換為 PhoneticVariant 物件並評分
        for word in candidate_words:
            # 略過原詞 (稍後過濾或評分時處理)
            if word == term:
                continue

            # 計算該變體的拼音 (用於去重和評分)
            variant_phonetic = self.phonetic_transform(word)

            # 計算分數
            score = self.calculate_score(base_phonetic, variant_phonetic)

            variants.append(
                PhoneticVariant(
                    text=word,
                    phonetic_key=variant_phonetic,
                    score=score,
                    source=VariantSource.PHONETIC_FUZZY,
                    metadata={"base_phonetic": base_phonetic},
                )
            )

        # 4. 加入硬編碼規則 (如果有)
        if include_hardcoded:
            hardcoded_texts = self.apply_hardcoded_rules(term)
            for ht in hardcoded_texts:
                try:
                    p_key = self.phonetic_transform(ht)
                    variants.append(
                        PhoneticVariant(
                            text=ht,
                            phonetic_key=p_key,
                            score=0.85,  # 硬編碼給予高分
                            source=VariantSource.HARDCODED_PATTERN,
                        )
                    )
                except:
                    pass

        # 5. 去重 (Phonetic key based)
        unique_variants = self._deduplicate_by_phonetic(variants)

        # 6. 排序 (分數高 -> 低)
        sorted_variants = sorted(
            unique_variants, key=lambda v: (-v.score, len(v.text), v.text)
        )

        return sorted_variants[:max_variants]

    def filter_homophones(self, term_list):
        """
        過濾同音詞

        輸入一個詞彙列表,將「去聲調拼音」完全相同的詞進行過濾
        保留每個拼音的前 2 個出現詞 (原詞 + 1 個變體)。
        滿足「保留一拼音不同的」需求。

        Args:
            term_list: 詞彙列表 (如 ["測試", "側試", "策試"])

        Returns:
            dict: {
                "kept": [...],      # 保留的詞 (如 ["測試", "側試"])
                "filtered": [...]   # 過濾掉的同音詞 (如 ["策試"])
            }
        """
        kept = []
        filtered = []
        seen_pinyins = {}

        for term in term_list:
            # 取得去聲調拼音
            pinyin_str = self.utils.get_pinyin_string(term)

            count = seen_pinyins.get(pinyin_str, 0)
            if count >= 2:
                # 拼音已存在超過保留上限, 過濾
                filtered.append(term)
            else:
                # 保留
                kept.append(term)
                seen_pinyins[pinyin_str] = count + 1

        return {"kept": kept, "filtered": filtered}

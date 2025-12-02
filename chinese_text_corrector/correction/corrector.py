"""
中文文本校正器模組

用於 ASR 後處理,透過專有名詞詞典進行模糊音修正
特別適用於未微調/訓練模型的情境
"""

import pypinyin
import Levenshtein
import re
from ..core.phonetic_config import PhoneticConfig
from ..core.phonetic_utils import PhoneticUtils
from ..dictionary.generator import FuzzyDictionaryGenerator


class ChineseTextCorrector:
    """
    中文文本校正器

    功能:
    - ASR 輸出後處理,修正專有名詞的辨識錯誤
    - 支援模糊音匹配 (捲舌音、n/l 不分、台灣國語特徵等)
    - 上下文關鍵字加分機制
    - 權重系統優化匹配優先級
    - 豁免清單避免誤改
    """

    @staticmethod
    def _filter_aliases_by_pinyin(aliases, utils):
        """
        過濾別名列表,保留拼音唯一的項目 (類似 Set 行為)

        Args:
            aliases: 別名列表
            utils: PhoneticUtils 實例

        Returns:
            list: 過濾後的別名列表 (保留第一個出現的拼音)
        """
        seen_pinyins = set()
        filtered = []

        for alias in aliases:
            pinyin_str = utils.get_pinyin_string(alias)
            if pinyin_str not in seen_pinyins:
                filtered.append(alias)
                seen_pinyins.add(pinyin_str)

        return filtered

    @classmethod
    def from_terms(cls, term_dict, exclusions=None, config=None):
        """
        從詞彙列表建立自動校正器 (類方法工廠)

        自動生成模糊音別名並建立校正器,支援多種輸入格式

        Args:
            term_dict: 詞彙字典,支援三種格式:
                1. 完整格式: {"台北車站": {"aliases": [...], "keywords": [...], "weight": 0.3}}
                2. 簡化格式: {"台北車站": ["北車", "臺北"]}  (僅別名)
                3. 最簡格式: ["台北車站", "阿斯匹靈"]  (僅關鍵字,自動生成別名)
            exclusions: 豁免清單 (可選)
            config: PhoneticConfig 實例 (可選)

        Returns:
            ChineseTextCorrector: 自動配置的校正器實例

        Example:
            >>> # 格式 1: 完整格式
            >>> corrector = ChineseTextCorrector.from_terms({
            ...     "台北車站": {
            ...         "aliases": ["北車"],
            ...         "keywords": ["等", "接"],
            ...         "weight": 0.2
            ...     }
            ... })

            >>> # 格式 2: 僅別名 (自動補全)
            >>> corrector = ChineseTextCorrector.from_terms({
            ...     "台北車站": ["北車", "臺北車站"]
            ... })

            >>> # 格式 3: 僅關鍵字 (自動生成別名)
            >>> corrector = ChineseTextCorrector.from_terms(["台北車站", "阿斯匹靈"])

            >>> result = corrector.correct("我在北車等你")
        """
        # 初始化工具
        utils = PhoneticUtils(config=config)
        generator = FuzzyDictionaryGenerator(config=config)

        # 處理最簡格式: list → dict
        if isinstance(term_dict, list):
            term_dict = {term: {} for term in term_dict}

        # 轉換為標準格式並自動生成缺失的別名
        normalized_dict = {}

        for term, value in term_dict.items():
            # 標準化數據格式
            normalized_value = cls._normalize_term_value(
                term, value, generator, utils
            )

            if normalized_value:
                normalized_dict[term] = normalized_value

        # 使用標準化的字典建立校正器
        return cls(
            term_mapping=normalized_dict,
            exclusions=exclusions,
            config=config
        )

    @classmethod
    def _normalize_term_value(cls, term, value, generator, utils):
        """
        標準化詞彙配置數據

        Args:
            term: 標準詞
            value: 原始配置 (可能是 list, dict, 或空 dict)
            generator: FuzzyDictionaryGenerator 實例
            utils: PhoneticUtils 實例

        Returns:
            dict: 標準化後的配置 {"aliases": [...], "keywords": [...], "weight": float}
        """
        # 處理簡化格式: list of aliases
        if isinstance(value, list):
            value = {"aliases": value}

        # 處理字典格式
        elif isinstance(value, dict):
            # 確保有 aliases 鍵
            if "aliases" not in value:
                value["aliases"] = []
        else:
            # 不支援的格式,返回 None
            return None

        # 如果沒有提供別名,自動生成
        if not value["aliases"]:
            fuzzy_result = generator.generate_fuzzy_dictionary([term])

            if term in fuzzy_result:
                # 排除標準詞本身,只保留變體
                auto_aliases = [
                    alias for alias in fuzzy_result[term] if alias != term
                ]

                # 拼音去重 (不限制數量,使用所有去重後的變體)
                auto_aliases = cls._filter_aliases_by_pinyin(auto_aliases, utils)
                value["aliases"] = auto_aliases
        else:
            # 手動提供的別名也要拼音去重
            value["aliases"] = cls._filter_aliases_by_pinyin(
                value["aliases"], utils
            )

        # 轉換為標準格式
        return {
            "aliases": value["aliases"],
            "keywords": value.get("keywords", []),
            "weight": value.get("weight", 0.0)
        }

    def __init__(self, term_mapping, exclusions=None, config=None):
        """
        初始化校正器

        Args:
            term_mapping: 詞庫字典,結構支援:
                - 簡化版: {"標準詞": ["別名1", "別名2"]}
                - 完整版: {"標準詞": {
                    "aliases": ["別名1", "別名2"],
                    "keywords": ["關鍵字1", "關鍵字2"],
                    "weight": 0.3
                }}
            exclusions: 豁免清單 (list),這些詞不會被修正
            config: PhoneticConfig 實例,若為 None 則使用預設配置
        """
        self.use_canonical = True  # 固定為 True,一律修正為標準詞
        self.config = config or PhoneticConfig
        self.utils = PhoneticUtils(config=self.config)

        # 將豁免詞轉為集合,提升查詢速度
        self.exclusions = set(exclusions) if exclusions else set()

        # 建構搜尋索引
        self.search_index = self._build_search_index(term_mapping)

    def _build_search_index(self, term_mapping):
        """
        建構搜尋索引

        遍歷傳入的 term_mapping,預先計算所有熱詞的拼音與特徵

        Args:
            term_mapping: 詞庫字典

        Returns:
            list: 搜尋索引列表,依詞長由大到小排序
        """
        search_index = []

        for canonical, data in term_mapping.items():
            # 解析詞庫資料
            aliases, keywords, weight = self._parse_term_data(data)

            # 將標準詞(canonical)與別名(aliases)合併為目標集合
            targets = set(aliases) | {canonical}

            # 為每個目標詞建立索引項目
            for term in targets:
                index_item = self._create_index_item(
                    term, canonical, keywords, weight
                )
                search_index.append(index_item)

        # 依照詞長由大到小排序 (Greedy Match)
        # 確保長詞優先被比對 (例如 "台北車站" 優先於 "北車")
        search_index.sort(key=lambda x: x["len"], reverse=True)

        return search_index

    def _parse_term_data(self, data):
        """
        解析詞庫資料,判斷是簡化版(list)還是完整版(dict)

        Args:
            data: 詞庫資料 (list 或 dict)

        Returns:
            tuple: (aliases, keywords, weight)
        """
        if isinstance(data, list):
            # 簡化版
            aliases = data
            keywords = []
            weight = 0.0
        else:
            # 完整版
            aliases = data.get("aliases", [])
            keywords = data.get("keywords", [])
            weight = data.get("weight", 0.0)

        return aliases, keywords, weight

    def _create_index_item(self, term, canonical, keywords, weight):
        """
        為單一詞彙建立索引項目,預先計算拼音與特徵

        Args:
            term: 目標詞 (別名或標準詞)
            canonical: 標準詞
            keywords: 上下文關鍵字列表
            weight: 權重分數

        Returns:
            dict: 索引項目
        """
        # 預先計算目標詞的拼音 (不含聲調)
        pinyin_str = self.utils.get_pinyin_string(term)

        # 預先計算聲母 (用於短詞嚴格檢查)
        initials_list = pypinyin.lazy_pinyin(
            term, style=pypinyin.INITIALS, strict=False
        )

        return {
            "term": term,  # 實際詞彙 (如: Pyton)
            "canonical": canonical,  # 標準詞 (如: Python)
            "keywords": [k.lower() for k in keywords],  # 上下文關鍵字
            "weight": weight,  # 優先權重 (越高分越容易被選中)
            "pinyin_str": pinyin_str,  # 拼音字串
            "initials": initials_list,  # 聲母列表
            "len": len(term),  # 字數長度
            "is_mixed": self.utils.contains_english(term),  # 是否混有英文
        }

    def _get_dynamic_threshold(self, word_len, is_mixed=False):
        """
        動態決定容錯率 (Threshold)

        字數越短,容錯率越低 (必須更像);混有英文或長詞則容許較高誤差

        Args:
            word_len: 詞彙長度
            is_mixed: 是否混有英文

        Returns:
            float: 容錯率閾值
        """
        if is_mixed:
            return 0.45  # 英文混用通常容錯較高
        if word_len <= 2:
            return 0.20  # 2字詞必須非常準確
        elif word_len == 3:
            return 0.30
        else:
            return 0.40  # 4字以上寬容度最高

    def _check_context_bonus(
        self, full_text, start_idx, end_idx, keywords, window_size=10
    ):
        """
        上下文加分檢查 (增強版:計算最近關鍵字距離)

        檢查目標詞前後 window_size 範圍內是否出現指定的 keywords,
        並返回最近關鍵字的距離 (距離越近,加分越多)

        Args:
            full_text: 完整文本
            start_idx: 目標詞起始索引
            end_idx: 目標詞結束索引
            keywords: 關鍵字列表
            window_size: 視窗大小 (預設 10 字)

        Returns:
            tuple: (是否命中, 最近距離)
                - 是否命中: bool
                - 最近距離: int (0=緊鄰, window_size=最遠, None=未命中)
        """
        if not keywords:
            return False, None

        # 計算滑動視窗範圍,防止超出字串邊界
        ctx_start = max(0, start_idx - window_size)
        ctx_end = min(len(full_text), end_idx + window_size)

        context_text = full_text[ctx_start:ctx_end]
        min_distance = None

        for kw in keywords:
            kw_idx = context_text.find(kw)
            if kw_idx != -1:
                # 計算關鍵字到目標詞的實際距離
                kw_abs_pos = ctx_start + kw_idx

                # 距離 = 關鍵字與目標詞之間的字符數
                if kw_abs_pos < start_idx:
                    # 關鍵字在目標詞前面
                    distance = start_idx - (kw_abs_pos + len(kw))
                elif kw_abs_pos >= end_idx:
                    # 關鍵字在目標詞後面
                    distance = kw_abs_pos - end_idx
                else:
                    # 關鍵字與目標詞重疊 (緊鄰)
                    distance = 0

                # 記錄最小距離
                if min_distance is None or distance < min_distance:
                    min_distance = distance

        if min_distance is not None:
            return True, min_distance
        return False, None

    def _build_protection_mask(self, asr_text):
        """
        建立全域保護遮罩

        找出所有 "豁免詞" 在原句中的位置,將這些索引標記為 Protected
        目的: 防止長詞豁免中的短詞被誤修 (如 "什麼是" 豁免,防止內部的 "麼是" 被修成 "默示")

        Args:
            asr_text: ASR 輸出文本

        Returns:
            set: 受保護的索引集合
        """
        protected_indices = set()
        if self.exclusions:
            for exclusion_term in self.exclusions:
                # 使用 re.escape 避免特殊符號導致 regex 錯誤
                for match in re.finditer(re.escape(exclusion_term), asr_text):
                    for idx in range(match.start(), match.end()):
                        protected_indices.add(idx)
        return protected_indices

    def _is_segment_protected(self, start_idx, word_len, protected_indices):
        """
        檢查當前片段是否位於保護區

        如果當前視窗內的任何一個字位於保護區,整段跳過

        Args:
            start_idx: 片段起始索引
            word_len: 片段長度
            protected_indices: 受保護的索引集合

        Returns:
            bool: 是否位於保護區
        """
        for idx in range(start_idx, start_idx + word_len):
            if idx in protected_indices:
                return True
        return False

    def _is_valid_segment(self, segment):
        """
        檢查片段是否有效

        如果片段含有標點符號或非中英數字符,視為無效片段
        這能避免吃到 "。C語" 這種跨標點的錯誤

        Args:
            segment: 文本片段

        Returns:
            bool: 是否有效片段
        """
        if re.search(r"[^a-zA-Z0-9\u4e00-\u9fa5]", segment):
            return False
        return True

    def _calculate_pinyin_similarity(self, segment, target_pinyin_str):
        """
        計算片段與目標詞的拼音相似度

        增強版: 支援韻母模糊和特例音節匹配

        Args:
            segment: 文本片段
            target_pinyin_str: 目標拼音字串

        Returns:
            tuple: (window_pinyin_str, error_ratio, is_fuzzy_match)
        """
        # 局部拼音計算 (Local Pinyin Calculation)
        # 針對當前視窗內的文字即時運算拼音,確保拼音與文字索引 100% 對齊
        window_pinyin_str = self.utils.get_pinyin_string(segment)
        target_pinyin_lower = target_pinyin_str.lower()

        # 先檢查特例音節 (優先級最高)
        # 注意: 只對「多字詞」應用特例音節,避免影響單字常用詞
        window_pinyin_list = self.utils.get_pinyin(segment)
        if (
            len(segment) >= 2
            and len(window_pinyin_list) <= 2
            and len(target_pinyin_lower) < 10
        ):
            if self.utils.check_special_syllable_match(
                window_pinyin_str, target_pinyin_lower, bidirectional=False
            ):
                return window_pinyin_str, 0.0, True

        # 檢查韻母模糊匹配
        if self.utils.check_finals_fuzzy_match(
            window_pinyin_str, target_pinyin_lower
        ):
            # 韻母模糊匹配,給予低誤差率
            return window_pinyin_str, 0.1, True

        # 計算 Levenshtein 編輯距離比例
        dist = Levenshtein.distance(window_pinyin_str, target_pinyin_lower)
        max_len = max(len(window_pinyin_str), len(target_pinyin_lower))
        error_ratio = dist / max_len if max_len > 0 else 0

        return window_pinyin_str, error_ratio, False

    def _check_initials_match(self, segment, item):
        """
        針對短中文詞進行嚴格聲母比對

        Args:
            segment: 文本片段
            item: 索引項目

        Returns:
            bool: 聲母是否匹配
        """
        word_len = item["len"]
        if word_len <= 3 and not item["is_mixed"]:
            window_initials = pypinyin.lazy_pinyin(
                segment, style=pypinyin.INITIALS, strict=False
            )
            if not self.utils.is_fuzzy_initial_match(
                window_initials, item["initials"]
            ):
                return False
        return True

    def _calculate_final_score(self, error_ratio, item, has_context, context_distance=None):
        """
        計算最終分數 (增強版:考慮關鍵字距離)

        分數越低優先級越高

        Args:
            error_ratio: 錯誤率
            item: 索引項目
            has_context: 是否命中上下文
            context_distance: 最近關鍵字距離 (0-10,越小越近)

        Returns:
            float: 最終分數
        """
        final_score = error_ratio

        # 權重應用: 分數越低優先級越高
        final_score -= item["weight"]

        if has_context and context_distance is not None:
            # 距離加權公式:
            # distance = 0 (緊鄰) → bonus = 0.8
            # distance = 5 (中等) → bonus = 0.5
            # distance = 10 (最遠) → bonus = 0.2
            distance_factor = 1.0 - (context_distance / 10.0 * 0.6)
            context_bonus = 0.8 * distance_factor
            final_score -= context_bonus

        return final_score

    def _create_candidate(
        self, start_idx, word_len, original, item, score, has_context
    ):
        """
        建立候選修正項目

        Args:
            start_idx: 起始索引
            word_len: 詞長
            original: 原始文本
            item: 索引項目
            score: 分數
            has_context: 是否命中上下文

        Returns:
            dict: 候選項目
        """
        replacement = item["canonical"] if self.use_canonical else item["term"]

        return {
            "start": start_idx,
            "end": start_idx + word_len,
            "original": original,
            "replacement": replacement,
            "score": score,
            "has_context": has_context,
        }

    def _process_exact_match(self, asr_text, start_idx, original_segment, item):
        """
        處理絕對匹配 (Exact Match)

        如果字串完全等於 term,直接命中,不需要算拼音距離

        Args:
            asr_text: ASR 輸出文本
            start_idx: 起始索引
            original_segment: 原始片段
            item: 索引項目

        Returns:
            dict or None: 候選項目或 None
        """
        if original_segment != item["term"]:
            return None

        # 檢查上下文加分 (增強版:獲取距離)
        has_context, context_distance = self._check_context_bonus(
            asr_text, start_idx, start_idx + item["len"], item["keywords"]
        )

        # 計算最終分數 (使用距離加權)
        final_score = self._calculate_final_score(
            0.0, item, has_context, context_distance
        )

        return self._create_candidate(
            start_idx, item["len"], original_segment, item, final_score, has_context
        )

    def _process_fuzzy_match(self, asr_text, start_idx, original_segment, item):
        """
        處理模糊匹配 (Fuzzy Match)

        使用拼音相似度、聲母檢查、韻母模糊、特例音節來判斷是否匹配

        Args:
            asr_text: ASR 輸出文本
            start_idx: 起始索引
            original_segment: 原始片段
            item: 索引項目

        Returns:
            dict or None: 候選項目或 None
        """
        word_len = item["len"]
        threshold = self._get_dynamic_threshold(word_len, item["is_mixed"])

        # 計算拼音相似度 (增強版,支援韻母模糊和特例音節)
        window_pinyin_str, error_ratio, is_fuzzy_match = (
            self._calculate_pinyin_similarity(original_segment, item["pinyin_str"])
        )

        # 如果是韻母模糊或特例音節匹配,放寬門檻
        if is_fuzzy_match:
            threshold = max(threshold, 0.15)

        if error_ratio > threshold:
            return None

        # 聲母檢查: 針對短中文詞進行嚴格聲母比對
        if not self._check_initials_match(original_segment, item):
            return None

        # 檢查上下文 (增強版:獲取距離)
        has_context, context_distance = self._check_context_bonus(
            asr_text, start_idx, start_idx + word_len, item["keywords"]
        )

        # 計算最終分數 (使用距離加權)
        final_score = self._calculate_final_score(
            error_ratio, item, has_context, context_distance
        )

        replacement = item["canonical"] if self.use_canonical else item["term"]

        # 只有當內容有改變時才加入候選
        if original_segment == replacement:
            return None

        return self._create_candidate(
            start_idx, word_len, original_segment, item, final_score, has_context
        )

    def _find_candidates(self, asr_text, protected_indices):
        """
        遍歷搜尋索引,找出所有候選修正項目

        Args:
            asr_text: ASR 輸出文本
            protected_indices: 受保護的索引集合

        Returns:
            list: 候選項目列表
        """
        text_len = len(asr_text)
        candidates = []

        for item in self.search_index:
            word_len = item["len"]
            if word_len > text_len:
                continue

            # 滑動視窗掃描
            for i in range(text_len - word_len + 1):

                # 檢查保護區遮罩
                if self._is_segment_protected(i, word_len, protected_indices):
                    continue

                original_segment = asr_text[i : i + word_len]

                # 垃圾字元過濾
                if not self._is_valid_segment(original_segment):
                    continue

                # 再次確認豁免清單 (雙重保險)
                if original_segment in self.exclusions:
                    continue

                # 情境 A: 絕對匹配 (Exact Match)
                candidate = self._process_exact_match(
                    asr_text, i, original_segment, item
                )
                if candidate:
                    candidates.append(candidate)
                    continue

                # 情境 B: 模糊匹配 (Fuzzy Match)
                candidate = self._process_fuzzy_match(
                    asr_text, i, original_segment, item
                )
                if candidate:
                    candidates.append(candidate)

        return candidates

    def _resolve_conflicts(self, candidates):
        """
        衝突解決 (Conflict Resolution)

        依照分數排序,選擇不重疊的最佳候選

        Args:
            candidates: 候選項目列表

        Returns:
            list: 最終候選項目列表
        """
        # 依照分數排序 (越低分越好)
        candidates.sort(key=lambda x: x["score"])

        final_candidates = []
        for cand in candidates:
            is_conflict = False
            # 檢查是否與已接受的候選詞位置重疊
            for accepted in final_candidates:
                # 判斷區間重疊邏輯: max(Start1, Start2) < min(End1, End2)
                if max(cand["start"], accepted["start"]) < min(
                    cand["end"], accepted["end"]
                ):
                    is_conflict = True
                    break

            # 若無衝突則接受此修正
            if not is_conflict:
                final_candidates.append(cand)

        return final_candidates

    def _apply_replacements(self, asr_text, final_candidates):
        """
        替換文字

        從後面對前面進行替換 (Reverse),避免 index 跑掉

        Args:
            asr_text: ASR 輸出文本
            final_candidates: 最終候選項目列表

        Returns:
            str: 修正後的文本
        """
        # 從後面對前面進行替換
        final_candidates.sort(key=lambda x: x["start"], reverse=True)
        final_text_list = list(asr_text)

        for cand in final_candidates:
            if cand["original"] != cand["replacement"]:
                tag = "[上下文命中]" if cand.get("has_context") else "[發音修正]"
                print(
                    f"{tag} '{cand['original']}' -> '{cand['replacement']}' (Score: {cand['score']:.3f})"
                )
            final_text_list[cand["start"] : cand["end"]] = list(
                cand["replacement"]
            )

        return "".join(final_text_list)

    def correct(self, asr_text):
        """
        執行文字校正

        Args:
            asr_text: ASR 輸出的文本

        Returns:
            str: 校正後的文本

        Example:
            >>> corrector = ChineseTextCorrector({
            ...     "台北車站": ["北車", "臺北車站"]
            ... })
            >>> corrector.correct("我在北車等你")
            '[發音修正] '北車' -> '台北車站' (Score: -0.000)'
            '我在台北車站等你'
        """
        # 步驟 1: 建立全域保護遮罩
        protected_indices = self._build_protection_mask(asr_text)

        # 步驟 2: 遍歷搜尋索引,找出所有候選修正項目
        candidates = self._find_candidates(asr_text, protected_indices)

        # 步驟 3: 衝突解決
        final_candidates = self._resolve_conflicts(candidates)

        # 步驟 4: 替換文字
        return self._apply_replacements(asr_text, final_candidates)

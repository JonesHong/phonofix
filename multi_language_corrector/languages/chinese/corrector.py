"""
中文修正器模組

實作針對中文語音識別 (ASR) 錯誤的修正邏輯。
核心演算法基於拼音相似度 (Pinyin Similarity) 與編輯距離 (Levenshtein Distance)。

效能優化:
- 使用 functools.lru_cache 快取拼音計算結果
- 避免對相同字串重複呼叫 pypinyin (這是主要的效能瓶頸)
"""

import pypinyin
import Levenshtein
import re
from functools import lru_cache
from typing import Generator, Optional, Callable, Dict, List, Any, TYPE_CHECKING, Union
from .config import ChinesePhoneticConfig
from .utils import ChinesePhoneticUtils
from .fuzzy_generator import ChineseFuzzyGenerator

if TYPE_CHECKING:
    from multi_language_corrector.engine.chinese_engine import ChineseEngine


# =============================================================================
# 拼音快取 (Performance Critical)
# =============================================================================
# pypinyin 呼叫是效能瓶頸，使用 lru_cache 可達到 10x+ 加速

@lru_cache(maxsize=50000)
def cached_get_pinyin_string(text: str) -> str:
    """快取版拼音字串計算"""
    pinyin_list = pypinyin.lazy_pinyin(text, style=pypinyin.NORMAL)
    return "".join(pinyin_list)


@lru_cache(maxsize=50000)
def cached_get_initials(text: str) -> tuple:
    """快取版聲母列表計算"""
    return tuple(pypinyin.lazy_pinyin(text, style=pypinyin.INITIALS, strict=False))


class ChineseCorrector:
    """
    中文修正器

    功能:
    - 載入專有名詞庫並建立搜尋索引
    - 針對輸入文本進行滑動視窗掃描
    - 結合拼音模糊比對與上下文關鍵字驗證
    - 修正 ASR 產生的同音異字或近音字錯誤
    """
    
    # =========================================================================
    # 工廠方法
    # =========================================================================
    
    @classmethod
    def _from_engine(
        cls,
        engine: "ChineseEngine",
        term_mapping: Dict[str, Dict],
        exclusions: Optional[set] = None,
    ) -> "ChineseCorrector":
        """
        由 ChineseEngine 調用的內部工廠方法
        
        此方法使用 Engine 提供的共享元件，避免重複初始化。
        
        Args:
            engine: ChineseEngine 實例
            term_mapping: 正規化的專有名詞映射
            exclusions: 排除詞集合
            
        Returns:
            ChineseCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance.config = engine.config
        instance.utils = engine.utils
        instance.use_canonical = True  # V2 固定為 True
        instance.exclusions = exclusions or set()
        instance.search_index = instance._build_search_index(term_mapping)
        
        return instance

    @staticmethod
    def _filter_aliases_by_pinyin(aliases, utils):
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
        utils = ChinesePhoneticUtils(config=config)
        generator = ChineseFuzzyGenerator(config=config)

        if isinstance(term_dict, list):
            term_dict = {term: {} for term in term_dict}

        normalized_dict = {}
        for term, value in term_dict.items():
            normalized_value = cls._normalize_term_value(
                term, value, generator, utils
            )
            if normalized_value:
                normalized_dict[term] = normalized_value

        return cls(
            term_mapping=normalized_dict,
            exclusions=exclusions,
            config=config
        )

    @classmethod
    def _normalize_term_value(cls, term, value, generator, utils):
        if isinstance(value, list):
            value = {"aliases": value}
        elif isinstance(value, dict):
            if "aliases" not in value:
                value["aliases"] = []
        else:
            return None

        if not value["aliases"]:
            fuzzy_result = generator.generate_variants(term)
            # Note: generate_variants returns a list of variants including the term itself.
            # The original code used generate_fuzzy_dictionary which returned a dict.
            # We need to adapt here.
            
            # If fuzzy_result is a list:
            auto_aliases = [alias for alias in fuzzy_result if alias != term]
            auto_aliases = cls._filter_aliases_by_pinyin(auto_aliases, utils)
            value["aliases"] = auto_aliases
        else:
            value["aliases"] = cls._filter_aliases_by_pinyin(
                value["aliases"], utils
            )

        return {
            "aliases": value["aliases"],
            "keywords": value.get("keywords", []),
            "exclusions": value.get("exclusions", []),
            "weight": value.get("weight", 0.0)
        }

    def __init__(self, term_mapping, exclusions=None, config=None):
        """
        初始化修正器

        Args:
            term_mapping: 專有名詞映射表
            exclusions: 排除詞列表 (這些詞不會被修正)
            config: ChinesePhoneticConfig 實例
        """
        self._engine = None  # 舊版 API 不使用 Engine
        self.use_canonical = True  # V2 固定為 True，一律修正為標準詞
        self.config = config or ChinesePhoneticConfig
        self.utils = ChinesePhoneticUtils(config=self.config)
        self.exclusions = set(exclusions) if exclusions else set()
        self.search_index = self._build_search_index(term_mapping)

    def _build_search_index(self, term_mapping):
        """
        建立搜尋索引

        將標準化的專有名詞庫轉換為便於搜尋的列表結構。
        每個索引項目包含:
        - 原始詞彙 (term)
        - 標準詞彙 (canonical)
        - 關鍵字 (keywords)
        - 權重 (weight)
        - 拼音字串 (pinyin_str)
        - 聲母列表 (initials)
        - 長度 (len)
        - 是否混合語言 (is_mixed)

        索引按詞長降序排列，以優先匹配長詞。
        """
        search_index = []
        for canonical, data in term_mapping.items():
            aliases, keywords, exclusions, weight = self._parse_term_data(data)
            targets = set(aliases) | {canonical}
            for term in targets:
                index_item = self._create_index_item(
                    term, canonical, keywords, exclusions, weight
                )
                search_index.append(index_item)
        search_index.sort(key=lambda x: x["len"], reverse=True)
        return search_index

    def _parse_term_data(self, data):
        """解析專有名詞資料結構，提取別名、關鍵字、排除關鍵字與權重"""
        if isinstance(data, list):
            aliases = data
            keywords = []
            exclusions = []
            weight = 0.0
        else:
            aliases = data.get("aliases", [])
            keywords = data.get("keywords", [])
            exclusions = data.get("exclusions", [])
            weight = data.get("weight", 0.0)
        return aliases, keywords, exclusions, weight

    def _create_index_item(self, term, canonical, keywords, exclusions, weight):
        """建立單個索引項目，預先計算拼音與聲母特徵"""
        # 使用快取版本的拼音計算
        pinyin_str = cached_get_pinyin_string(term)
        initials_list = list(cached_get_initials(term))
        return {
            "term": term,
            "canonical": canonical,
            "keywords": [k.lower() for k in keywords],
            "exclusions": [e.lower() for e in exclusions],
            "weight": weight,
            "pinyin_str": pinyin_str,
            "initials": initials_list,
            "len": len(term),
            "is_mixed": self.utils.contains_english(term),
        }

    def _get_dynamic_threshold(self, word_len, is_mixed=False):
        """
        根據詞長動態計算容錯率閾值

        策略:
        - 混合語言詞彙 (如 "C語言"): 容錯率較高 (0.45)
        - 短詞 (<=2): 容錯率低 (0.20)，避免誤匹配
        - 中詞 (3): 容錯率中 (0.30)
        - 長詞 (>3): 容錯率高 (0.40)
        """
        if is_mixed:
            return 0.45
        if word_len <= 2:
            return 0.20
        elif word_len == 3:
            return 0.30
        else:
            return 0.40

    def _check_context_bonus(self, full_text, start_idx, end_idx, keywords, window_size=10):
        """
        檢查上下文關鍵字加分

        若在修正目標附近的視窗內發現相關關鍵字，則給予額外加分 (降低距離分數)。
        這有助於區分同音異義詞。

        Args:
            full_text: 完整文本
            start_idx: 目標詞起始索引
            end_idx: 目標詞結束索引
            keywords: 關鍵字列表
            window_size: 上下文視窗大小 (預設 10 字符)

        Returns:
            (bool, float): (是否命中關鍵字, 關鍵字距離)
        """
        if not keywords:
            return False, None
        ctx_start = max(0, start_idx - window_size)
        ctx_end = min(len(full_text), end_idx + window_size)
        context_text = full_text[ctx_start:ctx_end]
        min_distance = None
        for kw in keywords:
            kw_idx = context_text.find(kw)
            if kw_idx != -1:
                kw_abs_pos = ctx_start + kw_idx
                if kw_abs_pos < start_idx:
                    distance = start_idx - (kw_abs_pos + len(kw))
                elif kw_abs_pos >= end_idx:
                    distance = kw_abs_pos - end_idx
                else:
                    distance = 0
                if min_distance is None or distance < min_distance:
                    min_distance = distance
        if min_distance is not None:
            return True, min_distance
        return False, None

    def _build_protection_mask(self, asr_text):
        """建立保護遮罩，標記不應被修正的區域 (如排除詞)"""
        protected_indices = set()
        if self.exclusions:
            for exclusion_term in self.exclusions:
                for match in re.finditer(re.escape(exclusion_term), asr_text):
                    for idx in range(match.start(), match.end()):
                        protected_indices.add(idx)
        return protected_indices

    def _is_segment_protected(self, start_idx, word_len, protected_indices):
        """檢查特定片段是否包含受保護的索引"""
        for idx in range(start_idx, start_idx + word_len):
            if idx in protected_indices:
                return True
        return False

    def _is_valid_segment(self, segment):
        """檢查片段是否包含有效字符 (中文、英文、數字)"""
        if re.search(r"[^a-zA-Z0-9\u4e00-\u9fa5]", segment):
            return False
        return True

    def _has_exclusion_keyword(self, full_text, exclusions):
        """
        檢查是否命中排除關鍵字
        
        策略:
        - 如果沒有定義 exclusions，則不排除
        - 如果有定義 exclusions，則文本中包含任一排除關鍵字就排除
        
        Args:
            full_text: 完整文本
            exclusions: 排除關鍵字列表
            
        Returns:
            bool: 如果應該排除則返回 True
        """
        if not exclusions:
            return False
        
        full_text_lower = full_text.lower()
        for excl in exclusions:
            if excl.lower() in full_text_lower:
                return True
        return False

    def _has_required_keyword(self, full_text, keywords):
        """
        檢查是否滿足關鍵字必要條件
        
        策略:
        - 如果沒有定義 keywords，則無條件通過
        - 如果有定義 keywords，則文本中必須包含至少一個關鍵字
        
        Args:
            full_text: 完整文本
            keywords: 關鍵字列表
            
        Returns:
            bool: 如果滿足條件則返回 True
        """
        if not keywords:
            return True
        
        full_text_lower = full_text.lower()
        for kw in keywords:
            if kw.lower() in full_text_lower:
                return True
        return False

    def _calculate_pinyin_similarity(self, segment, target_pinyin_str):
        """
        計算拼音相似度

        結合多種策略:
        1. 特殊音節映射 (如 hua <-> fa)
        2. 韻母模糊匹配 (如 in <-> ing)
        3. Levenshtein 編輯距離

        Returns:
            (str, float, bool): (視窗拼音字串, 錯誤率, 是否為模糊匹配)
        """
        # 使用快取版本的拼音計算
        window_pinyin_str = cached_get_pinyin_string(segment)
        target_pinyin_lower = target_pinyin_str.lower()
        
        # 快速路徑：完全匹配
        if window_pinyin_str == target_pinyin_lower:
            return window_pinyin_str, 0.0, True
        
        # 特殊音節匹配
        if len(segment) >= 2 and len(target_pinyin_lower) < 10:
            if self.utils.check_special_syllable_match(
                window_pinyin_str, target_pinyin_lower, bidirectional=False
            ):
                return window_pinyin_str, 0.0, True
        
        # 韻母模糊匹配
        if self.utils.check_finals_fuzzy_match(
            window_pinyin_str, target_pinyin_lower
        ):
            return window_pinyin_str, 0.1, True
        
        # Levenshtein 編輯距離
        dist = Levenshtein.distance(window_pinyin_str, target_pinyin_lower)
        max_len = max(len(window_pinyin_str), len(target_pinyin_lower))
        error_ratio = dist / max_len if max_len > 0 else 0
        return window_pinyin_str, error_ratio, False

    def _check_initials_match(self, segment, item):
        """
        檢查聲母是否匹配

        策略:
        - 短詞 (<=3): 所有聲母都必須模糊匹配
        - 長詞 (>3): 至少第一個聲母必須模糊匹配，避免 "在北車用" 被誤匹配到 "台北車站"
        """
        word_len = item["len"]
        if item["is_mixed"]:
            return True  # 混合語言詞跳過聲母檢查
        
        # 使用快取版本的聲母計算
        window_initials = list(cached_get_initials(segment))
        
        if word_len <= 3:
            # 短詞: 所有聲母都必須匹配
            if not self.utils.is_fuzzy_initial_match(
                window_initials, item["initials"]
            ):
                return False
        else:
            # 長詞: 至少第一個聲母必須匹配
            # 這可以避免 "在北車用" (z-b-ch-y) 被誤匹配到 "台北車站" (t-b-ch-zh)
            if window_initials and item["initials"]:
                first_window = window_initials[0]
                first_target = item["initials"][0]
                if first_window != first_target:
                    # 檢查是否屬於同一模糊音群組
                    group1 = self.config.FUZZY_INITIALS_MAP.get(first_window)
                    group2 = self.config.FUZZY_INITIALS_MAP.get(first_target)
                    if not (group1 and group2 and group1 == group2):
                        return False
        return True

    def _calculate_final_score(self, error_ratio, item, has_context, context_distance=None):
        """
        計算最終分數 (越低越好)

        公式: 錯誤率 - 詞彙權重 - 上下文加分
        """
        final_score = error_ratio
        final_score -= item["weight"]
        if has_context and context_distance is not None:
            distance_factor = 1.0 - (context_distance / 10.0 * 0.6)
            context_bonus = 0.8 * distance_factor
            final_score -= context_bonus
        return final_score

    def _create_candidate(self, start_idx, word_len, original, item, score, has_context):
        """建立候選修正物件"""
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
        """處理完全匹配的情況 (別名精確匹配)"""
        if original_segment != item["term"]:
            return None
        
        # 檢查關鍵字必要條件：如果有定義 keywords 但沒命中，則跳過
        if not self._has_required_keyword(asr_text, item["keywords"]):
            return None
        
        # 檢查排除關鍵字：如果有定義 exclusions 且命中，則跳過
        if self._has_exclusion_keyword(asr_text, item["exclusions"]):
            return None
        
        has_context, context_distance = self._check_context_bonus(
            asr_text, start_idx, start_idx + item["len"], item["keywords"]
        )
        final_score = self._calculate_final_score(
            0.0, item, has_context, context_distance
        )
        return self._create_candidate(
            start_idx, item["len"], original_segment, item, final_score, has_context
        )

    def _process_fuzzy_match(self, asr_text, start_idx, original_segment, item):
        """
        處理模糊匹配

        核心邏輯:
        1. 檢查關鍵字必要條件 (如果有定義 keywords)
        2. 檢查排除關鍵字 (如果有定義 exclusions)
        3. 計算拼音相似度與錯誤率
        4. 檢查是否超過容錯閾值
        5. 檢查聲母是否匹配 (針對短詞)
        6. 計算上下文加分
        7. 計算最終分數
        """
        word_len = item["len"]
        
        # 檢查關鍵字必要條件：如果有定義 keywords 但沒命中，則跳過
        if not self._has_required_keyword(asr_text, item["keywords"]):
            return None
        
        # 檢查排除關鍵字：如果有定義 exclusions 且命中，則跳過
        if self._has_exclusion_keyword(asr_text, item["exclusions"]):
            return None
        
        threshold = self._get_dynamic_threshold(word_len, item["is_mixed"])
        window_pinyin_str, error_ratio, is_fuzzy_match = (
            self._calculate_pinyin_similarity(original_segment, item["pinyin_str"])
        )
        if is_fuzzy_match:
            threshold = max(threshold, 0.15)
        if error_ratio > threshold:
            return None
        if not self._check_initials_match(original_segment, item):
            return None
        has_context, context_distance = self._check_context_bonus(
            asr_text, start_idx, start_idx + word_len, item["keywords"]
        )
        final_score = self._calculate_final_score(
            error_ratio, item, has_context, context_distance
        )
        replacement = item["canonical"] if self.use_canonical else item["term"]
        if original_segment == replacement:
            return None
        return self._create_candidate(
            start_idx, word_len, original_segment, item, final_score, has_context
        )

    def _find_candidates(self, asr_text, protected_indices):
        """
        搜尋所有可能的修正候選

        遍歷所有索引項目，在文本中進行滑動視窗比對。
        """
        text_len = len(asr_text)
        candidates = []
        for item in self.search_index:
            word_len = item["len"]
            if word_len > text_len:
                continue
            for i in range(text_len - word_len + 1):
                if self._is_segment_protected(i, word_len, protected_indices):
                    continue
                original_segment = asr_text[i : i + word_len]
                if not self._is_valid_segment(original_segment):
                    continue
                if original_segment in self.exclusions:
                    continue
                candidate = self._process_exact_match(
                    asr_text, i, original_segment, item
                )
                if candidate:
                    candidates.append(candidate)
                    continue
                candidate = self._process_fuzzy_match(
                    asr_text, i, original_segment, item
                )
                if candidate:
                    candidates.append(candidate)
        return candidates

    def _resolve_conflicts(self, candidates):
        """
        解決候選衝突

        當多個候選修正重疊時，選擇分數最低 (最佳) 的候選。
        """
        candidates.sort(key=lambda x: x["score"])
        final_candidates = []
        for cand in candidates:
            is_conflict = False
            for accepted in final_candidates:
                if max(cand["start"], accepted["start"]) < min(
                    cand["end"], accepted["end"]
                ):
                    is_conflict = True
                    break
            if not is_conflict:
                final_candidates.append(cand)
        return final_candidates

    def _apply_replacements(self, asr_text, final_candidates, silent=False):
        """應用修正並輸出日誌"""
        final_candidates.sort(key=lambda x: x["start"], reverse=True)
        final_text_list = list(asr_text)
        for cand in final_candidates:
            if cand["original"] != cand["replacement"]:
                if not silent:
                    tag = "[上下文命中]" if cand.get("has_context") else "[發音修正]"
                    print(
                        f"{tag} '{cand['original']}' -> '{cand['replacement']}' (Score: {cand['score']:.3f})"
                    )
            final_text_list[cand["start"] : cand["end"]] = list(
                cand["replacement"]
            )
        return "".join(final_text_list)

    def correct(self, asr_text: str, silent: bool = False) -> str:
        """
        執行修正流程

        Args:
            asr_text: 輸入的 ASR 文本
            silent: 是否靜默模式 (不輸出修正日誌)

        Returns:
            修正後的文本
        """
        protected_indices = self._build_protection_mask(asr_text)
        candidates = self._find_candidates(asr_text, protected_indices)
        final_candidates = self._resolve_conflicts(candidates)
        return self._apply_replacements(asr_text, final_candidates, silent=silent)

    def correct_streaming(
        self,
        asr_text: str,
        on_correction: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Generator[Dict[str, Any], None, str]:
        """
        串流式修正 - 邊處理邊回報進度

        這個方法會在找到每個有效修正時立即通知，
        讓使用者可以看到即時進度，減少等待感。

        Args:
            asr_text: 輸入的 ASR 文本
            on_correction: 找到有效修正時的回調函數

        Yields:
            Dict: 每個有效的修正候選 (在衝突解決後)
        
        Returns:
            str: 最終修正後的文本 (透過 generator.send() 無法取得，
                 需要使用 return value 或最後一個 yield)

        Usage:
            # 方法 1: 使用 callback
            def on_fix(correction):
                print(f"找到修正: {correction['original']} -> {correction['replacement']}")
            
            result = None
            for correction in corrector.correct_streaming(text, on_correction=on_fix):
                result = correction  # 最後一個是結果字串
            
            # 方法 2: 收集所有修正
            corrections = list(corrector.correct_streaming(text))
            final_text = corrections[-1] if corrections else text
        """
        protected_indices = self._build_protection_mask(asr_text)
        candidates = self._find_candidates(asr_text, protected_indices)
        final_candidates = self._resolve_conflicts(candidates)
        
        # 按位置排序，從前到後報告
        final_candidates_sorted = sorted(final_candidates, key=lambda x: x["start"])
        
        for cand in final_candidates_sorted:
            if cand["original"] != cand["replacement"]:
                if on_correction:
                    on_correction(cand)
                yield cand
        
        # 最後 yield 結果字串
        result = self._apply_replacements(asr_text, final_candidates, silent=True)
        yield result

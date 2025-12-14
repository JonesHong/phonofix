"""
中文修正器模組

實作針對中文拼寫錯誤的修正邏輯（常見來源包含 ASR/LLM/手動輸入）。
核心演算法基於拼音相似度 (Pinyin Similarity) 與編輯距離 (Levenshtein Distance)。

使用方式:
    from phonofix import ChineseEngine

    engine = ChineseEngine()
    corrector = engine.create_corrector({'台北車站': ['北車', '台北站']})
    result = corrector.correct('我在北車等你')

注意：此模組使用延遲導入 (Lazy Import) 機制，
僅在實際使用中文功能時才會載入 pypinyin。
"""

import logging
import re
import uuid
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, Optional

import Levenshtein

from phonofix.core.events import CorrectionEventHandler
from phonofix.core.protocols.corrector import ContextAwareCorrectorProtocol
from phonofix.utils.aho_corasick import AhoCorasick
from phonofix.utils.logger import TimingContext, get_logger

from .utils import _get_pypinyin

if TYPE_CHECKING:
    from phonofix.languages.chinese.engine import ChineseEngine


# =============================================================================
# 拼音快取 (Performance Critical)
# =============================================================================
# pypinyin 呼叫是效能瓶頸，使用 lru_cache 可達到 10x+ 加速

@lru_cache(maxsize=50000)
def cached_get_pinyin_string(text: str) -> str:
    """快取版拼音字串計算"""
    pypinyin = _get_pypinyin()
    pinyin_list = pypinyin.lazy_pinyin(text, style=pypinyin.NORMAL)
    return "".join(pinyin_list)

@lru_cache(maxsize=50000)
def cached_get_pinyin_syllables(text: str) -> tuple[str, ...]:
    """快取版拼音音節列表（無聲調）"""
    pypinyin = _get_pypinyin()
    return tuple(pypinyin.lazy_pinyin(text, style=pypinyin.NORMAL))


@lru_cache(maxsize=50000)
def cached_get_initials(text: str) -> tuple:
    """快取版聲母列表計算"""
    pypinyin = _get_pypinyin()
    return tuple(pypinyin.lazy_pinyin(text, style=pypinyin.INITIALS, strict=False))


class ChineseCorrector(ContextAwareCorrectorProtocol):
    """
    中文修正器

    功能:
    - 載入專有名詞庫並建立搜尋索引
    - 針對輸入文本進行滑動視窗掃描
    - 結合拼音模糊比對與上下文關鍵字驗證
    - 修正同音異字或近音字造成的拼寫錯誤

    建立方式:
        使用 ChineseEngine.create_corrector() 建立實例
    """

    @classmethod
    def _from_engine(
        cls,
        engine: "ChineseEngine",
        term_mapping: Dict[str, Dict],
        protected_terms: Optional[set] = None,
        on_event: Optional[CorrectionEventHandler] = None,
    ) -> "ChineseCorrector":
        """
        由 ChineseEngine 調用的內部工廠方法

        此方法使用 Engine 提供的共享元件，避免重複初始化。

        Args:
            engine: ChineseEngine 實例
            term_mapping: 正規化的專有名詞映射
            protected_terms: 受保護的詞彙集合 (這些詞不會被修正)

        Returns:
            ChineseCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance._logger = get_logger("corrector.chinese")
        instance.phonetic = engine.phonetic
        instance.tokenizer = engine.tokenizer
        instance.config = engine.config
        instance.utils = engine.utils
        instance.use_canonical = True
        instance.protected_terms = protected_terms or set()
        instance._on_event = on_event
        instance._exact_matcher = None
        instance._exact_items_by_alias = {}
        instance._protected_matcher = None

        if instance.protected_terms:
            matcher: AhoCorasick[str] = AhoCorasick()
            for term in instance.protected_terms:
                if term:
                    matcher.add(term, term)
            matcher.build()
            instance._protected_matcher = matcher
        instance.search_index = instance._build_search_index(term_mapping)
        instance._build_exact_matcher()
        instance._build_fuzzy_buckets()

        return instance

    def _build_exact_matcher(self) -> None:
        items_by_alias: dict[str, list[Dict[str, Any]]] = {}
        for item in self.search_index:
            if not item.get("is_alias"):
                continue
            alias = item["term"]
            if not alias:
                continue
            items_by_alias.setdefault(alias, []).append(item)

        if not items_by_alias:
            self._exact_items_by_alias = {}
            self._exact_matcher = None
            return

        matcher: AhoCorasick[str] = AhoCorasick()
        for alias in items_by_alias.keys():
            matcher.add(alias, alias)
        matcher.build()

        self._exact_items_by_alias = items_by_alias
        self._exact_matcher = matcher

    def _build_fuzzy_buckets(self) -> None:
        """
        建立便宜 pruning 用的分桶索引

        分桶維度：
        - 片段長度（len）
        - 首聲母群組（FUZZY_INITIALS_MAP）
        """
        buckets: dict[int, dict[str, list[Dict[str, Any]]]] = {}
        for item in self.search_index:
            word_len = int(item["len"])
            initials = item.get("initials") or []
            first = initials[0] if initials else ""
            group = self.config.FUZZY_INITIALS_MAP.get(first) or first or ""
            buckets.setdefault(word_len, {}).setdefault(group, []).append(item)

        self._fuzzy_buckets = buckets

    def _emit_replacement(self, candidate: Dict[str, Any], *, silent: bool, trace_id: str | None) -> None:
        event = {
            "type": "replacement",
            "engine": getattr(self._engine, "_engine_name", "chinese"),
            "trace_id": trace_id,
            "start": candidate.get("start"),
            "end": candidate.get("end"),
            "original": candidate.get("original"),
            "replacement": candidate.get("replacement"),
            "canonical": candidate.get("canonical"),
            "alias": candidate.get("alias"),
            "score": candidate.get("score"),
            "has_context": candidate.get("has_context", False),
        }

        try:
            if self._on_event is not None:
                self._on_event(event)
        except Exception:
            if not silent:
                self._logger.exception("on_event 回呼執行失敗")

        if not silent and candidate.get("original") != candidate.get("replacement"):
            tag = "上下文命中" if candidate.get("has_context") else "發音修正"
            self._logger.info(
                f"[{tag}] '{candidate.get('original')}' -> '{candidate.get('replacement')}' "
                f"(Score: {candidate.get('score'):.3f})"
            )

    def _emit_pipeline_event(self, event: Dict[str, Any], *, silent: bool) -> None:
        try:
            if self._on_event is not None:
                self._on_event(event)
        except Exception:
            if not silent:
                self._logger.exception("on_event 回呼執行失敗")

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
            aliases, keywords, exclude_when, weight = self._parse_term_data(data)
            targets = set(aliases) | {canonical}
            for term in targets:
                index_item = self._create_index_item(
                    term, canonical, keywords, exclude_when, weight
                )
                search_index.append(index_item)
        search_index.sort(key=lambda x: x["len"], reverse=True)
        return search_index

    def _parse_term_data(self, data):
        """解析專有名詞資料結構，提取別名、關鍵字、上下文排除條件與權重"""
        if isinstance(data, list):
            aliases = data
            keywords = []
            exclude_when = []
            weight = 0.0
        else:
            aliases = data.get("aliases", [])
            keywords = data.get("keywords", [])
            exclude_when = data.get("exclude_when", [])
            weight = data.get("weight", 0.0)
        return aliases, keywords, exclude_when, weight

    def _create_index_item(self, term, canonical, keywords, exclude_when, weight):
        """建立單個索引項目，預先計算拼音與聲母特徵"""
        # 使用快取版本的拼音計算
        pinyin_str = cached_get_pinyin_string(term)
        pinyin_syllables = cached_get_pinyin_syllables(term)
        initials_list = list(cached_get_initials(term))
        is_alias = term != canonical
        return {
            "term": term,
            "canonical": canonical,
            "keywords": [k.lower() for k in keywords],
            "exclude_when": [e.lower() for e in exclude_when],
            "weight": weight,
            "pinyin_str": pinyin_str,
            "pinyin_syllables": pinyin_syllables,
            "initials": initials_list,
            "len": len(term),
            "is_mixed": self.utils.contains_english(term),
            "is_alias": is_alias,
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

    def _build_protection_mask(self, text: str) -> set[int]:
        """建立保護遮罩，標記不應被修正的區域 (受保護的詞彙)"""
        protected_indices: set[int] = set()
        if not self.protected_terms:
            return protected_indices

        if self._protected_matcher is None:
            for protected_term in self.protected_terms:
                if not protected_term:
                    continue
                for match in re.finditer(re.escape(protected_term), text):
                    protected_indices.update(range(match.start(), match.end()))
            return protected_indices

        for start, end, _word, _value in self._protected_matcher.iter_matches(text):
            protected_indices.update(range(start, end))
        return protected_indices

    def _is_segment_protected(self, start_idx, word_len, protected_indices):
        """檢查特定片段是否包含受保護的索引"""
        for idx in range(start_idx, start_idx + word_len):
            if idx in protected_indices:
                return True
        return False

    @staticmethod
    def _is_span_protected(start: int, end: int, protected_indices: set[int]) -> bool:
        for idx in range(start, end):
            if idx in protected_indices:
                return True
        return False

    def _is_valid_segment(self, segment):
        """檢查片段是否包含有效字符 (中文、英文、數字)"""
        if re.search(r"[^a-zA-Z0-9\u4e00-\u9fff]", segment):
            return False
        return True

    def _should_exclude_by_context(self, full_text, exclude_when):
        """
        檢查是否應根據上下文排除修正

        策略:
        - 如果沒有定義 exclude_when，則不排除
        - 如果有定義 exclude_when，則文本中包含任一排除條件就排除

        Args:
            full_text: 完整文本
            exclude_when: 上下文排除條件列表

        Returns:
            bool: 如果應該排除則返回 True
        """
        if not exclude_when:
            return False

        full_text_lower = full_text.lower()
        for condition in exclude_when:
            if condition.lower() in full_text_lower:
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

    def _calculate_pinyin_similarity(
        self,
        segment: str,
        target_pinyin_str: str,
        *,
        segment_syllables: tuple[str, ...] | None = None,
        target_syllables: tuple[str, ...] | None = None,
    ):
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

        # 音節級特殊音節映射（例如 hua <-> fa），避免「整串拼音」比對失效
        if (
            segment_syllables
            and target_syllables
            and len(segment_syllables) == len(target_syllables)
            and len(segment_syllables) <= 4
        ):
            syllable_map = self.config.SPECIAL_SYLLABLE_MAP_UNIDIRECTIONAL
            ok = True
            for seg_syl, tgt_syl in zip(segment_syllables, target_syllables):
                if seg_syl == tgt_syl:
                    continue
                if tgt_syl not in (syllable_map.get(seg_syl) or ()):
                    ok = False
                    break
            if ok:
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

    def _check_initials_match(self, segment, item, *, segment_initials: tuple[str, ...] | None = None):
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
        window_initials = list(segment_initials if segment_initials is not None else cached_get_initials(segment))

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

    def _score_candidate_drafts(self, drafts: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """
        統一計分階段

        目的：把「候選生成」與「打分」分離，之後可替換索引策略（BK-tree / n-gram 等）。
        """
        best: dict[tuple[int, int, str], Dict[str, Any]] = {}

        for draft in drafts:
            item = draft["item"]
            start = int(draft["start"])
            end = int(draft["end"])
            original = str(draft["original"])
            replacement = item["canonical"] if self.use_canonical else item["term"]

            if not replacement or original == replacement:
                continue

            score = self._calculate_final_score(
                float(draft["error_ratio"]),
                item,
                bool(draft.get("has_context", False)),
                draft.get("context_distance"),
            )

            candidate = {
                "start": start,
                "end": end,
                "original": original,
                "replacement": replacement,
                "canonical": item["canonical"],
                "alias": item["term"],
                "score": score,
                "has_context": bool(draft.get("has_context", False)),
            }

            key = (start, end, replacement)
            prev = best.get(key)
            if prev is None or candidate["score"] < prev["score"]:
                best[key] = candidate

        return list(best.values())

    def _generate_exact_candidate_drafts(
        self, text: str, protected_indices: set[int]
    ) -> list[Dict[str, Any]]:
        if not self._exact_matcher:
            return []

        drafts: list[Dict[str, Any]] = []
        for start, end, _word, alias in self._exact_matcher.iter_matches(text):
            if self._is_span_protected(start, end, protected_indices):
                continue

            original_segment = text[start:end]
            if not self._is_valid_segment(original_segment):
                continue
            if original_segment in self.protected_terms:
                continue

            for item in self._exact_items_by_alias.get(alias, []):
                # keywords / exclude_when 規則（與既有行為一致，context 用完整文本）
                if not self._has_required_keyword(text, item["keywords"]):
                    continue
                if self._should_exclude_by_context(text, item["exclude_when"]):
                    continue

                has_context, context_distance = self._check_context_bonus(
                    text, start, end, item["keywords"]
                )

                drafts.append(
                    {
                        "start": start,
                        "end": end,
                        "original": original_segment,
                        "error_ratio": 0.0,
                        "has_context": has_context,
                        "context_distance": context_distance,
                        "item": item,
                    }
                )

        return drafts

    def _process_fuzzy_match_draft(
        self,
        text: str,
        start_idx: int,
        original_segment: str,
        item: Dict[str, Any],
        *,
        segment_initials: tuple[str, ...] | None = None,
        segment_syllables: tuple[str, ...] | None = None,
    ):
        """
        處理模糊匹配

        核心邏輯:
        1. 檢查關鍵字必要條件 (如果有定義 keywords)
        2. 檢查上下文排除條件 (如果有定義 exclude_when)
        3. 計算拼音相似度與錯誤率
        4. 檢查是否超過容錯閾值
        5. 檢查聲母是否匹配 (針對短詞)
        6. 計算上下文加分
        7. 計算最終分數
        """
        word_len = item["len"]

        # 檢查關鍵字必要條件：如果有定義 keywords 但沒命中，則跳過
        if not self._has_required_keyword(text, item["keywords"]):
            return None

        # 檢查上下文排除條件：如果有定義 exclude_when 且命中，則跳過
        if self._should_exclude_by_context(text, item["exclude_when"]):
            return None

        # 便宜 pruning：先做首聲母/群組檢查，避免進入拼音 similarity 計算
        if not self._check_initials_match(original_segment, item, segment_initials=segment_initials):
            return None

        threshold = self._get_dynamic_threshold(word_len, item["is_mixed"])
        window_pinyin_str, error_ratio, is_fuzzy_match = self._calculate_pinyin_similarity(
            original_segment,
            item["pinyin_str"],
            segment_syllables=segment_syllables or cached_get_pinyin_syllables(original_segment),
            target_syllables=item.get("pinyin_syllables"),
        )
        if is_fuzzy_match:
            threshold = max(threshold, 0.15)
        if error_ratio > threshold:
            return None
        has_context, context_distance = self._check_context_bonus(text, start_idx, start_idx + word_len, item["keywords"])
        return {
            "start": start_idx,
            "end": start_idx + word_len,
            "original": original_segment,
            "error_ratio": error_ratio,
            "has_context": has_context,
            "context_distance": context_distance,
            "item": item,
        }

    def _generate_fuzzy_candidate_drafts(self, text: str, protected_indices: set[int]) -> list[Dict[str, Any]]:
        """
        搜尋所有可能的模糊修正候選（不計分，只產生候選資訊）

        遍歷所有索引項目，在文本中進行滑動視窗比對。
        """
        text_len = len(text)
        drafts: list[Dict[str, Any]] = []

        for word_len, groups in self._fuzzy_buckets.items():
            if word_len > text_len:
                continue

            for i in range(text_len - word_len + 1):
                if self._is_segment_protected(i, word_len, protected_indices):
                    continue

                original_segment = text[i : i + word_len]
                if not self._is_valid_segment(original_segment):
                    continue
                if original_segment in self.protected_terms:
                    continue

                segment_initials = tuple(cached_get_initials(original_segment))
                first = segment_initials[0] if segment_initials else ""
                group = self.config.FUZZY_INITIALS_MAP.get(first) or first or ""

                items = list(groups.get(group, []))
                if group == "":
                    items = list(groups.get("", []))
                if not items:
                    continue

                segment_syllables = cached_get_pinyin_syllables(original_segment)

                for item in items:
                    draft = self._process_fuzzy_match_draft(
                        text,
                        i,
                        original_segment,
                        item,
                        segment_initials=segment_initials,
                        segment_syllables=segment_syllables,
                    )
                    if draft:
                        drafts.append(draft)

        return drafts

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

    def _apply_replacements(
        self,
        text: str,
        final_candidates: list[Dict[str, Any]],
        silent: bool = False,
        *,
        trace_id: str | None = None,
    ) -> str:
        """應用修正並輸出日誌"""
        final_candidates.sort(key=lambda x: x["start"], reverse=True)
        final_text_list = list(text)
        for cand in final_candidates:
            self._emit_replacement(cand, silent=silent, trace_id=trace_id)
            final_text_list[cand["start"] : cand["end"]] = list(
                cand["replacement"]
            )
        return "".join(final_text_list)

    def correct(
        self,
        text: str,
        full_context: str | None = None,
        silent: bool = False,
        *,
        mode: str | None = None,
        fail_policy: str = "degrade",
        trace_id: str | None = None,
    ) -> str:
        """
        執行修正流程

        Args:
            text: 輸入文本
            full_context: 完整上下文（中文目前不使用，保留介面一致性）
            silent: 是否靜默模式 (不輸出修正日誌)

        Returns:
            修正後的文本
        """
        with TimingContext("ChineseCorrector.correct", self._logger, logging.DEBUG):
            protected_indices = self._build_protection_mask(text)

            if mode == "evaluation":
                fail_policy = "raise"
            elif mode == "production":
                fail_policy = "degrade"

            trace_id_value = trace_id or uuid.uuid4().hex

            drafts: list[Dict[str, Any]] = []
            drafts.extend(self._generate_exact_candidate_drafts(text, protected_indices))
            try:
                drafts.extend(self._generate_fuzzy_candidate_drafts(text, protected_indices))
            except Exception as exc:
                self._emit_pipeline_event(
                    {
                        "type": "fuzzy_error",
                        "engine": getattr(self._engine, "_engine_name", "chinese"),
                        "trace_id": trace_id_value,
                        "stage": "candidate_gen",
                        "fallback": "none" if fail_policy == "raise" else "exact_only",
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    },
                    silent=silent,
                )
                if fail_policy == "raise":
                    raise
                self._emit_pipeline_event(
                    {
                        "type": "degraded",
                        "engine": getattr(self._engine, "_engine_name", "chinese"),
                        "trace_id": trace_id_value,
                        "stage": "candidate_gen",
                        "fallback": "exact_only",
                        "degrade_reason": "fuzzy_error",
                    },
                    silent=silent,
                )
                if not silent:
                    self._logger.exception("產生 fuzzy 候選失敗，降級為 exact-only")

            candidates = self._score_candidate_drafts(drafts)
            final_candidates = self._resolve_conflicts(candidates)
            return self._apply_replacements(text, final_candidates, silent=silent, trace_id=trace_id_value)

    # 串流 API 已移除（Phase 6：精簡對外介面，改由上層自行分段/多次呼叫 correct()）

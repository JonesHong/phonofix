"""
日文修正器模組

實作針對日文拼寫錯誤的修正邏輯（常見來源包含 ASR/LLM/手動輸入）。
核心演算法基於羅馬拼音 (Romaji) 的相似度比對與滑動視窗掃描。

使用方式:
    from phonofix import JapaneseEngine

    engine = JapaneseEngine()
    corrector = engine.create_corrector({'アスピリン': ['asupirin']})
    result = corrector.correct('頭が痛いのでasupirinを飲みました')
"""

import logging
import re
import uuid
from typing import TYPE_CHECKING, Dict, List

from phonofix.core.events import CorrectionEventHandler
from phonofix.core.protocols.corrector import ContextAwareCorrectorProtocol
from phonofix.utils.aho_corasick import AhoCorasick
from phonofix.utils.logger import TimingContext, get_logger

if TYPE_CHECKING:
    from phonofix.languages.japanese.engine import JapaneseEngine


class JapaneseCorrector(ContextAwareCorrectorProtocol):
    """
    日文修正器

    功能:
    - 針對日文文本進行專有名詞修正
    - 使用滑動視窗掃描文本
    - 結合羅馬拼音相似度進行模糊比對
    - 支援 keywords 條件過濾 (需要上下文關鍵字才替換)
    - 支援 exclude_when 上下文排除 (看到排除詞時不替換)

    建立方式:
        使用 JapaneseEngine.create_corrector() 建立實例
    """

    @classmethod
    def _from_engine(
        cls,
        engine: "JapaneseEngine",
        term_mapping: Dict[str, Dict],
        protected_terms: set[str] | None = None,
        on_event: CorrectionEventHandler | None = None,
    ) -> "JapaneseCorrector":
        """
        從 Engine 建立輕量 Corrector 實例 (內部方法)

        Args:
            engine: JapaneseEngine 實例
            term_mapping: 正規化的專有名詞映射 (canonical -> config dict)

        Returns:
            JapaneseCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance._logger = get_logger("corrector.japanese")
        instance.phonetic = engine.phonetic
        instance.tokenizer = engine.tokenizer
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

        # 建立搜尋索引
        instance.search_index = instance._build_search_index(term_mapping)

        instance._build_exact_matcher()
        instance._build_fuzzy_buckets()

        return instance

    def _build_exact_matcher(self) -> None:
        items_by_alias: dict[str, list[Dict]] = {}
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
        buckets: dict[int, dict[int, list[Dict]]] = {}

        for item in self.search_index:
            token_count = int(item["token_count"])
            min_len = max(1, token_count - 2)
            max_len = token_count + 2

            phonetic = item.get("phonetic") or ""
            item["phonetic_len"] = len(phonetic)
            item["first_group"] = self._first_romaji_group(phonetic)
            item["max_len_diff"] = max(len(phonetic), 5) * 0.5

            group_id = item["first_group"]
            group_key = -1 if group_id is None else int(group_id)

            for window_len in range(min_len, max_len + 1):
                buckets.setdefault(window_len, {}).setdefault(group_key, []).append(item)

        self._fuzzy_buckets = buckets

    @staticmethod
    def _first_romaji_group(romaji: str) -> int | None:
        if not romaji:
            return None
        first = None
        for ch in romaji:
            if ch == " ":
                continue
            first = ch.lower()
            break
        if not first:
            return None

        vowels = {"a", "e", "i", "o", "u"}
        if first in vowels:
            return 0
        if first in {"p", "b"}:
            return 1
        if first in {"t", "d"}:
            return 2
        if first in {"k", "g"}:
            return 3
        if first in {"s", "z"}:
            return 4
        if first in {"h", "f"}:
            return 5
        if first in {"m", "n"}:
            return 6
        if first in {"r", "l"}:
            return 7
        if first in {"w", "y"}:
            return 8
        if first in {"j", "c"}:
            return 9
        return None

    def _emit_replacement(self, candidate: Dict, *, silent: bool, trace_id: str | None) -> None:
        event = {
            "type": "replacement",
            "engine": getattr(self._engine, "_engine_name", "japanese"),
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

    def _emit_pipeline_event(self, event: Dict, *, silent: bool) -> None:
        try:
            if self._on_event is not None:
                self._on_event(event)
        except Exception:
            if not silent:
                self._logger.exception("on_event 回呼執行失敗")

    def _build_search_index(self, term_mapping: Dict[str, Dict]) -> List[Dict]:
        """
        建立搜尋索引

        將別名映射轉換為列表結構，並預先計算拼音與 Token 數量。
        索引按 Token 數量降序排列，以優先匹配長詞。
        """
        search_index = []

        for canonical, config in term_mapping.items():
            aliases = config.get("aliases", [])
            weight = config.get("weight", 1.0)
            keywords = config.get("keywords", [])
            exclude_when = config.get("exclude_when", [])

            # 收集所有目標詞 (別名 + 正確詞本身)
            targets = set(aliases) | {canonical}

            for alias in targets:
                is_alias = alias != canonical
                # 計算別名的拼音
                phonetic = self.phonetic.to_phonetic(alias)
                if not phonetic:
                    continue

                # 計算別名的 Token 數量 (用於滑動視窗)
                tokens = self.tokenizer.tokenize(alias)
                token_count = len(tokens)

                search_index.append({
                    "term": alias,
                    "canonical": canonical,
                    "phonetic": phonetic,
                    "token_count": token_count,
                    "weight": weight,
                    "keywords": keywords,
                    "exclude_when": exclude_when,
                    "is_alias": is_alias,
                })

        # 按 Token 數量降序排列
        search_index.sort(key=lambda x: x["token_count"], reverse=True)
        return search_index

    def _generate_exact_candidate_drafts(
        self, text: str, context: str, protected_indices: set[int]
    ) -> list[Dict]:
        if not self._exact_matcher:
            return []

        drafts: list[Dict] = []
        for start, end, word, alias in self._exact_matcher.iter_matches(text):
            if self._is_span_protected(start, end, protected_indices):
                continue

            original_text = text[start:end]
            if original_text in self.protected_terms:
                continue

            for item in self._exact_items_by_alias.get(alias, []):
                if original_text == item["canonical"]:
                    continue
                if self._should_exclude_by_context(item["exclude_when"], context):
                    continue
                if not self._has_required_keyword(item["keywords"], context):
                    continue

                has_context, context_distance = self._check_context_bonus(
                    context, start, end, item["keywords"]
                )

                drafts.append(
                    {
                        "start": start,
                        "end": end,
                        "original": original_text,
                        "error_ratio": 0.0,
                        "has_context": has_context,
                        "context_distance": context_distance,
                        "item": item,
                    }
                )

        return drafts

    def _check_context_bonus(self, full_text, start_idx, end_idx, keywords, window_size=50):
        """
        檢查上下文關鍵字加分

        若在修正目標附近的視窗內發現相關關鍵字，則給予額外加分 (降低距離分數)。
        這有助於區分同音異義詞。

        Args:
            full_text: 完整文本
            start_idx: 目標詞起始索引
            end_idx: 目標詞結束索引
            keywords: 關鍵字列表
            window_size: 上下文視窗大小 (預設 50 字符)

        Returns:
            (bool, float): (是否命中關鍵字, 關鍵字距離)
        """
        if not keywords:
            return False, None
        ctx_start = max(0, start_idx - window_size)
        ctx_end = min(len(full_text), end_idx + window_size)
        context_text = full_text[ctx_start:ctx_end] # 日文不轉小寫，因為包含漢字

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

    def _calculate_final_score(self, error_ratio, item, has_context, context_distance=None):
        """
        計算最終分數 (越低越好)

        公式: 錯誤率 - 詞彙權重 - 上下文加分
        """
        final_score = error_ratio
        final_score -= item["weight"]
        if has_context and context_distance is not None:
            # 上下文加分邏輯
            distance_factor = 1.0 - (min(context_distance, 50) / 50.0 * 0.6)
            context_bonus = 0.8 * distance_factor
            final_score -= context_bonus
        return final_score

    def _create_candidate(self, start_idx, end_idx, original, item, score, has_context):
        """建立候選修正物件"""
        return {
            "start": start_idx,
            "end": end_idx,
            "original": original,
            "replacement": item["canonical"],
            "score": score,
            "has_context": has_context,
            "alias": item["term"]
        }

    def _should_exclude_by_context(self, exclude_when: List[str], context: str) -> bool:
        """檢查是否應根據上下文排除修正"""
        if not exclude_when:
            return False
        for condition in exclude_when:
            if condition in context:
                return True
        return False

    def _has_required_keyword(self, keywords: List[str], context: str) -> bool:
        """檢查是否滿足關鍵字必要條件"""
        if not keywords:
            return True
        for kw in keywords:
            if kw in context:
                return True
        return False

    def _build_protection_mask(self, text: str) -> set[int]:
        """
        建立保護遮罩，標記不應被修正的區域 (受保護的詞彙)

        與中文策略一致：只要候選片段與任一 protected_terms 有重疊，就跳過。
        """
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

    @staticmethod
    def _is_span_protected(start: int, end: int, protected_indices: set[int]) -> bool:
        for idx in range(start, end):
            if idx in protected_indices:
                return True
        return False

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
        修正日文文本

        Args:
            text: 輸入文本
            full_context: 完整上下文 (用於關鍵字判斷)
            silent: 是否靜默模式 (不輸出修正日誌)

        Returns:
            str: 修正後的文本
        """
        if not text or not self.search_index:
            return text

        with TimingContext("JapaneseCorrector.correct", self._logger, logging.DEBUG):
            context = full_context if full_context is not None else text
            protected_indices = self._build_protection_mask(text)

            if mode == "evaluation":
                fail_policy = "raise"
            elif mode == "production":
                fail_policy = "degrade"

            trace_id_value = trace_id or uuid.uuid4().hex

            drafts: list[Dict] = []
            drafts.extend(self._generate_exact_candidate_drafts(text, context, protected_indices))
            try:
                drafts.extend(self._generate_fuzzy_candidate_drafts(text, context, protected_indices))
            except Exception as exc:
                self._emit_pipeline_event(
                    {
                        "type": "fuzzy_error",
                        "engine": getattr(self._engine, "_engine_name", "japanese"),
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
                        "engine": getattr(self._engine, "_engine_name", "japanese"),
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

    def _generate_fuzzy_candidate_drafts(
        self, text: str, context: str, protected_indices: set[int]
    ) -> List[Dict]:
        """搜尋所有可能的模糊修正候選（不計分，只產生候選資訊）"""

        # 1. 分詞與索引
        tokens = self.tokenizer.tokenize(text)
        indices = self.tokenizer.get_token_indices(text)

        if not tokens:
            return []

        # 預先計算每個 token 的拼音
        token_phonetics = [self.phonetic.to_phonetic(t) for t in tokens]

        drafts: list[Dict] = []
        n = len(tokens)

        window_lengths = sorted([length for length in self._fuzzy_buckets.keys() if length <= n])
        if not window_lengths:
            return []

        for length in window_lengths:
            groups = self._fuzzy_buckets.get(length) or {}
            if not groups:
                continue

            for i in range(n - length + 1):
                start_char = indices[i][0]
                end_char = indices[i + length - 1][1]
                if self._is_span_protected(start_char, end_char, protected_indices):
                    continue

                window_phonetic = "".join(token_phonetics[i : i + length])
                if not window_phonetic:
                    continue

                window_first_group = self._first_romaji_group(window_phonetic)
                window_group_key = -1 if window_first_group is None else int(window_first_group)

                items = list(groups.get(window_group_key, [])) + list(groups.get(-1, []))
                if window_group_key == -1:
                    items = [it for bucket in groups.values() for it in bucket]

                for item in items:
                    if abs(len(window_phonetic) - int(item.get("phonetic_len", 0))) > float(
                        item.get("max_len_diff", 0.0)
                    ):
                        continue

                    error_ratio, is_match = self.phonetic.calculate_similarity_score(
                        window_phonetic, item["phonetic"]
                    )
                    if not is_match:
                        continue

                    if self._should_exclude_by_context(item["exclude_when"], context):
                        continue
                    if not self._has_required_keyword(item["keywords"], context):
                        continue

                    original_text = text[start_char:end_char]
                    if original_text in self.protected_terms:
                        continue
                    if original_text == item["canonical"]:
                        continue

                    has_context, context_distance = self._check_context_bonus(
                        context, start_char, end_char, item["keywords"]
                    )

                    drafts.append(
                        {
                            "start": start_char,
                            "end": end_char,
                            "original": original_text,
                            "error_ratio": error_ratio,
                            "has_context": has_context,
                            "context_distance": context_distance,
                            "item": item,
                        }
                    )

        return drafts

    def _score_candidate_drafts(self, drafts: list[Dict]) -> list[Dict]:
        best: dict[tuple[int, int, str], Dict] = {}

        for draft in drafts:
            item = draft["item"]
            start = int(draft["start"])
            end = int(draft["end"])
            original = str(draft["original"])
            replacement = item["canonical"]

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

    def _resolve_conflicts(self, candidates: List[Dict]) -> List[Dict]:
        """解決候選衝突"""
        # 按分數排序 (越低越好)
        candidates.sort(key=lambda x: x["score"])

        final_candidates = []
        for cand in candidates:
            is_conflict = False
            for accepted in final_candidates:
                if max(cand["start"], accepted["start"]) < min(cand["end"], accepted["end"]):
                    is_conflict = True
                    break
            if not is_conflict:
                final_candidates.append(cand)
            else:
                self._logger.debug(f"Conflict resolved: Dropped '{cand['original']}' (score={cand['score']}) in favor of existing match")

        return final_candidates

    def _apply_replacements(
        self, text: str, candidates: List[Dict], silent: bool = False, *, trace_id: str | None = None
    ) -> str:
        """應用修正並輸出日誌"""
        candidates.sort(key=lambda x: x["start"])

        result = []
        last_pos = 0
        for cand in candidates:
            # 如果原文與替換文相同，則不進行替換操作，但它佔用了位置防止錯誤修正
            if cand["original"] == cand["replacement"]:
                continue

            result.append(text[last_pos : cand["start"]])
            result.append(cand["replacement"])

            self._emit_replacement(cand, silent=silent, trace_id=trace_id)

            self._logger.debug(
                f"  [Match] '{cand['original']}' -> '{cand['replacement']}' "
                f"(via '{cand['alias']}', score={cand['score']:.3f})"
            )

            last_pos = cand["end"]
        result.append(text[last_pos:])
        return "".join(result)

"""
英文修正器模組

實作基於滑動視窗 (Sliding Window) 與語音相似度的英文專有名詞修正。

使用方式:
    from phonofix import EnglishEngine

    engine = EnglishEngine()
    corrector = engine.create_corrector({'Python': ['Pyton', 'Pyson']})
    result = corrector.correct('I use Pyton for ML')
"""

import logging
import re
import uuid
from typing import TYPE_CHECKING, Dict, List

from phonofix.core.events import CorrectionEventHandler
from phonofix.core.protocols.corrector import ContextAwareCorrectorProtocol
from phonofix.utils.aho_corasick import AhoCorasick
from phonofix.utils.logger import TimingContext, get_logger

from .config import EnglishPhoneticConfig

if TYPE_CHECKING:
    from phonofix.languages.english.engine import EnglishEngine


class EnglishCorrector(ContextAwareCorrectorProtocol):
    """
    英文修正器

    功能:
    - 針對英文文本進行專有名詞修正
    - 使用滑動視窗掃描文本
    - 結合 IPA 發音相似度進行模糊比對
    - 支援自動生成常見分割/聽寫變體
    - 支援 keywords 條件過濾 (需要上下文關鍵字才替換)
    - 支援 exclude_when 上下文排除 (看到排除詞時不替換)

    建立方式:
        使用 EnglishEngine.create_corrector() 建立實例
    """

    @classmethod
    def _from_engine(
        cls,
        engine: "EnglishEngine",
        term_mapping: Dict[str, Dict],
        protected_terms: set[str] | None = None,
        on_event: CorrectionEventHandler | None = None,
    ) -> "EnglishCorrector":
        """
        從 Engine 建立輕量 Corrector 實例 (內部方法)

        Args:
            engine: EnglishEngine 實例
            term_mapping: 正規化的專有名詞映射 (canonical -> config dict)

        Returns:
            EnglishCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance._logger = get_logger("corrector.english")
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

        # 供測試/除錯使用：alias -> canonical 的映射
        instance.term_mapping = {
            alias: canonical
            for canonical, config in term_mapping.items()
            for alias in config.get("aliases", [])
        }

        # 建立搜尋索引
        instance.search_index = instance._build_search_index(term_mapping)

        instance._build_exact_matcher()
        instance._build_fuzzy_buckets()

        return instance

    def _build_exact_matcher(self) -> None:
        """
        建立 surface alias 的 exact-match 索引（Aho-Corasick）

        - 只納入 aliases（不納入 canonical 本身），用來快速找候選區間
        - 每個 alias 可能對應多個 item（理論上應盡量避免，但這裡保守處理）
        """
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
        """
        建立便宜 pruning 用的分桶索引

        分桶維度：
        - window token 長度（token_count 的容許範圍）
        - 首音素群組（IPA 第一個音素）
        """
        buckets: dict[int, dict[int, list[Dict]]] = {}

        for item in self.search_index:
            token_count = int(item["token_count"])
            min_len = max(1, token_count - 2)
            max_len = token_count + 3

            phonetic = item.get("phonetic") or ""
            item["phonetic_len"] = len(phonetic)
            item["first_group"] = self._first_phoneme_group(phonetic)
            item["max_len_diff"] = max(len(phonetic), 5) * 0.6

            group_id = item["first_group"]
            group_key = -1 if group_id is None else int(group_id)

            for window_len in range(min_len, max_len + 1):
                buckets.setdefault(window_len, {}).setdefault(group_key, []).append(item)

        self._fuzzy_buckets = buckets

    @staticmethod
    def _first_ipa_symbol(ipa: str) -> str | None:
        for ch in ipa or "":
            if ch in {" ", "ˈ", "ˌ"}:
                continue
            return ch
        return None

    def _first_phoneme_group(self, ipa: str) -> int | None:
        first = self._first_ipa_symbol(ipa)
        if not first:
            return None
        for idx, group in enumerate(EnglishPhoneticConfig.FUZZY_PHONEME_GROUPS):
            if first in group:
                return idx
        return None

    def _emit_replacement(self, candidate: Dict, *, silent: bool, trace_id: str | None) -> None:
        event = {
            "type": "replacement",
            "engine": getattr(self._engine, "_engine_name", "english"),
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

        將別名映射轉換為列表結構，並預先計算 IPA。
        索引按 Token 數量降序排列，以優先匹配長詞。
        """
        # 1. 收集所有需要計算 IPA 的 tokens
        all_tokens = set()
        alias_tokens_map = {}

        # 展開所有別名
        flat_mapping = []
        for canonical, config in term_mapping.items():
            aliases = config.get("aliases", [])
            # 確保正確詞本身也在搜尋範圍 (如果需要)
            # 通常我們只搜尋別名，但有時正確詞也需要被處理 (例如大小寫修正)
            # 這裡我們將正確詞也視為一個潛在的目標，但通常它會是完全匹配
            targets = set(aliases) | {canonical}

            for alias in targets:
                is_alias = alias != canonical
                flat_mapping.append({
                    "term": alias,
                    "canonical": canonical,
                    "keywords": config.get("keywords", []),
                    "exclude_when": config.get("exclude_when", []),
                    "weight": config.get("weight", 0.0),
                    "is_alias": is_alias,
                })

                tokens = self.tokenizer.tokenize(alias)
                alias_tokens_map[alias] = tokens
                all_tokens.update(tokens)

        # 2. 批次計算 IPA
        token_ipa_map = self._engine._backend.to_phonetic_batch(list(all_tokens))

        # 3. 建立索引項目
        search_index = []
        for item in flat_mapping:
            alias = item["term"]
            tokens = alias_tokens_map[alias]
            ipa_parts = [token_ipa_map.get(t, '') for t in tokens]
            # 合併 IPA，移除空格以進行模糊比對
            alias_phonetic = "".join(ipa_parts)

            search_index.append({
                "term": alias,
                "canonical": item["canonical"],
                "phonetic": alias_phonetic,
                "token_count": len(tokens),
                "keywords": item["keywords"],
                "exclude_when": item["exclude_when"],
                "weight": item["weight"],
                "is_alias": item["is_alias"],
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
            window_size: 上下文視窗大小 (預設 50 字符，英文句子較長)

        Returns:
            (bool, float): (是否命中關鍵字, 關鍵字距離)
        """
        if not keywords:
            return False, None
        ctx_start = max(0, start_idx - window_size)
        ctx_end = min(len(full_text), end_idx + window_size)
        context_text = full_text[ctx_start:ctx_end].lower()

        min_distance = None
        for kw in keywords:
            kw_lower = kw.lower()
            kw_idx = context_text.find(kw_lower)
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
            # 距離越近，加分越多 (最大 0.8)
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
        context_lower = context.lower()
        for condition in exclude_when:
            if condition.lower() in context_lower:
                return True
        return False

    def _has_required_keyword(self, keywords: List[str], context: str) -> bool:
        """檢查是否滿足關鍵字必要條件"""
        if not keywords:
            return True
        context_lower = context.lower()
        for kw in keywords:
            if kw.lower() in context_lower:
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
            # fallback（理論上不會走到）：避免初始化階段異常導致保護機制失效
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
        執行英文文本修正

        Args:
            text: 待修正的英文文本
            full_context: 完整的原始句子 (用於 keyword 和 exclude_when 檢查)
            silent: 是否靜默模式 (不輸出修正日誌)

        Returns:
            str: 修正後的文本
        """
        with TimingContext("EnglishCorrector.correct", self._logger, logging.DEBUG):
            context = full_context if full_context else text
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
                        "engine": getattr(self._engine, "_engine_name", "english"),
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
                        "engine": getattr(self._engine, "_engine_name", "english"),
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
        tokens = self.tokenizer.tokenize(text)
        indices = self.tokenizer.get_token_indices(text)

        if not tokens:
            return []

        # 預先計算每個 token 的 IPA
        unique_tokens = list(set(tokens))
        token_ipa_map = self._engine._backend.to_phonetic_batch(unique_tokens)
        token_ipas = [token_ipa_map.get(token, '') for token in tokens]

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

                window_phonetic = "".join(token_ipas[i : i + length])
                if not window_phonetic:
                    continue

                window_first_group = self._first_phoneme_group(window_phonetic)
                window_group_key = -1 if window_first_group is None else int(window_first_group)

                # 只看同群組 + unknown 群組
                items = list(groups.get(window_group_key, [])) + list(groups.get(-1, []))
                if window_group_key == -1:
                    # 視窗首音素未知時，保守：檢查所有群組
                    items = [it for bucket in groups.values() for it in bucket]

                for item in items:
                    # 長度差上限 pruning
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
        """
        統一計分階段

        目的：把「候選生成」與「打分」分離，之後可替換索引策略（BK-tree / n-gram 等）。
        """
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
        """
        解決候選衝突

        當多個候選修正重疊時，選擇分數最低 (最佳) 的候選。
        """
        # 按分數排序 (越低越好)
        candidates.sort(key=lambda x: x["score"])

        final_candidates = []
        for cand in candidates:
            is_conflict = False
            for accepted in final_candidates:
                # 檢查區間重疊
                if max(cand["start"], accepted["start"]) < min(cand["end"], accepted["end"]):
                    is_conflict = True
                    break
            if not is_conflict:
                final_candidates.append(cand)

        return final_candidates

    def _apply_replacements(
        self, text: str, candidates: List[Dict], silent: bool = False, *, trace_id: str | None = None
    ) -> str:
        """應用修正並輸出日誌"""
        # 按位置從後往前替換，避免索引偏移 (或者重建字串)
        # 這裡使用重建字串的方式
        candidates.sort(key=lambda x: x["start"])

        result = []
        last_pos = 0
        for cand in candidates:
            # 加入未修正部分
            result.append(text[last_pos : cand["start"]])
            # 加入修正詞
            result.append(cand["replacement"])

            self._emit_replacement(cand, silent=silent, trace_id=trace_id)

            self._logger.debug(
                f"  [Match] '{cand['original']}' -> '{cand['replacement']}' "
                f"(via '{cand['alias']}', score={cand['score']:.3f})"
            )

            last_pos = cand["end"]

        result.append(text[last_pos:])
        return "".join(result)

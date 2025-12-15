"""
英文 corrector：候選生成與統一計分階段

這裡維持「行為不變」的前提，把原本散落在 EnglishCorrector 的邏輯搬出來，
以便後續替換索引策略或調整 scoring/filters 時不需要再碰 orchestrator。

效能關鍵點（避免回歸）：
- fuzzy 掃描以 `window token 長度` + `首音素群組` 分桶，避免每個窗口對所有 item 計算相似度
- token IPA 採 batch 計算並在窗口內做 join，避免重複呼叫 backend
"""

from __future__ import annotations

from typing import Any

from . import indexing as indexing_ops
from .filters import (
    check_context_bonus,
    has_required_keyword,
    is_span_protected,
    should_exclude_by_context,
    token_boundaries,
)
from .scoring import calculate_final_score
from .types import EnglishCandidate, EnglishCandidateDraft, EnglishIndexItem


def generate_exact_candidate_drafts(
    *,
    text: str,
    context: str,
    protected_indices: set[int],
    tokenizer: Any,
    exact_matcher: Any,
    exact_items_by_alias: dict[str, list[EnglishIndexItem]],
    protected_terms: set[str],
) -> list[EnglishCandidateDraft]:
    """
    exact-match 候選生成（Aho-Corasick surface alias）

    - 只要 surface alias 命中就產生 draft（error_ratio=0）
    - 再套用 exclude_when / keywords / protected_terms 等規則避免誤替換
    - 對短 alias 額外要求 token 邊界，避免子字串誤擊（例如 "go" 不應命中 "gopher"）
    """
    if not exact_matcher:
        return []

    boundaries = token_boundaries(tokenizer=tokenizer, text=text)

    drafts: list[EnglishCandidateDraft] = []
    for start, end, _word, alias in exact_matcher.iter_matches(text):
        if start not in boundaries or end not in boundaries:
            continue
        if is_span_protected(start=start, end=end, protected_indices=protected_indices):
            continue

        original_text = text[start:end]
        if original_text in protected_terms:
            continue

        for item in exact_items_by_alias.get(alias, []):
            if original_text == item["canonical"]:
                continue
            if should_exclude_by_context(exclude_when=item["exclude_when"], context=context):
                continue
            if not has_required_keyword(keywords=item["keywords"], context=context):
                continue

            has_context, context_distance = check_context_bonus(
                full_text=context,
                start_idx=int(start),
                end_idx=int(end),
                keywords=item["keywords"],
            )

            drafts.append(
                {
                    "start": int(start),
                    "end": int(end),
                    "original": str(original_text),
                    "error_ratio": 0.0,
                    "has_context": bool(has_context),
                    "context_distance": context_distance,
                    "item": item,
                }
            )

    return drafts


def generate_fuzzy_candidate_drafts(
    *,
    text: str,
    context: str,
    protected_indices: set[int],
    tokenizer: Any,
    backend: Any,
    phonetic: Any,
    fuzzy_buckets: dict[int, dict[int, list[EnglishIndexItem]]],
    protected_terms: set[str],
) -> list[EnglishCandidateDraft]:
    """
    搜尋所有可能的模糊修正候選（不計分，只產生候選資訊）

    流程（對齊中文/日文 pipeline 的思維）：
    1) 分詞 + 取得 token 在原文的 span（供回填 start/end）
    2) 以 backend batch 預先計算 token IPA（並重用），避免逐 token 呼叫
    3) 依 window 長度與首音素群組分桶，做便宜 pruning
    4) 只對可能命中的 items 計算相似度，命中後才產生 draft
    """
    tokens = tokenizer.tokenize(text)
    indices = tokenizer.get_token_indices(text)

    if not tokens:
        return []

    unique_tokens = list(set(tokens))
    token_ipa_map = backend.to_phonetic_batch(unique_tokens)
    token_ipas = [token_ipa_map.get(token, "") for token in tokens]

    drafts: list[EnglishCandidateDraft] = []
    n = len(tokens)

    window_lengths = sorted([length for length in fuzzy_buckets.keys() if length <= n])
    if not window_lengths:
        return []

    for length in window_lengths:
        groups = fuzzy_buckets.get(length) or {}
        if not groups:
            continue

        for i in range(n - length + 1):
            start_char = indices[i][0]
            end_char = indices[i + length - 1][1]
            # 受保護區段直接跳過：越早越好，避免進入後續 similarity 計算
            if is_span_protected(start=start_char, end=end_char, protected_indices=protected_indices):
                continue

            window_phonetic = "".join(token_ipas[i : i + length])
            if not window_phonetic:
                continue

            window_first_group = indexing_ops.first_phoneme_group(window_phonetic)
            window_group_key = -1 if window_first_group is None else int(window_first_group)

            # 只看同群組 + unknown 群組；視窗首音未知時保守掃描所有群組
            items = list(groups.get(window_group_key, [])) + list(groups.get(-1, []))
            if window_group_key == -1:
                # 視窗首音素未知時，保守：檢查所有群組
                items = [it for bucket in groups.values() for it in bucket]

            for item in items:
                # 長度差上限 pruning：避免拿非常不可能的 item 進 similarity
                if abs(len(window_phonetic) - int(item.get("phonetic_len", 0) or 0)) > float(
                    item.get("max_len_diff", 0.0) or 0.0
                ):
                    continue

                error_ratio, is_match = phonetic.calculate_similarity_score(window_phonetic, item["phonetic"])
                if not is_match:
                    continue

                if should_exclude_by_context(exclude_when=item["exclude_when"], context=context):
                    continue
                if not has_required_keyword(keywords=item["keywords"], context=context):
                    continue

                original_text = text[start_char:end_char]
                if original_text in protected_terms:
                    continue
                if original_text == item["canonical"]:
                    continue

                has_context, context_distance = check_context_bonus(
                    full_text=context,
                    start_idx=int(start_char),
                    end_idx=int(end_char),
                    keywords=item["keywords"],
                )

                drafts.append(
                    {
                        "start": int(start_char),
                        "end": int(end_char),
                        "original": str(original_text),
                        "error_ratio": float(error_ratio),
                        "has_context": bool(has_context),
                        "context_distance": context_distance,
                        "item": item,
                    }
                )

    return drafts


def score_candidate_drafts(*, drafts: list[EnglishCandidateDraft]) -> list[EnglishCandidate]:
    """
    統一計分階段

    目的：把「候選生成」與「打分」分離，之後可替換索引策略（BK-tree / n-gram 等）。
    """
    best: dict[tuple[int, int, str], EnglishCandidate] = {}

    for draft in drafts:
        item = draft["item"]
        start = int(draft["start"])
        end = int(draft["end"])
        original = str(draft["original"])
        replacement = item["canonical"]

        if not replacement or original == replacement:
            continue

        score = calculate_final_score(
            error_ratio=float(draft["error_ratio"]),
            item=item,
            has_context=bool(draft.get("has_context", False)),
            context_distance=draft.get("context_distance"),
        )

        candidate: EnglishCandidate = {
            "start": start,
            "end": end,
            "original": original,
            "replacement": replacement,
            "canonical": item["canonical"],
            "alias": item["term"],
            "score": float(score),
            "has_context": bool(draft.get("has_context", False)),
        }

        key = (start, end, replacement)
        prev = best.get(key)
        if prev is None or candidate["score"] < prev["score"]:
            best[key] = candidate

    return list(best.values())

"""
日文 corrector：候選生成與統一計分階段

這裡維持「行為不變」的前提，把原本散落在 JapaneseCorrector 的邏輯搬出來，
以便後續替換索引策略或調整 scoring/filters 時不需要再碰 orchestrator。

效能關鍵點（避免回歸）：
- fuzzy 掃描以 `window token 長度` + `首音群組` 分桶，避免每個窗口對所有 item 計算相似度
- token romaji 先去重計算並重用，降低重複 G2P 成本（backend 有快取，但仍可減少 Python 層開銷）
"""

from __future__ import annotations

from typing import Any

from . import indexing as indexing_ops
from .filters import (
    check_context_bonus,
    has_required_keyword,
    is_span_protected,
    should_exclude_by_context,
)
from .scoring import calculate_final_score
from .types import JapaneseCandidate, JapaneseCandidateDraft, JapaneseIndexItem


def _is_ascii_alnum(ch: str) -> bool:
    return bool(ch) and ch.isascii() and ch.isalnum()


def _is_ascii_word(s: str) -> bool:
    """
    判斷字串是否屬於 ASCII「單詞」類型（羅馬字/數字）。

    用途：
    - 日文文本常混入 romaji（例如 ai / kaihatsu / asupirinn）
    - exact-match 不應把短 alias 命中在更長的 romaji 片段內
      （例如 ai 命中在 k-ai-hatsu 裡、asupirin 命中在 asupirinn 裡）
    """
    if not s:
        return False
    return all(_is_ascii_alnum(ch) for ch in s)


def generate_exact_candidate_drafts(
    *,
    text: str,
    context: str,
    protected_indices: set[int],
    exact_matcher: Any,
    exact_items_by_alias: dict[str, list[JapaneseIndexItem]],
    protected_terms: set[str],
) -> list[JapaneseCandidateDraft]:
    """
    exact-match 候選生成（Aho-Corasick surface alias）

    - 只要 surface alias 命中就產生 draft（error_ratio=0）
    - 再套用 exclude_when / keywords / protected_terms 等規則避免誤替換
    """
    if not exact_matcher:
        return []

    drafts: list[JapaneseCandidateDraft] = []
    for start, end, _word, alias in exact_matcher.iter_matches(text):
        original_text = text[start:end]

        # ASCII alias（romaji）邊界檢查：
        # - 避免短 alias 命中在更長的 romaji 片段內（ai in kaihatsu）
        # - 避免部分命中造成殘留尾巴（asupirin in asupirinn）
        if _is_ascii_word(str(original_text)):
            before = text[start - 1] if start > 0 else ""
            after = text[end] if end < len(text) else ""
            if _is_ascii_alnum(before) or _is_ascii_alnum(after):
                continue

        if is_span_protected(start=start, end=end, protected_indices=protected_indices):
            continue

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
    phonetic: Any,
    fuzzy_buckets: dict[int, dict[int, list[JapaneseIndexItem]]],
    protected_terms: set[str],
) -> list[JapaneseCandidateDraft]:
    """
    搜尋所有可能的模糊修正候選（不計分，只產生候選資訊）

    流程（對齊中文/英文 pipeline 的思維）：
    1) 分詞 + 取得 token 在原文的 span（供回填 start/end）
    2) 預先計算每個 token 的 romaji（去重重用）
    3) 依 window 長度與首音群組分桶，做便宜 pruning
    4) 只對可能命中的 items 計算相似度，命中後才產生 draft
    """
    tokens = tokenizer.tokenize(text)
    indices = tokenizer.get_token_indices(text)

    if not tokens:
        return []

    seen: set[str] = set()
    unique_tokens: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)

    token_phonetic_map = {t: phonetic.to_phonetic(t) for t in unique_tokens}
    token_phonetics = [token_phonetic_map.get(t, "") for t in tokens]

    drafts: list[JapaneseCandidateDraft] = []
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

            window_phonetic = "".join(token_phonetics[i : i + length])
            if not window_phonetic:
                continue

            window_first_group = indexing_ops.first_romaji_group(window_phonetic)
            window_group_key = -1 if window_first_group is None else int(window_first_group)

            # 只看同群組 + unknown 群組；視窗首音未知時保守掃描所有群組
            items = list(groups.get(window_group_key, [])) + list(groups.get(-1, []))
            if window_group_key == -1:
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


def score_candidate_drafts(*, drafts: list[JapaneseCandidateDraft]) -> list[JapaneseCandidate]:
    """
    將候選草稿（draft）轉成最終候選（candidate），並做基本去重。

    - 透過 scoring.calculate_final_score 計算最終分數（越低越好）
    - 以 (start, end, replacement) 為 key 保留最佳候選，避免重複套用
    """
    best: dict[tuple[int, int, str], JapaneseCandidate] = {}

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

        candidate: JapaneseCandidate = {
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

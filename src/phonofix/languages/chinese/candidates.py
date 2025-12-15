"""
中文 corrector：候選生成與統一計分階段

這裡維持「行為不變」的前提，把原本散落在 ChineseCorrector 的邏輯搬出來，
以便後續替換索引策略或調整 scoring/filters 時不需要再碰 orchestrator。

效能關鍵點（避免回歸）：
- fuzzy 掃描以 `len` + `首聲母群組` 分桶，只遍歷「可能命中」的 items
- 在每個窗口只計算一次 `segment_initials/segment_syllables` 並傳入內層比對
- 即使 backend 有 LRU 快取，仍可避免大量 Python 層呼叫與中間物件建立
"""

from __future__ import annotations

from typing import Any

from .filters import (
    check_context_bonus,
    has_required_keyword,
    is_segment_protected,
    is_span_protected,
    is_valid_segment,
    should_exclude_by_context,
)
from .scoring import (
    calculate_final_score,
    calculate_pinyin_similarity,
    check_initials_match,
    get_dynamic_threshold,
)
from .types import ChineseCandidate, ChineseCandidateDraft, ChineseIndexItem


def generate_exact_candidate_drafts(
    *,
    text: str,
    context: str,
    protected_indices: set[int],
    exact_matcher: Any,
    exact_items_by_alias: dict[str, list[ChineseIndexItem]],
    protected_terms: set[str],
) -> list[ChineseCandidateDraft]:
    """
    產生 exact-match 候選草稿。

    流程：
    - 使用 `exact_matcher`（Aho-Corasick）掃描 text
    - 對每個命中的 alias，找到對應的 index items
    - 套用 keywords / exclude_when / protected_terms 等規則
    - 回傳 draft 列表（後續由 scoring/replace 處理）
    """
    if not exact_matcher:
        return []

    drafts: list[ChineseCandidateDraft] = []
    for start, end, _word, alias in exact_matcher.iter_matches(text):
        if is_span_protected(start=start, end=end, protected_indices=protected_indices):
            continue

        original_segment = text[start:end]
        if not is_valid_segment(segment=original_segment):
            continue
        if original_segment in protected_terms:
            continue

        for item in exact_items_by_alias.get(alias, []):
            # keywords / exclude_when 規則（與既有行為一致，context 用完整文本）
            if not has_required_keyword(full_text=context, keywords=item["keywords"]):
                continue
            if should_exclude_by_context(full_text=context, exclude_when=item["exclude_when"]):
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
                    "original": str(original_segment),
                    "error_ratio": 0.0,
                    "has_context": bool(has_context),
                    "context_distance": context_distance,
                    "item": item,
                }
            )

    return drafts


def process_fuzzy_match_draft(
    *,
    context: str,
    start_idx: int,
    original_segment: str,
    item: ChineseIndexItem,
    engine: Any,
    config: Any,
    utils: Any,
    segment_initials: tuple[str, ...] | None = None,
    segment_syllables: tuple[str, ...] | None = None,
) -> ChineseCandidateDraft | None:
    """
    處理模糊匹配

    核心邏輯:
    1. 檢查關鍵字必要條件 (如果有定義 keywords)
    2. 檢查上下文排除條件 (如果有定義 exclude_when)
    3. 計算拼音相似度與錯誤率
    4. 檢查是否超過容錯閾值
    5. 檢查聲母是否匹配 (針對短詞)
    6. 計算上下文加分
    """
    word_len = int(item["len"])
    backend = engine.backend

    if not has_required_keyword(full_text=context, keywords=item["keywords"]):
        return None

    if should_exclude_by_context(full_text=context, exclude_when=item["exclude_when"]):
        return None

    if not check_initials_match(
        engine=engine,
        config=config,
        utils=utils,
        segment=original_segment,
        item=item,
        segment_initials=segment_initials,
    ):
        return None

    threshold = get_dynamic_threshold(word_len=word_len, is_mixed=bool(item["is_mixed"]))
    _window_pinyin_str, error_ratio, is_fuzzy_match = calculate_pinyin_similarity(
        engine=engine,
        config=config,
        utils=utils,
        segment=original_segment,
        target_pinyin_str=item["pinyin_str"],
        segment_syllables=segment_syllables or backend.get_pinyin_syllables(original_segment),
        target_syllables=item.get("pinyin_syllables"),
    )
    # 目前 drafts 不需要 window_pinyin_str；保留回傳值以避免未來要 trace/debug 時再改簽名
    if is_fuzzy_match:
        threshold = max(threshold, 0.15)
    if error_ratio > threshold:
        return None

    has_context, context_distance = check_context_bonus(
        full_text=context,
        start_idx=int(start_idx),
        end_idx=int(start_idx + word_len),
        keywords=item["keywords"],
    )
    return {
        "start": int(start_idx),
        "end": int(start_idx + word_len),
        "original": str(original_segment),
        "error_ratio": float(error_ratio),
        "has_context": bool(has_context),
        "context_distance": context_distance,
        "item": item,
    }


def generate_fuzzy_candidate_drafts(
    *,
    text: str,
    context: str,
    protected_indices: set[int],
    fuzzy_buckets: dict[int, dict[str, list[ChineseIndexItem]]],
    config: Any,
    engine: Any,
    utils: Any,
    protected_terms: set[str],
) -> list[ChineseCandidateDraft]:
    """
    搜尋所有可能的模糊修正候選（不計分，只產生候選資訊）

    遍歷所有索引項目，在文本中進行滑動視窗比對。
    """
    text_len = len(text)
    drafts: list[ChineseCandidateDraft] = []

    for word_len, groups in fuzzy_buckets.items():
        if word_len > text_len:
            continue

        for i in range(text_len - word_len + 1):
            # 受保護區段直接跳過：這一步越早越好，避免進入後續拼音/相似度計算
            if is_segment_protected(start_idx=i, word_len=int(word_len), protected_indices=protected_indices):
                continue

            original_segment = text[i : i + word_len]
            if not is_valid_segment(segment=original_segment):
                continue
            if original_segment in protected_terms:
                continue

            backend = engine.backend
            # 先取首聲母群組做分桶（便宜 pruning）
            segment_initials = tuple(backend.get_initials(original_segment))
            first = segment_initials[0] if segment_initials else ""
            group = config.FUZZY_INITIALS_MAP.get(first) or first or ""

            items = list(groups.get(group, []))
            if group == "":
                items = list(groups.get("", []))
            if not items:
                continue

            # 同一窗口的音節可重用（避免對每個 item 重複呼叫 backend）
            segment_syllables = backend.get_pinyin_syllables(original_segment)

            for item in items:
                draft = process_fuzzy_match_draft(
                    context=context,
                    start_idx=int(i),
                    original_segment=original_segment,
                    item=item,
                    engine=engine,
                    config=config,
                    utils=utils,
                    segment_initials=segment_initials,
                    segment_syllables=segment_syllables,
                )
                if draft:
                    drafts.append(draft)

    return drafts


def score_candidate_drafts(*, drafts: list[ChineseCandidateDraft], use_canonical: bool) -> list[ChineseCandidate]:
    """
    統一計分階段

    目的：把「候選生成」與「打分」分離，之後可替換索引策略（BK-tree / n-gram 等）。
    """
    best: dict[tuple[int, int, str], ChineseCandidate] = {}

    for draft in drafts:
        item = draft["item"]
        start = int(draft["start"])
        end = int(draft["end"])
        original = str(draft["original"])
        replacement = item["canonical"] if use_canonical else item["term"]

        if not replacement or original == replacement:
            continue

        score = calculate_final_score(
            error_ratio=float(draft["error_ratio"]),
            item=item,
            has_context=bool(draft.get("has_context", False)),
            context_distance=draft.get("context_distance"),
        )

        candidate: ChineseCandidate = {
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

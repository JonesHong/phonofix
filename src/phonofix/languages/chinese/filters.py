"""
中文 corrector：規則與過濾器

此模組包含：
- 受保護詞遮罩 (protection mask)
- segment/span 驗證與排除條件
- 上下文 keyword/exclude_when 判斷與加分距離

設計原則：
- 優先做「便宜 pruning」：先排除不可能/不應替換的區段，降低後續 similarity 計算成本
- 多數函式保持純函式風格（輸入 -> 輸出），方便單元測試與重用
"""

from __future__ import annotations

import re
from typing import Any

from phonofix.utils.aho_corasick import AhoCorasick


def check_context_bonus(
    *,
    full_text: str,
    start_idx: int,
    end_idx: int,
    keywords: list[str],
    window_size: int = 10,
) -> tuple[bool, float | None]:
    """
    檢查上下文關鍵字加分

    若在修正目標附近的視窗內發現相關關鍵字，則給予額外加分 (降低距離分數)。
    這有助於區分同音異義詞。
    """
    if not keywords:
        return False, None

    ctx_start = max(0, start_idx - window_size)
    ctx_end = min(len(full_text), end_idx + window_size)
    context_text = full_text[ctx_start:ctx_end]
    min_distance: float | None = None
    for kw in keywords:
        kw_idx = context_text.find(kw)
        if kw_idx == -1:
            continue

        kw_abs_pos = ctx_start + kw_idx
        if kw_abs_pos < start_idx:
            distance = start_idx - (kw_abs_pos + len(kw))
        elif kw_abs_pos >= end_idx:
            distance = kw_abs_pos - end_idx
        else:
            distance = 0

        if min_distance is None or distance < min_distance:
            min_distance = float(distance)

    if min_distance is not None:
        return True, min_distance
    return False, None


def build_protection_mask(
    *,
    text: str,
    protected_terms: set[str],
    protected_matcher: AhoCorasick[str] | None,
) -> set[int]:
    """
    建立保護遮罩，標記不應被修正的區域 (受保護的詞彙)

    - 若有提供 `protected_matcher`（Aho-Corasick），用它做線性掃描找出所有 match span
    - 否則退回用 `re.finditer`，功能相同但在 protected_terms 很多時較慢
    """
    protected_indices: set[int] = set()
    if not protected_terms:
        return protected_indices

    if protected_matcher is None:
        for protected_term in protected_terms:
            if not protected_term:
                continue
            for match in re.finditer(re.escape(protected_term), text):
                protected_indices.update(range(match.start(), match.end()))
        return protected_indices

    for start, end, _word, _value in protected_matcher.iter_matches(text):
        protected_indices.update(range(start, end))
    return protected_indices


def is_segment_protected(*, start_idx: int, word_len: int, protected_indices: set[int]) -> bool:
    """檢查特定片段是否包含受保護的索引"""
    for idx in range(start_idx, start_idx + word_len):
        if idx in protected_indices:
            return True
    return False


def is_span_protected(*, start: int, end: int, protected_indices: set[int]) -> bool:
    """
    檢查 span 是否命中保護遮罩。

    Args:
        start: span 起點（含）
        end: span 終點（不含）
        protected_indices: 保護遮罩索引集合
    """
    for idx in range(start, end):
        if idx in protected_indices:
            return True
    return False


def is_valid_segment(*, segment: str) -> bool:
    """檢查片段是否包含有效字符 (中文、英文、數字)"""
    if re.search(r"[^a-zA-Z0-9\u4e00-\u9fff]", segment):
        return False
    return True


def should_exclude_by_context(*, full_text: str, exclude_when: list[str]) -> bool:
    """
    檢查是否應根據上下文排除修正

    策略:
    - 如果沒有定義 exclude_when，則不排除
    - 如果有定義 exclude_when，則文本中包含任一排除條件就排除
    """
    if not exclude_when:
        return False

    full_text_lower = full_text.lower()
    for condition in exclude_when:
        if condition.lower() in full_text_lower:
            return True
    return False


def has_required_keyword(*, full_text: str, keywords: list[str]) -> bool:
    """
    檢查是否滿足關鍵字必要條件

    策略:
    - 如果沒有定義 keywords，則無條件通過
    - 如果有定義 keywords，則文本中必須包含至少一個關鍵字
    """
    if not keywords:
        return True

    full_text_lower = full_text.lower()
    for kw in keywords:
        if kw.lower() in full_text_lower:
            return True
    return False

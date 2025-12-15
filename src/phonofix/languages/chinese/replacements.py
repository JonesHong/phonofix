"""
中文 corrector：候選衝突解決與替換套用

說明：
- 本模組不做「候選產生/打分」；只處理結果集合的去衝突與套用
- 預設策略：分數越低越好（同既有行為），重疊時只保留最佳者
"""

from __future__ import annotations

from typing import Callable

from .types import ChineseCandidate


def resolve_conflicts(*, candidates: list[ChineseCandidate]) -> list[ChineseCandidate]:
    """
    解決候選衝突

    當多個候選修正重疊時，選擇分數最低 (最佳) 的候選。
    """
    candidates.sort(key=lambda x: x["score"])
    final_candidates: list[ChineseCandidate] = []
    for cand in candidates:
        is_conflict = False
        for accepted in final_candidates:
            if max(cand["start"], accepted["start"]) < min(cand["end"], accepted["end"]):
                is_conflict = True
                break
        if not is_conflict:
            final_candidates.append(cand)
    return final_candidates


def apply_replacements(
    *,
    text: str,
    final_candidates: list[ChineseCandidate],
    emit_replacement: Callable[[ChineseCandidate], None] | Callable[..., None],
    silent: bool = False,
    trace_id: str | None = None,
) -> str:
    """
    應用修正並輸出事件/日誌

    注意：
    - 必須由後往前套用（start 反向排序），否則前面的替換會改變後面候選的索引
    - 事件 emission 在這裡做，確保最終採用的候選與實際輸出一致
    """
    final_candidates.sort(key=lambda x: x["start"], reverse=True)
    final_text_list = list(text)
    for cand in final_candidates:
        emit_replacement(cand, silent=silent, trace_id=trace_id)
        final_text_list[cand["start"] : cand["end"]] = list(cand["replacement"])
    return "".join(final_text_list)

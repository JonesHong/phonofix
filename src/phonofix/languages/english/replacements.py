"""
英文 corrector：候選衝突解決與替換套用

說明：
- 本模組不做「候選產生/打分」；只處理結果集合的去衝突與套用
- 預設策略：分數越低越好（同既有行為），重疊時只保留最佳者
"""

from __future__ import annotations

from typing import Any, Callable

from .types import EnglishCandidate


def resolve_conflicts(*, candidates: list[EnglishCandidate]) -> list[EnglishCandidate]:
    """
    解決候選衝突

    當多個候選修正重疊時，選擇分數最低 (最佳) 的候選。
    """
    candidates.sort(key=lambda x: x["score"])

    final_candidates: list[EnglishCandidate] = []
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
    candidates: list[EnglishCandidate],
    emit_replacement: Callable[..., None],
    logger: Any,
    silent: bool = False,
    trace_id: str | None = None,
) -> str:
    """
    應用修正並輸出日誌

    注意：
    - candidates 會先依 start 由小到大排序，透過「重建字串」避免索引偏移問題
    - 事件 emission 在這裡做，確保最終採用的候選與實際輸出一致
    """
    candidates.sort(key=lambda x: x["start"])

    result: list[str] = []
    last_pos = 0
    for cand in candidates:
        result.append(text[last_pos : cand["start"]])
        result.append(cand["replacement"])

        emit_replacement(cand, silent=silent, trace_id=trace_id)

        logger.debug(
            f"  [Match] '{cand['original']}' -> '{cand['replacement']}' "
            f"(via '{cand['alias']}', score={cand['score']:.3f})"
        )

        last_pos = cand["end"]

    result.append(text[last_pos:])
    return "".join(result)

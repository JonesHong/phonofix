"""
日文 corrector：候選衝突解決與替換套用

說明：
- 本模組不做「候選產生/打分」；只處理結果集合的去衝突與套用
- 預設策略：分數越低越好（同既有行為），重疊時只保留最佳者
"""

from __future__ import annotations

from typing import Any, Callable

from .types import JapaneseCandidate


def resolve_conflicts(*, candidates: list[JapaneseCandidate], logger: Any | None = None) -> list[JapaneseCandidate]:
    """解決候選衝突（越低分越優先）"""
    # 優先順序：
    # 1) 分數越低越優先（既有行為）
    # 2) 分數相同時，優先保留「跨度更長」的候選，避免短 alias 吃掉長 alias
    #    典型案例：
    #    - ai 命中在 kaihatsu 內
    #    - asupirin 命中在 asupirinn 內
    candidates.sort(key=lambda x: (x["score"], -(int(x["end"]) - int(x["start"]))))

    final_candidates: list[JapaneseCandidate] = []
    for cand in candidates:
        is_conflict = False
        for accepted in final_candidates:
            if max(cand["start"], accepted["start"]) < min(cand["end"], accepted["end"]):
                is_conflict = True
                break
        if not is_conflict:
            final_candidates.append(cand)
        elif logger is not None:
            logger.debug(
                f"Conflict resolved: Dropped '{cand['original']}' (score={cand['score']}) in favor of existing match"
            )

    return final_candidates


def apply_replacements(
    *,
    text: str,
    candidates: list[JapaneseCandidate],
    emit_replacement: Callable[..., None],
    logger: Any,
    silent: bool = False,
    trace_id: str | None = None,
) -> str:
    """
    應用修正並輸出日誌（重建字串避免索引偏移）

    注意：
    - 必須以「重建字串」或「反向套用」處理索引偏移；此處採重建字串，行為較直觀
    - 事件 emission 在這裡做，確保最終採用的候選與實際輸出一致
    """
    candidates.sort(key=lambda x: x["start"])

    result: list[str] = []
    last_pos = 0
    for cand in candidates:
        # 如果原文與替換文相同，則不進行替換操作，但它佔用了位置防止錯誤修正
        if cand["original"] == cand["replacement"]:
            continue

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

"""
英文 corrector：計分

集中管理：
- 最終 score 計算（越低越好）

說明：
- 英文 similarity（IPA 產生 + fuzzy 規則）在 `EnglishPhoneticSystem` 中完成
- 本模組只處理「如何把 error_ratio 轉成最終排序分數」的政策層
"""

from __future__ import annotations

from typing import Any


def calculate_final_score(
    *,
    error_ratio: float,
    item: dict[str, Any],
    has_context: bool,
    context_distance: float | None = None,
) -> float:
    """
    計算最終分數 (越低越好)

    公式: 錯誤率 - 詞彙權重 - 上下文加分
    """
    final_score = float(error_ratio)
    final_score -= float(item["weight"])
    if has_context and context_distance is not None:
        # 上下文加分邏輯：距離越近，加分越多 (最大 0.8)
        distance_factor = 1.0 - (min(float(context_distance), 50.0) / 50.0 * 0.6)
        context_bonus = 0.8 * distance_factor
        final_score -= context_bonus
    return float(final_score)

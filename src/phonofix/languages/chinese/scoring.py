"""
中文 corrector：計分與相似度

集中管理：
- dynamic threshold
- initials pruning
- pinyin similarity（含特殊音節/韻母模糊/Levenshtein）
- 最終 score 計算

效能備註：
- 拼音/聲母計算本身由 `ChinesePhoneticBackend` 提供快取（避免重複呼叫 pypinyin）
- 但在窗口掃描中，仍會在外層預先算好 `segment_initials/segment_syllables` 並傳入，
  以避免同一窗口對多個 item 重複取值（即使有快取，也能減少 Python 層 overhead）。
"""

from __future__ import annotations

from typing import Any

import Levenshtein


def get_dynamic_threshold(*, word_len: int, is_mixed: bool = False) -> float:
    """
    根據詞長動態計算容錯率閾值

    策略:
    - 混合語言詞彙 (如 "C語言"): 容錯率較高 (0.45)
    - 短詞 (<=2): 容錯率低 (0.20)，避免誤匹配
    - 中詞 (3): 容錯率中 (0.30)
    - 長詞 (>3): 容錯率高 (0.40)
    """
    if is_mixed:
        return 0.45
    if word_len <= 2:
        return 0.20
    if word_len == 3:
        return 0.30
    return 0.40


def calculate_pinyin_similarity(
    *,
    engine: Any,
    config: Any,
    utils: Any,
    segment: str,
    target_pinyin_str: str,
    segment_syllables: tuple[str, ...] | None = None,
    target_syllables: tuple[str, ...] | None = None,
) -> tuple[str, float, bool]:
    """
    計算拼音相似度

    結合多種策略:
    1. 特殊音節映射 (如 hua <-> fa)
    2. 韻母模糊匹配 (如 in <-> ing)
    3. Levenshtein 編輯距離

    Returns:
        (str, float, bool): (視窗拼音字串, 錯誤率, 是否為模糊匹配)

    註：
    - 目前 drafts 不保存 `window_pinyin_str`（避免增加資料量），但這個回傳值保留：
      後續若要在 trace/event 中輸出 debug 資訊或做更進階 scoring，可直接使用。
    """
    backend = engine.backend
    window_pinyin_str = backend.to_phonetic(segment)
    target_pinyin_lower = target_pinyin_str.lower()

    # 快速路徑：完全匹配
    if window_pinyin_str == target_pinyin_lower:
        return window_pinyin_str, 0.0, True

    # 音節級特殊音節映射（例如 hua <-> fa），避免「整串拼音」比對失效
    if (
        segment_syllables
        and target_syllables
        and len(segment_syllables) == len(target_syllables)
        and len(segment_syllables) <= 4
    ):
        syllable_map = config.SPECIAL_SYLLABLE_MAP_UNIDIRECTIONAL
        ok = True
        for seg_syl, tgt_syl in zip(segment_syllables, target_syllables):
            if seg_syl == tgt_syl:
                continue
            if tgt_syl not in (syllable_map.get(seg_syl) or ()):
                ok = False
                break
        if ok:
            return window_pinyin_str, 0.0, True

    # 特殊音節匹配
    if len(segment) >= 2 and len(target_pinyin_lower) < 10:
        if utils.check_special_syllable_match(window_pinyin_str, target_pinyin_lower, bidirectional=False):
            return window_pinyin_str, 0.0, True

    # 韻母模糊匹配
    if utils.check_finals_fuzzy_match(window_pinyin_str, target_pinyin_lower):
        return window_pinyin_str, 0.1, True

    # Levenshtein 編輯距離
    dist = Levenshtein.distance(window_pinyin_str, target_pinyin_lower)
    max_len = max(len(window_pinyin_str), len(target_pinyin_lower))
    error_ratio = dist / max_len if max_len > 0 else 0.0
    return window_pinyin_str, float(error_ratio), False


def check_initials_match(
    *,
    engine: Any,
    config: Any,
    utils: Any,
    segment: str,
    item: dict[str, Any],
    segment_initials: tuple[str, ...] | None = None,
) -> bool:
    """
    檢查聲母是否匹配

    策略:
    - 短詞 (<=3): 所有聲母都必須模糊匹配
    - 長詞 (>3): 至少第一個聲母必須模糊匹配，避免 "在北車用" 被誤匹配到 "台北車站"
    """
    word_len = int(item["len"])
    if bool(item.get("is_mixed")):
        return True  # 混合語言詞跳過聲母檢查

    backend = engine.backend
    window_initials = list(segment_initials if segment_initials is not None else backend.get_initials(segment))

    if word_len <= 3:
        if not utils.is_fuzzy_initial_match(window_initials, item["initials"]):
            return False
    else:
        if window_initials and item["initials"]:
            first_window = window_initials[0]
            first_target = item["initials"][0]
            if first_window != first_target:
                group1 = config.FUZZY_INITIALS_MAP.get(first_window)
                group2 = config.FUZZY_INITIALS_MAP.get(first_target)
                if not (group1 and group2 and group1 == group2):
                    return False
    return True


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
        distance_factor = 1.0 - (float(context_distance) / 10.0 * 0.6)
        context_bonus = 0.8 * distance_factor
        final_score -= context_bonus
    return float(final_score)

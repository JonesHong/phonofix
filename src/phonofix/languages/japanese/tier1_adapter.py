"""ja Tier 1 adapter — normalized_cache hash lookup + dakuten/handakuten variant.

PhoneticMatcher will lookup this module's `apply` function via importlib dispatch.

日文 confusion 重點：
- 濁音 (dakuten ゛): が/か, ざ/さ, だ/た, ば/は, etc.
- 半濁音 (handakuten ゜): ぱ/ば/は
- 促音 (small つ): 表示 gemination, ASR 常 misalign
- 長音 (ー / おお / おう): 拼寫變體
- 漢字音讀/訓讀同字異音
"""

from __future__ import annotations

from typing import Iterable

# cutlet 把日文 → romaji
try:
    import cutlet

    _katsu = cutlet.Cutlet()
    _HAS_CUTLET = True
except (ImportError, Exception):
    _katsu = None
    _HAS_CUTLET = False

# 濁音/半濁音 → 清音 normalize map (僅 Tier 1 fallback 用)
DAKUTEN_NORMALIZE = {
    "が": "か",
    "ぎ": "き",
    "ぐ": "く",
    "げ": "け",
    "ご": "こ",
    "ざ": "さ",
    "じ": "し",
    "ず": "す",
    "ぜ": "せ",
    "ぞ": "そ",
    "だ": "た",
    "ぢ": "ち",
    "づ": "つ",
    "で": "て",
    "ど": "と",
    "ば": "は",
    "び": "ひ",
    "ぶ": "ふ",
    "べ": "へ",
    "ぼ": "ほ",
    "ぱ": "は",
    "ぴ": "ひ",
    "ぷ": "ふ",
    "ぺ": "へ",
    "ぽ": "ほ",
    # Katakana
    "ガ": "カ",
    "ギ": "キ",
    "グ": "ク",
    "ゲ": "ケ",
    "ゴ": "コ",
    "ザ": "サ",
    "ジ": "シ",
    "ズ": "ス",
    "ゼ": "セ",
    "ゾ": "ソ",
    "ダ": "タ",
    "ヂ": "チ",
    "ヅ": "ツ",
    "デ": "テ",
    "ド": "ト",
    "バ": "ハ",
    "ビ": "ヒ",
    "ブ": "フ",
    "ベ": "ヘ",
    "ボ": "ホ",
    "パ": "ハ",
    "ピ": "ヒ",
    "プ": "フ",
    "ペ": "ヘ",
    "ポ": "ホ",
}


def _dakuten_normalize(text: str) -> str:
    """濁音/半濁音 → 清音 (Tier 1 'tolerant' key)."""
    return "".join(DAKUTEN_NORMALIZE.get(c, c) for c in text)


def _text_to_romaji(text: str) -> str:
    """日文 → romaji via cutlet (degraded mode: identity)."""
    if not _HAS_CUTLET or _katsu is None:
        return text
    try:
        return _katsu.romaji(text)
    except Exception:
        return text


def build_index(aliases: Iterable[str]) -> dict[str, list[str]]:
    """
    Build {normalized_key → [original aliases]} index.

    normalized_key = romaji-normalize(dakuten-normalize(alias)).strip().lower()
    """
    idx: dict[str, list[str]] = {}
    for alias in aliases:
        normalized = _text_to_romaji(_dakuten_normalize(alias)).strip().lower()
        if not normalized:
            continue
        idx.setdefault(normalized, []).append(alias)
    return idx


def apply(text: str, index: dict) -> list[tuple[int, int, str, str]]:
    """
    Sliding window over text. Returns (start, end, matched_text, original_alias) list.
    Only fires when substr != alias (literal AC already covers exact match).
    """
    if not index:
        return []

    # Estimate alias length range from existing dict values (max length of original alias)
    alias_lens = {len(orig) for origs in index.values() for orig in origs}
    if not alias_lens:
        return []
    min_len, max_len = min(alias_lens), max(alias_lens)

    hits = []
    for length in range(min_len, max_len + 1):
        for start in range(len(text) - length + 1):
            substr = text[start : start + length]
            normalized = _text_to_romaji(_dakuten_normalize(substr)).strip().lower()
            if not normalized:
                continue
            if normalized in index:
                for alias in index[normalized]:
                    if substr != alias:  # skip literal-AC-covered
                        hits.append((start, start + length, substr, alias))
    return hits

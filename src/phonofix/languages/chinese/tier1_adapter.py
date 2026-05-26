"""zh Tier 1 adapter — pinyin canonical_key hash lookup.

PhoneticMatcher imports `build_index` + `apply` via per-language dispatch.

中文 confusion 重點（既有 FUZZY_INITIALS_MAP + FUZZY_FINALS_PAIRS + SPECIAL_SYLLABLE_MAP）:
- 聲母混淆: n/l, f/h, r/l, 捲舌/平舌, 送氣/不送氣
- 韻母混淆: in/ing, en/eng, an/ang, etc.
- 特例音節: e.g. fa↔hua
"""

from __future__ import annotations

from typing import Iterable

from phonofix.languages.chinese.canonical_key import canonical_key_for_phrase

try:
    from pypinyin import Style, pinyin

    _HAS_PYPINYIN = True
except ImportError:
    _HAS_PYPINYIN = False


def _text_to_pinyin(text: str) -> str:
    """Convert Chinese text to space-separated pinyin (no tones)."""
    if not _HAS_PYPINYIN:
        return ""
    return " ".join(p[0] for p in pinyin(text, style=Style.NORMAL, errors="ignore"))


def build_index(aliases: Iterable[str]) -> dict:
    """Build {canonical_key_tuple → [original aliases]} index."""
    if not _HAS_PYPINYIN:
        return {}
    idx: dict[tuple, list[str]] = {}
    for alias in aliases:
        py = _text_to_pinyin(alias)
        if not py.strip():
            continue
        key = canonical_key_for_phrase(py)
        idx.setdefault(key, []).append(alias)
    return idx


def apply(text: str, index: dict) -> list[tuple[int, int, str, str]]:
    """Sliding window; emit (start, end, matched, original_alias) when canonical_key matches.

    Skip literal exact (covered by AC literal layer).
    """
    if not _HAS_PYPINYIN or not index:
        return []

    alias_lens = {len(orig) for origs in index.values() for orig in origs}
    if not alias_lens:
        return []
    min_len, max_len = min(alias_lens), max(alias_lens)

    hits: list[tuple[int, int, str, str]] = []
    for length in range(min_len, max_len + 1):
        for start in range(len(text) - length + 1):
            substr = text[start : start + length]
            py = _text_to_pinyin(substr)
            if not py.strip():
                continue
            key = canonical_key_for_phrase(py)
            if key in index:
                for alias in index[key]:
                    if substr != alias:
                        hits.append((start, start + length, substr, alias))
    return hits

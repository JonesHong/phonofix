"""ko Tier 1 adapter — jamo decompose + confusion-aware hash lookup.

韓文 confusion 重點：
- Aspiration triad: ᄀ↔ᄏ↔ᄁ, ᄃ↔ᄐ↔ᄄ, ᄇ↔ᄑ↔ᄈ, ᄌ↔ᄎ↔ᄍ (Paper [1][4])
- Vowel formant: ᅢ↔ᅦ, ᅥ↔ᅩ, ᅳ↔ᅮ, ᅵ↔ᅮ, ᅱ↔ᅴ (Zeroth real-data)
- 받침 (coda): ᆫ↔ᆼ + omission
- 複합 jongseong: ᆲ↔ᇀ, ᆶ↔ᆯ

策略: alias 拆成 jamo sequence, 用 confusion map normalize 每 jamo 變 canonical
form (取每組 confusable 中字典序最小)，hash lookup。
"""

from __future__ import annotations

from typing import Iterable

from phonofix.languages.korean.confusion_rules import KOREAN_CONFUSION_MAP_JAMO
from phonofix.languages.korean.phonemizer import decompose_hangul


def _jamo_canonical(jamo: str) -> str:
    """
    For each jamo, return the canonical representative of its confusable set.
    Canonical = lexicographically smallest among {jamo} ∪ confusions.
    """
    if not jamo:
        return jamo
    confusable = KOREAN_CONFUSION_MAP_JAMO.get(jamo, set()) | {jamo}
    return min(confusable)


def _syllable_canonical(syllable: str) -> tuple[str, str, str]:
    """Decompose syllable → canonicalize each jamo."""
    cho, jung, jong = decompose_hangul(syllable)
    return (_jamo_canonical(cho), _jamo_canonical(jung), _jamo_canonical(jong))


def _text_canonical_key(text: str) -> tuple:
    """Convert Korean text to canonical jamo-triple sequence (tuple for hash)."""
    parts = []
    for ch in text:
        cho, jung, jong = decompose_hangul(ch)
        if cho:  # is hangul
            parts.append(_syllable_canonical(ch))
        else:
            # non-hangul: keep as-is (avoid collapse 跨 ASCII)
            parts.append((ch, "", ""))
    return tuple(parts)


def build_index(aliases: Iterable[str]) -> dict:
    """
    Build {canonical_jamo_key → [original aliases]} index.
    Confusable Korean syllables → same canonical key → hash match.
    """
    idx: dict[tuple, list[str]] = {}
    for alias in aliases:
        key = _text_canonical_key(alias)
        if not key:
            continue
        idx.setdefault(key, []).append(alias)
    return idx


def apply(text: str, index: dict) -> list[tuple[int, int, str, str]]:
    """
    Char-level sliding window over Korean text.
    Returns (start, end, matched_text, original_alias) list.
    Skip literal AC hits (substr == alias).
    """
    if not index:
        return []

    # Length range from alias originals
    alias_lens = {len(orig) for origs in index.values() for orig in origs}
    if not alias_lens:
        return []
    min_len, max_len = min(alias_lens), max(alias_lens)

    hits = []
    for length in range(min_len, max_len + 1):
        for start in range(len(text) - length + 1):
            substr = text[start : start + length]
            key = _text_canonical_key(substr)
            if key in index:
                for alias in index[key]:
                    if substr != alias:  # skip literal-AC-covered exact
                        hits.append((start, start + length, substr, alias))
    return hits

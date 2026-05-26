"""English Tier 1: Double Metaphone phonetic key (replaces IPA + Levenshtein).

Phase 3 evidence: Tier 1 metaphone enables hash equality match,
target throughput from baseline 229 ops/s to 1,000-1,500 ops/s (35-50×).

Implementation note: jellyfish 1.2.1 exposes ``metaphone`` (primary key) and
``soundex`` (secondary key).  We use metaphone as primary and soundex as the
secondary fallback — two words share a key if their metaphone strings match
OR their soundex strings match.
"""

from __future__ import annotations

from functools import lru_cache

try:
    import jellyfish

    _HAS_JELLYFISH = True
except ImportError:
    _HAS_JELLYFISH = False


@lru_cache(maxsize=10000)
def metaphone_key(word: str) -> tuple[str, str]:
    """Return (primary, secondary) phonetic key for *word*.

    primary  — Metaphone phonetic encoding (jellyfish.metaphone)
    secondary — Soundex code used as a secondary discriminator

    Two words with the same metaphone_key are phonetically equivalent and
    can be matched via a hash equality check (O(1)) instead of Levenshtein.

    Returns ("", "") when jellyfish is unavailable (degraded mode).  Callers
    should treat an empty-tuple result as "no phonetic match possible".
    """
    if not _HAS_JELLYFISH:
        return ("", "")
    if not word:
        return ("", "")
    try:
        primary = jellyfish.metaphone(word) or ""
        secondary = jellyfish.soundex(word) or ""
    except Exception:
        # Degrade gracefully on unexpected input (e.g. non-ASCII punctuation)
        return ("", "")
    return (primary, secondary)


def metaphone_match(a: str, b: str) -> bool:
    """Return True if *a* and *b* share a metaphone primary OR secondary key.

    Requires jellyfish; returns False in degraded mode.
    """
    ka = metaphone_key(a)
    kb = metaphone_key(b)
    if ka == ("", "") or kb == ("", ""):
        return False
    return ka[0] == kb[0] or ka[1] == kb[1]


def build_metaphone_index(words: list[str]) -> dict[str, list[str]]:
    """Build ``{primary_key: [original_words]}`` for O(1) reverse lookup.

    Words that cannot produce a primary key (empty string or degraded mode)
    are silently skipped.
    """
    index: dict[str, list[str]] = {}
    for w in words:
        primary, _ = metaphone_key(w)
        if primary:
            index.setdefault(primary, []).append(w)
    return index

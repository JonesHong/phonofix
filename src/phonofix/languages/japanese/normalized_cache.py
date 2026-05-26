"""Japanese Tier 1: build-time normalized key + per-window equality cache.

Codex POC (2026-05-26): 87.79x hot-loop speedup (5.04s -> 0.057s on 200 dict / 100 chars).
Recall trade-off: hits drop from 2,250 to 500 -> must combine with Tier 2 mutation set (Phase 3 W4).

Strategy:
- build_normalized_index(): precompute normalized key for every dict item at build time
- normalize_query_window(): LRU-cached per-window normalization (avoids re-compute in hot loop)
- lookup_normalized(): O(1) hash lookup — Tier 1 fast path
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .config import JapanesePhoneticConfig

# ---------------------------------------------------------------------------
# Internal normalization — mirrors JapanesePhoneticSystem._normalize_phonetic
# but as a pure module-level function so it can be used by lru_cache.
# We intentionally do NOT use str.translate; we use plain str.replace to match
# the existing dict-based rule set exactly (no str.translate needed).
# ---------------------------------------------------------------------------


def _normalize_phonetic_internal(phonetic: str) -> str:
    """Apply all JapanesePhoneticConfig normalization rules via str.replace.

    Rules applied (in order):
    1. ROMANIZATION_VARIANTS  — si->shi, sya->sha, la->ra, etc.
    2. FUZZY_LONG_VOWELS      — aa->a, ou->o, etc.
    3. FUZZY_GEMINATION       — kk->k, tt->t, etc.
    4. FUZZY_NASALS           — mb->nb, etc.

    All 46+ rules are handled via dict lookup (str.replace), never str.translate.
    """
    normalized = phonetic.lower()

    # 1. Romanization variants
    for variant, standard in JapanesePhoneticConfig.ROMANIZATION_VARIANTS.items():
        normalized = normalized.replace(variant, standard)

    # 2. Long vowel collapsing
    for long_vowel, short_vowel in JapanesePhoneticConfig.FUZZY_LONG_VOWELS.items():
        normalized = normalized.replace(long_vowel, short_vowel)

    # 3. Gemination simplification
    for geminated, single in JapanesePhoneticConfig.FUZZY_GEMINATION.items():
        normalized = normalized.replace(geminated, single)

    # 4. Nasal normalization
    for nasal_variant, standard in JapanesePhoneticConfig.FUZZY_NASALS.items():
        normalized = normalized.replace(nasal_variant, standard)

    return normalized


# ---------------------------------------------------------------------------
# Immutable record for a pre-normalized dict entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class JaNormalizedItem:
    """A dict alias/canonical pair with its pre-computed normalized key.

    Attributes:
        original:   The raw alias text as provided by the caller (used for backfill).
        normalized: _normalize_phonetic_internal(original) — the index key.
        canonical:  The canonical display string to substitute into output.
    """

    original: str
    normalized: str
    canonical: str


# ---------------------------------------------------------------------------
# Build-time index construction
# ---------------------------------------------------------------------------


def build_normalized_index(
    items: list[tuple[str, str]],
) -> dict[str, list[JaNormalizedItem]]:
    """Precompute a normalized-key index at build time.

    Args:
        items: [(alias_text, canonical_text), ...]
                alias_text   — the variant/alias to match against
                canonical_text — the display string to emit on match

    Returns:
        {normalized_key: [JaNormalizedItem, ...]}

    Two aliases that normalize to the same key share the same bucket, so a
    single O(1) lookup at query time returns all matching items.

    Example:
        build_normalized_index([("シヤ", "シャ"), ("sya", "sha")])
        # both "シヤ" and "sya" normalize to "sha" -> one bucket, two items
    """
    index: dict[str, list[JaNormalizedItem]] = {}
    for alias, canonical in items:
        norm_key = _normalize_phonetic_internal(alias)
        item = JaNormalizedItem(
            original=alias,
            normalized=norm_key,
            canonical=canonical,
        )
        index.setdefault(norm_key, []).append(item)
    return index


# ---------------------------------------------------------------------------
# Per-window cached normalization (hot-loop fast path)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=8192)
def normalize_query_window(text_window: str) -> str:
    """Normalize a query window with LRU caching.

    Caches up to 8192 distinct windows — sufficient for streaming (short
    windows repeat often) and batch (total unique windows bounded by text
    length).

    Args:
        text_window: A raw text slice from the sliding window.

    Returns:
        The normalized string (same rules as build_normalized_index).
    """
    return _normalize_phonetic_internal(text_window)


# ---------------------------------------------------------------------------
# Tier 1 fast-path lookup
# ---------------------------------------------------------------------------


def lookup_normalized(
    index: dict[str, list[JaNormalizedItem]],
    query_window: str,
) -> list[JaNormalizedItem]:
    """O(1) hash lookup — Tier 1 fast path.

    Normalizes query_window (via LRU cache) then returns all matching
    JaNormalizedItem records from the pre-built index.

    Args:
        index:        Built by build_normalized_index().
        query_window: Raw text slice to look up.

    Returns:
        List of matching JaNormalizedItem (empty list on miss).
    """
    return index.get(normalize_query_window(query_window), [])

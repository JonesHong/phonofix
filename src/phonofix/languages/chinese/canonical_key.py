"""Chinese Tier 1: canonical key collapse — hash equality replaces Levenshtein.

Core idea (from algorithm-upgrade-evidence.md §Tier 1):
  FUZZY_INITIALS_MAP / FUZZY_FINALS_PAIRS / SPECIAL_SYLLABLE_MAP already encode group
  membership. Instead of computing Levenshtein distance between two fuzzy syllables,
  collapse each syllable to a deterministic *canonical token* so that phonetically
  equivalent syllables produce the exact same string → hash equality O(1) match.

Apply order per syllable:
  1. SPECIAL_SYLLABLE_MAP_BIDIRECTIONAL override  (whole-syllable alias → canonical)
  2. FUZZY_INITIALS_MAP  (initial → group-id)
  3. FUZZY_FINALS_PAIRS  (final suffix → canonical suffix of the pair)

Two syllables with the same canonical_token() are phonetically equivalent under the
fuzzy rules defined in ChinesePhoneticConfig.
"""

from __future__ import annotations

from functools import lru_cache

from .config import ChinesePhoneticConfig

# ---------------------------------------------------------------------------
# Build-time lookup tables (module-level, constructed once)
# ---------------------------------------------------------------------------


# Whole-syllable canonical map:
# For each syllable that appears in SPECIAL_SYLLABLE_MAP_BIDIRECTIONAL,
# find its connected component (BFS), then choose the lex-min member as canonical.
# Example: {"fa": ["hua"], "hua": ["fa"]} → both collapse to "fa"  (lex min)
def _build_special_canonical_map() -> dict[str, str]:
    """Build syllable → canonical-syllable mapping from the bidirectional map."""
    bidir = ChinesePhoneticConfig.SPECIAL_SYLLABLE_MAP_BIDIRECTIONAL
    # Collect all nodes and adjacency
    adj: dict[str, set[str]] = {}
    for src, targets in bidir.items():
        adj.setdefault(src, set()).update(targets)
        for t in targets:
            adj.setdefault(t, set()).add(src)

    visited: set[str] = set()
    result: dict[str, str] = {}
    for node in sorted(adj):  # sorted → deterministic BFS start order
        if node in visited:
            continue
        # BFS to find connected component
        component: list[str] = []
        queue = [node]
        while queue:
            cur = queue.pop()
            if cur in visited:
                continue
            visited.add(cur)
            component.append(cur)
            for neighbour in adj.get(cur, ()):
                if neighbour not in visited:
                    queue.append(neighbour)
        canonical = min(component)  # lex-min = deterministic canonical for this group
        for member in component:
            result[member] = canonical
    return result


# Finals canonical map:
# For each pair (f1, f2) in FUZZY_FINALS_PAIRS, the canonical suffix is min(f1, f2).
# We build: suffix → canonical_suffix
def _build_finals_canonical_map() -> dict[str, str]:
    result: dict[str, str] = {}
    for f1, f2 in ChinesePhoneticConfig.FUZZY_FINALS_PAIRS:
        canonical_suffix = min(f1, f2)
        # Both members collapse to the same canonical suffix
        result[f1] = canonical_suffix
        result[f2] = canonical_suffix
    return result


_SPECIAL_CANONICAL: dict[str, str] = _build_special_canonical_map()
_FINALS_CANONICAL: dict[str, str] = _build_finals_canonical_map()
_INITIALS_ORDER = [
    # two-char initials must come before one-char to match greedily
    "zh",
    "ch",
    "sh",
    "b",
    "p",
    "m",
    "f",
    "d",
    "t",
    "n",
    "l",
    "g",
    "k",
    "h",
    "j",
    "q",
    "x",
    "z",
    "c",
    "s",
    "r",
    "y",
    "w",
]


def _split_initial_final(syllable: str) -> tuple[str, str]:
    """Split a bare pinyin syllable into (initial, final).  No tone marks assumed."""
    for init in _INITIALS_ORDER:
        if syllable.startswith(init):
            return init, syllable[len(init) :]
    return "", syllable  # zero-initial


def _canonical_initial(initial: str) -> str:
    """Return the group-id for *initial*, or the initial itself if not in any group."""
    return ChinesePhoneticConfig.FUZZY_INITIALS_MAP.get(initial, initial)


def _canonical_final(final: str) -> str:
    """Return the canonical suffix for *final* by collapsing any known fuzzy pair."""
    if not final:
        return final
    # Try matching any registered suffix (longest first for safety)
    for suffix in sorted(_FINALS_CANONICAL, key=len, reverse=True):
        if final.endswith(suffix):
            prefix = final[: -len(suffix)]
            return prefix + _FINALS_CANONICAL[suffix]
    return final


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def canonical_token(pinyin_syllable: str) -> str:
    """Collapse a pinyin syllable to its canonical form.

    Apply order:
      1. SPECIAL_SYLLABLE_MAP_BIDIRECTIONAL override — whole-syllable equivalence
         class collapses to lex-min representative (e.g. "hua"/"fa" → "fa").
      2. FUZZY_INITIALS_MAP — initial collapses to its group-id
         (e.g. "zh"/"z" both → "z_group").
      3. FUZZY_FINALS_PAIRS — final suffix collapses to lex-min of the pair
         (e.g. "ang"/"an" → "an", "ing"/"in" → "in").

    Returns the canonical token string.  Two syllables with the same token are
    phonetically equivalent under the configured fuzzy rules.

    Edge cases:
      - Empty string → returned as-is.
      - Syllables not in any map → unchanged (e.g. standard "ma" → "ma").
      - Tone marks are NOT stripped here; callers should strip tones upstream.
    """
    if not pinyin_syllable:
        return pinyin_syllable

    s = pinyin_syllable.lower().strip()

    # Step 1 — whole-syllable special map (bidirectional equivalence classes)
    if s in _SPECIAL_CANONICAL:
        return _SPECIAL_CANONICAL[s]

    # Step 2 & 3 — split into initial + final, canonicalize each part
    initial, final = _split_initial_final(s)
    c_initial = _canonical_initial(initial)
    c_final = _canonical_final(final)

    return c_initial + "|" + c_final


@lru_cache(maxsize=10_000)
def canonical_key_for_phrase(phrase_pinyin: str) -> tuple[str, ...]:
    """Convert a phrase's space-separated pinyin to a canonical key tuple.

    Two phrases with the same canonical_key_for_phrase() are phonetically
    equivalent under the fuzzy rules → hash equality match, no Levenshtein needed.

    Args:
        phrase_pinyin: Space-separated pinyin syllables, e.g. ``"ni hao"``.

    Returns:
        Tuple of canonical tokens, e.g. ``("n_l_group|i", "h|an")``.
        Empty string input → ``()``.
        Single syllable with no space → 1-element tuple.
    """
    if not phrase_pinyin or not phrase_pinyin.strip():
        return ()
    syllables = phrase_pinyin.strip().split()
    return tuple(canonical_token(s) for s in syllables)

"""Tier 3: AC + delete-1 pattern expansion.

For each alias, register additional patterns with 1 character deleted.
AC scan O(text) finds all hits; phonetic compute only on hits (not sliding window).

Result: phonetic_compute_count drops from text × dict (e.g. 17640) to actual_hits (~10× order).

Codex measured (codex-review-2026-05-26.md):
  delete-1 query ~5× faster than self-impl AC
  memory 100×+ smaller (17.42 MB vs 0.07 MB)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

# import AC adapter from Phase 2
from phonofix.utils.ac_pyahocorasick import ACEngine


@dataclass(frozen=True)
class ExpandedPattern:
    pattern: str  # the actual string registered to AC (may be delete-1 variant)
    original_alias: str  # canonical alias before deletion
    deletion_pos: Optional[int]  # None if no deletion (original), else 0..len-1

    @property
    def is_original(self) -> bool:
        return self.deletion_pos is None


def expand_delete_1(alias: str) -> list[ExpandedPattern]:
    """
    Generate original + all delete-1 variants of an alias.

    "北車" → [ExpandedPattern("北車", "北車", None),
              ExpandedPattern("車", "北車", 0),
              ExpandedPattern("北", "北車", 1)]

    For alias of length N: returns 1 + N patterns.
    Short aliases (len < 2): only original (no deletion).

    Unicode-safe: operates on Python str code-points, not bytes.
    """
    if not alias:
        return []

    result: list[ExpandedPattern] = [
        ExpandedPattern(pattern=alias, original_alias=alias, deletion_pos=None)
    ]

    # Only generate delete-1 variants when alias has ≥ 2 characters
    if len(alias) >= 2:
        for i in range(len(alias)):
            deleted = alias[:i] + alias[i + 1 :]
            result.append(ExpandedPattern(pattern=deleted, original_alias=alias, deletion_pos=i))

    return result


def build_ac_with_expansion(aliases: Iterable[str]) -> ACEngine:
    """
    Build AC engine with original + delete-1 expanded patterns.
    Each pattern's payload is the ExpandedPattern record.
    Caller can identify hits as original vs delete-1 via payload.

    When two ExpandedPatterns produce the same pattern string (e.g. two
    different aliases both delete-1 to the same substring), the last one
    inserted wins (pyahocorasick overwrites duplicate keys).  This is
    acceptable because filter_hits deduplicates by original_alias anyway.
    """
    ac = ACEngine()
    for alias in aliases:
        for ep in expand_delete_1(alias):
            ac.add(ep.pattern, payload=ep)
    ac.build()
    return ac


def filter_hits(
    raw_hits: list[tuple[int, int, str, ExpandedPattern]],
    text: str,
) -> list[tuple[int, int, str, ExpandedPattern]]:
    """
    Post-process AC hits: deduplicate overlapping delete-1 matches of same alias,
    prefer original-pattern hits over delete-1 hits at same span.

    Rules (applied in priority order):
    1. For each unique (original_alias, start) pair, keep only the best hit:
       - prefer is_original over delete-1
       - among delete-1 hits at same start, prefer larger span (longer matched word)
    2. Remove hits that are fully contained within a higher-priority hit of the
       same original_alias.

    Returns a new list sorted by start position.
    """
    if not raw_hits:
        return []

    # Group by (original_alias, start_position); pick best per group
    # Key: (original_alias, start) → best hit so far
    best: dict[tuple[str, int], tuple[int, int, str, ExpandedPattern]] = {}

    for hit in raw_hits:
        start, end, word, ep = hit
        key = (ep.original_alias, start)
        if key not in best:
            best[key] = hit
        else:
            prev = best[key]
            prev_ep = prev[3]
            # Prefer original over delete-1
            if ep.is_original and not prev_ep.is_original:
                best[key] = hit
            elif not ep.is_original and prev_ep.is_original:
                pass  # keep prev
            else:
                # Both same type — prefer longer span
                if (end - start) > (prev[1] - prev[0]):
                    best[key] = hit

    # Deduplicate: for same original_alias, remove hits fully contained in another
    hits_list = sorted(best.values(), key=lambda h: (h[0], -(h[1] - h[0])))

    # Remove hits whose span is fully contained within a wider hit of same alias
    deduped: list[tuple[int, int, str, ExpandedPattern]] = []
    seen_spans: dict[str, list[tuple[int, int]]] = {}

    for hit in hits_list:
        start, end, word, ep = hit
        alias = ep.original_alias
        spans = seen_spans.setdefault(alias, [])
        contained = any(s <= start and end <= e for s, e in spans)
        if not contained:
            deduped.append(hit)
            spans.append((start, end))

    return sorted(deduped, key=lambda h: h[0])

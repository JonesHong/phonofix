"""Tests for Tier 2 mutation set pre-compute (src/phonofix/core/mutation_set.py)."""

from __future__ import annotations

import time

import pytest

from phonofix.core.mutation_set import (
    MutationEntry,
    build_mutation_index,
    lookup_mutation,
)

# ---------------------------------------------------------------------------
# Mock helpers (inline, deterministic)
# ---------------------------------------------------------------------------


def mock_phonemize(text: str) -> list[tuple[str, ...]]:
    """All characters of text form a single phoneme tuple.

    e.g. "ab" → [('a', 'b')]  (one sequence, two phonemes)
    This mirrors real G2P where a word maps to one phoneme sequence.
    """
    return [tuple(text)]


def mock_confusion(p: tuple[str, ...]) -> set[tuple[str, ...]]:
    """
    Simple confusion rule:
      ('a',) → {('e',), ('o',)}
      ('b',) → {('p',)}
    All other phonemes have no confusables.
    """
    table: dict[tuple[str, ...], set[tuple[str, ...]]] = {
        ("a",): {("e",), ("o",)},
        ("b",): {("p",)},
    }
    return table.get(p, set())


def no_confusion(p: tuple[str, ...]) -> set[tuple[str, ...]]:  # noqa: ARG001
    """Confusion function that returns empty set for everything."""
    return set()


# ---------------------------------------------------------------------------
# MutationEntry dataclass properties
# ---------------------------------------------------------------------------


class TestMutationEntry:
    def test_frozen(self):
        entry = MutationEntry(mutation_key="e", canonical_alias="abc", distance=1)
        with pytest.raises((AttributeError, TypeError)):
            entry.mutation_key = "x"  # type: ignore[misc]

    def test_slots(self):
        entry = MutationEntry(mutation_key="e", canonical_alias="abc", distance=1)
        assert not hasattr(entry, "__dict__"), "slots=True should suppress __dict__"

    def test_fields(self):
        entry = MutationEntry(mutation_key="k", canonical_alias="alias", distance=1)
        assert entry.mutation_key == "k"
        assert entry.canonical_alias == "alias"
        assert entry.distance == 1


# ---------------------------------------------------------------------------
# build_mutation_index — structural correctness
# ---------------------------------------------------------------------------


class TestBuildMutationIndex:
    def test_empty_aliases_returns_empty_index(self):
        index = build_mutation_index([], mock_phonemize, mock_confusion)
        assert index == {}

    def test_alias_with_no_confusables_produces_no_entries(self):
        # 'z' has no confusables in mock_confusion
        index = build_mutation_index(["z"], mock_phonemize, no_confusion)
        assert index == {}

    def test_single_alias_single_confusable(self):
        # alias="b" → phonemes=('b',) → confusion({('b',)}) = {('p',)}
        # mutation key = "p", canonical_alias = "b"
        index = build_mutation_index(["b"], mock_phonemize, mock_confusion)
        assert "p" in index
        entries = index["p"]
        assert len(entries) == 1
        assert entries[0].canonical_alias == "b"
        assert entries[0].distance == 1

    def test_single_alias_multiple_confusables(self):
        # alias="a" → confusion({('a',)}) = {('e',), ('o',)} → 2 mutations
        index = build_mutation_index(["a"], mock_phonemize, mock_confusion)
        keys = set(index.keys())
        assert "e" in keys
        assert "o" in keys
        for entries in index.values():
            for entry in entries:
                assert entry.canonical_alias == "a"
                assert entry.distance == 1

    def test_multi_phoneme_alias_generates_correct_count(self):
        # alias="ab":
        #   phonemes = [('a',), ('b',)]
        #   pos 0: ('a',) → confusables {('e',), ('o',)} → keys "e|b", "o|b"
        #   pos 1: ('b',) → confusables {('p',)}          → key  "a|p"
        # total 3 distinct mutation keys
        index = build_mutation_index(["ab"], mock_phonemize, mock_confusion)
        assert "e|b" in index
        assert "o|b" in index
        assert "a|p" in index
        # Each entry points back to canonical alias "ab"
        for entries in index.values():
            for entry in entries:
                assert entry.canonical_alias == "ab"

    def test_n_phonemes_k_confusables_count(self):
        # alias="ba": phonemes [('b',), ('a',)]
        #   pos 0: ('b',) → {('p',)} → 1 mutation  "p|a"
        #   pos 1: ('a',) → {('e',), ('o',)} → 2 mutations "b|e", "b|o"
        # total = 3 mutations
        index = build_mutation_index(["ba"], mock_phonemize, mock_confusion)
        total_entries = sum(len(v) for v in index.values())
        assert total_entries == 3

    def test_two_aliases_share_same_mutation_key(self):
        # alias "ae" pos-0 swap 'a'→'e' gives "e|e"
        # alias "eb" has no 'a' — but let's use alias "ea" pos-0 swap 'e'→? no rule
        # Easier: alias "ab" → "e|b"; alias "eb" → pos-0 'e' no rule, pos-1 'b'→'p' → "e|p"
        # Actually use alias "ab" and "cb" where 'c' confuses to nothing
        # Best: alias1="ab" → "e|b" among others
        #        alias2="ab2" is awkward. Use two aliases that each map to same mutation:
        # alias "ae": phonemes [('a',), ('e',)], pos-0 'a'→'e' → ("e","e") key "e|e"
        # alias "be": phonemes [('b',), ('e',)], pos-0 'b'→'p' → ("p","e") key "p|e"; no "e|e"
        # Let's instead construct directly: alias "ea" no 'a' confusion at pos-0 for 'e'
        # Simplest: mock_confusion('a') → {'e','o'}; so "aa" pos-0 → "e|a", "o|a"; pos-1 → "a|e","a|o"
        # and "ca" (c no rule) pos-1 → "c|e","c|o"
        # Two aliases both yielding "a|e"? "aa"→"a|e" (pos-1 swap) and... "a" → "e" and "o" only
        # Use alias "za" and "xa" — both have 'a' at pos-1 → both produce key "z|e","z|o" / "x|e","x|o"
        # Still no shared key. Use same alias text twice? No.
        # Cleanest: alias1="ab" → mutations include "e|b"; alias2="eb" → pos-1 'b'→'p' → "e|p"
        # not shared. Let's use alias1 = "ab", alias2 = "ab" (identical) → both register to "e|b"
        index = build_mutation_index(["ab", "ab"], mock_phonemize, mock_confusion)
        # "e|b" should have 2 entries (one per alias occurrence)
        assert len(index["e|b"]) == 2
        for entry in index["e|b"]:
            assert entry.canonical_alias == "ab"

    def test_two_distinct_aliases_share_mutation_key(self):
        # alias1 = "ab": pos-0 'a'→'e' → key "e|b", canonical_alias="ab"
        # alias2 = "eb": pos-1 'b'→'p' → key "e|p", canonical_alias="eb"  (no shared key)
        # Use alias1="ab" and alias2="ac" where 'c' no rule → both produce key "e|b"? No, "e|c" ≠ "e|b"
        # The truly shared scenario: alias1="ab" → "e|b"; alias2=ANOTHER alias whose
        # phoneme sequence after one swap == ('e','b') i.e. original is ('o','b') swap 'o'→'e'
        # but mock_confusion has no 'o'→'e' rule.
        # Alternative: define a second confusion function for this test only.
        def confusion2(p: tuple[str, ...]) -> set[tuple[str, ...]]:
            if p == ("a",):
                return {("e",)}
            if p == ("x",):
                return {("e",)}
            return set()

        # alias1="ab" pos-0 'a'→'e' → "e|b"
        # alias2="xb" pos-0 'x'→'e' → "e|b"   ← shared key!
        index = build_mutation_index(["ab", "xb"], mock_phonemize, confusion2)
        assert "e|b" in index
        entries = index["e|b"]
        assert len(entries) == 2
        canonical_aliases = {e.canonical_alias for e in entries}
        assert canonical_aliases == {"ab", "xb"}

    def test_max_distance_not_1_raises(self):
        with pytest.raises(NotImplementedError):
            build_mutation_index(["a"], mock_phonemize, mock_confusion, max_distance=2)

    def test_distance_field_is_1(self):
        index = build_mutation_index(["a"], mock_phonemize, mock_confusion)
        for entries in index.values():
            for entry in entries:
                assert entry.distance == 1


# ---------------------------------------------------------------------------
# lookup_mutation — query correctness
# ---------------------------------------------------------------------------


class TestLookupMutation:
    def test_lookup_hit_returns_entries(self):
        # alias "a" → mutation "e" and "o"
        index = build_mutation_index(["a"], mock_phonemize, mock_confusion)
        results = lookup_mutation(index, ("e",))
        assert len(results) == 1
        assert results[0].canonical_alias == "a"

    def test_lookup_miss_returns_empty_list(self):
        index = build_mutation_index(["a"], mock_phonemize, mock_confusion)
        results = lookup_mutation(index, ("z",))
        assert results == []

    def test_lookup_empty_index_returns_empty(self):
        results = lookup_mutation({}, ("a",))
        assert results == []

    def test_lookup_multi_phoneme_key(self):
        # alias "ab" → among mutations "e|b" (pos-0 swap)
        index = build_mutation_index(["ab"], mock_phonemize, mock_confusion)
        results = lookup_mutation(index, ("e", "b"))
        assert len(results) == 1
        assert results[0].canonical_alias == "ab"

    def test_lookup_returns_list_not_mutation(self):
        index = build_mutation_index(["a"], mock_phonemize, mock_confusion)
        result = lookup_mutation(index, ("e",))
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Performance guard
# ---------------------------------------------------------------------------


class TestBuildPerformance:
    def test_large_build_under_50ms(self):
        """100 aliases × ~5 phonemes × ~3 confusables ≈ 1500 entries < 50ms."""

        def phonemize_5(text: str) -> list[tuple[str, ...]]:
            # Always return 5-phoneme tuple regardless of text
            return [("a", "b", "c", "d", "e")]

        def confusion_3(p: tuple[str, ...]) -> set[tuple[str, ...]]:
            # Each phoneme has 3 confusables
            base = p[0] if p else "x"
            return {(base + "1",), (base + "2",), (base + "3",)}

        aliases = [f"alias_{i}" for i in range(100)]

        start = time.perf_counter()
        index = build_mutation_index(aliases, phonemize_5, confusion_3)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50, f"build took {elapsed_ms:.1f}ms (limit 50ms)"
        # Sanity: index is non-empty
        assert len(index) > 0

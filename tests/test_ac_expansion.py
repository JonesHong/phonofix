"""Tests for Tier 3 AC + delete-1 expansion (src/phonofix/core/ac_expansion.py)."""

from __future__ import annotations

from phonofix.core.ac_expansion import (
    ExpandedPattern,
    build_ac_with_expansion,
    expand_delete_1,
    filter_hits,
)

# ---------------------------------------------------------------------------
# expand_delete_1 — basic behaviour
# ---------------------------------------------------------------------------


class TestExpandDelete1:
    def test_two_char_alias_returns_three_patterns(self):
        """'北車' → original + 2 delete-1 = 3 patterns."""
        result = expand_delete_1("北車")
        assert len(result) == 3

    def test_two_char_alias_contains_original(self):
        result = expand_delete_1("北車")
        originals = [ep for ep in result if ep.is_original]
        assert len(originals) == 1
        assert originals[0].pattern == "北車"

    def test_two_char_alias_delete_1_variants(self):
        result = expand_delete_1("北車")
        variants = [ep for ep in result if not ep.is_original]
        patterns = {ep.pattern for ep in variants}
        # delete pos-0 → "車", delete pos-1 → "北"
        assert patterns == {"車", "北"}

    def test_single_char_alias_returns_one_pattern(self):
        """Single char: no deletion possible, only original."""
        result = expand_delete_1("a")
        assert len(result) == 1
        assert result[0].is_original
        assert result[0].pattern == "a"

    def test_empty_alias_returns_empty(self):
        result = expand_delete_1("")
        assert result == []

    def test_three_char_ascii_returns_four_patterns(self):
        """'abc' → original + 3 delete-1 = 4 patterns."""
        result = expand_delete_1("abc")
        assert len(result) == 4
        patterns = {ep.pattern for ep in result}
        assert patterns == {"abc", "bc", "ac", "ab"}

    def test_unicode_cjk_four_char(self):
        """'台北車站' → 1 + 4 = 5 patterns, all unicode-safe."""
        result = expand_delete_1("台北車站")
        assert len(result) == 5
        patterns = {ep.pattern for ep in result}
        expected_variants = {"北車站", "台車站", "台北站", "台北車"}
        assert expected_variants.issubset(patterns)
        assert "台北車站" in patterns

    def test_all_patterns_carry_correct_original_alias(self):
        for ep in expand_delete_1("北車"):
            assert ep.original_alias == "北車"

    def test_deletion_pos_none_for_original(self):
        result = expand_delete_1("北車")
        for ep in result:
            if ep.is_original:
                assert ep.deletion_pos is None

    def test_deletion_pos_range_for_variants(self):
        alias = "abc"
        result = expand_delete_1(alias)
        variants = [ep for ep in result if not ep.is_original]
        positions = {ep.deletion_pos for ep in variants}
        assert positions == {0, 1, 2}


# ---------------------------------------------------------------------------
# ExpandedPattern.is_original
# ---------------------------------------------------------------------------


class TestExpandedPatternIsOriginal:
    def test_is_original_true_when_deletion_pos_none(self):
        ep = ExpandedPattern(pattern="北車", original_alias="北車", deletion_pos=None)
        assert ep.is_original is True

    def test_is_original_false_when_deletion_pos_set(self):
        ep = ExpandedPattern(pattern="車", original_alias="北車", deletion_pos=0)
        assert ep.is_original is False


# ---------------------------------------------------------------------------
# build_ac_with_expansion
# ---------------------------------------------------------------------------


class TestBuildACWithExpansion:
    def test_empty_aliases_builds_empty_ac(self):
        ac = build_ac_with_expansion([])
        hits = list(ac.find_all("台北車站"))
        assert hits == []

    def test_single_alias_ac_finds_original(self):
        ac = build_ac_with_expansion(["北車"])
        hits = list(ac.find_all("台北車站"))
        # At minimum, the original "北車" must be found
        found_words = {h[2] for h in hits}
        assert "北車" in found_words

    def test_single_alias_ac_finds_delete1_variants(self):
        ac = build_ac_with_expansion(["北車"])
        hits = list(ac.find_all("台北車站"))
        found_words = {h[2] for h in hits}
        # delete-1 variants "北" and "車" appear in "台北車站"
        assert "北" in found_words or "車" in found_words

    def test_payload_is_expanded_pattern_instance(self):
        ac = build_ac_with_expansion(["北車"])
        for _start, _end, word, payload in ac.find_all("台北車站"):
            assert isinstance(payload, ExpandedPattern)

    def test_two_aliases_both_registered(self):
        ac = build_ac_with_expansion(["北車", "台北"])
        hits = list(ac.find_all("台北車站"))
        original_aliases = {h[3].original_alias for h in hits}
        assert "北車" in original_aliases
        assert "台北" in original_aliases

    def test_single_char_alias_no_explosion(self):
        """Single-char alias should register only original, not crash."""
        ac = build_ac_with_expansion(["站"])
        hits = list(ac.find_all("台北車站"))
        assert any(h[2] == "站" for h in hits)


# ---------------------------------------------------------------------------
# filter_hits
# ---------------------------------------------------------------------------


class TestFilterHits:
    def _make_hit(
        self,
        start: int,
        end: int,
        pattern: str,
        original_alias: str,
        deletion_pos=None,
    ):
        ep = ExpandedPattern(
            pattern=pattern,
            original_alias=original_alias,
            deletion_pos=deletion_pos,
        )
        return (start, end, pattern, ep)

    def test_empty_hits_returns_empty(self):
        assert filter_hits([], "任意文字") == []

    def test_prefer_original_over_delete1_at_same_start(self):
        """Original hit at start=1 beats delete-1 hit at start=1."""
        original_hit = self._make_hit(1, 3, "北車", "北車", deletion_pos=None)
        delete1_hit = self._make_hit(1, 2, "北", "北車", deletion_pos=1)
        result = filter_hits([delete1_hit, original_hit], "台北車站")
        # Only original should survive
        assert len(result) == 1
        assert result[0][3].is_original

    def test_deduplicate_overlapping_delete1_same_alias(self):
        """Two delete-1 hits of same alias at same start → keep longer span."""
        hit_a = self._make_hit(0, 1, "北", "北車", deletion_pos=1)
        hit_b = self._make_hit(0, 2, "北車", "北車", deletion_pos=None)
        result = filter_hits([hit_a, hit_b], "北車站")
        assert len(result) == 1

    def test_different_aliases_both_kept(self):
        """Hits from different original_aliases are independent."""
        hit_1 = self._make_hit(0, 2, "北車", "北車", deletion_pos=None)
        hit_2 = self._make_hit(3, 5, "車站", "車站", deletion_pos=None)
        result = filter_hits([hit_1, hit_2], "北車 車站")
        assert len(result) == 2

    def test_result_sorted_by_start(self):
        hit_a = self._make_hit(5, 7, "北車", "北車", deletion_pos=None)
        hit_b = self._make_hit(0, 2, "台北", "台北", deletion_pos=None)
        result = filter_hits([hit_a, hit_b], "台北車站是北車")
        assert result[0][0] < result[1][0]


# ---------------------------------------------------------------------------
# E2E: build AC with ["北車"], find_all in "台北車站", filter → 1 original hit
# ---------------------------------------------------------------------------


class TestE2E:
    def test_e2e_find_original_hit_in_text(self):
        ac = build_ac_with_expansion(["北車"])
        text = "台北車站"
        raw_hits = list(ac.find_all(text))
        assert raw_hits, "AC should find at least one hit"
        filtered = filter_hits(raw_hits, text)
        # After filtering, the original "北車" hit should be present
        originals = [h for h in filtered if h[3].is_original and h[3].original_alias == "北車"]
        assert len(originals) >= 1
        # Verify span points to the right text slice
        start, end, word, ep = originals[0]
        assert text[start:end] == "北車"

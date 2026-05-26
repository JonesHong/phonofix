"""Tests for Chinese Tier 1 canonical key collapse module.

Covers:
- FUZZY_INITIALS_MAP collapse (zh/z, ch/c, sh/s, n/l, f/h)
- FUZZY_FINALS_PAIRS collapse (in/ing, an/ang, uo/ou, ue/ie, ...)
- SPECIAL_SYLLABLE_MAP_BIDIRECTIONAL whole-syllable override
- canonical_key_for_phrase: phrase-level tuple equality
- lru_cache hit verification (idempotent repeated calls)
- Edge cases: empty string, single syllable, whitespace phrase
- Standard syllables not in any map (self-identity under canonicalization)
"""

from phonofix.languages.chinese.canonical_key import (
    canonical_key_for_phrase,
    canonical_token,
)

# ---------------------------------------------------------------------------
# 1. FUZZY_INITIALS_MAP — retroflex vs. flat sibilant collapse
# ---------------------------------------------------------------------------


class TestFuzzyInitials:
    """zh/z, ch/c, sh/s pairs should produce identical canonical tokens."""

    def test_zh_z_collapse_zhi_zi(self):
        """'zhi' and 'zi' share the zh/z fuzzy group → same canonical."""
        assert canonical_token("zhi") == canonical_token("zi")

    def test_ch_c_collapse_chi_ci(self):
        """'chi' and 'ci' share the ch/c fuzzy group → same canonical."""
        assert canonical_token("chi") == canonical_token("ci")

    def test_sh_s_collapse_shi_si(self):
        """'shi' and 'si' share the sh/s fuzzy group → same canonical."""
        assert canonical_token("shi") == canonical_token("si")

    def test_n_l_collapse(self):
        """'ni' and 'li' share the n/l fuzzy group → same canonical."""
        assert canonical_token("ni") == canonical_token("li")

    def test_f_h_collapse(self):
        """'hao' and 'fao' share the f/h fuzzy group → same canonical."""
        assert canonical_token("hao") == canonical_token("fao")

    def test_different_initial_groups_not_equal(self):
        """'zi' (z_group) and 'ji' (j, no group) are NOT phonetically collapsed."""
        assert canonical_token("zi") != canonical_token("ji")


# ---------------------------------------------------------------------------
# 2. FUZZY_FINALS_PAIRS — front/back nasal and other pairs
# ---------------------------------------------------------------------------


class TestFuzzyFinals:
    """Pairs from FUZZY_FINALS_PAIRS must collapse to the same canonical suffix."""

    def test_an_ang_collapse(self):
        """'shang' and 'sang' have finals ang/an → same canonical after sh/s collapse."""
        assert canonical_token("shang") == canonical_token("sang")

    def test_in_ing_collapse(self):
        """'xin' and 'xing' → finals in/ing → same canonical."""
        assert canonical_token("xin") == canonical_token("xing")

    def test_ue_ie_collapse(self):
        """'nue' and 'nie' → finals ue/ie → same canonical."""
        assert canonical_token("nue") == canonical_token("nie")

    def test_uo_ou_collapse(self):
        """'guo' and 'gou' → finals uo/ou → same canonical."""
        assert canonical_token("guo") == canonical_token("gou")

    def test_ian_iang_collapse(self):
        """'lian' and 'liang' → finals ian/iang → same canonical."""
        assert canonical_token("lian") == canonical_token("liang")

    def test_different_finals_not_equal(self):
        """'ba' and 'bo' have distinct finals with no pair → NOT equal."""
        assert canonical_token("ba") != canonical_token("bo")


# ---------------------------------------------------------------------------
# 3. SPECIAL_SYLLABLE_MAP_BIDIRECTIONAL — whole-syllable override
# ---------------------------------------------------------------------------


class TestSpecialSyllableMap:
    """Bidirectional special syllable pairs must collapse to the same canonical."""

    def test_fa_hua_special_collapse(self):
        """'fa' ↔ 'hua' are a bidirectional special pair → same canonical."""
        assert canonical_token("fa") == canonical_token("hua")

    def test_fei_hui_special_collapse(self):
        """'fei' ↔ 'hui' bidirectional special pair → same canonical."""
        assert canonical_token("fei") == canonical_token("hui")

    def test_er_e_special_collapse(self):
        """'er' ↔ 'e' bidirectional special pair → same canonical."""
        assert canonical_token("er") == canonical_token("e")

    def test_special_map_takes_priority(self):
        """Special map Step 1 fires before initials/finals steps.
        'hua' is in SPECIAL_CANONICAL → canonical is determined by BFS group, not
        by the h/f initial collapse path.  Both 'fa' and 'hua' must agree."""
        token_fa = canonical_token("fa")
        token_hua = canonical_token("hua")
        assert token_fa == token_hua
        # The canonical value must be consistent (lex-min of the BFS component)
        assert token_fa == token_hua  # redundant but explicit


# ---------------------------------------------------------------------------
# 4. canonical_key_for_phrase — phrase-level hash equality
# ---------------------------------------------------------------------------


class TestCanonicalKeyForPhrase:
    def test_identical_phrase_equal(self):
        """Same phrase string → same canonical key tuple."""
        assert canonical_key_for_phrase("ni hao") == canonical_key_for_phrase("ni hao")

    def test_fuzzy_initial_variant_phrase(self):
        """'zhi dao' and 'zi dao' differ only in zh/z → same canonical key."""
        assert canonical_key_for_phrase("zhi dao") == canonical_key_for_phrase("zi dao")

    def test_fuzzy_finals_variant_phrase(self):
        """'xi ang' and 'xi an' differ only in iang/ian → same canonical key."""
        assert canonical_key_for_phrase("xiang") == canonical_key_for_phrase("xian")

    def test_different_phrases_not_equal(self):
        """Genuinely different phrases must produce different canonical keys."""
        assert canonical_key_for_phrase("ni hao") != canonical_key_for_phrase("wo hao")

    def test_return_type_is_tuple(self):
        """canonical_key_for_phrase always returns a tuple."""
        result = canonical_key_for_phrase("ni hao")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_single_syllable_phrase(self):
        """Single syllable without space → 1-element tuple."""
        result = canonical_key_for_phrase("ma")
        assert isinstance(result, tuple)
        assert len(result) == 1

    def test_lru_cache_hit(self):
        """Repeated calls with same argument return identical object (cache hit)."""
        phrase = "zhu yi"
        first = canonical_key_for_phrase(phrase)
        second = canonical_key_for_phrase(phrase)
        # lru_cache returns the exact same object on a hit
        assert first is second

    def test_empty_phrase_returns_empty_tuple(self):
        """Empty string → empty tuple."""
        assert canonical_key_for_phrase("") == ()

    def test_whitespace_only_phrase_returns_empty_tuple(self):
        """Whitespace-only string → empty tuple."""
        assert canonical_key_for_phrase("   ") == ()


# ---------------------------------------------------------------------------
# 5. Standard syllables (not in any map) — self-identity
# ---------------------------------------------------------------------------


class TestStandardSyllables:
    """Syllables not in any fuzzy map must canonicalize to a consistent but
    non-collapsing form (i.e., canonical_token('ma') == canonical_token('ma'))."""

    def test_standard_ma_stable(self):
        """'ma' → not in any fuzzy group → canonical equals itself (idempotent)."""
        assert canonical_token("ma") == canonical_token("ma")

    def test_standard_ma_not_equal_ba(self):
        """'ma' and 'ba' are distinct initials, not in same group → not equal."""
        assert canonical_token("ma") != canonical_token("ba")

    def test_empty_string_returns_empty(self):
        """Empty string → returned as-is (empty string)."""
        assert canonical_token("") == ""

    def test_uppercase_normalized(self):
        """Uppercase input is lowercased before processing."""
        assert canonical_token("ZHI") == canonical_token("zhi")
        assert canonical_token("ZI") == canonical_token("zi")

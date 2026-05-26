"""Tests for Korean Tier 1 adapter (jamo decompose + confusion-aware hash lookup).

Covers:
- _jamo_canonical idempotency
- Vowel confusion: ᅥ↔ᅩ (터↔토)
- Alveolar confusion: ᄃ↔ᄌ (다↔자) — both sides in KOREAN_CONFUSION_MAP_JAMO
- 받침 nasal swap: ᆫ↔ᆼ (안↔앙)
- build_index + apply end-to-end
- Empty index guard
- Literal exact-match skip (AC covers)
- Non-hangul char isolation (no cross-char collapse)
- Multi-span hits
- Mixed hangul + ASCII alias
"""

from phonofix.languages.korean.tier1_adapter import (
    _jamo_canonical,
    _syllable_canonical,
    _text_canonical_key,
    apply,
    build_index,
)

# ---------------------------------------------------------------------------
# _jamo_canonical
# ---------------------------------------------------------------------------


class TestJamoCanonical:
    def test_idempotent_map_source(self):
        """canonical applied twice to a map-source jamo must be stable."""
        # ᄀ is a source key: confusable={ᄏ,ᄁ} → canonical=min({ᄀ,ᄏ,ᄁ})=ᄀ
        c1 = _jamo_canonical("ᄀ")
        c2 = _jamo_canonical(c1)
        assert c1 == c2

    def test_idempotent_map_destination_becomes_canonical(self):
        """ᄌ is a source key; its canonical maps to ᄃ; re-applying must be stable."""
        # ᄌ confusable includes ᄃ, and ᄃ confusable includes ᄌ → min collapses
        c1 = _jamo_canonical("ᄌ")
        c2 = _jamo_canonical(c1)
        assert c1 == c2

    def test_empty_string_passthrough(self):
        """Empty jamo (no jongseong) must pass through unchanged."""
        assert _jamo_canonical("") == ""

    def test_unmapped_jamo_returns_self(self):
        """A jamo not in the confusion map returns itself."""
        # ᄂ (U+1102, 'n') has no entry in KOREAN_CONFUSION_MAP_JAMO
        assert _jamo_canonical("ᄂ") == "ᄂ"


# ---------------------------------------------------------------------------
# _syllable_canonical
# ---------------------------------------------------------------------------


class TestSyllableCanonical:
    def test_vowel_eo_o_collision(self):
        """터(ᅥ) and 토(ᅩ) share canonical — ᅥ↔ᅩ bidirectional in map."""
        assert _syllable_canonical("터") == _syllable_canonical("토")

    def test_alveolar_da_ja_collision(self):
        """다(ᄃ) and 자(ᄌ) share canonical — ᄃ↔ᄌ bidirectional (Paper [2])."""
        assert _syllable_canonical("다") == _syllable_canonical("자")

    def test_distinct_syllables_stay_distinct(self):
        """안(ᄋ+ᅡ+ᆫ) vs 가(ᄀ+ᅡ) must NOT collide."""
        assert _syllable_canonical("안") != _syllable_canonical("가")


# ---------------------------------------------------------------------------
# _text_canonical_key
# ---------------------------------------------------------------------------


class TestTextCanonicalKey:
    def test_batchim_nasal_swap(self):
        """안녕 vs 앙녕: ᆫ↔ᆼ (받침) — both sides in map → same canonical key."""
        assert _text_canonical_key("안녕") == _text_canonical_key("앙녕")

    def test_different_words_differ(self):
        """Unrelated words must produce distinct canonical keys."""
        assert _text_canonical_key("안녕") != _text_canonical_key("사랑")

    def test_non_hangul_char_isolated(self):
        """ASCII char is stored as (ch,'','') — no collapse with hangul."""
        key_a = _text_canonical_key("a")
        key_b = _text_canonical_key("b")
        assert key_a != key_b


# ---------------------------------------------------------------------------
# build_index + apply (end-to-end)
# ---------------------------------------------------------------------------


class TestApply:
    def test_batchim_swap_hits(self):
        """앙녕하세요 (받침 ᆫ→ᆼ swap) must hit alias 안녕하세요."""
        idx = build_index(["안녕하세요"])
        hits = apply("앙녕하세요", idx)
        assert len(hits) == 1
        start, end, matched, alias = hits[0]
        assert matched == "앙녕하세요"
        assert alias == "안녕하세요"
        assert (start, end) == (0, 5)

    def test_vowel_eo_o_hit(self):
        """토 (ᅩ→ᅥ) must hit alias 터."""
        idx = build_index(["터"])
        hits = apply("토", idx)
        assert len(hits) == 1
        assert hits[0][2] == "토"
        assert hits[0][3] == "터"

    def test_alveolar_ja_da_hit(self):
        """자 (alveolar ᄌ↔ᄃ) must hit alias 다."""
        idx = build_index(["다"])
        hits = apply("자", idx)
        assert len(hits) == 1
        assert hits[0][2] == "자"
        assert hits[0][3] == "다"

    def test_multi_span_hits(self):
        """앙다자: 앙→안 (받침) + 자→다 (alveolar); 다 is exact → skipped."""
        idx = build_index(["안", "다"])
        hits = apply("앙다자", idx)
        matched_texts = {h[2] for h in hits}
        aliases = {h[3] for h in hits}
        assert "앙" in matched_texts
        assert "안" in aliases
        assert "자" in matched_texts
        assert "다" in aliases
        # '다' exact → skipped
        exact_hits = [h for h in hits if h[2] == "다"]
        assert exact_hits == []

    def test_empty_index_returns_empty(self):
        """Empty index must return empty list without error."""
        assert apply("안녕", {}) == []

    def test_literal_exact_match_skipped(self):
        """Exact substr == alias is skipped — AC covers it."""
        idx = build_index(["안녕"])
        hits = apply("안녕", idx)
        assert hits == []

    def test_non_hangul_no_false_collapse(self):
        """ASCII chars must not collapse across values."""
        idx = build_index(["hello"])
        # exact skip
        assert apply("hello", idx) == []
        # different ASCII → no match
        assert apply("helko", idx) == []

    def test_mixed_hangul_ascii_alias(self):
        """자페 hits alias 다페 (ᄌ↔ᄃ confusion, ASCII ᅦ same)."""
        idx = build_index(["다페"])
        hits = apply("자페", idx)
        assert len(hits) == 1
        assert hits[0][2] == "자페"
        assert hits[0][3] == "다페"

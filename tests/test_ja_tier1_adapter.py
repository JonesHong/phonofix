"""Tests for ja Tier 1 adapter: _dakuten_normalize, build_index, apply."""

from __future__ import annotations

from phonofix.languages.japanese.tier1_adapter import (
    DAKUTEN_NORMALIZE,
    _dakuten_normalize,
    apply,
    build_index,
)

# ---------------------------------------------------------------------------
# _dakuten_normalize
# ---------------------------------------------------------------------------


class TestDakutenNormalize:
    def test_hiragana_dakuten_ga(self):
        assert _dakuten_normalize("が") == "か"

    def test_hiragana_dakuten_za(self):
        assert _dakuten_normalize("ざ") == "さ"

    def test_hiragana_dakuten_da(self):
        assert _dakuten_normalize("だ") == "た"

    def test_hiragana_handakuten_pa(self):
        # ぱ (handakuten) → は (seion)
        assert _dakuten_normalize("ぱ") == "は"

    def test_katakana_dakuten_za(self):
        assert _dakuten_normalize("ザ") == "サ"

    def test_katakana_dakuten_ba(self):
        assert _dakuten_normalize("バ") == "ハ"

    def test_katakana_handakuten_pa(self):
        assert _dakuten_normalize("パ") == "ハ"

    def test_no_change_on_seion(self):
        # Plain kana should pass through unchanged
        assert _dakuten_normalize("か") == "か"
        assert _dakuten_normalize("サ") == "サ"

    def test_mixed_string(self):
        # が (dakuten) + か (seion) → か + か
        assert _dakuten_normalize("がか") == "かか"

    def test_non_japanese_passthrough(self):
        assert _dakuten_normalize("hello") == "hello"

    def test_katakana_word_basu(self):
        # バス → ハス
        assert _dakuten_normalize("バス") == "ハス"

    def test_all_dakuten_keys_have_mapping(self):
        # Every key in DAKUTEN_NORMALIZE should map to its seion (non-empty value)
        for k, v in DAKUTEN_NORMALIZE.items():
            assert v, f"Empty mapping for {k!r}"
            assert k != v, f"Self-mapping for {k!r}"


# ---------------------------------------------------------------------------
# build_index
# ---------------------------------------------------------------------------


class TestBuildIndex:
    def test_single_alias_key_is_romaji_of_seion(self):
        idx = build_index(["バス"])
        # バス dakuten_normalize → ハス, romaji → "Hasu", lower → "hasu"
        assert "hasu" in idx
        assert "バス" in idx["hasu"]

    def test_multiple_aliases_sharing_key(self):
        # バス and ハス both normalize to "hasu"
        idx = build_index(["バス", "ハス"])
        assert "hasu" in idx
        assert set(idx["hasu"]) == {"バス", "ハス"}

    def test_empty_iterable_returns_empty(self):
        assert build_index([]) == {}

    def test_plain_seion_alias(self):
        # ハス has no dakuten — just romaji of ハス
        idx = build_index(["ハス"])
        assert "hasu" in idx

    def test_hiragana_dakuten_alias(self):
        # ばす → はす → romaji → "hasu"
        idx = build_index(["ばす"])
        assert "hasu" in idx

    def test_generator_input(self):
        # Accepts any Iterable, not just list
        idx = build_index(alias for alias in ["バス"])
        assert "hasu" in idx


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


class TestApply:
    def _basu_index(self):
        """Index built from alias 'バス'."""
        return build_index(["バス"])

    def test_find_devoiced_span(self):
        # Text contains ハス (dakuten missing) — should match バス
        idx = self._basu_index()
        hits = apply("ハスに乗る", idx)
        assert len(hits) >= 1
        starts = [h[0] for h in hits]
        assert 0 in starts

    def test_hit_shape(self):
        idx = self._basu_index()
        hits = apply("ハスに乗る", idx)
        start, end, substr, alias = hits[0]
        assert substr == "ハス"
        assert alias == "バス"
        assert end - start == len("ハス")

    def test_exact_match_skipped(self):
        # Text == alias exactly → apply should NOT fire (literal AC covers it)
        idx = build_index(["バス"])
        hits = apply("バス", idx)
        # バス in text, index key "hasu" from alias "バス"
        # substr "バス" normalized → "hasu", alias "バス" — substr == alias → skip
        assert hits == []

    def test_empty_index_returns_empty(self):
        assert apply("ハスに乗る", {}) == []

    def test_no_match_in_unrelated_text(self):
        idx = self._basu_index()
        hits = apply("今日はいい天気です", idx)
        assert hits == []

    def test_multiple_hits_in_text(self):
        # Two occurrences of ハス in one text
        idx = self._basu_index()
        hits = apply("ハスとハス", idx)
        matched_starts = {h[0] for h in hits}
        assert 0 in matched_starts
        assert 3 in matched_starts  # "ハスと" is 3 chars then ハス again

    def test_hiragana_dakuten_missing(self):
        # ばす in text, alias ばす — exact → skip; alias バス — different kana script
        # Build index from hiragana alias ばす
        idx = build_index(["ばす"])
        # text はす (seion) should also normalize to "hasu"
        hits = apply("はす", idx)
        # はす != ばす → should fire
        assert len(hits) >= 1
        assert hits[0][3] == "ばす"


# ---------------------------------------------------------------------------
# Degraded mode: cutlet not available
# ---------------------------------------------------------------------------


class TestDegradedMode:
    """Simulate cutlet import failure — adapter must not crash."""

    def test_apply_no_crash_without_cutlet(self, monkeypatch):
        import phonofix.languages.japanese.tier1_adapter as adapter

        monkeypatch.setattr(adapter, "_HAS_CUTLET", False)
        monkeypatch.setattr(adapter, "_katsu", None)

        # In degraded mode romaji falls back to identity; index keys are raw text
        idx = adapter.build_index(["バス"])
        # Key will be dakuten_normalize("バス") = "ハス" (no romaji conversion)
        assert len(idx) == 1  # still builds one entry
        # apply should not raise
        hits = adapter.apply("ハス", idx)
        # ハス == ハス → skip (exact). But idx key is "ハス".lower() = "ハス"
        # Actually: substr "ハス" lower = "ハス", key "ハス" → match but substr==alias skip
        assert isinstance(hits, list)

    def test_build_index_no_crash_without_cutlet(self, monkeypatch):
        import phonofix.languages.japanese.tier1_adapter as adapter

        monkeypatch.setattr(adapter, "_HAS_CUTLET", False)
        monkeypatch.setattr(adapter, "_katsu", None)

        idx = adapter.build_index(["が", "ざ", "ば"])
        # Each should produce a key without error
        assert isinstance(idx, dict)
        assert len(idx) > 0

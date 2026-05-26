"""Tests for English Tier 1 adapter — Double Metaphone hash lookup."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_adapter():
    from phonofix.languages.english import tier1_adapter

    return tier1_adapter


# ---------------------------------------------------------------------------
# build_index tests
# ---------------------------------------------------------------------------


def test_build_index_single_word_has_metaphone_key():
    """build_index(['smith']) must produce exactly one key for metaphone('smith')."""
    adapter = _import_adapter()
    from phonofix.languages.english.metaphone import metaphone_key

    idx = adapter.build_index(["smith"])
    primary, _ = metaphone_key("smith")
    assert primary in idx
    assert "smith" in idx[primary]


def test_build_index_groups_homophones():
    """smith and smyth share the same metaphone primary — both land on one key."""
    adapter = _import_adapter()
    from phonofix.languages.english.metaphone import metaphone_key

    idx = adapter.build_index(["smith", "smyth"])
    primary, _ = metaphone_key("smith")
    assert set(idx[primary]) == {"smith", "smyth"}


def test_build_index_multi_word_composite_key():
    """Multi-word alias keyed by space-joined metaphone of each word."""
    adapter = _import_adapter()
    from phonofix.languages.english.metaphone import metaphone_key

    idx = adapter.build_index(["Catherine the great"])
    p_cath, _ = metaphone_key("Catherine")
    p_the, _ = metaphone_key("the")
    p_great, _ = metaphone_key("great")
    expected_key = f"{p_cath} {p_the} {p_great}"
    assert expected_key in idx
    assert "Catherine the great" in idx[expected_key]


def test_build_index_empty_input():
    adapter = _import_adapter()
    assert adapter.build_index([]) == {}


def test_build_index_whitespace_only_alias_skipped():
    adapter = _import_adapter()
    idx = adapter.build_index(["   ", "\t"])
    assert idx == {}


# ---------------------------------------------------------------------------
# apply tests
# ---------------------------------------------------------------------------


def test_apply_spelling_variant_smyth_hits_smith():
    """'smyth' in text should surface as a hit against alias 'smith' (spelling variant)."""
    adapter = _import_adapter()
    idx = adapter.build_index(["smith"])
    hits = adapter.apply("smyth went home", idx)

    assert len(hits) == 1
    start, end, matched, alias = hits[0]
    assert matched == "smyth"
    assert alias == "smith"


def test_apply_multi_word_alias_katherine_hits_catherine():
    """'Katherine the Great' in text must match alias 'Catherine the great'."""
    adapter = _import_adapter()
    idx = adapter.build_index(["Catherine the great"])
    hits = adapter.apply("Katherine the Great is famous", idx)

    assert len(hits) >= 1
    matched_texts = [h[2] for h in hits]
    assert any("Katherine the Great" in t for t in matched_texts)


def test_apply_literal_match_does_not_fire():
    """When text word matches alias case-insensitively it is NOT reported (no-op)."""
    adapter = _import_adapter()
    idx = adapter.build_index(["smith"])
    hits = adapter.apply("Smith is here", idx)
    # "Smith" == "smith" (case-insensitive) → must not be reported
    assert all(h[2].lower() != "smith" or h[3].lower() != "smith" for h in hits)
    # More direct: no hit where matched == alias (case-insensitive)
    for start, end, matched, alias in hits:
        assert matched.lower() != alias.lower()


def test_apply_empty_text_returns_empty():
    adapter = _import_adapter()
    idx = adapter.build_index(["smith"])
    assert adapter.apply("", idx) == []


def test_apply_empty_index_returns_empty():
    adapter = _import_adapter()
    assert adapter.apply("smyth went home", {}) == []


def test_apply_punctuation_handling():
    """alias 'Smith' must still be found when text has 'Smith,'."""
    adapter = _import_adapter()
    # The alias we're looking for is "smyth" (the canonical); text has "Smith,"
    # _WORD_RE strips trailing comma — "Smith" is extracted as token.
    # "Smith" metaphone == "smyth" metaphone but Smith==smyth case-insensitively?
    # Smith (S530 primary SM0) != alias "smyth" → so the literal guard doesn't fire.
    idx = adapter.build_index(["smyth"])
    hits = adapter.apply("Hello Smith, how are you?", idx)
    matched_texts = [h[2] for h in hits]
    assert "Smith" in matched_texts


def test_apply_contraction_dont_hits_dont_alias():
    """Alias 'dont' (no apostrophe) should match text token \"don't\"."""
    adapter = _import_adapter()
    from phonofix.languages.english.metaphone import metaphone_key

    # Both "dont" and "don't" share the same metaphone primary
    p_dont, _ = metaphone_key("dont")
    p_dont2, _ = metaphone_key("don't")
    assert p_dont == p_dont2, "Pre-condition: same metaphone key"

    idx = adapter.build_index(["dont"])
    hits = adapter.apply("I don't know", idx)
    # "don't" != "dont" → literal guard must NOT suppress this hit
    matched_texts = [h[2] for h in hits]
    assert "don't" in matched_texts


def test_apply_degraded_mode_no_crash(monkeypatch):
    """When _HAS_METAPHONE is False, build_index returns {} and apply returns [] — no crash."""
    import phonofix.languages.english.tier1_adapter as adapter_mod

    original = adapter_mod._HAS_METAPHONE
    try:
        adapter_mod._HAS_METAPHONE = False
        idx = adapter_mod.build_index(["smith"])
        assert idx == {}
        result = adapter_mod.apply("smyth went home", idx)
        assert result == []
    finally:
        adapter_mod._HAS_METAPHONE = original

"""Tests for English Tier 1 Double Metaphone wrapper.

All tests that require jellyfish are guarded with @pytest.mark.skipif so
the suite still passes when jellyfish is not installed.
"""

from __future__ import annotations

import pytest

from phonofix.languages.english.metaphone import (
    _HAS_JELLYFISH,
    build_metaphone_index,
    metaphone_key,
    metaphone_match,
)

_SKIP_NO_JELLYFISH = pytest.mark.skipif(not _HAS_JELLYFISH, reason="jellyfish not installed")


# ---------------------------------------------------------------------------
# 1. metaphone_key — primary/secondary keys
# ---------------------------------------------------------------------------


@_SKIP_NO_JELLYFISH
def test_smith_smyth_same_primary():
    """smith / smyth are phonetically identical — same primary key."""
    ka = metaphone_key("smith")
    kb = metaphone_key("smyth")
    assert ka[0] == kb[0], f"Expected same primary: {ka[0]!r} vs {kb[0]!r}"


@_SKIP_NO_JELLYFISH
def test_knight_night_same_primary():
    """Silent-k: knight and night should share a primary metaphone key."""
    ka = metaphone_key("knight")
    kb = metaphone_key("night")
    assert ka[0] == kb[0], f"Expected same primary: {ka[0]!r} vs {kb[0]!r}"


@_SKIP_NO_JELLYFISH
def test_phone_fone_same_primary():
    """ph≡f rule: phone / fone share primary key."""
    ka = metaphone_key("phone")
    kb = metaphone_key("fone")
    assert ka[0] == kb[0]


@_SKIP_NO_JELLYFISH
def test_colour_color_same_key():
    """British / American spelling variants share both keys."""
    ka = metaphone_key("colour")
    kb = metaphone_key("color")
    assert ka == kb


@_SKIP_NO_JELLYFISH
def test_returns_two_element_tuple():
    """metaphone_key always returns a 2-tuple of strings."""
    result = metaphone_key("hello")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(s, str) for s in result)


# ---------------------------------------------------------------------------
# 2. metaphone_match — same-sound True, different-sound False
# ---------------------------------------------------------------------------


@_SKIP_NO_JELLYFISH
def test_metaphone_match_homophones_true():
    assert metaphone_match("smith", "smyth") is True


@_SKIP_NO_JELLYFISH
def test_metaphone_match_knight_night_true():
    assert metaphone_match("knight", "night") is True


@_SKIP_NO_JELLYFISH
def test_metaphone_match_different_words_false():
    """Completely unrelated words should not match."""
    assert metaphone_match("elephant", "computer") is False


@_SKIP_NO_JELLYFISH
def test_metaphone_match_same_word_true():
    """A word always matches itself."""
    assert metaphone_match("python", "python") is True


# ---------------------------------------------------------------------------
# 3. build_metaphone_index — O(1) reverse lookup structure
# ---------------------------------------------------------------------------


@_SKIP_NO_JELLYFISH
def test_build_index_smith_smyth_same_bucket():
    """smith and smyth must land in the same primary-key bucket."""
    index = build_metaphone_index(["smith", "smyth", "jones"])
    # Find the bucket that contains smith
    bucket_key = metaphone_key("smith")[0]
    assert bucket_key in index
    bucket = index[bucket_key]
    assert "smith" in bucket
    assert "smyth" in bucket


@_SKIP_NO_JELLYFISH
def test_build_index_jones_separate_bucket():
    """jones must land in a different bucket from smith."""
    build_metaphone_index(["smith", "smyth", "jones"])
    smith_key = metaphone_key("smith")[0]
    jones_key = metaphone_key("jones")[0]
    assert smith_key != jones_key


@_SKIP_NO_JELLYFISH
def test_build_index_returns_dict():
    result = build_metaphone_index(["hello", "world"])
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 4. LRU cache hit (call twice, expect identical object identity)
# ---------------------------------------------------------------------------


@_SKIP_NO_JELLYFISH
def test_lru_cache_hit():
    """Second call must return the cached tuple (same object)."""
    # Clear cache to start clean
    metaphone_key.cache_clear()
    first = metaphone_key("caching")
    second = metaphone_key("caching")
    assert first is second  # LRU cache returns identical object


# ---------------------------------------------------------------------------
# 5. Edge cases
# ---------------------------------------------------------------------------


def test_empty_string_returns_empty_tuple():
    """Empty string must return ('', '') regardless of jellyfish availability."""
    result = metaphone_key("")
    assert result == ("", "")


def test_degraded_mode_flag():
    """_HAS_JELLYFISH must be a bool."""
    assert isinstance(_HAS_JELLYFISH, bool)


def test_degraded_mode_metaphone_match_false():
    """metaphone_match returns False when keys are ('', '')."""
    # If jellyfish is available, this test is vacuous but still passes.
    # If jellyfish is missing, ('', '') == ('', '') so match would naively
    # be True — but the function explicitly checks for empty keys.
    if not _HAS_JELLYFISH:
        assert metaphone_match("hello", "hello") is False


@_SKIP_NO_JELLYFISH
def test_unicode_non_english_no_raise():
    """Non-ASCII / CJK input must not raise — degrade gracefully."""
    try:
        result = metaphone_key("中文")
        assert isinstance(result, tuple)
    except Exception as exc:
        pytest.fail(f"metaphone_key raised on Unicode input: {exc}")


@_SKIP_NO_JELLYFISH
def test_build_index_empty_list():
    """build_metaphone_index on empty list returns empty dict."""
    assert build_metaphone_index([]) == {}

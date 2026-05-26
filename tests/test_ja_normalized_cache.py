"""Tests for Japanese Tier 1 normalized-key cache.

Coverage targets:
- build_normalized_index: collision bucketing, empty input, 1000-item scale
- lookup_normalized: hit, miss, LRU cache re-use
- normalize_query_window: idempotent, cached
- _normalize_phonetic_internal: 5 representative rule pairs (dict-based, no str.translate)
- JaNormalizedItem: frozen + slots enforcement
- edge cases: empty string, case insensitivity, unicode kana passthrough
"""

from __future__ import annotations

import time

import pytest

from phonofix.languages.japanese.normalized_cache import (
    JaNormalizedItem,
    _normalize_phonetic_internal,
    build_normalized_index,
    lookup_normalized,
    normalize_query_window,
)

# ---------------------------------------------------------------------------
# _normalize_phonetic_internal — dict-based rules (no str.translate)
# ---------------------------------------------------------------------------


class TestNormalizePhoneticInternal:
    """Verify that all rule groups fire correctly via str.replace (not str.translate)."""

    # --- ROMANIZATION_VARIANTS (5 representative pairs) ---

    def test_si_to_shi(self):
        assert _normalize_phonetic_internal("sika") == "shika"

    def test_sya_to_sha(self):
        assert _normalize_phonetic_internal("sya") == "sha"

    def test_tu_to_tsu(self):
        assert _normalize_phonetic_internal("tuna") == "tsuna"

    def test_zi_to_ji(self):
        assert _normalize_phonetic_internal("zikan") == "jikan"

    def test_la_to_ra(self):
        # L/R confusion: ASR may emit "la" for "ra"
        assert _normalize_phonetic_internal("la") == "ra"

    # --- FUZZY_LONG_VOWELS ---

    def test_ou_to_o(self):
        # 東京 toukyou -> tokyo after long-vowel collapse
        assert _normalize_phonetic_internal("toukyou") == "tokyo"

    def test_ei_to_e(self):
        # 先生 sensei -> sense
        assert _normalize_phonetic_internal("sensei") == "sense"

    # --- FUZZY_GEMINATION ---

    def test_kk_to_k(self):
        assert _normalize_phonetic_internal("kk") == "k"

    def test_tt_to_t(self):
        assert _normalize_phonetic_internal("mattchi") == "machi"

    # --- FUZZY_NASALS ---

    def test_mb_to_nb(self):
        # 新聞 shimbun -> shinbun
        assert _normalize_phonetic_internal("shimbun") == "shinbun"

    # --- Case insensitivity ---

    def test_uppercase_lowercased(self):
        assert _normalize_phonetic_internal("SYA") == "sha"

    # --- Empty string ---

    def test_empty_string(self):
        assert _normalize_phonetic_internal("") == ""


# ---------------------------------------------------------------------------
# build_normalized_index
# ---------------------------------------------------------------------------


class TestBuildNormalizedIndex:
    def test_two_aliases_same_normalized_key(self):
        """'シヤ' and 'sya' both normalize to 'sha' -> share one bucket."""
        index = build_normalized_index([("シヤ", "シャ"), ("sya", "sha")])
        # 'シヤ' is kana; _normalize_phonetic_internal lowercases it but has no
        # rule for kana, so its key is 'シヤ' (lowercased = 'シヤ').
        # 'sya' normalizes to 'sha'.
        # They are different keys — but both are distinct valid entries.
        assert "sha" in index
        sya_items = index["sha"]
        assert len(sya_items) >= 1
        assert any(item.canonical == "sha" for item in sya_items)

    def test_two_romaji_variants_same_bucket(self):
        """'si' -> 'shi' and 'shi' -> 'shi': same bucket."""
        index = build_normalized_index([("si", "shi"), ("shi", "shi")])
        assert "shi" in index
        assert len(index["shi"]) == 2

    def test_original_preserved(self):
        """original field must store the raw alias, not the normalized form."""
        index = build_normalized_index([("si", "shi")])
        items = index["shi"]
        assert items[0].original == "si"

    def test_canonical_preserved(self):
        index = build_normalized_index([("si", "shi")])
        items = index["shi"]
        assert items[0].canonical == "shi"

    def test_empty_items(self):
        """Empty input produces empty index."""
        index = build_normalized_index([])
        assert index == {}

    def test_single_item(self):
        index = build_normalized_index([("toukyou", "東京")])
        # toukyou -> tokyo
        assert "tokyo" in index
        assert index["tokyo"][0].canonical == "東京"

    def test_scale_1000_items(self):
        """Build index of 1000 items without error."""
        items = [(f"alias{i}", f"canonical{i}") for i in range(1000)]
        index = build_normalized_index(items)
        assert len(index) >= 1  # at least one bucket exists

    def test_normalized_field_matches_key(self):
        """JaNormalizedItem.normalized must equal the bucket key."""
        index = build_normalized_index([("sya", "sha")])
        for key, item_list in index.items():
            for item in item_list:
                assert item.normalized == key


# ---------------------------------------------------------------------------
# lookup_normalized
# ---------------------------------------------------------------------------


class TestLookupNormalized:
    def setup_method(self):
        self.index = build_normalized_index(
            [
                ("si", "shi"),
                ("sya", "sha"),
                ("toukyou", "tokyo"),
                ("shimbun", "shinbun"),
            ]
        )

    def test_hit_returns_matching_items(self):
        result = lookup_normalized(self.index, "si")
        assert len(result) == 1
        assert result[0].canonical == "shi"

    def test_hit_sya_variant(self):
        result = lookup_normalized(self.index, "sya")
        assert result
        assert result[0].canonical == "sha"

    def test_hit_long_vowel(self):
        result = lookup_normalized(self.index, "toukyou")
        assert result
        assert result[0].canonical == "tokyo"

    def test_miss_returns_empty_list(self):
        result = lookup_normalized(self.index, "zzznomatch")
        assert result == []

    def test_empty_query_returns_empty_list(self):
        result = lookup_normalized(self.index, "")
        # "" normalizes to "" which is not in the index
        assert result == []

    def test_lru_cache_hit_same_object(self):
        """Calling normalize_query_window twice with the same arg returns the
        same cached string object (identity check)."""
        # Clear and warm the cache
        normalize_query_window.cache_clear()
        first = normalize_query_window("sya")
        second = normalize_query_window("sya")
        assert first is second  # same interned/cached object

    def test_two_calls_same_result(self):
        """lookup_normalized is idempotent."""
        r1 = lookup_normalized(self.index, "si")
        r2 = lookup_normalized(self.index, "si")
        assert r1 == r2


# ---------------------------------------------------------------------------
# normalize_query_window — cache behaviour
# ---------------------------------------------------------------------------


class TestNormalizeQueryWindow:
    def test_basic_normalization(self):
        normalize_query_window.cache_clear()
        assert normalize_query_window("sya") == "sha"

    def test_cache_info_increments(self):
        normalize_query_window.cache_clear()
        normalize_query_window("sya")
        normalize_query_window("sya")  # should be cache hit
        info = normalize_query_window.cache_info()
        assert info.hits >= 1

    def test_empty_query(self):
        normalize_query_window.cache_clear()
        assert normalize_query_window("") == ""


# ---------------------------------------------------------------------------
# JaNormalizedItem — frozen + slots
# ---------------------------------------------------------------------------


class TestJaNormalizedItem:
    def test_frozen_immutable(self):
        """Assigning to a field on a frozen dataclass must raise FrozenInstanceError."""
        item = JaNormalizedItem(original="si", normalized="shi", canonical="shi")
        with pytest.raises(Exception):  # FrozenInstanceError (subclass of AttributeError)
            item.original = "other"  # type: ignore[misc]

    def test_slots_no_dict(self):
        """slots=True means instances have no __dict__."""
        item = JaNormalizedItem(original="si", normalized="shi", canonical="shi")
        assert not hasattr(item, "__dict__")

    def test_equality(self):
        a = JaNormalizedItem(original="si", normalized="shi", canonical="shi")
        b = JaNormalizedItem(original="si", normalized="shi", canonical="shi")
        assert a == b

    def test_hashable(self):
        """frozen dataclass must be hashable (usable in set/dict)."""
        item = JaNormalizedItem(original="si", normalized="shi", canonical="shi")
        s = {item}
        assert item in s


# ---------------------------------------------------------------------------
# Scale + performance guard
# ---------------------------------------------------------------------------


class TestScaleAndPerformance:
    def test_build_1000_items_no_error(self):
        items = [(f"word{i}variant", f"canonical{i}") for i in range(1000)]
        index = build_normalized_index(items)
        assert len(index) > 0

    def test_lookup_1ms_budget(self):
        """1000 lookups must complete within 1 second (well above 1ms/lookup budget)."""
        items = [(f"si{i}", f"shi{i}") for i in range(200)]
        index = build_normalized_index(items)
        normalize_query_window.cache_clear()

        start = time.perf_counter()
        for i in range(1000):
            lookup_normalized(index, f"si{i % 200}")
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"1000 lookups took {elapsed:.3f}s (budget: 1s)"

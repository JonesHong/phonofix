"""Tests for dict schema v2 validator — Phase 2."""

from __future__ import annotations

import pytest

from phonofix.core.dict_schema import (
    DictSchemaError,
    DictV2,
    TermMode,
    validate_dict,
)

# ---------------------------------------------------------------------------
# Minimal valid payloads (reusable fixtures)
# ---------------------------------------------------------------------------

VALID_REPLACE_TERM = {
    "canonical": "雷電将軍",
    "mode": "replace",
    "aliases": ["雷霆将軍"],
    "keywords": ["原神"],
    "weight": 0.0,
}

VALID_PROTECT_TERM = {
    "canonical": "枝節",
    "mode": "protect",
}

MINIMAL_VALID_DICT = {
    "version": 2,
    "language": "zh",
    "terms": [VALID_REPLACE_TERM],
}


# ===========================================================================
# version field
# ===========================================================================


def test_version_2_ok():
    result = validate_dict(MINIMAL_VALID_DICT)
    assert isinstance(result, DictV2)
    assert result.version == 2


def test_version_1_raises():
    raw = {**MINIMAL_VALID_DICT, "version": 1}
    with pytest.raises(DictSchemaError, match="version"):
        validate_dict(raw)


def test_version_3_raises():
    raw = {**MINIMAL_VALID_DICT, "version": 3}
    with pytest.raises(DictSchemaError, match="version"):
        validate_dict(raw)


def test_version_string_raises():
    raw = {**MINIMAL_VALID_DICT, "version": "2"}
    with pytest.raises(DictSchemaError, match="version"):
        validate_dict(raw)


def test_version_missing_raises():
    raw = {"language": "zh", "terms": [VALID_REPLACE_TERM]}
    with pytest.raises(DictSchemaError, match="version"):
        validate_dict(raw)


# ===========================================================================
# language field
# ===========================================================================


@pytest.mark.parametrize("lang", ["zh", "ja", "en", "ko"])
def test_valid_languages(lang):
    raw = {**MINIMAL_VALID_DICT, "language": lang}
    result = validate_dict(raw)
    assert result.language == lang


def test_language_es_raises():
    raw = {**MINIMAL_VALID_DICT, "language": "es"}
    with pytest.raises(DictSchemaError, match="language"):
        validate_dict(raw)


def test_language_fr_raises():
    raw = {**MINIMAL_VALID_DICT, "language": "fr"}
    with pytest.raises(DictSchemaError, match="language"):
        validate_dict(raw)


def test_language_missing_raises():
    raw = {"version": 2, "terms": [VALID_REPLACE_TERM]}
    with pytest.raises(DictSchemaError, match="language"):
        validate_dict(raw)


# ===========================================================================
# mode=replace
# ===========================================================================


def test_replace_with_aliases_ok():
    raw = {
        "version": 2,
        "language": "zh",
        "terms": [
            {"canonical": "雷電将軍", "mode": "replace", "aliases": ["雷霆将軍"]},
        ],
    }
    result = validate_dict(raw)
    term = result.terms[0]
    assert term.mode == TermMode.REPLACE
    assert term.aliases == ["雷霆将軍"]


def test_replace_empty_aliases_raises():
    raw = {
        "version": 2,
        "language": "zh",
        "terms": [
            {"canonical": "雷電将軍", "mode": "replace", "aliases": []},
        ],
    }
    with pytest.raises(DictSchemaError, match="non-empty.*aliases|aliases.*non-empty"):
        validate_dict(raw)


def test_replace_missing_aliases_raises():
    raw = {
        "version": 2,
        "language": "zh",
        "terms": [
            {"canonical": "雷電将軍", "mode": "replace"},
        ],
    }
    with pytest.raises(DictSchemaError, match="aliases"):
        validate_dict(raw)


def test_replace_with_keywords_and_weight_ok():
    raw = {
        "version": 2,
        "language": "zh",
        "terms": [
            {
                "canonical": "雷電将軍",
                "mode": "replace",
                "aliases": ["雷霆将軍"],
                "keywords": ["原神", "遊戲"],
                "weight": 1.5,
            }
        ],
    }
    result = validate_dict(raw)
    term = result.terms[0]
    assert term.keywords == ["原神", "遊戲"]
    assert term.weight == 1.5


# ===========================================================================
# mode=protect
# ===========================================================================


def test_protect_no_aliases_ok():
    raw = {
        "version": 2,
        "language": "zh",
        "terms": [VALID_PROTECT_TERM],
    }
    result = validate_dict(raw)
    term = result.terms[0]
    assert term.mode == TermMode.PROTECT
    assert term.canonical == "枝節"
    assert term.aliases == []
    assert term.keywords == []
    assert term.weight == 0.0


def test_protect_with_aliases_raises():
    raw = {
        "version": 2,
        "language": "zh",
        "terms": [
            {"canonical": "枝節", "mode": "protect", "aliases": ["枝葉"]},
        ],
    }
    with pytest.raises(DictSchemaError, match="aliases"):
        validate_dict(raw)


def test_protect_with_keywords_raises():
    raw = {
        "version": 2,
        "language": "zh",
        "terms": [
            {"canonical": "枝節", "mode": "protect", "keywords": ["植物"]},
        ],
    }
    with pytest.raises(DictSchemaError, match="keywords"):
        validate_dict(raw)


def test_protect_with_nonzero_weight_raises():
    raw = {
        "version": 2,
        "language": "zh",
        "terms": [
            {"canonical": "枝節", "mode": "protect", "weight": 0.5},
        ],
    }
    with pytest.raises(DictSchemaError, match="weight"):
        validate_dict(raw)


# ===========================================================================
# duplicate canonical
# ===========================================================================


def test_duplicate_canonical_raises():
    raw = {
        "version": 2,
        "language": "zh",
        "terms": [
            {"canonical": "雷電将軍", "mode": "replace", "aliases": ["雷霆将軍"]},
            {"canonical": "雷電将軍", "mode": "replace", "aliases": ["Raiden Shogun"]},
        ],
    }
    with pytest.raises(DictSchemaError, match="[Dd]uplicate.*canonical|canonical.*[Dd]uplicate"):
        validate_dict(raw)


def test_unique_canonicals_ok():
    raw = {
        "version": 2,
        "language": "zh",
        "terms": [
            {"canonical": "雷電将軍", "mode": "replace", "aliases": ["雷霆将軍"]},
            {"canonical": "枝節", "mode": "protect"},
        ],
    }
    result = validate_dict(raw)
    assert len(result.terms) == 2


# ===========================================================================
# confusion_overrides
# ===========================================================================


def test_confusion_overrides_empty_dict_ok():
    raw = {**MINIMAL_VALID_DICT, "confusion_overrides": {}}
    result = validate_dict(raw)
    assert result.confusion_overrides == {}


def test_confusion_overrides_valid_mapping_ok():
    raw = {
        **MINIMAL_VALID_DICT,
        "confusion_overrides": {"ㄢ": ["ㄤ"], "n": ["l"]},
    }
    result = validate_dict(raw)
    assert result.confusion_overrides == {"ㄢ": ["ㄤ"], "n": ["l"]}


def test_confusion_overrides_absent_ok():
    raw = {k: v for k, v in MINIMAL_VALID_DICT.items() if k != "confusion_overrides"}
    result = validate_dict(raw)
    assert result.confusion_overrides == {}


# ===========================================================================
# Full SPEC.md Appendix A example (complete yaml loaded)
# ===========================================================================


def test_spec_appendix_a_full_example_ok():
    """Complete example from SPEC.md Appendix A must validate without error."""
    raw = {
        "version": 2,
        "language": "zh",
        "terms": [
            {
                "canonical": "雷電将軍",
                "mode": "replace",
                "aliases": ["雷霆将軍"],
                "keywords": ["原神"],
                "weight": 0.0,
            },
            {
                "canonical": "枝節",
                "mode": "protect",
            },
        ],
        "confusion_overrides": {
            "ㄢ": ["ㄤ"],
        },
    }
    result = validate_dict(raw)
    assert result.version == 2
    assert result.language == "zh"
    assert len(result.terms) == 2

    replace_term = result.terms[0]
    assert replace_term.canonical == "雷電将軍"
    assert replace_term.mode == TermMode.REPLACE
    assert replace_term.aliases == ["雷霆将軍"]
    assert replace_term.keywords == ["原神"]
    assert replace_term.weight == 0.0

    protect_term = result.terms[1]
    assert protect_term.canonical == "枝節"
    assert protect_term.mode == TermMode.PROTECT
    assert protect_term.aliases == []

    assert result.confusion_overrides == {"ㄢ": ["ㄤ"]}


# ===========================================================================
# Multi-alias replace term
# ===========================================================================


def test_replace_multiple_aliases_ok():
    raw = {
        "version": 2,
        "language": "ja",
        "terms": [
            {
                "canonical": "台北駅",
                "mode": "replace",
                "aliases": ["北車", "台北車站", "タイペイ"],
            }
        ],
    }
    result = validate_dict(raw)
    assert result.terms[0].aliases == ["北車", "台北車站", "タイペイ"]


# ===========================================================================
# mode field validation
# ===========================================================================


def test_invalid_mode_raises():
    raw = {
        "version": 2,
        "language": "en",
        "terms": [
            {"canonical": "hello", "mode": "unknown", "aliases": ["hi"]},
        ],
    }
    with pytest.raises(DictSchemaError, match="mode"):
        validate_dict(raw)


def test_missing_mode_raises():
    raw = {
        "version": 2,
        "language": "en",
        "terms": [
            {"canonical": "hello", "aliases": ["hi"]},
        ],
    }
    with pytest.raises(DictSchemaError, match="mode"):
        validate_dict(raw)


# ===========================================================================
# canonical field validation
# ===========================================================================


def test_missing_canonical_raises():
    raw = {
        "version": 2,
        "language": "ko",
        "terms": [
            {"mode": "replace", "aliases": ["대박"]},
        ],
    }
    with pytest.raises(DictSchemaError, match="canonical"):
        validate_dict(raw)

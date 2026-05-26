"""Phase 1 skeleton tests for registry + registry_defaults.

These tests verify protocol structure and stub behaviour only.
No G2P backend implementations are tested here.
"""

import pytest

from phonofix.registry import (
    get_g2p,
    get_tokenizer,
    list_backends,
    register_g2p,
    register_tokenizer,
)
from phonofix.registry_defaults import DEFAULT_G2P, DEFAULT_TOKENIZER

# ---------------------------------------------------------------------------
# 1. Import sanity
# ---------------------------------------------------------------------------


def test_registry_imports_cleanly() -> None:
    """registry module imports without errors."""
    import phonofix.registry as _r  # noqa: F401 — import is the assertion

    assert _r is not None


def test_registry_defaults_imports_cleanly() -> None:
    """registry_defaults module imports without errors."""
    import phonofix.registry_defaults as _d  # noqa: F401

    assert _d is not None


# ---------------------------------------------------------------------------
# 2. Stub functions raise NotImplementedError
# ---------------------------------------------------------------------------


def test_register_g2p_raises() -> None:
    """register_g2p is a Phase 1 stub — must raise NotImplementedError."""
    with pytest.raises(NotImplementedError):
        register_g2p(object())  # type: ignore[arg-type]


def test_get_g2p_raises() -> None:
    """get_g2p is a Phase 1 stub — must raise NotImplementedError."""
    with pytest.raises(NotImplementedError):
        get_g2p("zh")


def test_register_tokenizer_raises() -> None:
    """register_tokenizer is a Phase 1 stub — must raise NotImplementedError."""
    with pytest.raises(NotImplementedError):
        register_tokenizer(object())  # type: ignore[arg-type]


def test_get_tokenizer_raises() -> None:
    """get_tokenizer is a Phase 1 stub — must raise NotImplementedError."""
    with pytest.raises(NotImplementedError):
        get_tokenizer("ja")


def test_list_backends_raises() -> None:
    """list_backends is a Phase 1 stub — must raise NotImplementedError."""
    with pytest.raises(NotImplementedError):
        list_backends()


# ---------------------------------------------------------------------------
# 3. DEFAULT_G2P / DEFAULT_TOKENIZER cover all 4 languages
# ---------------------------------------------------------------------------

_LANGUAGES = ["zh", "ja", "en", "ko"]


@pytest.mark.parametrize("lang", _LANGUAGES)
def test_default_g2p_has_entry(lang: str) -> None:
    assert lang in DEFAULT_G2P, f"DEFAULT_G2P missing entry for '{lang}'"
    assert isinstance(DEFAULT_G2P[lang], str)
    assert DEFAULT_G2P[lang]  # non-empty string


@pytest.mark.parametrize("lang", _LANGUAGES)
def test_default_tokenizer_has_entry(lang: str) -> None:
    assert lang in DEFAULT_TOKENIZER, f"DEFAULT_TOKENIZER missing entry for '{lang}'"
    mode, lib = DEFAULT_TOKENIZER[lang]
    assert mode in ("char", "word"), f"Unexpected mode '{mode}' for '{lang}'"
    # lib may be None (built-in) or a non-empty string
    assert lib is None or (isinstance(lib, str) and lib)

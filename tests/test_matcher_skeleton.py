"""Phase 2 skeleton tests for PhoneticMatcher.

Verify import hygiene, constructor attribute assignment,
and that every method body raises NotImplementedError.
No real G2P backend is exercised here.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from phonofix.core.matcher import PhoneticMatcher

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_phonemizer(language: str = "zh") -> SimpleNamespace:
    """Minimal stand-in that satisfies PhoneticMatcher ctor."""
    return SimpleNamespace(language=language, name="mock-phonemizer")


def _make_matcher(
    dictionary=None,
    on_event=None,
    language: str = "zh",
) -> PhoneticMatcher:
    return PhoneticMatcher(
        phonemizer=_mock_phonemizer(language),
        dictionary=dictionary if dictionary is not None else {},
        on_event=on_event,
    )


# ---------------------------------------------------------------------------
# 1. Import sanity
# ---------------------------------------------------------------------------


def test_import_cleanly() -> None:
    """PhoneticMatcher imports without errors."""
    import phonofix.core.matcher as _m  # noqa: F401

    assert _m is not None


# ---------------------------------------------------------------------------
# 2. Constructor — attribute assignment
# ---------------------------------------------------------------------------


def test_ctor_stores_phonemizer() -> None:
    ph = _mock_phonemizer()
    m = PhoneticMatcher(phonemizer=ph, dictionary={})
    assert m.phonemizer is ph


def test_ctor_stores_dictionary() -> None:
    d = {"台積電": {"aliases": ["太積電"]}}
    m = PhoneticMatcher(phonemizer=_mock_phonemizer(), dictionary=d)
    assert m.dictionary is d


def test_ctor_on_event_defaults_to_none() -> None:
    m = PhoneticMatcher(phonemizer=_mock_phonemizer(), dictionary={})
    assert m.on_event is None


def test_ctor_stores_on_event_callable() -> None:
    events: list[tuple[str, dict]] = []

    def handler(event: str, payload: dict) -> None:
        events.append((event, payload))

    m = PhoneticMatcher(phonemizer=_mock_phonemizer(), dictionary={}, on_event=handler)
    assert m.on_event is handler


def test_ctor_accepts_simple_namespace_phonemizer() -> None:
    """SimpleNamespace (duck-typed) phonemizer must not cause ctor errors."""
    ph = SimpleNamespace(language="en", name="stub")
    m = PhoneticMatcher(phonemizer=ph, dictionary={})
    assert m.phonemizer.language == "en"


# ---------------------------------------------------------------------------
# 3. Phase 3 methods raise NotImplementedError
# ---------------------------------------------------------------------------


def test_correct_raises() -> None:
    with pytest.raises(NotImplementedError, match="Phase 3"):
        _make_matcher().correct("台積電")


def test_correct_batch_raises() -> None:
    with pytest.raises(NotImplementedError, match="Phase 3"):
        _make_matcher().correct_batch(["台積電", "微軟"])


def test_explain_raises() -> None:
    with pytest.raises(NotImplementedError, match="Phase 3"):
        _make_matcher().explain("台積電")


def test_diagnose_raises() -> None:
    with pytest.raises(NotImplementedError, match="Phase 3"):
        _make_matcher().diagnose()


# ---------------------------------------------------------------------------
# 4. Phase 4 methods raise NotImplementedError
# ---------------------------------------------------------------------------


def test_feed_raises() -> None:
    with pytest.raises(NotImplementedError, match="Phase 4"):
        _make_matcher().feed("台積")


def test_flush_raises() -> None:
    with pytest.raises(NotImplementedError, match="Phase 4"):
        _make_matcher().flush()


def test_add_terms_raises() -> None:
    with pytest.raises(NotImplementedError, match="Phase 4"):
        _make_matcher().add_terms([{"canonical": "台積電"}])


def test_remove_terms_raises() -> None:
    with pytest.raises(NotImplementedError, match="Phase 4"):
        _make_matcher().remove_terms(["台積電"])

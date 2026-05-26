"""Phase 2→5 sanity tests for PhoneticMatcher.

Verify import hygiene, constructor attribute assignment,
and that the integration no longer raises NotImplementedError.
No real G2P backend is exercised here — uses a SimpleNamespace mock phonemizer.
"""

from __future__ import annotations

from types import SimpleNamespace

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
    events: list = []

    def handler(event) -> None:
        events.append(event)

    m = PhoneticMatcher(phonemizer=_mock_phonemizer(), dictionary={}, on_event=handler)
    assert m.on_event is handler
    m.close()


def test_ctor_accepts_simple_namespace_phonemizer() -> None:
    """SimpleNamespace (duck-typed) phonemizer must not cause ctor errors."""
    ph = SimpleNamespace(language="en", name="stub")
    m = PhoneticMatcher(phonemizer=ph, dictionary={})
    assert m.phonemizer.language == "en"


# ---------------------------------------------------------------------------
# 3. Methods are now IMPLEMENTED (Phase 5) — no more NotImplementedError
# ---------------------------------------------------------------------------


def test_correct_returns_str() -> None:
    """correct() no longer raises — returns a string."""
    m = _make_matcher()
    result = m.correct("台積電")
    assert isinstance(result, str)


def test_correct_batch_returns_list() -> None:
    """correct_batch() no longer raises — returns a list."""
    m = _make_matcher()
    result = m.correct_batch(["台積電", "微軟"])
    assert isinstance(result, list)
    assert len(result) == 2


def test_explain_returns_dict() -> None:
    """explain() no longer raises — returns a dict."""
    m = _make_matcher()
    result = m.explain("台積電")
    assert isinstance(result, dict)
    assert "version" in result


def test_diagnose_returns_dict() -> None:
    """diagnose() no longer raises — returns a dict."""
    m = _make_matcher()
    result = m.diagnose()
    assert isinstance(result, dict)
    assert "version" in result


def test_feed_returns_str() -> None:
    """feed() no longer raises — returns a string."""
    m = _make_matcher()
    result = m.feed("台積")
    assert isinstance(result, str)


def test_flush_returns_str() -> None:
    """flush() no longer raises — returns a string."""
    m = _make_matcher()
    result = m.flush()
    assert isinstance(result, str)


def test_add_terms_no_raise() -> None:
    """add_terms() no longer raises."""
    m = _make_matcher()
    # Empty dict entry — gracefully handled
    m.add_terms([{"canonical": "台積電", "mode": "protect"}])


def test_remove_terms_no_raise() -> None:
    """remove_terms() no longer raises."""
    m = _make_matcher()
    m.remove_terms(["台積電"])

"""Tests for Phoneme dataclass and Phonemizer Protocol (v0.4.0 Phase 2)."""

from __future__ import annotations

import pytest

from phonofix.core.phonemizer import Phoneme, Phonemizer

# ---------------------------------------------------------------------------
# Phoneme — immutability (frozen=True)
# ---------------------------------------------------------------------------


def test_phoneme_is_frozen():
    """Phoneme must be immutable; setting any attribute should raise."""
    p = Phoneme(value="p", language="zh")
    with pytest.raises((AttributeError, TypeError)):
        p.value = "b"  # type: ignore[misc]


def test_phoneme_frozen_weight():
    """Weight field is also immutable."""
    p = Phoneme(value="n", language="zh", weight=0.5)
    with pytest.raises((AttributeError, TypeError)):
        p.weight = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Phoneme — hashability (slots=True + frozen=True → __hash__ generated)
# ---------------------------------------------------------------------------


def test_phoneme_is_hashable():
    """Phoneme must be hashable so it can appear in sets / dict keys."""
    p1 = Phoneme(value="ɑ", language="en")
    p2 = Phoneme(value="n", language="zh")
    phoneme_set = {p1, p2}
    assert len(phoneme_set) == 2


def test_phoneme_hashable_dedup():
    """Two equal Phonemes hash to the same bucket → set deduplicates them."""
    p1 = Phoneme(value="l", language="zh", weight=0.3)
    p2 = Phoneme(value="l", language="zh", weight=0.3)
    assert len({p1, p2}) == 1


# ---------------------------------------------------------------------------
# Phoneme — equality
# ---------------------------------------------------------------------------


def test_phoneme_equality_same():
    """Phonemes with identical fields must be equal."""
    assert Phoneme("p", "en", 0.0) == Phoneme("p", "en", 0.0)


def test_phoneme_equality_different_language():
    """Same value but different language → not equal."""
    assert Phoneme("p", "en") != Phoneme("p", "zh")


def test_phoneme_equality_different_weight():
    """Same value + language but different weight → not equal."""
    assert Phoneme("n", "zh", 0.0) != Phoneme("n", "zh", 0.5)


def test_phoneme_default_weight():
    """Default weight is 0.0."""
    p = Phoneme(value="m", language="en")
    assert p.weight == 0.0


# ---------------------------------------------------------------------------
# Phoneme — slots=True (no __dict__)
# ---------------------------------------------------------------------------


def test_phoneme_no_dict():
    """slots=True means no __dict__ attribute on instances."""
    p = Phoneme(value="k", language="ko")
    assert not hasattr(p, "__dict__")


# ---------------------------------------------------------------------------
# Phonemizer — Protocol structural check (runtime_checkable)
# ---------------------------------------------------------------------------


class FakePhonemizer:
    """Minimal concrete implementation satisfying the Phonemizer Protocol."""

    language: str = "zh"
    name: str = "fake"

    def phonemize(self, text: str) -> list[Phoneme]:
        return [Phoneme(value=c, language=self.language) for c in text]

    def confusion(self, p: Phoneme) -> set[Phoneme]:
        # Simple stub: n/l confusion for zh
        if p.language == "zh" and p.value == "n":
            return {Phoneme("l", "zh")}
        return set()

    def cost(self, a: Phoneme, b: Phoneme) -> float:
        return 0.0 if a == b else 1.0


def test_phonemizer_isinstance_check():
    """FakePhonemizer satisfies the runtime-checkable Phonemizer Protocol."""
    fake = FakePhonemizer()
    assert isinstance(fake, Phonemizer)


def test_phonemizer_phonemize_returns_list_of_phoneme():
    """phonemize() must return a list of Phoneme instances."""
    fake = FakePhonemizer()
    result = fake.phonemize("ab")
    assert isinstance(result, list)
    assert all(isinstance(p, Phoneme) for p in result)


def test_phonemizer_confusion_returns_set():
    """confusion() must return a set; zh n→l confusion included."""
    fake = FakePhonemizer()
    p = Phoneme("n", "zh")
    confused = fake.confusion(p)
    assert isinstance(confused, set)
    assert Phoneme("l", "zh") in confused


def test_phonemizer_cost_identical():
    """cost() of identical phonemes must be 0.0."""
    fake = FakePhonemizer()
    p = Phoneme("p", "en")
    assert fake.cost(p, p) == 0.0


def test_phonemizer_cost_different():
    """cost() of different phonemes must be > 0."""
    fake = FakePhonemizer()
    a = Phoneme("p", "en")
    b = Phoneme("b", "en")
    assert fake.cost(a, b) > 0.0


def test_non_phonemizer_fails_isinstance():
    """An object missing required methods must NOT satisfy the Protocol."""

    class Incomplete:
        language: str = "en"
        name: str = "incomplete"
        # missing phonemize / confusion / cost

    assert not isinstance(Incomplete(), Phonemizer)

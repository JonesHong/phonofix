"""Tests for Korean MVP phonemizer (Phase 5).

Coverage:
- decompose_hangul: basic syllables + non-hangul
- KoreanPhonemizer.phonemize: hangul / mixed text
- KoreanPhonemizer.confusion: known + unknown phoneme
- KoreanPhonemizer.cost: same / confusable / different
- ImportError path: use_ko_pron=True without library
- Protocol conformance check
- LRU cache hit
"""

from __future__ import annotations

import pytest

from phonofix.core.phonemizer import Phoneme, Phonemizer
from phonofix.languages.korean.phonemizer import (
    KoreanPhonemizer,
    decompose_hangul,
)

# ---------------------------------------------------------------------------
# decompose_hangul
# ---------------------------------------------------------------------------


def test_decompose_ga():
    """가 → (ᄀ, ᅡ, '') — no jongseong."""
    cho, jung, jong = decompose_hangul("가")
    assert cho == "ᄀ"
    assert jung == "ᅡ"
    assert jong == ""


def test_decompose_han():
    """한 → (ᄒ, ᅡ, ᆫ) — has jongseong ㄴ."""
    cho, jung, jong = decompose_hangul("한")
    assert cho == "ᄒ"
    assert jung == "ᅡ"
    assert jong == "ᆫ"


def test_decompose_non_hangul_ascii():
    """ASCII character returns ('', '', '')."""
    assert decompose_hangul("A") == ("", "", "")


def test_decompose_non_hangul_digit():
    """Digit returns ('', '', '')."""
    assert decompose_hangul("1") == ("", "", "")


def test_decompose_non_hangul_space():
    """Space returns ('', '', '')."""
    assert decompose_hangul(" ") == ("", "", "")


# ---------------------------------------------------------------------------
# KoreanPhonemizer.phonemize
# ---------------------------------------------------------------------------


def test_phonemize_two_hangul_syllables():
    """가나 → exactly 2 Phoneme objects."""
    phonemes = KoreanPhonemizer().phonemize("가나")
    assert len(phonemes) == 2
    assert all(isinstance(p, Phoneme) for p in phonemes)
    assert all(p.language == "ko" for p in phonemes)


def test_phonemize_hangugeo_jamo():
    """한국어 → 3 Phoneme, each with correct jamo prefix."""
    phonemes = KoreanPhonemizer().phonemize("한국어")
    assert len(phonemes) == 3
    # 한: cho=ᄒ, jung=ᅡ, jong=ᆫ
    assert phonemes[0].value.startswith("ᄒ")
    # 국: cho=ᄀ
    assert phonemes[1].value.startswith("ᄀ")
    # 어: cho=ᄋ (zero-initial consonant slot)
    assert phonemes[2].value.startswith("ᄋ")


def test_phonemize_ascii_passthrough():
    """ASCII chars are passed through as single-char Phonemes."""
    phonemes = KoreanPhonemizer().phonemize("hello")
    assert len(phonemes) == 5
    values = [p.value for p in phonemes]
    assert values == list("hello")


def test_phonemize_mixed_text():
    """Mixed hangul + latin → correct count and language tag."""
    phonemes = KoreanPhonemizer().phonemize("안녕hi")
    assert len(phonemes) == 4  # 안, 녕, h, i
    assert phonemes[0].language == "ko"
    assert phonemes[2].value == "h"


# ---------------------------------------------------------------------------
# KoreanPhonemizer.confusion
# ---------------------------------------------------------------------------


def test_confusion_ga_contains_ka_kka():
    """가 confuses with 카 and 까."""
    p_ga = Phoneme(value="가", language="ko")
    phonemizer = KoreanPhonemizer()
    confused = phonemizer.confusion(p_ga)
    confused_values = {c.value for c in confused}
    assert "카" in confused_values
    assert "까" in confused_values


def test_confusion_unknown_phoneme_empty():
    """Unknown phoneme → empty confusion set."""
    p_unknown = Phoneme(value="XYZ", language="ko")
    confused = KoreanPhonemizer().confusion(p_unknown)
    assert confused == set()


def test_confusion_returns_phoneme_objects():
    """confusion() returns set of Phoneme, not raw strings."""
    p_ae = Phoneme(value="애", language="ko")
    confused = KoreanPhonemizer().confusion(p_ae)
    assert all(isinstance(c, Phoneme) for c in confused)


# ---------------------------------------------------------------------------
# KoreanPhonemizer.cost
# ---------------------------------------------------------------------------


def test_cost_same_phoneme_zero():
    """cost(p, p) == 0.0."""
    p = Phoneme(value="가", language="ko")
    assert KoreanPhonemizer().cost(p, p) == 0.0


def test_cost_confusable_pair_0_3():
    """cost(가, 카) == 0.3 (confusable)."""
    p_ga = Phoneme(value="가", language="ko")
    p_ka = Phoneme(value="카", language="ko")
    assert KoreanPhonemizer().cost(p_ga, p_ka) == pytest.approx(0.3)


def test_cost_totally_different_1_0():
    """cost(가, 히) == 1.0 (no confusion rule)."""
    p_ga = Phoneme(value="가", language="ko")
    p_hi = Phoneme(value="히", language="ko")
    assert KoreanPhonemizer().cost(p_ga, p_hi) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# use_ko_pron flag
# ---------------------------------------------------------------------------


def test_use_ko_pron_false_works_without_library():
    """use_ko_pron=False must work regardless of ko_pron availability."""
    phonemizer = KoreanPhonemizer(use_ko_pron=False)
    assert phonemizer.use_ko_pron is False
    phonemes = phonemizer.phonemize("가")
    assert len(phonemes) == 1


def test_use_ko_pron_true_raises_if_not_installed(monkeypatch):
    """use_ko_pron=True raises ImportError when ko_pron is absent."""
    import phonofix.languages.korean.phonemizer as mod

    monkeypatch.setattr(mod, "_HAS_KO_PRON", False)
    with pytest.raises(ImportError):
        KoreanPhonemizer(use_ko_pron=True)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_phonemizer_protocol_conformance():
    """KoreanPhonemizer satisfies the runtime_checkable Phonemizer Protocol."""
    phonemizer = KoreanPhonemizer()
    assert isinstance(phonemizer, Phonemizer)


# ---------------------------------------------------------------------------
# LRU cache hit
# ---------------------------------------------------------------------------


def test_lru_cache_hit():
    """Second call with same text returns the same list object (cached)."""
    phonemizer = KoreanPhonemizer()
    result1 = phonemizer.phonemize("가나다")
    result2 = phonemizer.phonemize("가나다")
    assert result1 is result2  # exact same object from cache

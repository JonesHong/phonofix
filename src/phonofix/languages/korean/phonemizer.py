"""KoreanPhonemizer — Hangul Jamo decompose + ko-pron G2P (MVP).

Implements Phonemizer Protocol (core/phonemizer.py).
"""

from __future__ import annotations

from functools import lru_cache

from phonofix.core.phonemizer import Phoneme
from phonofix.languages.korean import KOREAN_INSTALL_HINT

try:
    import ko_pron  # noqa: F401

    _HAS_KO_PRON = True
except ImportError:
    _HAS_KO_PRON = False

# Hangul Jamo unicode ranges
HANGUL_BASE = 0xAC00  # 가
HANGUL_END = 0xD7A3  # 힣
CHO_COUNT = 19  # 초성 (initial consonants)
JUNG_COUNT = 21  # 중성 (medial vowels)
JONG_COUNT = 28  # 종성 (final consonants, +1 for no jongseong)

CHO_TABLE = [
    "ᄀ",
    "ᄁ",
    "ᄂ",
    "ᄃ",
    "ᄄ",
    "ᄅ",
    "ᄆ",
    "ᄇ",
    "ᄈ",
    "ᄉ",
    "ᄊ",
    "ᄋ",
    "ᄌ",
    "ᄍ",
    "ᄎ",
    "ᄏ",
    "ᄐ",
    "ᄑ",
    "ᄒ",
]
JUNG_TABLE = [
    "ᅡ",
    "ᅢ",
    "ᅣ",
    "ᅤ",
    "ᅥ",
    "ᅦ",
    "ᅧ",
    "ᅨ",
    "ᅩ",
    "ᅪ",
    "ᅫ",
    "ᅬ",
    "ᅭ",
    "ᅮ",
    "ᅯ",
    "ᅰ",
    "ᅱ",
    "ᅲ",
    "ᅳ",
    "ᅴ",
    "ᅵ",
]
JONG_TABLE = [
    "",
    "ᆨ",
    "ᆩ",
    "ᆪ",
    "ᆫ",
    "ᆬ",
    "ᆭ",
    "ᆮ",
    "ᆯ",
    "ᆰ",
    "ᆱ",
    "ᆲ",
    "ᆳ",
    "ᆴ",
    "ᆵ",
    "ᆶ",
    "ᆷ",
    "ᆸ",
    "ᆹ",
    "ᆺ",
    "ᆻ",
    "ᆼ",
    "ᆽ",
    "ᆾ",
    "ᆿ",
    "ᇀ",
    "ᇁ",
    "ᇂ",
]


def decompose_hangul(syllable: str) -> tuple[str, str, str]:
    """가 → (ᄀ, ᅡ, '') tuple of (cho, jung, jong)."""
    code = ord(syllable)
    if not (HANGUL_BASE <= code <= HANGUL_END):
        return ("", "", "")
    offset = code - HANGUL_BASE
    jong_idx = offset % JONG_COUNT
    jung_idx = (offset // JONG_COUNT) % JUNG_COUNT
    cho_idx = offset // (JUNG_COUNT * JONG_COUNT)
    return (CHO_TABLE[cho_idx], JUNG_TABLE[jung_idx], JONG_TABLE[jong_idx])


class KoreanPhonemizer:
    """Implements core.phonemizer.Phonemizer Protocol."""

    language = "ko"
    name = "korean-jamo"  # or "ko-pron" if available

    def __init__(self, use_ko_pron: bool | None = None):
        # default: use ko_pron if available, else jamo-only fallback
        self.use_ko_pron = _HAS_KO_PRON if use_ko_pron is None else use_ko_pron
        if self.use_ko_pron and not _HAS_KO_PRON:
            raise ImportError(KOREAN_INSTALL_HINT)

    @lru_cache(maxsize=10000)
    def phonemize(self, text: str) -> list[Phoneme]:
        """Text → phoneme sequence. Jamo per syllable + optional ko_pron romanization."""
        phonemes = []
        for ch in text:
            cho, jung, jong = decompose_hangul(ch)
            if cho:  # is hangul
                # one Phoneme per syllable, value = jamo tuple joined
                value = f"{cho}{jung}{jong}"
                phonemes.append(Phoneme(value=value, language="ko", weight=0.0))
            else:
                # non-hangul char — pass through as-is
                phonemes.append(Phoneme(value=ch, language="ko", weight=0.0))
        return phonemes

    def confusion(self, p: Phoneme) -> set[Phoneme]:
        """5-10 條 MVP confusion rules. Real ground truth 待 50 句 KsponSpeech 分析."""
        from phonofix.languages.korean.confusion_rules import KOREAN_CONFUSION_MAP

        confusables = KOREAN_CONFUSION_MAP.get(p.value, set())
        return {Phoneme(value=c, language="ko", weight=0.0) for c in confusables}

    def cost(self, a: Phoneme, b: Phoneme) -> float:
        if a == b:
            return 0.0
        if b in self.confusion(a):
            return 0.3  # similar phoneme cost
        return 1.0  # totally different

"""
英文發音系統實作模組

本模組只負責：
- IPA 表示法的正規化（供距離計算）
- IPA 字串相似度計算（Levenshtein + 群組/骨架）

G2P（文字 -> IPA）、espeak-ng/phonemizer 初始化與快取由 backend 單一真實來源負責：
- phonofix.backend.english_backend.EnglishPhoneticBackend
"""

from __future__ import annotations

import Levenshtein

from phonofix.backend import EnglishPhoneticBackend, get_english_backend
from phonofix.core.phonetic_interface import PhoneticSystem

from .config import EnglishPhoneticConfig


class EnglishPhoneticSystem(PhoneticSystem):
    """
    英文發音系統（IPA distance / fuzzy match）

    注意：
    - `to_phonetic()` 會委派給 backend 做 G2P，再做必要的 IPA 正規化。
    - 相似度計算只針對 IPA 字串，不直接依賴 phonemizer。
    """

    def __init__(self, backend: EnglishPhoneticBackend | None = None) -> None:
        self._backend = backend or get_english_backend()

    def to_phonetic(self, text: str) -> str:
        ipa = self._backend.to_phonetic(text)
        return self._normalize_ipa_for_distance(ipa)

    def are_fuzzy_similar(self, phonetic1: str, phonetic2: str) -> bool:
        _, is_match = self.calculate_similarity_score(phonetic1, phonetic2)
        return is_match

    def calculate_similarity_score(self, phonetic1: str, phonetic2: str) -> tuple[float, bool]:
        """
        計算 IPA 相似度分數

        Returns:
            (error_ratio, is_fuzzy_match)
            error_ratio: 0.0 ~ 1.0 (越低越相似)
            is_fuzzy_match: 是否通過模糊匹配閾值
        """
        raw1 = self._normalize_ipa_for_distance(phonetic1)
        raw2 = self._normalize_ipa_for_distance(phonetic2)

        max_len = max(len(raw1), len(raw2))
        min_len = min(len(raw1), len(raw2))
        if max_len == 0:
            return 0.0, True

        if min_len > 0 and (max_len - min_len) / min_len > 0.8:
            return 1.0, False

        ratio_raw = Levenshtein.distance(raw1, raw2) / max_len

        g1 = self._map_to_phoneme_groups(raw1)
        g2 = self._map_to_phoneme_groups(raw2)
        g_max = max(len(g1), len(g2))
        ratio_group = Levenshtein.distance(g1, g2) / g_max if g_max else ratio_raw

        c1 = self._consonant_skeleton(raw1)
        c2 = self._consonant_skeleton(raw2)
        c_max = max(len(c1), len(c2))
        ratio_cons = Levenshtein.distance(c1, c2) / c_max if c_max >= 4 else 1.0

        error_ratio = min(ratio_raw, ratio_group, ratio_cons)
        tolerance = self.get_tolerance(max_len)

        if raw1 and raw2 and not self._are_first_phonemes_similar(raw1, raw2):
            tolerance = min(tolerance, 0.15)

        return error_ratio, error_ratio <= tolerance

    def _normalize_ipa_for_distance(self, ipa: str) -> str:
        ipa = (ipa or "").replace(" ", "")
        ipa = ipa.replace("ː", "")
        ipa = ipa.replace("ɚ", "ə").replace("ɝ", "ə")
        ipa = ipa.replace("ɡ", "g")
        return ipa

    def _map_to_phoneme_groups(self, ipa: str) -> str:
        mapped: list[str] = []
        for ch in ipa:
            code = None
            for idx, group in enumerate(EnglishPhoneticConfig.FUZZY_PHONEME_GROUPS):
                if ch in group:
                    code = chr(ord("A") + idx)
                    break
            mapped.append(code if code is not None else ch)
        return "".join(mapped)

    def _consonant_skeleton(self, ipa: str) -> str:
        vowels = {
            "a",
            "e",
            "i",
            "o",
            "u",
            "ɪ",
            "ɛ",
            "æ",
            "ɑ",
            "ɔ",
            "ʌ",
            "ə",
            "ɐ",
            "ʊ",
            "ɚ",
            "ɝ",
        }
        weak = {"j", "w"}
        return "".join([ch for ch in ipa if ch not in vowels and ch not in weak])

    def _are_first_phonemes_similar(self, phonetic1: str, phonetic2: str) -> bool:
        if not phonetic1 or not phonetic2:
            return True

        first1 = phonetic1[0]
        first2 = phonetic2[0]

        if first1 == first2:
            return True

        for group in EnglishPhoneticConfig.FUZZY_PHONEME_GROUPS:
            if first1 in group and first2 in group:
                return True

        return False

    def get_tolerance(self, length: int) -> float:
        if length <= 3:
            return 0.15
        if length <= 5:
            return 0.25
        if length <= 8:
            return 0.35
        return 0.40


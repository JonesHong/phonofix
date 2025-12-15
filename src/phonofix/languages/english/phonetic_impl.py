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
        """
        初始化英文發音系統。

        Args:
            backend: 可選 backend（未提供則取得英文 backend 單例）

        注意：
        - backend 會負責 phonemizer/espeak-ng 初始化與快取
        - 本類別專注在 IPA 正規化與相似度計算
        """
        self._backend = backend or get_english_backend()

    def to_phonetic(self, text: str) -> str:
        """
        將文字轉換為 IPA（並做距離計算用的正規化）。

        流程：
        - 委派 backend 做 G2P（文字 -> IPA）
        - 去除空白/長音等符號，使距離計算更穩定
        """
        ipa = self._backend.to_phonetic(text)
        return self._normalize_ipa_for_distance(ipa)

    def are_fuzzy_similar(self, phonetic1: str, phonetic2: str) -> bool:
        """
        判斷兩個 IPA 是否可視為模糊相似（符合容錯閾值）。

        這是一個 convenience wrapper，內部呼叫 `calculate_similarity_score()`。
        """
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
        """
        將 IPA 正規化成適合距離計算的形式。

        目的：
        - 去除空白與長音符號（ː）
        - 統一一些 IPA 表示差異（例如 ɚ/ɝ -> ə，ɡ -> g）
        """
        ipa = (ipa or "").replace(" ", "")
        ipa = ipa.replace("ː", "")
        ipa = ipa.replace("ɚ", "ə").replace("ɝ", "ə")
        ipa = ipa.replace("ɡ", "g")
        return ipa

    def _map_to_phoneme_groups(self, ipa: str) -> str:
        """
        將 IPA 字元映射到「音素群組代碼」以降低距離敏感度。

        說明：
        - EnglishPhoneticConfig.FUZZY_PHONEME_GROUPS 定義了相近音的群組
        - 把同群組音素映射成同一代碼（A/B/C...），可提高模糊匹配的召回率
        """
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
        """
        從 IPA 中抽出「子音骨架」字串。

        用途：
        - 有些 ASR 錯誤主要落在母音上；子音骨架距離能提供更穩定的判斷
        - 僅在骨架足夠長（c_max >= 4）時納入評分，避免過短造成誤判
        """
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
        """
        檢查首音是否相容（作為額外保守門檻）。

        - 若首音差異過大，常代表完全不同詞彙，即使後續距離小也可能是誤命中
        - 這裡使用 FUZZY_PHONEME_GROUPS 允許「首音同群組」的寬鬆匹配
        """
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
        """
        根據 IPA 長度選擇容錯閾值（越短越嚴格）。

        直覺：
        - 短詞只要改一點就差很多，因此 tolerance 低
        - 長詞允許更多差異，因此 tolerance 高
        """
        if length <= 3:
            return 0.15
        if length <= 5:
            return 0.25
        if length <= 8:
            return 0.35
        return 0.40

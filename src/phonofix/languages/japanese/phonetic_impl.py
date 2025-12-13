"""
日文發音系統實作模組

實作基於 Cutlet (Romaji) 的日文發音轉換。
"""

from __future__ import annotations

from typing import Tuple
from phonofix.core.phonetic_interface import PhoneticSystem
from .utils import _get_cutlet
from .config import JapanesePhoneticConfig


class JapanesePhoneticSystem(PhoneticSystem):
    """
    日文發音系統

    功能:
    - 將日文文本 (漢字、假名) 轉換為羅馬拼音 (Romaji)
    - 使用 Cutlet 庫進行轉換，支援語境讀音 (如助詞 'ha' -> 'wa')
    - 支援基於規則的模糊比對 (長音、促音、羅馬字變體)
    """

    def to_phonetic(self, text: str) -> str:
        """
        將日文文本轉換為羅馬拼音

        Args:
            text: 輸入日文文本

        Returns:
            str: 羅馬拼音字串 (小寫)
        """
        if not text:
            return ""
            
        cutlet = _get_cutlet()
        # 轉換為羅馬拼音並轉小寫
        romaji = cutlet.romaji(text).lower()
        
        # 移除空格 (Cutlet 預設會加空格)
        # 我們希望得到連續的拼音字串以進行比對
        # 例如 "Tokyo Station" -> "tokyostation"
        romaji = romaji.replace(" ", "")
        
        # 移除長音符號 (Macrons) 以統一格式
        # Cutlet 預設使用赫本式 (Hepburn) 會產生長音符號
        macrons = {
            "ā": "a", "ī": "i", "ū": "u", "ē": "e", "ō": "o",
            "â": "a", "î": "i", "û": "u", "ê": "e", "ô": "o",
        }
        for m, p in macrons.items():
            romaji = romaji.replace(m, p)
            
        return romaji

    def calculate_similarity_score(self, phonetic1: str, phonetic2: str) -> Tuple[float, bool]:
        """
        計算羅馬拼音相似度分數

        Returns:
            (error_ratio, is_fuzzy_match)
            error_ratio: 0.0 ~ 1.0 (越低越相似)
            is_fuzzy_match: 是否通過模糊匹配閾值
        """
        import Levenshtein
        
        # 1. 正規化
        norm1 = self._normalize_phonetic(phonetic1)
        norm2 = self._normalize_phonetic(phonetic2)
        
        # 2. 計算編輯距離
        dist = Levenshtein.distance(norm1, norm2)
        max_len = max(len(norm1), len(norm2))
        
        if max_len == 0:
            return 0.0, True
            
        ratio = dist / max_len
        
        return ratio, ratio <= self.get_tolerance(max_len)

    def _normalize_phonetic(self, phonetic: str) -> str:
        """
        正規化羅馬拼音以進行模糊比對
        
        應用 config 中定義的模糊規則：
        1. 羅馬字變體標準化 (si -> shi)
        2. 長音縮短 (aa -> a, ou -> o)
        3. 促音簡化 (kk -> k)
        4. 鼻音標準化 (mb -> nb)
        """
        normalized = phonetic
        
        # 1. 羅馬字變體標準化
        for variant, standard in JapanesePhoneticConfig.ROMANIZATION_VARIANTS.items():
            normalized = normalized.replace(variant, standard)
            
        # 2. 長音縮短
        for long_vowel, short_vowel in JapanesePhoneticConfig.FUZZY_LONG_VOWELS.items():
            normalized = normalized.replace(long_vowel, short_vowel)
            
        # 3. 促音簡化
        for geminated, single in JapanesePhoneticConfig.FUZZY_GEMINATION.items():
            normalized = normalized.replace(geminated, single)
            
        # 4. 鼻音標準化
        for nasal_variant, standard in JapanesePhoneticConfig.FUZZY_NASALS.items():
            normalized = normalized.replace(nasal_variant, standard)
            
        return normalized

    def are_fuzzy_similar(self, phonetic1: str, phonetic2: str) -> bool:
        """
        判斷兩個羅馬拼音是否模糊相似

        Args:
            phonetic1: 拼音字串 1
            phonetic2: 拼音字串 2

        Returns:
            bool: 是否相似
        """
        _, is_match = self.calculate_similarity_score(phonetic1, phonetic2)
        return is_match

    def get_tolerance(self, length: int) -> float:
        """
        根據文本長度決定容錯率

        Args:
            length: 發音字串長度

        Returns:
            float: 容錯率閾值（0.0 ~ 1.0，越低越嚴格）
        """
        return 0.25 if length > 5 else 0.15

"""
IPA 音標到拼寫的反向映射

這個模組負責將 IPA 音標轉換回可能的英文拼寫。
策略：基於音素→字母組合的規則映射（Rule-based approach）
"""

from typing import List, Dict, Set
import re
from .config import EnglishPhoneticConfig


class IPAToSpellingMapper:
    """
    IPA 音標到拼寫的反向映射

    使用策略：
    1. 音素→字母規則映射（主要）
    2. 頻率加權選擇最佳拼寫
    3. 處理多音素組合
    """

    def __init__(self, config=None):
        self.config = config or EnglishPhoneticConfig
        # 使用 config 中的 IPA_TO_GRAPHEME_MAP
        self._ipa_to_grapheme_map = self.config.IPA_TO_GRAPHEME_MAP
        # 構建反向索引：按音素長度排序（優先匹配長音素）
        self._sorted_phonemes = sorted(
            self._ipa_to_grapheme_map.keys(),
            key=len,
            reverse=True
        )

    def ipa_to_spellings(
        self,
        ipa: str,
        max_results: int = 10,
        include_weighted: bool = True
    ) -> List[str]:
        """
        將 IPA 轉換為可能的拼寫

        Args:
            ipa: IPA 音標（如 "ˈpaɪθɑn"）
            max_results: 最多返回幾個拼寫
            include_weighted: 是否使用頻率加權排序

        Returns:
            List[str]: 可能的拼寫列表，按可能性排序
        """
        # 移除重音符號（不影響拼寫）
        cleaned_ipa = self._remove_stress_markers(ipa)

        # 使用規則生成所有可能的拼寫
        spellings = self._apply_grapheme_rules(cleaned_ipa)

        # 如果需要頻率加權，則排序
        if include_weighted and hasattr(self.config, 'GRAPHEME_FREQUENCY_WEIGHTS'):
            spellings = self._sort_by_frequency(spellings)

        # 去重並限制數量
        unique_spellings = []
        seen = set()
        for spelling in spellings:
            if spelling.lower() not in seen:
                unique_spellings.append(spelling)
                seen.add(spelling.lower())
                if len(unique_spellings) >= max_results:
                    break

        return unique_spellings

    def _remove_stress_markers(self, ipa: str) -> str:
        """移除重音符號"""
        # 移除主重音 (ˈ) 和次重音 (ˌ)
        return ipa.replace('ˈ', '').replace('ˌ', '')

    def _apply_grapheme_rules(self, ipa: str) -> List[str]:
        """
        應用音素→字母規則生成拼寫變體

        策略：
        1. 貪婪匹配：優先匹配長音素（如 "tʃ" 優先於 "t"）
        2. 對每個音素，優先使用最常見的字母組合
        3. 生成主要拼寫 + 少量變體
        """
        # 將 IPA 分割為音素序列
        phonemes = self._segment_ipa(ipa)

        # 策略 1: 使用最常見的字母組合（每個音素取第一個選項）
        primary_spelling = []
        for phoneme in phonemes:
            if phoneme in self._ipa_to_grapheme_map:
                # 取最常見的字母組合（列表第一個）
                primary_spelling.append(self._ipa_to_grapheme_map[phoneme][0])
            else:
                # 未知音素直接使用原字符
                primary_spelling.append(phoneme)

        main_spelling = ''.join(primary_spelling)
        spellings = [main_spelling]

        # 策略 2: 為關鍵音素生成變體（只對特殊音素生成變體）
        # 選擇最多影響拼寫的幾個位置生成變體
        special_phonemes = {'θ', 'ð', 'ʃ', 'ʒ', 'tʃ', 'dʒ', 'ŋ',
                          'iː', 'eɪ', 'aɪ', 'oʊ', 'aʊ', 'ɔː', 'uː', 'ɜː'}

        for i, phoneme in enumerate(phonemes):
            if phoneme in special_phonemes and phoneme in self._ipa_to_grapheme_map:
                alternatives = self._ipa_to_grapheme_map[phoneme][1:3]  # 取第2, 3個選項
                for alt in alternatives:
                    variant_parts = primary_spelling.copy()
                    variant_parts[i] = alt
                    spellings.append(''.join(variant_parts))
                    if len(spellings) >= 30:
                        break

            if len(spellings) >= 30:
                break

        return spellings

    def _segment_ipa(self, ipa: str) -> List[str]:
        """
        將 IPA 字串分割為音素序列

        使用貪婪匹配：優先匹配長音素

        Args:
            ipa: IPA 字串（如 "paɪθɑn"）

        Returns:
            List[str]: 音素列表（如 ["p", "aɪ", "θ", "ɑ", "n"]）
        """
        phonemes = []
        i = 0

        while i < len(ipa):
            matched = False

            # 貪婪匹配：優先匹配長音素
            for phoneme in self._sorted_phonemes:
                if ipa[i:].startswith(phoneme):
                    phonemes.append(phoneme)
                    i += len(phoneme)
                    matched = True
                    break

            # 如果沒有匹配，取單個字符
            if not matched:
                phonemes.append(ipa[i])
                i += 1

        return phonemes

    def _generate_combinations(
        self,
        grapheme_options: List[List[str]],
        max_combinations: int = 50
    ) -> List[str]:
        """
        生成所有字母組合的笛卡爾積

        Args:
            grapheme_options: 每個位置的字母組合選項
            max_combinations: 最大組合數（防止組合爆炸）

        Returns:
            List[str]: 所有可能的拼寫組合
        """
        if not grapheme_options:
            return []

        # 遞迴生成組合
        def _combine(options_list):
            if not options_list:
                return [""]

            first_options = options_list[0]
            rest_combinations = _combine(options_list[1:])

            results = []
            for first in first_options:
                for rest in rest_combinations:
                    results.append(first + rest)
                    if len(results) >= max_combinations:
                        return results

            return results

        return _combine(grapheme_options)

    def _sort_by_frequency(self, spellings: List[str]) -> List[str]:
        """
        根據字母組合頻率排序拼寫

        使用 GRAPHEME_FREQUENCY_WEIGHTS 對拼寫進行評分

        Args:
            spellings: 拼寫列表

        Returns:
            List[str]: 排序後的拼寫列表（高頻優先）
        """
        weights = self.config.GRAPHEME_FREQUENCY_WEIGHTS

        def _score_spelling(spelling: str) -> float:
            """計算拼寫的頻率分數"""
            score = 0.0
            spelling_lower = spelling.lower()

            # GRAPHEME_FREQUENCY_WEIGHTS 結構: {phoneme: {grapheme: weight}}
            for phoneme, grapheme_weights in weights.items():
                for grapheme, weight in grapheme_weights.items():
                    # 計算 grapheme 在 spelling 中出現的次數
                    count = spelling_lower.count(grapheme.lower())
                    score += count * weight

            # 給予長度懲罰（避免過長的拼寫）
            length_penalty = len(spelling) * 0.01
            return score - length_penalty

        # 按分數降序排序
        scored = [(spelling, _score_spelling(spelling)) for spelling in spellings]
        scored.sort(key=lambda x: x[1], reverse=True)

        return [spelling for spelling, _ in scored]


def ipa_to_spellings(ipa: str, max_results: int = 10) -> List[str]:
    """
    便捷函數：將 IPA 轉換為拼寫

    Args:
        ipa: IPA 音標
        max_results: 最多返回幾個拼寫

    Returns:
        List[str]: 可能的拼寫列表
    """
    mapper = IPAToSpellingMapper()
    return mapper.ipa_to_spellings(ipa, max_results=max_results)

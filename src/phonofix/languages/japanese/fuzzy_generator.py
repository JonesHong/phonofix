"""
日文模糊變體生成器 (JapaneseFuzzyGenerator)

整合 config.py 規則，針對日文 ASR 常見的長音、清濁音、助詞混淆、
以及羅馬拼音系統差異 (Hepburn vs Kunrei) 進行變體生成。
"""

import itertools
from typing import List, Set, Dict

# 引用你的配置與工具
from .config import JapanesePhoneticConfig
from .utils import _get_fugashi, _get_cutlet


class JapaneseFuzzyGenerator:
    """
    日文模糊變體生成器
    """

    def __init__(self, config: JapanesePhoneticConfig = None):
        self.config = config or JapanesePhoneticConfig()

        # 預先建立羅馬拼音的反向映射 (shi -> si)，用於生成變體
        self._romaji_reverse_map = {}
        for k, v in self.config.ROMANIZATION_VARIANTS.items():
            if v not in self._romaji_reverse_map:
                self._romaji_reverse_map[v] = []
            self._romaji_reverse_map[v].append(k)

    def _kata_to_hira(self, text: str) -> str:
        """片假名轉平假名"""
        hira = []
        for ch in text:
            if "\u30a1" <= ch <= "\u30f6":
                hira.append(chr(ord(ch) - 0x60))
            else:
                hira.append(ch)
        return "".join(hira)

    def _kanji_to_hiragana_list(self, text: str) -> List[str]:
        """使用 fugashi 取得精確讀音"""
        tagger = _get_fugashi()
        words = []
        for word in tagger(text):
            try:
                reading = word.feature.kana
                if not reading:
                    reading = word.surface
            except AttributeError:
                reading = word.surface
            words.append(self._kata_to_hira(reading))
        return words

    def _get_kana_variations(self, char: str) -> List[str]:
        """
        針對單一平假名生成混淆變體 (基於發音相似性)
        所有映射規則從 config 讀取
        """
        variations = {char}

        # 1. 助詞混淆 (從 config 讀取)
        if char in self.config.PARTICLE_CONFUSIONS:
            variations.add(self.config.PARTICLE_CONFUSIONS[char])

        # 2. 清濁音混淆 (從 config 讀取)
        if char in self.config.VOICED_CONSONANT_MAP:
            variations.add(self.config.VOICED_CONSONANT_MAP[char])

        # 反向映射 (濁音 -> 清音)
        for k, v in self.config.VOICED_CONSONANT_MAP.items():
            if char == v:
                variations.add(k)

        # 3. 半濁音混淆 (從 config 讀取)
        if char in self.config.SEMI_VOICED_MAP:
            variations.add(self.config.SEMI_VOICED_MAP[char])

        # 反向映射 (半濁音 -> 清音)
        for k, v in self.config.SEMI_VOICED_MAP.items():
            if char == v:
                variations.add(k)

        # 4. 近音混淆 (從 config 讀取)
        if char in self.config.SIMILAR_SOUND_CONFUSIONS:
            variations.update(self.config.SIMILAR_SOUND_CONFUSIONS[char])

        return list(variations)

    def _apply_kana_phrase_rules(self, hira_text: str) -> Set[str]:
        """平假名層級的整詞規則"""
        variants = {hira_text}
        if "おう" in hira_text:
            variants.add(hira_text.replace("おう", "おお"))
            variants.add(hira_text.replace("おう", "おー"))
            variants.add(hira_text.replace("おう", "お"))  # 省略

        if "えい" in hira_text:
            variants.add(hira_text.replace("えい", "ええ"))
            variants.add(hira_text.replace("えい", "え"))

        if "っ" in hira_text:
            variants.add(hira_text.replace("っ", ""))

        return variants

    def _apply_romaji_config_rules(self, romaji: str) -> Set[str]:
        """應用 config.py 中的羅馬拼音規則生成變體"""
        variants = {romaji}

        for wrong, standard in self.config.ROMANIZATION_VARIANTS.items():
            if standard in romaji:
                variants.add(romaji.replace(standard, wrong))
            if wrong in romaji:
                variants.add(romaji.replace(wrong, standard))

        for long_v, short_v in self.config.FUZZY_LONG_VOWELS.items():
            if long_v in romaji:
                variants.add(romaji.replace(long_v, short_v))

        for double_c, single_c in self.config.FUZZY_GEMINATION.items():
            if double_c in romaji:
                variants.add(romaji.replace(double_c, single_c))

        for m_ver, n_ver in self.config.FUZZY_NASALS.items():
            if m_ver in romaji:
                variants.add(romaji.replace(m_ver, n_ver))
            if n_ver in romaji:
                variants.add(romaji.replace(n_ver, m_ver))

        return variants

    def _get_phonetic_key(self, term: str) -> str:
        """
        取得語音指紋 (用於判斷同音詞)

        對於日文字符：轉為平假名
        對於羅馬字：標準化處理（移除長音、促音差異）
        """
        has_japanese = any(
            "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff" for ch in term
        )

        if has_japanese:
            # 日文字符：轉為平假名
            hira_list = self._kanji_to_hiragana_list(term)
            return "".join(hira_list)
        else:
            # 羅馬字：標準化處理
            normalized = term.lower().strip().replace(" ", "")

            # 應用標準化規則 (移除長音、促音差異)
            for long_v, short_v in self.config.FUZZY_LONG_VOWELS.items():
                normalized = normalized.replace(long_v, short_v)

            for double_c, single_c in self.config.FUZZY_GEMINATION.items():
                normalized = normalized.replace(double_c, single_c)

            # 標準化羅馬拼音變體
            for wrong, standard in self.config.ROMANIZATION_VARIANTS.items():
                normalized = normalized.replace(wrong, standard)

            return normalized

    def filter_homophones(self, term_list: List[str]) -> Dict[str, List[str]]:
        """過濾同音詞 (收斂變體)"""
        kept = []
        filtered = []
        seen_keys = set()

        for term in term_list:
            key = self._get_phonetic_key(term)
            if key in seen_keys:
                filtered.append(term)
            else:
                kept.append(term)
                seen_keys.add(key)

        return {"kept": kept, "filtered": filtered}

    def generate_variants(self, term: str, max_variants: int = 30) -> List[str]:
        """生成日文詞彙的模糊變體"""
        hira_parts = self._kanji_to_hiragana_list(term)
        base_hira = "".join(hira_parts)

        char_options = [self._get_kana_variations(ch) for ch in base_hira]

        kana_combinations = []
        for i, combo in enumerate(itertools.product(*char_options)):
            if i > 50:
                break
            kana_combinations.append("".join(combo))

        final_kana_variants = set()
        for combo in kana_combinations:
            final_kana_variants.update(self._apply_kana_phrase_rules(combo))

        cutlet_katsu = _get_cutlet()
        romaji_variants = set()

        for k_var in list(final_kana_variants)[:10]:
            try:
                r_base = cutlet_katsu.romaji(k_var)
                if not r_base:
                    continue
                r_clean = r_base.replace(" ", "")
                romaji_variants.update(self._apply_romaji_config_rules(r_clean))
            except Exception:
                continue

        all_variants = final_kana_variants.union(romaji_variants)
        if term in all_variants:
            all_variants.remove(term)

        # 收斂同音變體 (只保留發音相同的第一個)
        variant_list = sorted(list(all_variants), key=lambda x: (len(x), x))
        filtered_result = self.filter_homophones(variant_list)

        # 只返回保留的變體
        return filtered_result["kept"][:max_variants]

"""
日文模糊變體生成器 (JapaneseFuzzyGenerator)

整合 config.py 規則，針對日文 ASR 常見的長音、清濁音、助詞混淆、
以及羅馬拼音系統差異 (Hepburn vs Kunrei) 進行變體生成。
"""

import itertools
from typing import List, Set, Dict

from phonofix.core.fuzzy_generator_interface import (
    BaseFuzzyGenerator,
    PhoneticVariant,
    VariantSource,
)
from .config import JapanesePhoneticConfig
from .utils import _get_fugashi, _get_cutlet
from phonofix.utils.cache import cached_method


class JapaneseFuzzyGenerator(BaseFuzzyGenerator):
    """
    日文模糊變體生成器
    """

    def __init__(self, config: JapanesePhoneticConfig = None):
        super().__init__(config)
        self.config = config or JapanesePhoneticConfig()

    # ========== 實現抽象方法 ==========

    @cached_method(maxsize=1000)
    def phonetic_transform(self, term: str) -> str:
        """文字 → Romaji (Task 7.3: 添加 LRU 緩存)"""
        # 先轉換為平假名
        hira_list = self._kanji_to_hiragana_list(term)
        base_hira = "".join(hira_list)

        # 平假名 → Romaji
        cutlet_katsu = _get_cutlet()
        try:
            romaji = cutlet_katsu.romaji(base_hira)
            return romaji.replace(" ", "")
        except:
            return base_hira

    @cached_method(maxsize=1000)
    def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
        """Romaji → 模糊 Romaji 變體 (Task 7.3: 添加 LRU 緩存)"""
        return list(self._apply_romaji_config_rules(phonetic_key))

    def phonetic_to_text(self, phonetic_key: str) -> str:
        """Romaji → 假名（直接返回 Romaji）"""
        return phonetic_key

    def apply_hardcoded_rules(self, term: str) -> List[str]:
        """應用假名層級的整詞規則"""
        # 轉為平假名
        hira_list = self._kanji_to_hiragana_list(term)
        base_hira = "".join(hira_list)

        # 應用整詞規則
        variants = self._apply_kana_phrase_rules(base_hira)
        return list(variants)

    # ========== 覆寫 generate_variants 以支援漢字變體 ==========

    def generate_variants(self, term, max_variants=30, include_hardcoded=True):
        """
        生成日文詞彙的模糊變體（Task 7.1: 支持漢字變體）

        增強流程：
        1. 語音維度生成：調用父類方法獲取假名/羅馬字變體
        2. 漢字變體生成：為含有漢字的詞彙生成漢字替換變體
        3. 去重與排序：使用語音 key 去重，按評分和長度排序

        Args:
            term: 日文詞彙（漢字/假名/羅馬字）
            max_variants: 最大變體數量（預設 30）
            include_hardcoded: 是否包含硬編碼規則（預設 True）

        Returns:
            List[PhoneticVariant]: 變體列表，包含完整語音資訊和漢字變體
        """
        variants = []

        # ========== 1. 語音維度生成 ==========
        # 調用父類方法獲取假名/羅馬字變體
        phonetic_variants = super().generate_variants(
            term,
            max_variants=max_variants * 2,  # 多生成一些，後續過濾
            include_hardcoded=include_hardcoded
        )
        variants.extend(phonetic_variants)

        # ========== 2. 漢字變體生成（Task 7.1 新增）==========
        if self._has_kanji(term):
            kanji_variants = self._generate_kanji_variants(term)
            variants.extend(kanji_variants)

        # ========== 3. 去重與排序 ==========
        # 使用語音 key 去重
        seen_phonetic_keys = set()
        unique_variants = []

        for variant in variants:
            if variant.phonetic_key not in seen_phonetic_keys:
                unique_variants.append(variant)
                seen_phonetic_keys.add(variant.phonetic_key)

        # 按評分降序、長度升序、文字字典序排序
        sorted_variants = sorted(
            unique_variants,
            key=lambda v: (-v.score, len(v.text), v.text)
        )

        return sorted_variants[:max_variants]

    # ========== 保留現有方法 ==========

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

        對於日文字符：轉為平假名 + 正規化長音/促音
        對於羅馬字：標準化處理（移除長音、促音差異）
        """
        has_japanese = any(
            "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff" for ch in term
        )

        if has_japanese:
            # 日文字符：轉為平假名
            hira_list = self._kanji_to_hiragana_list(term)
            base_hira = "".join(hira_list)

            # 正規化假名中的長音/促音變體
            normalized = base_hira

            # 1. 促音去除：っ → (empty)
            normalized = normalized.replace("っ", "")

            # 2. 片假名長音符號：ー → (empty)
            normalized = normalized.replace("ー", "")

            # 3. 長音正規化（通用規則）
            # 策略：あ段+う/お → あ段，い段/え段+い/え → い段/え段
            # 使用循環處理直到沒有變化

            prev = None
            max_iterations = 10  # 防止無限循環
            iteration = 0

            while prev != normalized and iteration < max_iterations:
                prev = normalized
                iteration += 1

                # あ段長音：あう/ああ → あ, かう/かー/かあ → か
                for char in ['あ', 'か', 'が', 'さ', 'ざ', 'た', 'だ', 'な', 'は', 'ば', 'ぱ', 'ま', 'や', 'ら', 'わ']:
                    normalized = normalized.replace(f"{char}あ", char)
                    normalized = normalized.replace(f"{char}ー", char)

                # お段長音：おう/おお/おー → お, こう/こお/こー → こ
                for char in ['お', 'こ', 'ご', 'そ', 'ぞ', 'と', 'ど', 'の', 'ほ', 'ぼ', 'ぽ', 'も', 'よ', 'ろ', 'を']:
                    normalized = normalized.replace(f"{char}う", char)
                    normalized = normalized.replace(f"{char}お", char)
                    normalized = normalized.replace(f"{char}ー", char)

                # 拗音お段長音：きょう/きょお → きょ, しょう → しょ
                for yoon in ['きゃ', 'きゅ', 'きょ', 'ぎゃ', 'ぎゅ', 'ぎょ',
                           'しゃ', 'しゅ', 'しょ', 'じゃ', 'じゅ', 'じょ',
                           'ちゃ', 'ちゅ', 'ちょ', 'にゃ', 'にゅ', 'にょ',
                           'ひゃ', 'ひゅ', 'ひょ', 'びゃ', 'びゅ', 'びょ', 'ぴゃ', 'ぴゅ', 'ぴょ',
                           'みゃ', 'みゅ', 'みょ', 'りゃ', 'りゅ', 'りょ']:
                    if yoon.endswith('ょ'):
                        normalized = normalized.replace(f"{yoon}う", yoon)
                        normalized = normalized.replace(f"{yoon}お", yoon)
                        normalized = normalized.replace(f"{yoon}ー", yoon)

                # い段長音：いい/いー → い, きい/きー → き
                for char in ['い', 'き', 'ぎ', 'し', 'じ', 'ち', 'に', 'ひ', 'び', 'ぴ', 'み', 'り']:
                    normalized = normalized.replace(f"{char}い", char)
                    normalized = normalized.replace(f"{char}ー", char)

                # え段長音：えい/ええ/えー → え, けい/けー → け
                for char in ['え', 'け', 'げ', 'せ', 'ぜ', 'て', 'で', 'ね', 'へ', 'べ', 'ぺ', 'め', 'れ']:
                    normalized = normalized.replace(f"{char}い", char)
                    normalized = normalized.replace(f"{char}え", char)
                    normalized = normalized.replace(f"{char}ー", char)

                # う段長音：うう/うー → う, くう/くー → く
                for char in ['う', 'く', 'ぐ', 'す', 'ず', 'つ', 'ぬ', 'ふ', 'ぶ', 'ぷ', 'む', 'ゆ', 'る']:
                    normalized = normalized.replace(f"{char}う", char)
                    normalized = normalized.replace(f"{char}ー", char)

            # 4. 撥音標準化：ん 保留（無需正規化）
            # 未來可擴展：m 音前的ん vs 其他ん的正規化

            return normalized
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

    # ========== Task 7.1: 漢字變體生成 ==========

    def _has_kanji(self, text: str) -> bool:
        """
        檢查文字是否包含漢字

        Args:
            text: 輸入文字

        Returns:
            bool: 是否包含漢字
        """
        return any('\u4e00' <= ch <= '\u9fff' for ch in text)

    def _generate_kanji_variants(self, term: str) -> List[PhoneticVariant]:
        """
        生成漢字變體

        策略：
        1. 保留原詞的漢字形式
        2. 查找常見同音異字

        Args:
            term: 原始詞（包含漢字）

        Returns:
            List[PhoneticVariant]: 漢字變體列表
        """
        variants = []

        # 1. 保留原詞漢字（最高評分）
        base_phonetic = self.phonetic_transform(term)
        variants.append(PhoneticVariant(
            text=term,
            phonetic_key=base_phonetic,
            score=1.0,
            source=VariantSource.PHONETIC_FUZZY,
            metadata={"type": "original_kanji"}
        ))

        # 2. 查找同音異字
        homophones = self._lookup_homophones_from_dict(term)

        for homophone in homophones:
            homophone_phonetic = self.phonetic_transform(homophone)
            # 使用父類的 calculate_score 方法計算相似度
            score = self.calculate_score(base_phonetic, homophone_phonetic)

            variants.append(PhoneticVariant(
                text=homophone,
                phonetic_key=homophone_phonetic,
                score=score * 0.9,  # 同音異字評分稍低於原詞
                source=VariantSource.PHONETIC_FUZZY,
                metadata={"type": "kanji_variant"}
            ))

        return variants

    def _lookup_homophones_from_dict(self, term: str) -> List[str]:
        """
        從預定義字典中查找同音異字

        注意：這是簡化實現，未來可整合 mecab-ipadic 完整字典

        Args:
            term: 原始詞（漢字）

        Returns:
            List[str]: 同音異字列表
        """
        # 常見同音異字表（可擴展）
        COMMON_HOMOPHONES = {
            # 地名
            "東京": ["凍京", "東經"],
            "大阪": ["大坂"],
            "京都": ["教都"],

            # 常用詞
            "会社": ["會社", "回社"],
            "社会": ["社會"],
            "学校": ["學校"],
            "先生": ["先聲"],
            "時間": ["時感", "時刊"],
            "場所": ["場處"],
            "仕事": ["私事"],
            "電話": ["電化"],
            "日本": ["二本", "日本"],
            "今日": ["教"],

            # 醫藥品（ASR 常見錯誤）
            "アスピリン": ["明日ピリン"],
            "ロキソニン": ["六腰人"],
        }

        return COMMON_HOMOPHONES.get(term, [])

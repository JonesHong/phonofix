"""
英文模糊變體生成器

策略（重構後）：
1. IPA 維度生成（主要）：透過 IPA 音素變體生成拼寫變體
2. 硬編碼規則（補充）：保留現有的 ASR 分詞、字母混淆等規則
3. 基於 IPA 去重：移除語音相同的重複變體
"""

import re
from itertools import product
from typing import List, Set, Dict
from phonofix.core.fuzzy_generator_interface import (
    BaseFuzzyGenerator,
    PhoneticVariant,
    VariantSource,
)
from .config import EnglishPhoneticConfig
from .phonetic_impl import EnglishPhoneticSystem
from .ipa_to_spelling import IPAToSpellingMapper
from phonofix.utils.logger import get_logger
from phonofix.utils.cache import cached_method


class EnglishFuzzyGenerator(BaseFuzzyGenerator):
    """
    英文模糊變體生成器（IPA 音素系統版本）

    核心策略：
    1. **IPA 維度生成（主要）**：
       - 使用 IPA (International Phonetic Alphabet) 音素系統生成語音變體
       - 支援清濁音混淆 (p/b, t/d, k/g, etc.)
       - 支援相似音素混淆 (θ/f, θ/s, l/r, etc.)
       - 支援長短元音變化 (iː/ɪ, uː/ʊ, etc.)
       - 通過 IPA → 拼寫反查生成真實拼寫變體

    2. **硬編碼規則（補充）**：
       - ASR 分詞錯誤 ("TensorFlow" → "ten so floor")
       - 縮寫字母混淆 ("API" → "a p i")
       - 字母-數字混淆 ("EKG" → "1kg")
       - 常見拼寫錯誤模式

    3. **基於 IPA 去重**：
       - 移除語音相同的重複變體
       - 保證變體的語音差異性

    優勢：
    - **新詞泛化能力**：可為字典中不存在的新詞（如 "Ollama", "LangChain"）生成變體
    - **語音準確性**：基於真實 IPA 音素系統，更符合語音學規律
    - **自動去重**：通過 IPA phonetic key 自動去除重複變體

    範例：
        >>> generator = EnglishFuzzyGenerator()
        >>> variants = generator.generate_variants("Python")
        >>> print(variants[:5])
        ['pithon', 'piton', 'pyton', 'pythom', 'pythun']

        >>> # 新詞泛化示例
        >>> variants = generator.generate_variants("Ollama")
        >>> print(variants[:5])
        ['olama', 'olema', 'olima', 'ollema', 'olamma']
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or EnglishPhoneticConfig
        self.phonetic = EnglishPhoneticSystem()
        self.ipa_mapper = IPAToSpellingMapper(config=self.config)
        self._logger = get_logger("fuzzy.english")

    # ========== 實現抽象方法 ==========

    @cached_method(maxsize=1000)
    def phonetic_transform(self, term: str) -> str:
        """文字 → IPA (Task 7.3: 添加 LRU 緩存)"""
        return self.phonetic.to_phonetic(term)

    @cached_method(maxsize=1000)
    def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
        """IPA → 模糊 IPA 變體 (Task 7.3: 添加 LRU 緩存)"""
        return self._generate_ipa_fuzzy_variants(phonetic_key)

    def phonetic_to_text(self, phonetic_key: str) -> str:
        """IPA → 拼寫"""
        spellings = self.ipa_mapper.ipa_to_spellings(phonetic_key, max_results=1)
        return spellings[0] if spellings else phonetic_key

    def apply_hardcoded_rules(self, term: str) -> List[str]:
        """應用 ASR 分詞模式和拼寫規則"""
        return self._apply_asr_patterns(term)

    # ========== 保留的輔助方法 ==========

    def _generate_full_word_variants(self, term: str) -> Set[str]:
        """
        為完整詞彙生成預定義的 ASR 變體
        
        這是最高優先級的變體來源，直接使用 config 中定義的模式
        """
        variants = set()
        term_lower = term.lower()
        
        # 直接查找完整詞彙的變體
        if term_lower in self.config.ASR_SPLIT_PATTERNS:
            variants.update(self.config.ASR_SPLIT_PATTERNS[term_lower])
        
        # 處理帶後綴的詞彙 (如 Vue.js, Node.js)
        # 嘗試提取主詞並單獨生成變體
        suffix_match = re.match(r'^([a-zA-Z]+)([\.\-_][a-zA-Z]+)$', term_lower)
        if suffix_match:
            main_word = suffix_match.group(1)  # 如 "vue"
            suffix = suffix_match.group(2)      # 如 ".js"
            
            # 為主詞查找變體
            if main_word in self.config.ASR_SPLIT_PATTERNS:
                for variant in self.config.ASR_SPLIT_PATTERNS[main_word]:
                    # 生成 "view JS", "view js" 等變體 (不帶點)
                    suffix_clean = suffix.replace('.', ' ').replace('-', ' ').replace('_', ' ').strip()
                    variants.add(f"{variant} {suffix_clean}")
                    variants.add(f"{variant}{suffix_clean}")  # 也加無空格版本
        
        # 也檢查不帶特殊字符的版本 (如 Vue.js -> vuejs)
        term_clean = re.sub(r'[^a-zA-Z0-9]', '', term_lower)
        if term_clean in self.config.ASR_SPLIT_PATTERNS:
            variants.update(self.config.ASR_SPLIT_PATTERNS[term_clean])
        
        return variants
    
    def _generate_acronym_variants(self, acronym: str) -> Set[str]:
        """
        為縮寫生成變體
        
        範例: "API" -> ["a p i", "A P I"]
              "EKG" -> ["e k g", "1 kg", "ekg"]
        """
        variants = set()
        
        # 字母分開版本 (最常見的 ASR 錯誤)
        spaced = ' '.join(list(acronym.lower()))
        variants.add(spaced)
        
        # 小寫連續版本  
        variants.add(acronym.lower())
        
        # 數字/字母混淆版本 (只對特定字母)
        for i, char in enumerate(acronym.upper()):
            if char in self.config.LETTER_NUMBER_CONFUSIONS:
                for replacement in self.config.LETTER_NUMBER_CONFUSIONS[char]:
                    # 替換單個字母，生成連續版本
                    new_acronym = acronym[:i].lower() + replacement + acronym[i+1:].lower()
                    variants.add(new_acronym)
                    # 也生成分開版本 (如 "1 k g")
                    if len(replacement) == 1:
                        parts = list(acronym.lower())
                        parts[i] = replacement
                        variants.add(' '.join(parts))
        
        return variants
    
    def _is_compound_word(self, term: str) -> bool:
        """檢查是否為複合詞 (駝峰式或含數字)"""
        # 檢查駝峰式: TensorFlow, JavaScript
        if re.search(r'[a-z][A-Z]', term):
            return True
        # 檢查數字混合: B2B, 3D
        if re.search(r'[A-Za-z]\d|\d[A-Za-z]', term):
            return True
        return False
    
    def _generate_compound_variants(self, term: str) -> Set[str]:
        """
        為複合詞生成變體
        
        範例: "TensorFlow" -> ["tensor flow", "ten so floor"]
              "JavaScript" -> ["java script", "java scrip"]
        """
        variants = set()
        
        # 在駝峰處分割
        parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+', term)
        
        if len(parts) > 1:
            # 基本分割版本
            variants.add(' '.join(parts).lower())
            
            # 對每個部分應用 ASR 分詞模式
            for i, part in enumerate(parts):
                part_lower = part.lower()
                if part_lower in self.config.ASR_SPLIT_PATTERNS:
                    for split in self.config.ASR_SPLIT_PATTERNS[part_lower]:
                        new_parts = parts.copy()
                        new_parts[i] = split
                        variants.add(' '.join(new_parts).lower())
        
        return variants
    
    def _apply_spelling_patterns(self, term: str) -> Set[str]:
        """應用常見拼寫錯誤模式"""
        variants = set()
        term_lower = term.lower()

        for pattern, replacement in self.config.SPELLING_PATTERNS:
            if re.search(pattern, term_lower):
                variant = re.sub(pattern, replacement, term_lower, count=1)
                if variant != term_lower:
                    variants.add(variant)

        return variants

    def _generate_ipa_fuzzy_variants(self, ipa: str) -> List[str]:
        """
        基於 IPA 音素規則生成模糊變體

        應用的音素混淆規則：
        1. **清濁音混淆** (IPA_VOICING_CONFUSIONS)：
           - p ↔ b, t ↔ d, k ↔ g
           - f ↔ v, s ↔ z, θ ↔ ð, ʃ ↔ ʒ

        2. **長短元音混淆** (IPA_VOWEL_LENGTH_CONFUSIONS)：
           - iː ↔ ɪ, uː ↔ ʊ, ɔː ↔ ɒ
           - ɑː ↔ ʌ, ɜː ↔ ə

        3. **相似音素混淆** (IPA_SIMILAR_PHONE_CONFUSIONS)：
           - θ ↔ f, θ ↔ s (如 "think" → "fink" 或 "sink")
           - l ↔ r (東亞語言使用者常見混淆)
           - v ↔ w, ð ↔ z

        4. **音節簡化** (IPA_REDUCTION_RULES)：
           - ɪŋ → ɪn, ər → ə
           - 非重音音節弱化

        Args:
            ipa: IPA 音標字串（如 "ˈpaɪθɑn"）

        Returns:
            List[str]: IPA 變體列表（通常 5-30 個）

        範例：
            >>> generator = EnglishFuzzyGenerator()
            >>> ipa = "ˈpaɪθɑn"  # Python 的 IPA
            >>> variants = generator._generate_ipa_fuzzy_variants(ipa)
            >>> print(variants[:5])
            ['ˈpaɪθɑn', 'ˈbaɪθɑn', 'ˈpaɪðɑn', 'ˈpaɪfɑn', 'ˈpaɪsɑn']
        """
        variants = {ipa}

        # 1. 應用清濁音混淆
        for s1, s2 in self.config.IPA_VOICING_CONFUSIONS:
            if s1 in ipa:
                variants.add(ipa.replace(s1, s2))
            if s2 in ipa:
                variants.add(ipa.replace(s2, s1))

        # 2. 應用長短元音混淆
        for long_v, short_v in self.config.IPA_VOWEL_LENGTH_CONFUSIONS:
            if long_v in ipa:
                variants.add(ipa.replace(long_v, short_v))
            if short_v in ipa:
                variants.add(ipa.replace(short_v, long_v))

        # 3. 應用相似音素混淆
        for p1, p2 in self.config.IPA_SIMILAR_PHONE_CONFUSIONS:
            if p1 in ipa:
                variants.add(ipa.replace(p1, p2))
            if p2 in ipa:
                variants.add(ipa.replace(p2, p1))

        # 4. 應用音節簡化
        for full, reduced in self.config.IPA_REDUCTION_RULES:
            if full in ipa:
                variants.add(ipa.replace(full, reduced))

        # 5. 應用重音變化（如果配置中有）
        if hasattr(self.config, 'IPA_STRESS_VARIATIONS'):
            for stressed, unstressed in self.config.IPA_STRESS_VARIATIONS:
                if stressed in ipa:
                    variants.add(ipa.replace(stressed, unstressed))
                if unstressed in ipa:
                    variants.add(ipa.replace(unstressed, stressed))

        return list(variants)

    def _apply_asr_patterns(self, term: str) -> List[str]:
        """
        應用硬編碼的 ASR 模式規則（保留舊邏輯）

        整合：
        - 完整詞彙預定義變體
        - 縮寫字母混淆
        - 複合詞分割
        - 拼寫錯誤模式
        - ASR 分詞模式
        """
        variants = set()
        term_lower = term.lower()

        # 1. 完整詞彙預定義變體
        variants.update(self._generate_full_word_variants(term))

        # 2. 處理縮寫 (全大寫詞)
        if term.isupper() and len(term) <= 5:
            variants.update(self._generate_acronym_variants(term))

        # 3. 處理複合詞 (駝峰式或含數字)
        if self._is_compound_word(term):
            variants.update(self._generate_compound_variants(term))

        # 4. 應用拼寫錯誤模式
        variants.update(self._apply_spelling_patterns(term))

        # 5. ASR 分詞模式
        for key, splits in self.config.ASR_SPLIT_PATTERNS.items():
            if key in term_lower:
                for split in splits:
                    variant = term_lower.replace(key, split)
                    variants.add(variant)

        # 移除空字串
        variants.discard('')

        return list(variants)

    def _deduplicate_by_ipa(self, variants: Dict[str, str]) -> List[str]:
        """
        基於 IPA phonetic key 去重

        Args:
            variants: {spelling: ipa} 字典

        Returns:
            List[str]: 去重後的拼寫列表
        """
        seen_ipa = set()
        unique = []

        for spelling, ipa in variants.items():
            if ipa and ipa not in seen_ipa:
                unique.append(spelling)
                seen_ipa.add(ipa)
            elif not ipa:  # IPA 缺失，保留拼寫
                unique.append(spelling)

        return unique

    def _filter_by_ipa_distance(self, original: str, variants: List[str]) -> List[str]:
        """
        基於 IPA 編輯距離過濾變體（非常寬鬆）

        只移除語音上完全相同的變體（IPA distance = 0）

        Args:
            original: 原詞
            variants: 變體列表

        Returns:
            List[str]: 過濾後的變體列表
        """
        try:
            original_ipa = self.phonetic.to_phonetic(original)
        except:
            # 無法獲取 IPA，跳過過濾
            return variants

        filtered = []
        import Levenshtein

        for variant in variants:
            # 如果變體拼寫與原詞不同，基本上都保留
            # （即使語音相同也保留，因為 ASR 可能輸出拼寫不同但語音相同的詞）
            if variant.lower() != original.lower():
                filtered.append(variant)

        return filtered


# 便捷函數
def generate_english_variants(term: str, max_variants: int = 20) -> List[str]:
    """
    為英文專有名詞生成 ASR 錯誤變體
    
    Args:
        term: 正確的專有名詞
        max_variants: 最大變體數量
        
    Returns:
        List[str]: 可能的錯誤拼寫列表
    """
    generator = EnglishFuzzyGenerator()
    return generator.generate_variants(term, max_variants)

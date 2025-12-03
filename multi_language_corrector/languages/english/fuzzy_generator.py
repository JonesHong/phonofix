"""
英文模糊變體生成器

從專有名詞的 IPA 音標反推可能的 ASR 錯誤拼寫變體。
"""

import eng_to_ipa as ipa
import re
from itertools import product
from typing import List, Set
from .config import EnglishPhoneticConfig


class EnglishFuzzyGenerator:
    """
    英文模糊變體生成器
    
    策略:
    1. 常見 ASR 分詞錯誤 (TensorFlow -> Ten so floor)
    2. 字母發音錯誤 (API -> a p i)
    3. 數字/字母混淆 (EKG -> 1 kg, B2B -> b to b)
    4. 常見拼寫錯誤模式 (Python -> Pyton)
    5. 完整詞彙直接匹配 (kubernetes -> cooper net ease)
    """
    
    def __init__(self, config=None):
        self.config = config or EnglishPhoneticConfig
    
    def generate_variants(self, term: str, max_variants: int = 30) -> List[str]:
        """
        為專有名詞生成可能的 ASR 錯誤變體
        
        Args:
            term: 正確的專有名詞 (如 "Python", "TensorFlow")
            max_variants: 最大變體數量
            
        Returns:
            List[str]: 可能的錯誤拼寫列表
        """
        variants: Set[str] = set()
        term_lower = term.lower()
        
        # 0. 先檢查完整詞彙是否有預定義的 ASR 變體
        variants.update(self._generate_full_word_variants(term))
        
        # 1. 處理縮寫 (全大寫詞)
        if term.isupper() and len(term) <= 5:
            variants.update(self._generate_acronym_variants(term))
        
        # 2. 處理複合詞 (駝峰式或含數字)
        if self._is_compound_word(term):
            variants.update(self._generate_compound_variants(term))
        
        # 3. 應用拼寫錯誤模式
        variants.update(self._apply_spelling_patterns(term))
        
        # 4. 檢查已知的 ASR 分詞模式 (針對詞的部分)
        for key, splits in self.config.ASR_SPLIT_PATTERNS.items():
            if key in term_lower:
                for split in splits:
                    variant = term_lower.replace(key, split)
                    variants.add(variant)
        
        # 5. 移除原詞本身和空變體
        variants.discard(term)
        variants.discard(term.lower())
        variants.discard('')
        
        # 過濾掉太相似的變體 (只保留有意義的差異)
        filtered = self._filter_similar_variants(term, list(variants))
        
        return filtered[:max_variants]
    
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
    
    def _filter_similar_variants(self, original: str, variants: List[str]) -> List[str]:
        """過濾掉與原詞完全相同的變體，但保留有空格差異的"""
        import Levenshtein
        
        filtered = []
        original_lower = original.lower()
        
        for variant in variants:
            # 跳過完全相同的 (包括大小寫)
            if variant.lower() == original_lower:
                continue
            
            # 保留有空格差異的變體 (如 "a p i" vs "api")
            # 這是 ASR 常見的分詞錯誤
            if ' ' in variant and variant.replace(' ', '').lower() == original_lower:
                filtered.append(variant)
                continue
            
            # 保留有足夠字符差異的
            variant_clean = variant.lower().replace(' ', '')
            original_clean = original_lower.replace(' ', '')
            dist = Levenshtein.distance(original_clean, variant_clean)
            if dist >= 1:
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

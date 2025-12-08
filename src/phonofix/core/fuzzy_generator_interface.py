"""
模糊變體生成器抽象基類

定義統一的變體生成流程和接口，強制三語言架構一致。

核心設計：
1. 統一數據結構 (PhoneticVariant)
2. 抽象方法接口 (phonetic_transform, generate_phonetic_variants, phonetic_to_text)
3. 模板方法模式 (generate_variants)
4. 可選覆蓋方法 (apply_hardcoded_rules, calculate_score)

使用範例：
    >>> class MyFuzzyGenerator(BaseFuzzyGenerator):
    ...     def phonetic_transform(self, term: str) -> str:
    ...         return term.lower()  # 簡化示例
    ...
    ...     def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
    ...         return [phonetic_key, phonetic_key + "s"]
    ...
    ...     def phonetic_to_text(self, phonetic_key: str) -> str:
    ...         return phonetic_key
    >>>
    >>> generator = MyFuzzyGenerator()
    >>> variants = generator.generate_variants("test")
    >>> print([v.text for v in variants])
    ['tests']
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class VariantSource(Enum):
    """變體來源類型"""
    PHONETIC_FUZZY = "phonetic_fuzzy"    # 語音模糊規則
    HARDCODED_PATTERN = "hardcoded"      # 硬編碼模式
    PHRASE_RULE = "phrase_rule"          # 整詞規則
    ROMANIZATION = "romanization"        # 羅馬化變體


@dataclass
class PhoneticVariant:
    """
    語音變體結構（統一格式）

    Attributes:
        text: 顯示文字（使用者看到的）
        phonetic_key: 語音 key（Pinyin/IPA/Romaji，用於去重）
        score: 置信度評分 (0.0-1.0)，越高表示越可能是正確變體
        source: 變體來源類型
        metadata: 額外元數據（如音素規則類型、編輯距離等）

    範例：
        >>> variant = PhoneticVariant(
        ...     text="pithon",
        ...     phonetic_key="ˈpɪθɑn",
        ...     score=0.85,
        ...     source=VariantSource.PHONETIC_FUZZY,
        ...     metadata={"rule": "vowel_length"}
        ... )
        >>> print(f"{variant.text} ({variant.score:.2f})")
        pithon (0.85)
    """
    text: str
    phonetic_key: str
    score: float = 1.0
    source: VariantSource = VariantSource.PHONETIC_FUZZY
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """驗證數據有效性"""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {self.score}")
        if not self.text:
            raise ValueError("Text cannot be empty")
        if not self.phonetic_key:
            raise ValueError("Phonetic key cannot be empty")


class BaseFuzzyGenerator(ABC):
    """
    模糊變體生成器抽象基類

    統一流程（模板方法模式）：
    1. 文字 → 語音 key (phonetic_transform)
    2. 語音 key → 模糊語音 key 變體 (generate_phonetic_variants)
    3. 模糊語音 key → 文字 (phonetic_to_text)
    4. 基於語音 key 去重 (deduplicate_by_phonetic)
    5. 評分與排序 (score_and_rank)

    子類實現範例：
        - ChineseFuzzyGenerator: Pinyin 系統
        - EnglishFuzzyGenerator: IPA 系統
        - JapaneseFuzzyGenerator: Romaji 系統

    使用範例：
        >>> generator = EnglishFuzzyGenerator()
        >>> variants = generator.generate_variants("Python", max_variants=10)
        >>> for v in variants[:3]:
        ...     print(f"{v.text} (score: {v.score:.2f}, phonetic: {v.phonetic_key})")
        pithon (score: 0.92, phonetic: ˈpɪθɑn)
        bython (score: 0.88, phonetic: ˈbaɪθɑn)
        pythom (score: 0.85, phonetic: ˈpaɪθɑm)
    """

    def __init__(self, config: Optional[Any] = None):
        """
        初始化生成器

        Args:
            config: 語言特定配置對象（如 EnglishPhoneticConfig）
        """
        self.config = config

    # ========== 抽象方法（子類必須實現）==========

    @abstractmethod
    def phonetic_transform(self, term: str) -> str:
        """
        文字 → 語音 key

        將輸入文字轉換為語音表示（Pinyin/IPA/Romaji）

        Args:
            term: 輸入文字（如 "台北", "Python", "東京"）

        Returns:
            str: 語音 key（如 "taibei", "ˈpaɪθɑn", "toukyou"）

        Raises:
            RuntimeError: 如果語音轉換失敗（如缺少依賴）

        範例：
            >>> generator = EnglishFuzzyGenerator()
            >>> ipa = generator.phonetic_transform("Python")
            >>> print(ipa)
            ˈpaɪθɑn
        """
        pass

    @abstractmethod
    def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
        """
        語音 key → 模糊語音 key 變體

        應用語音混淆規則生成變體（如清濁音混淆、相似音混淆）

        Args:
            phonetic_key: 標準語音 key

        Returns:
            List[str]: 模糊語音 key 列表（包含原始 key）

        範例：
            >>> generator = EnglishFuzzyGenerator()
            >>> variants = generator.generate_phonetic_variants("ˈpaɪθɑn")
            >>> print(variants[:5])
            ['ˈpaɪθɑn', 'ˈbaɪθɑn', 'ˈpaɪðɑn', 'ˈpaɪfɑn', 'ˈpaɪsɑn']
        """
        pass

    @abstractmethod
    def phonetic_to_text(self, phonetic_key: str) -> str:
        """
        語音 key → 代表文字（用於 UX 展示）

        將語音 key 轉換回文字表示。對於 IPA 系統，這是反向查找；
        對於 Pinyin 系統，這可能是直接使用 Pinyin。

        Args:
            phonetic_key: 語音 key

        Returns:
            str: 代表性文字

        範例：
            >>> generator = EnglishFuzzyGenerator()
            >>> text = generator.phonetic_to_text("ˈpɪθɑn")
            >>> print(text)
            pithon
        """
        pass

    # ========== 可選方法（子類可覆蓋）==========

    def apply_hardcoded_rules(self, term: str) -> List[str]:
        """
        應用硬編碼規則（補充）

        用於處理特殊情況（如縮寫、複合詞、常見錯誤模式）

        Args:
            term: 輸入文字

        Returns:
            List[str]: 硬編碼規則生成的變體

        範例：
            >>> generator = EnglishFuzzyGenerator()
            >>> variants = generator.apply_hardcoded_rules("TensorFlow")
            >>> print(variants)
            ['tensor flow', 'ten so floor']
        """
        return []

    def calculate_score(self, base_key: str, variant_key: str) -> float:
        """
        計算變體置信度評分

        基於編輯距離計算兩個語音 key 的相似度評分

        Args:
            base_key: 原始語音 key
            variant_key: 變體語音 key

        Returns:
            float: 評分 (0.0-1.0)，1.0 表示完全相同，0.0 表示完全不同

        範例：
            >>> generator = EnglishFuzzyGenerator()
            >>> score = generator.calculate_score("ˈpaɪθɑn", "ˈbaɪθɑn")
            >>> print(f"{score:.2f}")
            0.86
        """
        try:
            import Levenshtein
        except ImportError:
            # 如果沒有 Levenshtein，使用簡單的相似度計算
            if base_key == variant_key:
                return 1.0
            # 簡單的前綴相似度
            common_len = sum(1 for a, b in zip(base_key, variant_key) if a == b)
            max_len = max(len(base_key), len(variant_key))
            return common_len / max_len if max_len > 0 else 0.0

        # 基於編輯距離計算評分
        dist = Levenshtein.distance(base_key, variant_key)
        max_len = max(len(base_key), len(variant_key))

        if max_len == 0:
            return 1.0

        similarity = 1.0 - (dist / max_len)
        return max(0.0, min(1.0, similarity))

    # ========== 模板方法（統一流程）==========

    def generate_variants(
        self,
        term: str,
        max_variants: int = 30,
        include_hardcoded: bool = True
    ) -> List[PhoneticVariant]:
        """
        統一的變體生成流程（模板方法）

        這是主要的公開接口，協調所有步驟並返回最終變體列表。

        工作流程：
        1. 語音維度生成（Term → IPA → Fuzzy IPA → Spellings）
        2. 硬編碼規則生成（補充）
        3. 基於語音 key 去重
        4. 過濾原詞
        5. 評分與排序

        Args:
            term: 輸入詞彙
            max_variants: 最大變體數量（預設 30）
            include_hardcoded: 是否包含硬編碼規則（預設 True）

        Returns:
            List[PhoneticVariant]: 變體列表（已排序，按評分降序）

        範例：
            >>> generator = EnglishFuzzyGenerator()
            >>> variants = generator.generate_variants("Python", max_variants=5)
            >>> for v in variants:
            ...     print(f"{v.text} ({v.score:.2f})")
            pithon (0.92)
            bython (0.88)
            pythom (0.85)
            piton (0.82)
            pyton (0.80)
        """
        variants = []

        # ========== Step 1: 語音維度生成 ==========
        try:
            # 1.1 文字 → 語音 key
            base_phonetic = self.phonetic_transform(term)

            # 1.2 語音 key → 模糊語音 key 變體
            phonetic_variants = self.generate_phonetic_variants(base_phonetic)

            # 1.3 模糊語音 key → 文字
            for p_var in phonetic_variants:
                text = self.phonetic_to_text(p_var)
                score = self.calculate_score(base_phonetic, p_var)

                variants.append(PhoneticVariant(
                    text=text,
                    phonetic_key=p_var,
                    score=score,
                    source=VariantSource.PHONETIC_FUZZY,
                    metadata={"base_phonetic": base_phonetic}
                ))

        except Exception as e:
            # 語音生成失敗，記錄錯誤但繼續
            import logging
            logging.warning(f"Phonetic generation failed for '{term}': {e}")

        # ========== Step 2: 硬編碼規則（補充）==========
        if include_hardcoded:
            hardcoded_texts = self.apply_hardcoded_rules(term)

            for text in hardcoded_texts:
                try:
                    p_key = self.phonetic_transform(text)
                    variants.append(PhoneticVariant(
                        text=text,
                        phonetic_key=p_key,
                        score=0.8,  # 硬編碼規則評分稍低
                        source=VariantSource.HARDCODED_PATTERN
                    ))
                except:
                    # 無法獲取語音 key，使用文字本身
                    variants.append(PhoneticVariant(
                        text=text,
                        phonetic_key=text.lower(),
                        score=0.7,
                        source=VariantSource.HARDCODED_PATTERN
                    ))

        # ========== Step 3: 基於語音 key 去重 ==========
        unique_variants = self._deduplicate_by_phonetic(variants)

        # ========== Step 4: 過濾原詞 ==========
        filtered = [
            v for v in unique_variants
            if v.text.lower() != term.lower()
        ]

        # ========== Step 5: 評分與排序 ==========
        sorted_variants = sorted(
            filtered,
            key=lambda v: (-v.score, len(v.text), v.text)
        )

        return sorted_variants[:max_variants]

    def _deduplicate_by_phonetic(
        self,
        variants: List[PhoneticVariant]
    ) -> List[PhoneticVariant]:
        """
        基於語音 key 去重（保留評分最高的）

        Args:
            variants: 變體列表

        Returns:
            List[PhoneticVariant]: 去重後的變體列表
        """
        seen_keys = {}

        for variant in variants:
            key = variant.phonetic_key

            if key not in seen_keys:
                seen_keys[key] = variant
            else:
                # 保留評分較高的
                if variant.score > seen_keys[key].score:
                    seen_keys[key] = variant

        return list(seen_keys.values())


# ========== 便捷函數 ==========

def convert_to_simple_list(variants: List[PhoneticVariant]) -> List[str]:
    """
    將 PhoneticVariant 列表轉換為簡單的字串列表

    用於向後兼容舊 API，或簡化輸出。

    Args:
        variants: PhoneticVariant 列表

    Returns:
        List[str]: 文字列表

    範例：
        >>> variants = [
        ...     PhoneticVariant("pithon", "ˈpɪθɑn", 0.92),
        ...     PhoneticVariant("bython", "ˈbaɪθɑn", 0.88)
        ... ]
        >>> simple = convert_to_simple_list(variants)
        >>> print(simple)
        ['pithon', 'bython']
    """
    return [v.text for v in variants]

"""
測試 BaseFuzzyGenerator 抽象基類

驗證：
1. PhoneticVariant 數據結構
2. VariantSource 枚舉
3. BaseFuzzyGenerator 模板方法流程
4. 抽象方法強制實現
5. 去重機制
6. 評分計算
"""

import pytest
from typing import List
from phonofix.core.fuzzy_generator_interface import (
    BaseFuzzyGenerator,
    PhoneticVariant,
    VariantSource,
    convert_to_simple_list,
)


class TestPhoneticVariant:
    """測試 PhoneticVariant 數據結構"""

    def test_basic_creation(self):
        """測試基本創建"""
        variant = PhoneticVariant(
            text="pithon",
            phonetic_key="ˈpɪθɑn",
            score=0.85
        )

        assert variant.text == "pithon"
        assert variant.phonetic_key == "ˈpɪθɑn"
        assert variant.score == 0.85
        assert variant.source == VariantSource.PHONETIC_FUZZY
        assert variant.metadata == {}

    def test_with_metadata(self):
        """測試包含元數據"""
        variant = PhoneticVariant(
            text="bython",
            phonetic_key="ˈbaɪθɑn",
            score=0.88,
            source=VariantSource.HARDCODED_PATTERN,
            metadata={"rule": "voicing"}
        )

        assert variant.metadata["rule"] == "voicing"
        assert variant.source == VariantSource.HARDCODED_PATTERN

    def test_score_validation(self):
        """測試評分驗證"""
        # 正常評分
        variant = PhoneticVariant("test", "tɛst", 0.5)
        assert variant.score == 0.5

        # 無效評分
        with pytest.raises(ValueError, match="Score must be between 0.0 and 1.0"):
            PhoneticVariant("test", "tɛst", 1.5)

        with pytest.raises(ValueError, match="Score must be between 0.0 and 1.0"):
            PhoneticVariant("test", "tɛst", -0.1)

    def test_empty_validation(self):
        """測試空值驗證"""
        # 空文字
        with pytest.raises(ValueError, match="Text cannot be empty"):
            PhoneticVariant("", "tɛst", 0.5)

        # 空語音 key
        with pytest.raises(ValueError, match="Phonetic key cannot be empty"):
            PhoneticVariant("test", "", 0.5)


class TestVariantSource:
    """測試 VariantSource 枚舉"""

    def test_enum_values(self):
        """測試枚舉值"""
        assert VariantSource.PHONETIC_FUZZY.value == "phonetic_fuzzy"
        assert VariantSource.HARDCODED_PATTERN.value == "hardcoded"
        assert VariantSource.PHRASE_RULE.value == "phrase_rule"
        assert VariantSource.ROMANIZATION.value == "romanization"


class SimpleFuzzyGenerator(BaseFuzzyGenerator):
    """簡單的測試用生成器"""

    def phonetic_transform(self, term: str) -> str:
        """簡化：直接返回小寫"""
        return term.lower()

    def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
        """簡化：生成幾個簡單變體"""
        return [
            phonetic_key,
            phonetic_key + "s",
            phonetic_key[:-1] if len(phonetic_key) > 1 else phonetic_key,
        ]

    def phonetic_to_text(self, phonetic_key: str) -> str:
        """簡化：直接返回 key"""
        return phonetic_key


class TestBaseFuzzyGenerator:
    """測試 BaseFuzzyGenerator 抽象基類"""

    def setup_method(self):
        self.generator = SimpleFuzzyGenerator()

    def test_abstract_methods_required(self):
        """測試抽象方法必須實現"""
        # 嘗試創建沒有實現抽象方法的子類
        with pytest.raises(TypeError):
            class IncompleteGenerator(BaseFuzzyGenerator):
                pass

            IncompleteGenerator()

    def test_template_method_workflow(self):
        """測試模板方法工作流"""
        variants = self.generator.generate_variants("test", max_variants=5)

        # 應該生成變體
        assert len(variants) > 0

        # 所有變體都是 PhoneticVariant
        assert all(isinstance(v, PhoneticVariant) for v in variants)

        # 變體不包含原詞
        assert "test" not in [v.text for v in variants]

        # 按評分排序
        scores = [v.score for v in variants]
        assert scores == sorted(scores, reverse=True)

    def test_phonetic_deduplication(self):
        """測試基於語音 key 去重"""
        # 創建重複的語音 key
        variants = [
            PhoneticVariant("test1", "tɛst", 0.9),
            PhoneticVariant("test2", "tɛst", 0.8),  # 相同 key，評分較低
            PhoneticVariant("test3", "tɛst", 0.95),  # 相同 key，評分最高
            PhoneticVariant("other", "ʌðər", 0.85),
        ]

        deduped = self.generator._deduplicate_by_phonetic(variants)

        # 應該只保留一個 "tɛst" (評分最高的)
        tɛst_variants = [v for v in deduped if v.phonetic_key == "tɛst"]
        assert len(tɛst_variants) == 1
        assert tɛst_variants[0].text == "test3"
        assert tɛst_variants[0].score == 0.95

    def test_calculate_score(self):
        """測試評分計算"""
        # 完全相同
        score = self.generator.calculate_score("test", "test")
        assert score == 1.0

        # 完全不同
        score = self.generator.calculate_score("test", "xyz")
        assert score < 0.5

        # 部分相似
        score = self.generator.calculate_score("test", "tests")
        assert 0.7 < score < 1.0

    def test_max_variants_limit(self):
        """測試最大變體數量限制"""
        variants = self.generator.generate_variants("test", max_variants=2)
        assert len(variants) <= 2

    def test_include_hardcoded_flag(self):
        """測試 include_hardcoded 參數"""
        # 使用硬編碼規則
        variants_with = self.generator.generate_variants(
            "test", include_hardcoded=True
        )

        # 不使用硬編碼規則
        variants_without = self.generator.generate_variants(
            "test", include_hardcoded=False
        )

        # 兩者應該都能生成變體（因為有語音規則）
        assert len(variants_with) > 0
        assert len(variants_without) > 0

    def test_hardcoded_rules(self):
        """測試硬編碼規則"""
        # 基類默認返回空列表
        hardcoded = self.generator.apply_hardcoded_rules("test")
        assert hardcoded == []


class HardcodedGenerator(SimpleFuzzyGenerator):
    """帶硬編碼規則的測試生成器"""

    def apply_hardcoded_rules(self, term: str) -> List[str]:
        """返回一些硬編碼變體"""
        if term.lower() == "api":
            return ["a p i", "A P I"]
        return []


class TestHardcodedRules:
    """測試硬編碼規則整合"""

    def setup_method(self):
        self.generator = HardcodedGenerator()

    def test_hardcoded_variants_included(self):
        """測試硬編碼變體被包含"""
        variants = self.generator.generate_variants("API", max_variants=10)

        # 應該包含硬編碼變體
        texts = [v.text for v in variants]
        assert "a p i" in texts or "A P I" in texts

    def test_hardcoded_source_type(self):
        """測試硬編碼變體的來源類型"""
        variants = self.generator.generate_variants("API", max_variants=10)

        # 找到硬編碼變體
        hardcoded_variants = [
            v for v in variants if v.source == VariantSource.HARDCODED_PATTERN
        ]

        assert len(hardcoded_variants) > 0


class TestConvertToSimpleList:
    """測試便捷函數"""

    def test_convert_to_simple_list(self):
        """測試轉換為簡單列表"""
        variants = [
            PhoneticVariant("pithon", "ˈpɪθɑn", 0.92),
            PhoneticVariant("bython", "ˈbaɪθɑn", 0.88),
            PhoneticVariant("pythom", "ˈpaɪθɑm", 0.85),
        ]

        simple = convert_to_simple_list(variants)

        assert simple == ["pithon", "bython", "pythom"]
        assert all(isinstance(s, str) for s in simple)


class TestEdgeCases:
    """測試邊界情況"""

    def setup_method(self):
        self.generator = SimpleFuzzyGenerator()

    def test_empty_string(self):
        """測試空字串"""
        variants = self.generator.generate_variants("")

        # 應該返回空列表或處理錯誤
        assert isinstance(variants, list)

    def test_single_character(self):
        """測試單字符"""
        variants = self.generator.generate_variants("a")

        # 應該能處理
        assert isinstance(variants, list)

    def test_very_long_term(self):
        """測試超長詞"""
        long_term = "a" * 100
        variants = self.generator.generate_variants(long_term, max_variants=5)

        # 應該能處理並限制數量
        assert len(variants) <= 5


class TestScoreCalculationWithoutLevenshtein:
    """測試無 Levenshtein 時的評分計算"""

    def test_fallback_scoring(self):
        """測試降級評分機制"""
        generator = SimpleFuzzyGenerator()

        # 完全相同
        score = generator.calculate_score("test", "test")
        assert score == 1.0

        # 前綴相似
        score = generator.calculate_score("test", "testing")
        assert 0 < score < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

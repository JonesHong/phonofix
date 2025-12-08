"""
測試統一架構 (Unified Architecture)

驗證：
1. 三語言模組的統一接口
2. 返回類型一致性
3. 語音去重機制
4. 評分範圍一致性
5. 向後兼容性
"""

import pytest
from phonofix.core.fuzzy_generator_interface import (
    BaseFuzzyGenerator,
    PhoneticVariant,
    VariantSource,
)
from phonofix.languages.chinese.fuzzy_generator import ChineseFuzzyGenerator
from phonofix.languages.english.fuzzy_generator import EnglishFuzzyGenerator
from phonofix.languages.japanese.fuzzy_generator import JapaneseFuzzyGenerator


class TestUnifiedInterface:
    """測試統一接口"""

    def test_all_generators_inherit_base(self):
        """所有生成器應繼承 BaseFuzzyGenerator"""
        generators = [
            ChineseFuzzyGenerator,
            EnglishFuzzyGenerator,
            JapaneseFuzzyGenerator
        ]

        for gen_class in generators:
            assert issubclass(gen_class, BaseFuzzyGenerator)

    def test_all_generators_have_same_interface(self):
        """所有生成器應有相同的接口"""
        generators = [
            ChineseFuzzyGenerator(),
            EnglishFuzzyGenerator(),
            JapaneseFuzzyGenerator()
        ]

        required_methods = [
            'generate_variants',
            'phonetic_transform',
            'generate_phonetic_variants',
            'phonetic_to_text'
        ]

        for gen in generators:
            for method in required_methods:
                assert hasattr(gen, method), f"{gen.__class__.__name__} 缺少方法 {method}"

    def test_optional_methods_present(self):
        """測試可選方法是否存在"""
        generators = [
            ChineseFuzzyGenerator(),
            EnglishFuzzyGenerator(),
            JapaneseFuzzyGenerator()
        ]

        for gen in generators:
            # apply_hardcoded_rules 是可選方法
            assert hasattr(gen, 'apply_hardcoded_rules')


class TestReturnTypeConsistency:
    """測試返回類型一致性"""

    def test_backward_compatible_mode_returns_list_of_strings(self):
        """向後兼容模式應返回 List[str]"""
        test_cases = [
            (ChineseFuzzyGenerator(), "台北"),
            # 註：英文和日文測試需要外部依賴，在 CI 環境中可能失敗
            # (EnglishFuzzyGenerator(), "Python"),
            # (JapaneseFuzzyGenerator(), "東京")
        ]

        for gen, term in test_cases:
            variants = gen.generate_variants(term, max_variants=5)

            # 應返回列表
            assert isinstance(variants, list)

            # 列表中應該是字串
            for variant in variants:
                assert isinstance(variant, str)

    def test_phonetic_variant_mode_returns_list_of_variants(self):
        """PhoneticVariant 模式應返回 List[PhoneticVariant]"""
        test_cases = [
            (ChineseFuzzyGenerator(), "台北"),
            # 註：英文和日文測試需要外部依賴
        ]

        for gen, term in test_cases:
            variants = gen.generate_variants(
                term,
                max_variants=5,
                return_phonetic_variants=True
            )

            # 應返回列表
            assert isinstance(variants, list)

            # 列表中應該是 PhoneticVariant
            for variant in variants:
                assert isinstance(variant, PhoneticVariant)
                assert hasattr(variant, 'text')
                assert hasattr(variant, 'phonetic_key')
                assert hasattr(variant, 'score')
                assert hasattr(variant, 'source')


class TestPhoneticDeduplication:
    """測試語音去重機制"""

    def test_chinese_phonetic_deduplication(self):
        """測試中文同音詞去重"""
        gen = ChineseFuzzyGenerator()

        # 同音詞：台北、苔背（都是 taibei）
        homophones = ["台北", "苔背"]
        result = gen.filter_homophones(homophones)

        # 應該只保留一個
        assert len(result["kept"]) == 1
        assert len(result["filtered"]) == 1

    # 註：日文測試需要 cutlet 和 fugashi 依賴，在 CI 環境中跳過
    # def test_japanese_phonetic_deduplication(self):
    #     """測試日文同音詞去重"""
    #     gen = JapaneseFuzzyGenerator()
    #     homophones = ["とうきょう", "東京"]
    #     result = gen.filter_homophones(homophones)
    #     assert "kept" in result
    #     assert "filtered" in result


class TestScoringConsistency:
    """測試評分一致性"""

    def test_scores_in_valid_range(self):
        """評分應在 0.0-1.0 範圍內"""
        test_cases = [
            (ChineseFuzzyGenerator(), "測試"),
            # 註：英文和日文測試需要外部依賴
        ]

        for gen, term in test_cases:
            variants = gen.generate_variants(
                term,
                max_variants=10,
                return_phonetic_variants=True
            )

            for variant in variants:
                assert 0.0 <= variant.score <= 1.0, \
                    f"評分超出範圍: {variant.score}"

    def test_scores_sorted_descending(self):
        """評分應按降序排列"""
        test_cases = [
            (ChineseFuzzyGenerator(), "測試"),
            # 註：英文和日文測試需要外部依賴
        ]

        for gen, term in test_cases:
            variants = gen.generate_variants(
                term,
                max_variants=10,
                return_phonetic_variants=True
            )

            if len(variants) > 1:
                scores = [v.score for v in variants]
                assert scores == sorted(scores, reverse=True), \
                    f"評分未按降序排列: {scores}"


class TestVariantSourceTypes:
    """測試變體來源類型"""

    def test_source_types_are_valid_enums(self):
        """變體來源應該是有效的枚舉值"""
        test_cases = [
            (ChineseFuzzyGenerator(), "測試"),
            # 註：英文和日文測試需要外部依賴
        ]

        for gen, term in test_cases:
            variants = gen.generate_variants(
                term,
                max_variants=10,
                return_phonetic_variants=True
            )

            for variant in variants:
                assert isinstance(variant.source, VariantSource), \
                    f"來源類型無效: {variant.source}"


class TestMaxVariantsLimit:
    """測試變體數量限制"""

    def test_respects_max_variants_limit(self):
        """應遵守 max_variants 限制"""
        test_cases = [
            (ChineseFuzzyGenerator(), "測試"),
            # 註：英文和日文測試需要外部依賴
        ]

        max_limit = 5

        for gen, term in test_cases:
            # 向後兼容模式
            variants_legacy = gen.generate_variants(term, max_variants=max_limit)
            assert len(variants_legacy) <= max_limit

            # PhoneticVariant 模式
            variants_new = gen.generate_variants(
                term,
                max_variants=max_limit,
                return_phonetic_variants=True
            )
            assert len(variants_new) <= max_limit


class TestBackwardCompatibility:
    """測試向後兼容性"""

    def test_generate_variants_without_flags_works(self):
        """不帶參數的 generate_variants 應正常工作（向後兼容）"""
        generators = [
            ChineseFuzzyGenerator(),
            # 註：英文和日文測試需要外部依賴
        ]

        test_terms = ["測試"]

        for gen, term in zip(generators, test_terms):
            # 舊 API：只傳 term
            variants = gen.generate_variants(term)

            # 應該返回字串列表
            assert isinstance(variants, list)
            if len(variants) > 0:
                assert all(isinstance(v, str) for v in variants)

    def test_generate_variants_with_max_variants_works(self):
        """帶 max_variants 參數的 generate_variants 應正常工作"""
        generators = [
            ChineseFuzzyGenerator(),
            # 註：英文和日文測試需要外部依賴
        ]

        test_terms = ["測試"]

        for gen, term in zip(generators, test_terms):
            # 舊 API：term + max_variants
            variants = gen.generate_variants(term, max_variants=5)

            # 應該返回字串列表
            assert isinstance(variants, list)
            assert len(variants) <= 5


class TestEdgeCases:
    """測試邊界情況"""

    def test_empty_string_handling(self):
        """測試空字串處理"""
        generators = [
            ChineseFuzzyGenerator(),
            # 註：英文和日文測試需要外部依賴
        ]

        for gen in generators:
            variants = gen.generate_variants("")

            # 應該能處理（返回空列表或包含空字串）
            assert isinstance(variants, list)

    def test_single_character_handling(self):
        """測試單字符處理"""
        test_cases = [
            (ChineseFuzzyGenerator(), "中"),
            # 註：英文和日文測試需要外部依賴
        ]

        for gen, term in test_cases:
            variants = gen.generate_variants(term)

            # 應該能處理
            assert isinstance(variants, list)


class TestPerformance:
    """性能測試（確保無回歸）"""

    def test_reasonable_execution_time(self):
        """測試執行時間合理（簡單檢查，不做精確計時）"""
        import time

        test_cases = [
            (ChineseFuzzyGenerator(), "台北車站"),
            # 註：英文和日文測試需要外部依賴
        ]

        for gen, term in test_cases:
            start = time.time()
            variants = gen.generate_variants(term, max_variants=30)
            elapsed = time.time() - start

            # 應該在合理時間內完成（例如 < 5 秒）
            assert elapsed < 5.0, f"執行時間過長: {elapsed:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

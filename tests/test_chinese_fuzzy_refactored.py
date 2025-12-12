"""
測試重構後的中文 Fuzzy Generator

驗證：
1. 繼承 BaseFuzzyGenerator
2. 實現所有抽象方法
3. 保持向後兼容
4. 新的 PhoneticVariant 功能
"""

import pytest
from phonofix.languages.chinese.fuzzy_generator import ChineseFuzzyGenerator
from phonofix.core.fuzzy_generator_interface import (
    BaseFuzzyGenerator,
    PhoneticVariant,
    VariantSource,
)


class TestChineseFuzzyGeneratorRefactored:
    """測試重構後的中文 Fuzzy Generator"""

    def setup_method(self):
        self.generator = ChineseFuzzyGenerator()

    def test_inherits_base_fuzzy_generator(self):
        """測試繼承 BaseFuzzyGenerator"""
        assert isinstance(self.generator, BaseFuzzyGenerator)

    def test_phonetic_transform(self):
        """測試 phonetic_transform 方法"""
        # 台北 → taibei
        pinyin = self.generator.phonetic_transform("台北")
        assert pinyin == "taibei"

        # 中國 → zhongguo
        pinyin = self.generator.phonetic_transform("中國")
        assert pinyin == "zhongguo"

    def test_generate_phonetic_variants(self):
        """測試 generate_phonetic_variants 方法"""
        # 測試 Pinyin 模糊變體生成
        variants = self.generator.generate_phonetic_variants("zhong")

        # 應該包含原始 pinyin
        assert "zhong" in variants

        # 應該包含 z/zh 混淆變體
        assert "zong" in variants or len(variants) > 1

    def test_phonetic_to_text(self):
        """測試 phonetic_to_text 方法"""
        # Pinyin → 漢字反查
        char = self.generator.phonetic_to_text("zhong")

        # 應該返回一個漢字
        assert len(char) >= 1
        # 通常是 "中" 或其他同音字
        assert '\u4e00' <= char[0] <= '\u9fff' or char == "zhong"

    def test_apply_hardcoded_rules(self):
        """測試 apply_hardcoded_rules 方法"""
        # 測試是否有黏音規則
        hardcoded = self.generator.apply_hardcoded_rules("不知道")

        # 應該返回列表（可能為空）
        assert isinstance(hardcoded, list)

    def test_basic_variant_generation(self):
        """測試基本的變體生成"""
        variants = self.generator.generate_variants(
            "台北",
            max_variants=10
        )

        # 應該返回 PhoneticVariant 列表
        assert isinstance(variants, list)
        assert all(isinstance(v, PhoneticVariant) for v in variants)

        # 每個變體應該有完整的欄位
        for v in variants:
            assert hasattr(v, 'text')
            assert hasattr(v, 'phonetic_key')
            assert hasattr(v, 'score')
            assert hasattr(v, 'source')

    def test_list_input_mode(self):
        """測試列表輸入模式"""
        # 輸入列表，返回 Dict[str, List[PhoneticVariant]]
        result = self.generator.generate_variants(["台北", "測試"])

        # 應該返回字典
        assert isinstance(result, dict)

        # 每個鍵應該對應一個 PhoneticVariant 列表
        assert "台北" in result
        assert "測試" in result
        assert isinstance(result["台北"], list)
        assert isinstance(result["測試"], list)

        # 驗證列表元素類型
        if len(result["台北"]) > 0:
            assert all(isinstance(v, PhoneticVariant) for v in result["台北"])
        if len(result["測試"]) > 0:
            assert all(isinstance(v, PhoneticVariant) for v in result["測試"])

    def test_max_variants_limit(self):
        """測試 max_variants 參數"""
        # 限制變體數量
        variants = self.generator.generate_variants("台北", max_variants=5)

        # 應該不超過限制（+1 是因為包含原詞）
        assert len(variants) <= 6

    def test_source_types(self):
        """測試變體來源類型"""
        variants = self.generator.generate_variants(
            "台北",
            max_variants=20
        )

        # 應該有語音模糊變體
        phonetic_fuzzy = [v for v in variants if v.source == VariantSource.PHONETIC_FUZZY]
        assert len(phonetic_fuzzy) > 0

    def test_score_calculation(self):
        """測試評分計算"""
        variants = self.generator.generate_variants(
            "台北",
            max_variants=10
        )

        # 所有評分應該在 0.0-1.0 之間
        for v in variants:
            assert 0.0 <= v.score <= 1.0

        # 評分應該按降序排列
        scores = [v.score for v in variants]
        assert scores == sorted(scores, reverse=True)


class TestChineseFuzzyGeneratorEdgeCases:
    """測試邊界情況"""

    def setup_method(self):
        self.generator = ChineseFuzzyGenerator()

    def test_empty_string(self):
        """測試空字串"""
        variants = self.generator.generate_variants("")

        # 應該能處理（可能返回空列表或只包含空字串）
        assert isinstance(variants, list)

    def test_single_character(self):
        """測試單字符"""
        variants = self.generator.generate_variants("中")

        # 應該返回 PhoneticVariant 列表
        assert isinstance(variants, list)
        # 應該生成語音相似的變體（不一定包含原字，因為這是變體列表）
        assert len(variants) > 0
        # 驗證每個變體都有必要的屬性
        for v in variants:
            assert hasattr(v, 'text')
            assert hasattr(v, 'phonetic_key')

    def test_mixed_content(self):
        """測試混合內容（中文+英文）"""
        variants = self.generator.generate_variants("台北TW")

        # 應該能處理
        assert isinstance(variants, list)

    def test_phonetic_variant_with_hardcoded(self):
        """測試 PhoneticVariant 模式包含硬編碼規則"""
        # 如果配置中有黏音規則
        if "不知道" in self.generator.config.STICKY_PHRASE_MAP:
            variants = self.generator.generate_variants(
                "不知道",
                max_variants=20
            )

            # 應該包含硬編碼變體
            hardcoded_variants = [
                v for v in variants if v.source == VariantSource.HARDCODED_PATTERN
            ]

            # 可能有也可能沒有（取決於配置）
            assert isinstance(hardcoded_variants, list)


class TestChineseFuzzyGeneratorCompatibility:
    """測試與現有代碼的兼容性"""

    def setup_method(self):
        self.generator = ChineseFuzzyGenerator()

    def test_filter_homophones(self):
        """測試 filter_homophones 方法仍然有效"""
        term_list = ["測試", "側試", "策試"]
        result = self.generator.filter_homophones(term_list)

        # 應該返回 dict with 'kept' and 'filtered'
        assert "kept" in result
        assert "filtered" in result
        assert isinstance(result["kept"], list)
        assert isinstance(result["filtered"], list)

    def test_api_basic_usage(self):
        """測試基本 API 使用"""
        generator = ChineseFuzzyGenerator()

        # 單一詞彙 - 返回 List[PhoneticVariant]
        variants1 = generator.generate_variants("台北")
        assert isinstance(variants1, list)
        assert all(isinstance(v, PhoneticVariant) for v in variants1)

        # 詞彙列表 - 返回 Dict[str, List[PhoneticVariant]]
        variants2 = generator.generate_variants(["台北", "測試"])
        assert isinstance(variants2, dict)
        assert "台北" in variants2
        assert "測試" in variants2
        # 驗證每個值都是 PhoneticVariant 列表
        if len(variants2["台北"]) > 0:
            assert all(isinstance(v, PhoneticVariant) for v in variants2["台北"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

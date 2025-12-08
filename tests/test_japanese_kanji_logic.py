"""
測試日文漢字變體生成邏輯（不需要 fugashi/cutlet）

驗證核心邏輯的正確性，不依賴外部庫
"""

import pytest
from phonofix.languages.japanese.fuzzy_generator import JapaneseFuzzyGenerator


class TestHasKanjiLogic:
    """測試 _has_kanji 方法的邏輯（不需要外部依賴）"""

    def setup_method(self):
        self.generator = JapaneseFuzzyGenerator()

    def test_pure_ascii(self):
        """測試純 ASCII 字符"""
        assert not self.generator._has_kanji("abc123")
        assert not self.generator._has_kanji("hello")

    def test_unicode_ranges(self):
        """測試 Unicode 範圍識別"""
        # 漢字範圍：\u4e00 - \u9fff
        assert self.generator._has_kanji("\u4e00")  # 一（最小漢字）
        assert self.generator._has_kanji("\u9fff")  # （最大漢字）
        assert self.generator._has_kanji("\u6771\u4eac")  # 東京

    def test_hiragana_not_kanji(self):
        """測試平假名不被識別為漢字"""
        # 平假名範圍：\u3040 - \u309f
        assert not self.generator._has_kanji("\u3042")  # あ
        assert not self.generator._has_kanji("\u3093")  # ん

    def test_katakana_not_kanji(self):
        """測試片假名不被識別為漢字"""
        # 片假名範圍：\u30a0 - \u30ff
        assert not self.generator._has_kanji("\u30a2")  # ア
        assert not self.generator._has_kanji("\u30f3")  # ン

    def test_mixed_text(self):
        """測試混合文字"""
        assert self.generator._has_kanji("私はJohn")  # 包含「私」
        assert not self.generator._has_kanji("わたしはJohn")  # 無漢字

    def test_empty_string(self):
        """測試空字串"""
        assert not self.generator._has_kanji("")


class TestLookupHomophonesLogic:
    """測試 _lookup_homophones_from_dict 方法的邏輯"""

    def setup_method(self):
        self.generator = JapaneseFuzzyGenerator()

    def test_tokyo_homophones(self):
        """測試「東京」同音異字"""
        result = self.generator._lookup_homophones_from_dict("東京")

        assert isinstance(result, list)
        assert len(result) > 0
        assert "凍京" in result
        assert "東經" in result

    def test_company_homophones(self):
        """測試「会社」同音異字"""
        result = self.generator._lookup_homophones_from_dict("会社")

        assert isinstance(result, list)
        assert len(result) > 0
        assert "會社" in result

    def test_unknown_word_returns_empty(self):
        """測試未知詞返回空列表"""
        result = self.generator._lookup_homophones_from_dict("未知の言葉")

        assert result == []

    def test_dictionary_completeness(self):
        """測試字典完整性（至少 10 個詞條）"""
        # 測試多個詞
        test_words = [
            "東京", "大阪", "京都", "会社", "社会",
            "学校", "先生", "時間", "場所", "仕事"
        ]

        found_count = 0
        for word in test_words:
            result = self.generator._lookup_homophones_from_dict(word)
            if result:  # 非空列表
                found_count += 1

        # 至少 10 個詞有同音異字
        assert found_count == 10, f"只有 {found_count} 個詞有同音異字"


class TestKanjiVariantsDataStructure:
    """測試漢字變體的數據結構（不執行語音轉換）"""

    def setup_method(self):
        self.generator = JapaneseFuzzyGenerator()

    def test_has_kanji_identifies_correctly(self):
        """測試 _has_kanji 正確識別"""
        assert self.generator._has_kanji("東京")
        assert self.generator._has_kanji("会社")
        assert not self.generator._has_kanji("あいうえお")


class TestIntegration:
    """集成測試（不依賴外部庫）"""

    def setup_method(self):
        self.generator = JapaneseFuzzyGenerator()

    def test_dictionary_coverage(self):
        """測試字典覆蓋率"""
        # 確保有足夠的詞條
        all_words = [
            # 地名
            "東京", "大阪", "京都",
            # 常用詞
            "会社", "社会", "学校", "先生", "時間",
            "場所", "仕事", "電話", "日本", "今日",
            # 醫藥品
            "アスピリン", "ロキソニン"
        ]

        total_homophones = 0
        for word in all_words:
            homophones = self.generator._lookup_homophones_from_dict(word)
            total_homophones += len(homophones)

        # 總共應該有足夠多的同音異字
        assert total_homophones >= 15, \
            f"總同音異字數量不足: {total_homophones} < 15"

    def test_method_signatures(self):
        """測試方法簽名存在"""
        # 確保所有必要方法存在
        assert hasattr(self.generator, '_has_kanji')
        assert hasattr(self.generator, '_generate_kanji_variants')
        assert hasattr(self.generator, '_lookup_homophones_from_dict')
        assert hasattr(self.generator, 'generate_variants')

        # 確保方法可調用
        assert callable(self.generator._has_kanji)
        assert callable(self.generator._generate_kanji_variants)
        assert callable(self.generator._lookup_homophones_from_dict)


class TestAcceptanceCriteriaLogic:
    """驗收標準邏輯測試（不需要語音轉換）"""

    def setup_method(self):
        self.generator = JapaneseFuzzyGenerator()

    def test_criterion_1_method_exists(self):
        """驗收標準 1: 保留原詞漢字的方法存在"""
        # _generate_kanji_variants 方法應該存在
        assert hasattr(self.generator, '_generate_kanji_variants')

    def test_criterion_2_dictionary_size(self):
        """驗收標準 2: 至少 10 個詞有同音異字"""
        test_words = [
            "東京", "大阪", "京都",
            "会社", "社会", "学校",
            "先生", "時間", "場所", "仕事",
            "電話", "日本", "今日"
        ]

        words_with_homophones = 0
        for word in test_words:
            homophones = self.generator._lookup_homophones_from_dict(word)
            if homophones:
                words_with_homophones += 1

        assert words_with_homophones >= 10, \
            f"只有 {words_with_homophones} 個詞有同音異字，需要至少 10 個"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

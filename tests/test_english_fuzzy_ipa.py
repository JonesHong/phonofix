"""
測試英文 IPA 變體生成

驗證 Task 5.5 的測試要求：
1. IPA 音素模糊生成測試
2. 新詞泛化能力測試（關鍵）
3. IPA 去重測試
4. 性能測試
"""

import pytest
import time
from phonofix.languages.english.fuzzy_generator import EnglishFuzzyGenerator


class TestEnglishIPAGeneration:
    """測試英文 IPA 變體生成"""

    def setup_method(self):
        self.generator = EnglishFuzzyGenerator()

    def test_ipa_fuzzy_variants(self):
        """測試 IPA 音素模糊生成"""
        ipa = "ˈpaɪθɑn"
        variants = self.generator._generate_ipa_fuzzy_variants(ipa)

        # 變體數量合理
        assert 5 <= len(variants) <= 30, f"變體數量不合理: {len(variants)}"

        # 應包含清濁音變體 (p/b, θ/ð)
        ipa_str = ''.join(variants)
        has_voicing = 'b' in ipa_str or 'ð' in ipa_str
        assert has_voicing, "應包含清濁音變體"

        # 應包含相似音變體 (θ/f, θ/s)
        has_similar = 'f' in ipa_str or 's' in ipa_str
        assert has_similar, "應包含相似音素變體"

    def test_new_word_generalization(self):
        """測試新詞泛化能力（關鍵測試）"""
        # 這些詞在硬編碼字典中不存在，測試 IPA 系統的泛化能力
        new_words = [
            "Ollama",       # 新興 AI 工具
            "LangChain",    # AI 框架
            "Huggingface",  # AI 平台
            "Anthropic",    # 公司名
            "Claude",       # AI 助手
        ]

        for word in new_words:
            variants = self.generator.generate_variants(word, max_variants=20)

            # 應該能生成變體（不應該是空列表）
            assert len(variants) > 0, f"無法為新詞 '{word}' 生成變體"

            # 變體數量合理
            assert len(variants) <= 20, f"'{word}' 變體數量過多: {len(variants)}"

            # 變體應該與原詞不同
            assert word.lower() not in [v.lower() for v in variants], \
                f"變體中包含原詞: {word}"

    def test_deduplication_by_ipa(self):
        """測試基於 IPA 的去重"""
        # 測試去重功能
        variants = self.generator.generate_variants("Python")

        # 檢查沒有完全重複的變體
        variants_lower = [v.lower() for v in variants]
        assert len(variants_lower) == len(set(variants_lower)), \
            "存在重複的變體"

    def test_ipa_to_spelling_mapping(self):
        """測試 IPA → 拼寫反查"""
        from phonofix.languages.english.ipa_to_spelling import IPAToSpellingMapper

        mapper = IPAToSpellingMapper()

        # 測試常見 IPA 音素
        test_cases = [
            ("θɪŋk", "think"),   # 包含 θ 和 ŋ
            ("ʃɪp", "ship"),     # 包含 ʃ
            ("tʃiːp", "cheap"),  # 包含 tʃ 和 iː
            ("dʒʌmp", "jump"),   # 包含 dʒ 和 ʌ
        ]

        for ipa, expected in test_cases:
            spellings = mapper.ipa_to_spellings(ipa, max_results=5)

            # 應該生成拼寫
            assert len(spellings) > 0, f"無法為 IPA '{ipa}' 生成拼寫"

            # 預期拼寫應該在前幾個結果中
            assert expected in [s.lower() for s in spellings], \
                f"預期拼寫 '{expected}' 未出現在: {spellings}"

    def test_end_to_end_workflow(self):
        """測試端到端工作流：Term → IPA → Fuzzy IPA → Spellings"""
        term = "Python"

        # 1. Term → IPA
        base_ipa = self.generator.phonetic.to_phonetic(term)
        assert base_ipa, "無法生成 IPA"

        # 2. IPA → Fuzzy IPA
        ipa_variants = self.generator._generate_ipa_fuzzy_variants(base_ipa)
        assert len(ipa_variants) >= 5, "IPA 變體數量不足"

        # 3. Fuzzy IPA → Spellings
        for ipa_var in ipa_variants[:3]:
            spellings = self.generator.ipa_mapper.ipa_to_spellings(ipa_var, max_results=3)
            assert len(spellings) > 0, f"無法為 IPA '{ipa_var}' 生成拼寫"

        # 4. 完整流程
        variants = self.generator.generate_variants(term, max_variants=20)
        assert len(variants) >= 5, "最終變體數量不足"

    def test_performance(self):
        """測試性能"""
        # 單詞性能測試
        start = time.time()
        variants = self.generator.generate_variants("TensorFlow", max_variants=30)
        elapsed = time.time() - start

        # 應該在合理時間內完成（<2秒）
        assert elapsed < 2.0, f"生成時間過長: {elapsed:.2f}s"

        # 批次性能測試
        words = ["Python", "Java", "React", "Vue", "Angular"]
        start = time.time()
        for word in words:
            self.generator.generate_variants(word, max_variants=20)
        elapsed = time.time() - start

        # 平均每個詞 <1秒
        avg_time = elapsed / len(words)
        assert avg_time < 1.0, f"平均生成時間過長: {avg_time:.2f}s"

    def test_compatibility_with_existing_patterns(self):
        """測試與現有硬編碼模式的兼容性"""
        # 測試完整詞彙預定義變體仍然有效
        variants = self.generator.generate_variants("Python")

        # 硬編碼規則應該仍然生成特定變體（如果 config 中有定義）
        # 這裡測試至少生成了一些變體
        assert len(variants) > 0, "未生成任何變體"

        # 測試縮寫處理
        variants_api = self.generator.generate_variants("API")
        assert len(variants_api) > 0, "縮寫詞未生成變體"

        # 應該包含字母分開版本
        has_spaced = any(' ' in v for v in variants_api)
        assert has_spaced, "縮寫詞應包含字母分開版本"

    def test_integration_with_corrector(self):
        """測試與 corrector 的整合"""
        # 此測試需要 espeak-ng，如果未安裝則跳過
        try:
            from phonofix.engine.english_engine import EnglishEngine

            # 通過 Engine 創建 corrector
            engine = EnglishEngine()

            # 測試基本修正功能
            terms = {"Python": ["Pie thon", "Pyton"]}
            corrector = engine.create_corrector(terms)

            # 這些應該被修正
            test_cases = [
                ("I use Pie thon", "Python"),
                ("I use pyton", "Python"),
            ]

            for text, expected_term in test_cases:
                result = corrector.correct(text)
                # 檢查是否包含預期詞彙
                assert expected_term.lower() in result.lower(), \
                    f"未能修正 '{text}' 為 '{expected_term}': {result}"

        except RuntimeError as e:
            if "espeak" in str(e).lower():
                pytest.skip("espeak-ng 未安裝，跳過此測試")
            else:
                raise


class TestEnglishFuzzyGeneratorEdgeCases:
    """測試邊界情況"""

    def setup_method(self):
        self.generator = EnglishFuzzyGenerator()

    def test_empty_string(self):
        """測試空字串"""
        variants = self.generator.generate_variants("")
        assert len(variants) == 0, "空字串應返回空列表"

    def test_single_letter(self):
        """測試單字母"""
        variants = self.generator.generate_variants("a")
        # 單字母可能生成很少或沒有變體
        assert isinstance(variants, list), "應返回列表"

    def test_numbers(self):
        """測試數字"""
        variants = self.generator.generate_variants("123")
        # 數字應該能處理（可能通過 phonemizer）
        assert isinstance(variants, list), "應返回列表"

    def test_very_long_word(self):
        """測試超長詞"""
        long_word = "supercalifragilisticexpialidocious"
        variants = self.generator.generate_variants(long_word, max_variants=10)

        # 應該能處理長詞
        assert isinstance(variants, list), "應返回列表"
        assert len(variants) <= 10, "應遵守 max_variants 限制"

    def test_special_characters(self):
        """測試特殊字符"""
        variants = self.generator.generate_variants("Node.js")
        # 應該能處理帶特殊字符的詞
        assert isinstance(variants, list), "應返回列表"

    def test_mixed_case(self):
        """測試大小寫混合"""
        variants_lower = self.generator.generate_variants("python")
        variants_upper = self.generator.generate_variants("PYTHON")
        variants_mixed = self.generator.generate_variants("Python")

        # 所有版本應該生成變體
        assert len(variants_lower) > 0, "小寫版本應生成變體"
        assert len(variants_upper) > 0, "大寫版本應生成變體"
        assert len(variants_mixed) > 0, "混合大小寫版本應生成變體"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

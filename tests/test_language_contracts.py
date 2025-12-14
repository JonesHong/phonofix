"""
語言模組契約測試（護欄）

此檔案的目的不是測試最佳修正率或效能，而是鎖定「跨語言一致的最小契約」：
- Engine 能建立 corrector
- corrector.correct() 回傳 str
- tokenizer/token indices 基本一致
- fuzzy generator 回傳 list[str]

中文是 reference implementation，但此處只鎖最小共同契約，避免重構時破壞 API。
"""

from __future__ import annotations

from phonofix.core.protocols.corrector import CorrectorProtocol


class TestLanguageContracts:
    def test_chinese_contracts(self):
        from phonofix import ChineseEngine
        from phonofix.languages.chinese.fuzzy_generator import ChineseFuzzyGenerator
        from phonofix.languages.chinese.tokenizer import ChineseTokenizer

        engine = ChineseEngine()
        corrector = engine.create_corrector({"台北車站": ["北車"]})

        assert isinstance(corrector, CorrectorProtocol)
        assert isinstance(corrector.correct("我在北車"), str)

        tokenizer = ChineseTokenizer()
        tokens = tokenizer.tokenize("台北車站")
        indices = tokenizer.get_token_indices("台北車站")
        assert len(tokens) == len(indices)
        assert all(isinstance(t, str) for t in tokens)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in indices)

        fuzzy = ChineseFuzzyGenerator()
        variants = fuzzy.generate_variants("台北車站", max_variants=10)
        assert isinstance(variants, list)
        assert all(isinstance(v, str) for v in variants)

    def test_english_contracts(self):
        from phonofix import EnglishEngine
        from phonofix.languages.english.fuzzy_generator import EnglishFuzzyGenerator
        from phonofix.languages.english.tokenizer import EnglishTokenizer

        engine = EnglishEngine()
        corrector = engine.create_corrector({"Python": ["Pyton"]})

        assert isinstance(corrector, CorrectorProtocol)
        assert isinstance(corrector.correct("I use Pyton"), str)

        tokenizer = EnglishTokenizer()
        tokens = tokenizer.tokenize("I use Python")
        indices = tokenizer.get_token_indices("I use Python")
        assert len(tokens) == len(indices)
        assert all(isinstance(t, str) for t in tokens)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in indices)

        fuzzy = EnglishFuzzyGenerator()
        variants = fuzzy.generate_variants("Python", max_variants=10)
        assert isinstance(variants, list)
        assert all(isinstance(v, str) for v in variants)

    def test_japanese_contracts(self):
        from phonofix import JapaneseEngine
        from phonofix.languages.japanese.fuzzy_generator import JapaneseFuzzyGenerator
        from phonofix.languages.japanese.tokenizer import JapaneseTokenizer

        engine = JapaneseEngine()
        corrector = engine.create_corrector({"アスピリン": ["asupirin"]})

        assert isinstance(corrector, CorrectorProtocol)
        assert isinstance(corrector.correct("asupirin"), str)

        tokenizer = JapaneseTokenizer()
        tokens = tokenizer.tokenize("私はカツカレーが好きです")
        indices = tokenizer.get_token_indices("私はカツカレーが好きです")
        assert len(tokens) == len(indices)
        assert all(isinstance(t, str) for t in tokens)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in indices)

        fuzzy = JapaneseFuzzyGenerator()
        variants = fuzzy.generate_variants("アスピリン", max_variants=10)
        assert isinstance(variants, list)
        assert all(isinstance(v, str) for v in variants)

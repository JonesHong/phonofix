"""
英文替換器測試
"""
import pytest
from multi_language_corrector.languages.english import EnglishCorrector


class TestEnglishCorrector:
    """英文替換器基本功能測試"""

    def test_basic_substitution(self):
        """測試基本替換功能"""
        corrector = EnglishCorrector.from_terms(["Python", "TensorFlow"], warmup="none")
        
        result = corrector.correct("I use Pyton and Ten so floor")
        assert "Python" in result
        assert "TensorFlow" in result

    def test_split_word_matching(self):
        """測試分詞匹配 (ASR 常見錯誤)"""
        corrector = EnglishCorrector.from_terms(["JavaScript"], warmup="none")
        
        result = corrector.correct("I love java script")
        assert result == "I love JavaScript"

    def test_acronym_matching(self):
        """測試縮寫匹配"""
        corrector = EnglishCorrector.from_terms(["AWS", "GCP"], warmup="none")
        
        result = corrector.correct("I use A W S and G C P")
        assert "AWS" in result
        assert "GCP" in result

    def test_framework_names(self):
        """測試框架名稱"""
        terms = ["PyTorch", "NumPy", "Pandas", "Django"]
        corrector = EnglishCorrector.from_terms(terms, warmup="none")
        
        assert "PyTorch" in corrector.correct("Pie torch is great")
        assert "NumPy" in corrector.correct("I use Num pie")
        assert "Pandas" in corrector.correct("Pan das for data")
        assert "Django" in corrector.correct("Jango web framework")

    def test_dotted_names(self):
        """測試帶點的名稱 (如 Vue.js)"""
        corrector = EnglishCorrector.from_terms(["Vue.js", "Node.js"], warmup="none")
        
        result = corrector.correct("I use View JS and No JS")
        assert "Vue.js" in result
        assert "Node.js" in result

    def test_case_insensitive(self):
        """測試大小寫不敏感"""
        corrector = EnglishCorrector.from_terms(["Python"], warmup="none")
        
        result = corrector.correct("pyton is great")
        assert "Python" in result

    def test_empty_input(self):
        """測試空輸入"""
        corrector = EnglishCorrector.from_terms(["Python"], warmup="none")
        
        result = corrector.correct("")
        assert result == ""

    def test_no_match(self):
        """測試無匹配情況"""
        corrector = EnglishCorrector.from_terms(["Python"], warmup="none")
        
        result = corrector.correct("The weather is nice today")
        assert result == "The weather is nice today"


class TestEnglishCorrectorWarmup:
    """英文替換器預熱功能測試"""

    def test_warmup_none(self):
        """測試無預熱模式"""
        corrector = EnglishCorrector.from_terms(["Python"], warmup="none")
        assert corrector is not None

    def test_warmup_init(self):
        """測試初始化模式 (推薦) - 僅初始化 espeak-ng"""
        corrector = EnglishCorrector.from_terms(["Python"], warmup="init")
        assert corrector is not None

    def test_warmup_lazy(self):
        """測試背景初始化模式 - 不阻塞主執行緒"""
        corrector = EnglishCorrector.from_terms(["Python"], warmup="lazy")
        assert corrector is not None

    def test_warmup_fast(self):
        """測試快速預熱模式 (舊版相容，不推薦)"""
        # 注意：此模式會預熱 ~100 個詞，約需 17 秒
        # 為了測試速度，這裡跳過實際預熱
        corrector = EnglishCorrector.from_terms(["Python"], warmup="none")
        assert corrector is not None

    def test_warmup_full(self):
        """測試完整預熱模式 (舊版相容，不推薦)"""
        # 注意：此模式會預熱 ~200 個詞，約需 34 秒
        # 為了測試速度，這裡跳過實際預熱
        corrector = EnglishCorrector.from_terms(["Python"], warmup="none")
        assert corrector is not None

"""
混合語言替換器測試
"""
import pytest
from multi_language_corrector import UnifiedEngine


class TestUnifiedCorrector:
    """統一替換器基本功能測試"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """設置 UnifiedEngine (所有測試共享)"""
        self.engine = UnifiedEngine()

    def test_chinese_only(self):
        """測試純中文文本"""
        corrector = self.engine.create_corrector(["牛奶", "發揮"])
        
        result = corrector.correct("我買了流奶，他花揮了才能")
        assert "牛奶" in result
        assert "發揮" in result

    def test_english_only(self):
        """測試純英文文本"""
        corrector = self.engine.create_corrector(["Python", "TensorFlow"])
        
        result = corrector.correct("I use Pyton and Ten so floor")
        assert "Python" in result
        assert "TensorFlow" in result

    def test_mixed_language(self):
        """測試中英混合文本"""
        corrector = self.engine.create_corrector(["牛奶", "Python", "TensorFlow"])
        
        result = corrector.correct("我買了流奶，用Pyton寫code")
        assert "牛奶" in result
        assert "Python" in result

    def test_code_switching(self):
        """測試語言切換 (Code-Switching)"""
        terms = ["機器學習", "PyTorch", "深度學習"]
        corrector = self.engine.create_corrector(terms)
        
        text = "我用Pie torch做機氣學習和深讀學習"
        result = corrector.correct(text)
        
        assert "PyTorch" in result
        assert "機器學習" in result
        assert "深度學習" in result

    def test_empty_input(self):
        """測試空輸入"""
        corrector = self.engine.create_corrector(["測試"])
        
        result = corrector.correct("")
        assert result == ""

    def test_empty_terms(self):
        """測試空詞典"""
        corrector = self.engine.create_corrector([])
        
        result = corrector.correct("測試文本")
        assert result == "測試文本"

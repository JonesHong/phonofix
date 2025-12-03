"""
英文替換器測試
"""
import pytest
from multi_language_corrector import EnglishEngine


class TestEnglishCorrector:
    """英文替換器基本功能測試"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """設置 Engine (所有測試共享，Backend 單例模式)"""
        self.engine = EnglishEngine()

    def test_basic_substitution(self):
        """測試基本替換功能"""
        corrector = self.engine.create_corrector(["Python", "TensorFlow"])
        
        result = corrector.correct("I use Pyton and Ten so floor")
        assert "Python" in result
        assert "TensorFlow" in result

    def test_split_word_matching(self):
        """測試分詞匹配 (ASR 常見錯誤)"""
        corrector = self.engine.create_corrector(["JavaScript"])
        
        result = corrector.correct("I love java script")
        assert result == "I love JavaScript"

    def test_acronym_matching(self):
        """測試縮寫匹配"""
        corrector = self.engine.create_corrector(["AWS", "GCP"])
        
        result = corrector.correct("I use A W S and G C P")
        assert "AWS" in result
        assert "GCP" in result

    def test_framework_names(self):
        """測試框架名稱"""
        terms = ["PyTorch", "NumPy", "Pandas", "Django"]
        corrector = self.engine.create_corrector(terms)
        
        assert "PyTorch" in corrector.correct("Pie torch is great")
        assert "NumPy" in corrector.correct("I use Num pie")
        assert "Pandas" in corrector.correct("Pan das for data")
        assert "Django" in corrector.correct("Jango web framework")

    def test_dotted_names(self):
        """測試帶點的名稱 (如 Vue.js)"""
        corrector = self.engine.create_corrector(["Vue.js", "Node.js"])
        
        result = corrector.correct("I use View JS and No JS")
        assert "Vue.js" in result
        assert "Node.js" in result

    def test_case_insensitive(self):
        """測試大小寫不敏感"""
        corrector = self.engine.create_corrector(["Python"])
        
        result = corrector.correct("pyton is great")
        assert "Python" in result

    def test_empty_input(self):
        """測試空輸入"""
        corrector = self.engine.create_corrector(["Python"])
        
        result = corrector.correct("")
        assert result == ""

    def test_no_match(self):
        """測試無匹配情況"""
        corrector = self.engine.create_corrector(["Python"])
        
        result = corrector.correct("The weather is nice today")
        assert result == "The weather is nice today"


class TestEnglishEngineBackend:
    """英文 Engine 和 Backend 功能測試"""

    def test_engine_creation(self):
        """測試 Engine 建立"""
        engine = EnglishEngine()
        assert engine is not None

    def test_corrector_creation(self):
        """測試通過 Engine 建立 Corrector"""
        engine = EnglishEngine()
        corrector = engine.create_corrector(["Python"])
        assert corrector is not None

    def test_backend_singleton(self):
        """測試 Backend 單例模式"""
        engine1 = EnglishEngine()
        engine2 = EnglishEngine()
        # 兩個 Engine 應該共享同一個 Backend
        assert engine1._backend is engine2._backend

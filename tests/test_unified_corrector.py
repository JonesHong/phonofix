"""
混合語言替換器測試
"""
import pytest
from phonofix import UnifiedEngine


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


class TestCompetitiveCorrection:
    """
    方案 A 測試：短英數片段的雙重處理策略
    
    驗證 UnifiedCorrector 能正確處理被路由到 'en' 的短英數片段，
    讓中文修正器也有機會嘗試修正。
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """設置 UnifiedEngine"""
        self.engine = UnifiedEngine()

    def test_short_alphanumeric_1kg_to_ekg(self):
        """
        測試 "1kg" → "EKG" 的場景
        
        這是最典型的案例：
        - "1kg" 會被 LanguageRouter 歸類為 'en'
        - 但在中文語境（如「設備」「醫療」）下應該替換為 "EKG"
        """
        terms = {
            "EKG": {
                "aliases": ["1kg", "一kg"],
                "keywords": ["設備", "醫療", "心電圖"],
            }
        }
        corrector = self.engine.create_corrector(terms)
        
        # 有關鍵字時應該替換
        result = corrector.correct("這個1kg設備很重要")
        assert "EKG" in result, f"Expected 'EKG' in result, got: {result}"
        
        # 有關鍵字時應該替換
        result = corrector.correct("醫療1kg檢測")
        assert "EKG" in result, f"Expected 'EKG' in result, got: {result}"

    def test_short_alphanumeric_no_false_positive(self):
        """
        測試不應該誤替換的場景
        
        當 "1kg" 真的是重量單位時，不應該替換為 "EKG"
        """
        terms = {
            "EKG": {
                "aliases": ["1kg"],
                "keywords": ["設備", "醫療"],
                "exclude_when": ["重", "公斤", "重量"],
            }
        }
        corrector = self.engine.create_corrector(terms)
        
        # 有排除關鍵字時不應該替換
        result = corrector.correct("這個東西有1kg重")
        assert "EKG" not in result, f"Should not replace to 'EKG', got: {result}"
        assert "1kg" in result, f"Expected '1kg' preserved, got: {result}"

    def test_short_alphanumeric_2b_pencil(self):
        """
        測試 "2B" 鉛筆場景
        
        "2B" 是鉛筆型號，通常不需要替換
        除非有特定字典定義
        """
        # 沒有定義 2B 相關的替換
        corrector = self.engine.create_corrector(["牛奶"])
        
        result = corrector.correct("我買了2B鉛筆")
        assert "2B" in result, f"Expected '2B' preserved, got: {result}"

    def test_short_alphanumeric_a4_paper(self):
        """
        測試 "A4" 紙張場景
        """
        corrector = self.engine.create_corrector(["牛奶"])
        
        result = corrector.correct("我需要A4紙")
        assert "A4" in result, f"Expected 'A4' preserved, got: {result}"

    def test_longer_english_not_affected(self):
        """
        測試較長英文詞不受雙重處理影響
        
        較長的英文詞（>5字元）應該走正常路由，
        直接交給英文修正器處理
        """
        corrector = self.engine.create_corrector(["Python", "TensorFlow"])
        
        # "Pyton" (5字元) 應該被英文修正器處理
        result = corrector.correct("我用Pyton寫code")
        assert "Python" in result, f"Expected 'Python', got: {result}"
        
        # "Ten so floor" (>5字元) 應該被英文修正器處理
        result = corrector.correct("I use Ten so floor")
        assert "TensorFlow" in result, f"Expected 'TensorFlow', got: {result}"

    def test_mixed_short_and_long(self):
        """
        測試同時包含短英數和長英文的場景
        """
        terms = {
            "EKG": {
                "aliases": ["1kg"],
                "keywords": ["設備", "醫療"],
            },
            "TensorFlow": {
                "aliases": ["Ten so floor"],
            }
        }
        corrector = self.engine.create_corrector(terms)
        
        result = corrector.correct("醫療1kg設備用Ten so floor訓練")
        assert "EKG" in result, f"Expected 'EKG', got: {result}"
        assert "TensorFlow" in result, f"Expected 'TensorFlow', got: {result}"

    def test_chinese_context_priority(self):
        """
        測試中文上下文優先級
        
        當短英數片段在中文語境中，中文修正器應該有機會先處理
        """
        terms = {
            "台北車站": ["北車"],
            "EKG": {
                "aliases": ["1kg"],
                "keywords": ["設備"],
            }
        }
        corrector = self.engine.create_corrector(terms)
        
        # 中文片段正常處理
        result = corrector.correct("我在北車等你，旁邊有1kg設備")
        assert "台北車站" in result, f"Expected '台北車站', got: {result}"
        assert "EKG" in result, f"Expected 'EKG', got: {result}"

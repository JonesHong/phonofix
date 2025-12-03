"""
中文替換器測試
"""
import pytest
from multi_language_corrector.languages.chinese.corrector import ChineseCorrector as ChineseTextCorrector


class TestChineseCorrector:
    """中文替換器基本功能測試"""

    def test_basic_substitution(self):
        """測試基本替換功能"""
        # 注意：「北車」不是「台北車站」的模糊變體，需要手動指定
        corrector = ChineseTextCorrector.from_terms({
            "台北車站": {"aliases": ["北車"]},
            "牛奶": {}
        })
        
        result = corrector.correct("我在北車買了流奶")
        assert "台北車站" in result
        assert "牛奶" in result

    def test_fuzzy_matching_nl(self):
        """測試 n/l 模糊音匹配"""
        corrector = ChineseTextCorrector.from_terms(["牛奶"])
        
        result = corrector.correct("我買了流奶")
        assert result == "我買了牛奶"

    def test_fuzzy_matching_fh(self):
        """測試 f/h 模糊音匹配"""
        corrector = ChineseTextCorrector.from_terms(["發揮"])
        
        result = corrector.correct("他花揮了才能")
        assert result == "他發揮了才能"

    def test_abbreviation_expansion(self):
        """測試縮寫擴展"""
        corrector = ChineseTextCorrector.from_terms({
            "台北車站": {"aliases": ["北車"], "weight": 0.0}
        })
        
        result = corrector.correct("我在北車等你")
        assert result == "我在台北車站等你"

    def test_context_keywords(self):
        """測試上下文關鍵字"""
        corrector = ChineseTextCorrector.from_terms({
            "永和豆漿": {
                "aliases": ["永豆"],
                "keywords": ["吃", "喝", "買"],
                "weight": 0.3
            }
        })
        
        result = corrector.correct("我去買永豆")
        assert "永和豆漿" in result

    def test_exclusions(self):
        """測試豁免清單"""
        corrector = ChineseTextCorrector.from_terms(
            ["台北車站"],
            exclusions=["北側"]
        )
        
        result = corrector.correct("我在北側等你")
        assert "北側" in result  # 應保留，不被替換

    def test_empty_input(self):
        """測試空輸入"""
        corrector = ChineseTextCorrector.from_terms(["測試"])
        
        result = corrector.correct("")
        assert result == ""

    def test_no_match(self):
        """測試無匹配情況"""
        corrector = ChineseTextCorrector.from_terms(["台北車站"])
        
        result = corrector.correct("今天天氣很好")
        assert result == "今天天氣很好"

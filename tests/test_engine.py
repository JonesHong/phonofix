"""
Engine 層測試模組

測試新的三層架構：Backend → Engine → Corrector
"""

import pytest
import time


class TestEnglishEngine:
    """英文引擎測試"""

    def test_engine_initialization(self):
        """測試引擎初始化"""
        from phonofix.engine import EnglishEngine
        
        engine = EnglishEngine()
        assert engine.is_initialized()
        assert engine.phonetic is not None
        assert engine.tokenizer is not None
        assert engine.fuzzy_generator is not None
    
    def test_create_corrector(self):
        """測試建立修正器"""
        from phonofix.engine import EnglishEngine
        
        engine = EnglishEngine()
        corrector = engine.create_corrector({'Python': ['Pyton', 'Pyson']})
        
        assert corrector._engine is engine
        assert 'Python' in corrector.term_mapping.values()
        assert 'Pyton' in corrector.term_mapping
    
    def test_cache_sharing(self):
        """測試快取共享"""
        from phonofix.engine import EnglishEngine
        
        engine = EnglishEngine()
        
        # 第一個 corrector
        c1 = engine.create_corrector({'Python': ['Pyton']})
        stats_after_c1 = engine.get_backend_stats()
        
        # 第二個 corrector，使用相同詞彙
        c2 = engine.create_corrector({'Python': ['Pyton']})
        stats_after_c2 = engine.get_backend_stats()
        
        # 快取命中數應該增加
        assert stats_after_c2['hits'] > stats_after_c1['hits']
    
    def test_correction_functionality(self):
        """測試修正功能"""
        from phonofix.engine import EnglishEngine
        
        engine = EnglishEngine()
        corrector = engine.create_corrector({'Python': ['Pyton', 'Pyson']})
        
        result = corrector.correct('I use Pyton for ML')
        assert result == 'I use Python for ML'


class TestChineseEngine:
    """中文引擎測試"""

    def test_engine_initialization(self):
        """測試引擎初始化"""
        from phonofix.engine import ChineseEngine
        
        engine = ChineseEngine()
        assert engine.is_initialized()
        assert engine.phonetic is not None
        assert engine.tokenizer is not None
        assert engine.fuzzy_generator is not None
    
    def test_create_corrector(self):
        """測試建立修正器"""
        from phonofix.engine import ChineseEngine
        
        engine = ChineseEngine()
        corrector = engine.create_corrector({'台北車站': ['北車', '台北站']})
        
        assert corrector._engine is engine
        assert len(corrector.search_index) > 0
    
    def test_correction_functionality(self):
        """測試修正功能"""
        from phonofix.engine import ChineseEngine
        
        engine = ChineseEngine()
        corrector = engine.create_corrector({'台北車站': ['北車', '台北站']})
        
        result = corrector.correct('我在北車等你')
        assert '台北車站' in result


class TestUnifiedEngine:
    """統一引擎測試"""

    def test_engine_initialization(self):
        """測試引擎初始化"""
        from phonofix.engine import UnifiedEngine
        
        engine = UnifiedEngine()
        assert engine.is_initialized()
        assert engine.english_engine is not None
        assert engine.chinese_engine is not None
    
    def test_create_corrector_mixed_terms(self):
        """測試建立混合語言修正器"""
        from phonofix.engine import UnifiedEngine
        
        engine = UnifiedEngine()
        corrector = engine.create_corrector({
            '台北車站': ['北車'],
            'Python': ['Pyton'],
        })
        
        assert corrector._engine is engine
        assert 'zh' in corrector.correctors
        assert 'en' in corrector.correctors
    
    def test_create_corrector_chinese_only(self):
        """測試建立純中文修正器"""
        from phonofix.engine import UnifiedEngine
        
        engine = UnifiedEngine()
        corrector = engine.create_corrector({'台北車站': ['北車']})
        
        assert 'zh' in corrector.correctors
        assert 'en' not in corrector.correctors
    
    def test_create_corrector_english_only(self):
        """測試建立純英文修正器"""
        from phonofix.engine import UnifiedEngine
        
        engine = UnifiedEngine()
        corrector = engine.create_corrector({'Python': ['Pyton']})
        
        assert 'zh' not in corrector.correctors
        assert 'en' in corrector.correctors
    
    def test_mixed_correction(self):
        """測試混合語言修正"""
        from phonofix.engine import UnifiedEngine
        
        engine = UnifiedEngine()
        corrector = engine.create_corrector({
            '台北車站': ['北車'],
            'Python': ['Pyton'],
        })
        
        result = corrector.correct('我在北車學習Pyton')
        assert '台北車站' in result
        assert 'Python' in result


class TestBackendSingleton:
    """Backend 單例測試"""

    def test_english_backend_singleton(self):
        """測試英文 Backend 單例"""
        from phonofix.backend import get_english_backend
        
        backend1 = get_english_backend()
        backend2 = get_english_backend()
        
        assert backend1 is backend2
    
    def test_chinese_backend_singleton(self):
        """測試中文 Backend 單例"""
        from phonofix.backend import get_chinese_backend
        
        backend1 = get_chinese_backend()
        backend2 = get_chinese_backend()
        
        assert backend1 is backend2
    
    def test_backend_cache_persistence(self):
        """測試 Backend 快取持久性"""
        from phonofix.backend import get_english_backend
        
        backend = get_english_backend()
        backend.initialize()
        
        # 轉換一些文字
        backend.to_phonetic('hello')
        backend.to_phonetic('world')
        stats1 = backend.get_cache_stats()
        
        # 再次查詢相同文字
        backend.to_phonetic('hello')
        stats2 = backend.get_cache_stats()
        
        assert stats2['hits'] > stats1['hits']

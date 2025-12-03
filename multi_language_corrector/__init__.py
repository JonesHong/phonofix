"""
多語言語音相似修正器 (Multi-Language Phonetic Corrector)

基於語音相似度的專有名詞修正工具，支援 ASR/LLM 後處理。
支援中文（拼音）和英文（IPA）的語音相似度比對。

基本使用方式 (舊 API - 向後相容):
    from multi_language_corrector import UnifiedCorrector
    
    corrector = UnifiedCorrector({
        '台北車站': ['北車'],
        'Python': ['Pyton'],
    })
    result = corrector.correct('我在北車學習Pyton')

推薦使用方式 (新 API - 更高效能):
    from multi_language_corrector import UnifiedEngine
    
    # 應用程式啟動時初始化 Engine (一次性成本)
    engine = UnifiedEngine()
    
    # 需要時快速建立 Corrector (毫秒級)
    corrector = engine.create_corrector({
        '台北車站': ['北車'],
        'Python': ['Pyton'],
    })
    result = corrector.correct('我在北車學習Pyton')

效能優勢:
    - 舊 API: 每次建立 Corrector 需 ~2 秒 (espeak-ng 初始化)
    - 新 API: Engine 初始化 ~2 秒，後續 Corrector 建立 <10ms
"""

# =============================================================================
# 主要 API - Engine 層 (推薦使用)
# =============================================================================
from multi_language_corrector.engine import (
    UnifiedEngine,
    EnglishEngine,
    ChineseEngine,
)

# =============================================================================
# Corrector 層 (通常由 Engine 建立，但也可直接使用)
# =============================================================================
from multi_language_corrector.correction.unified_corrector import UnifiedCorrector
from multi_language_corrector.languages.chinese.corrector import ChineseCorrector
from multi_language_corrector.languages.english.corrector import EnglishCorrector

# =============================================================================
# Backend 層 (進階用途)
# =============================================================================
from multi_language_corrector.backend import (
    get_english_backend,
    get_chinese_backend,
    EnglishPhoneticBackend,
    ChinesePhoneticBackend,
)

__all__ = [
    # Engine 層 (推薦)
    'UnifiedEngine',
    'EnglishEngine',
    'ChineseEngine',
    
    # Corrector 層
    'UnifiedCorrector',
    'ChineseCorrector',
    'EnglishCorrector',
    
    # Backend 層 (進階)
    'get_english_backend',
    'get_chinese_backend',
    'EnglishPhoneticBackend',
    'ChinesePhoneticBackend',
]

__version__ = '0.2.0'

"""
多語言語音相似修正器 (Multi-Language Phonetic Corrector)

基於語音相似度的專有名詞修正工具，支援 ASR/LLM 後處理。
支援中文（拼音）和英文（IPA）的語音相似度比對。

使用方式:
    from multi_language_corrector import UnifiedEngine
    
    # 應用程式啟動時初始化 Engine (一次性成本, ~2秒)
    engine = UnifiedEngine()
    
    # 需要時快速建立 Corrector (毫秒級)
    corrector = engine.create_corrector({
        '台北車站': ['北車'],
        'Python': ['Pyton'],
    })
    result = corrector.correct('我在北車學習Pyton')

效能特性:
    - Engine 初始化: ~2 秒 (espeak-ng 載入)
    - Corrector 建立: <10ms (相同詞彙會更快，因為快取共享)
"""

# =============================================================================
# 主要 API - Engine 層
# =============================================================================
from multi_language_corrector.engine import (
    UnifiedEngine,
    EnglishEngine,
    ChineseEngine,
)

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
    # Engine 層
    'UnifiedEngine',
    'EnglishEngine',
    'ChineseEngine',
    
    # Backend 層 (進階)
    'get_english_backend',
    'get_chinese_backend',
    'EnglishPhoneticBackend',
    'ChinesePhoneticBackend',
]

__version__ = '1.0.0'

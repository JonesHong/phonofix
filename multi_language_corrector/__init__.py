"""
phonofix - 多語言語音相似修正器 (Multi-Language Phonetic Corrector)

基於語音相似度的專有名詞修正工具，支援 ASR/LLM 後處理。
支援中文（拼音）和英文（IPA）的語音相似度比對。

安裝方式:
    # 最小安裝 (僅核心)
    pip install phonofix
    
    # 中文支援
    pip install "phonofix[chinese]"
    
    # 英文支援 (還需安裝 espeak-ng)
    pip install "phonofix[english]"
    
    # 完整安裝
    pip install "phonofix[all]"

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
    
    # 啟用詳細日誌 (顯示計時與變體)
    engine = UnifiedEngine(verbose=True)
    
    # 進階: 自定義計時回呼
    engine = UnifiedEngine(
        verbose=True,
        on_timing=lambda op, t: print(f"{op}: {t:.3f}s")
    )
    
    # 進階: 使用標準 logging 控制
    import logging
    logging.getLogger("multi_language_corrector").setLevel(logging.DEBUG)

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
# 日誌工具
# =============================================================================
from multi_language_corrector.utils.logger import (
    get_logger,
    enable_debug_logging,
    enable_timing_logging,
)

# =============================================================================
# 依賴檢查工具
# =============================================================================
from multi_language_corrector.utils.lazy_imports import (
    is_chinese_available,
    is_english_available,
    check_chinese_dependencies,
    check_english_dependencies,
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
    
    # 日誌工具
    'get_logger',
    'enable_debug_logging',
    'enable_timing_logging',
    
    # 依賴檢查
    'is_chinese_available',
    'is_english_available',
    'check_chinese_dependencies',
    'check_english_dependencies',
    
    # Backend 層 (進階)
    'get_english_backend',
    'get_chinese_backend',
    'EnglishPhoneticBackend',
    'ChinesePhoneticBackend',
]

__version__ = '0.1.0'

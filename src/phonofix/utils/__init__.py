"""
工具模組

提供日誌、計時、延遲導入等通用工具。
"""

from .logger import (
    get_logger,
    log_timing,
    TimingContext,
)

from .lazy_imports import (
    is_chinese_available,
    is_english_available,
    check_chinese_dependencies,
    check_english_dependencies,
    CHINESE_INSTALL_HINT,
    ENGLISH_INSTALL_HINT,
)

__all__ = [
    # 日誌工具
    "get_logger",
    "log_timing",
    "TimingContext",
    
    # 依賴檢查
    "is_chinese_available",
    "is_english_available",
    "check_chinese_dependencies",
    "check_english_dependencies",
    "CHINESE_INSTALL_HINT",
    "ENGLISH_INSTALL_HINT",
]

"""
phonofix - 多語言語音相似修正器 (Multi-Language Phonetic Corrector)

核心概念（以中文為基準）：
- 使用者提供專有名詞字典（canonical + aliases）
- 系統把拼寫統一轉到「發音表示」維度建立比對群體（並做 auto-fuzzy 擴充）
- 文本進來同樣轉到發音維度比對，命中後回到原文字串做替換

官方入口（穩定 API）：
- `phonofix.EnglishEngine`
- `phonofix.ChineseEngine`
- `phonofix.JapaneseEngine`
"""

# =============================================================================
# Engine 層（官方入口）
# =============================================================================
from phonofix.languages.chinese import ChineseEngine
from phonofix.languages.english import EnglishEngine
from phonofix.languages.japanese import JapaneseEngine

# =============================================================================
# 日誌工具
# =============================================================================
from phonofix.utils.logger import enable_debug_logging, enable_timing_logging, get_logger

# =============================================================================
# 依賴檢查工具
# =============================================================================
from phonofix.utils.lazy_imports import (
    check_chinese_dependencies,
    check_english_dependencies,
    is_chinese_available,
    is_english_available,
)

# =============================================================================
# Backend 層（進階用途）
# =============================================================================
from phonofix.backend import (
    ChinesePhoneticBackend,
    EnglishPhoneticBackend,
    get_chinese_backend,
    get_english_backend,
)

# =============================================================================
# Protocol（進階用途）
# =============================================================================
from phonofix.core.protocols.corrector import CorrectorProtocol, ContextAwareCorrectorProtocol

__all__ = [
    # Engines
    "EnglishEngine",
    "ChineseEngine",
    "JapaneseEngine",
    # Logging
    "get_logger",
    "enable_debug_logging",
    "enable_timing_logging",
    # Dependency checks
    "is_chinese_available",
    "is_english_available",
    "check_chinese_dependencies",
    "check_english_dependencies",
    # Backend (advanced)
    "get_english_backend",
    "get_chinese_backend",
    "EnglishPhoneticBackend",
    "ChinesePhoneticBackend",
    # Protocols (advanced)
    "CorrectorProtocol",
    "ContextAwareCorrectorProtocol",
]

__version__ = "0.2.0"


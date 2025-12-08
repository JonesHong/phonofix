"""
修正引擎模組 (Engine Layer)

此模組包含修正引擎的實作，負責：
- 持有共享的 PhoneticSystem、Tokenizer、FuzzyGenerator
- 提供工廠方法建立輕量的 Corrector 實例
- 管理配置選項

Engine 是應用程式生命週期的物件，建立後可重複使用。
"""

from .base import CorrectorEngine
from .english_engine import EnglishEngine
from .chinese_engine import ChineseEngine
from .japanese_engine import JapaneseEngine
from .unified_engine import UnifiedEngine

__all__ = [
    "CorrectorEngine",
    "EnglishEngine",
    "ChineseEngine",
    "JapaneseEngine",
    "UnifiedEngine",
]

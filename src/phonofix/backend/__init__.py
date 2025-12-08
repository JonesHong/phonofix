"""
語音後端模組 (Backend Layer)

此模組包含語音處理的底層後端實作，負責：
- 初始化外部引擎 (espeak-ng, pypinyin)
- 管理語音轉換快取
- 提供基礎 G2P (Grapheme-to-Phoneme) 函數

所有後端都實作為單例模式，確保整個應用程式只初始化一次。
"""

from .base import PhoneticBackend
from .english_backend import EnglishPhoneticBackend, get_english_backend
from .chinese_backend import ChinesePhoneticBackend, get_chinese_backend

__all__ = [
    "PhoneticBackend",
    "EnglishPhoneticBackend",
    "ChinesePhoneticBackend",
    "get_english_backend",
    "get_chinese_backend",
]

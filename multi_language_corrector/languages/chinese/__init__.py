"""
中文修正模組

提供針對中文 ASR 輸出的模糊音修正功能。

主要類別:
- ChineseCorrector: 中文文本修正器
- FuzzyDictionaryGenerator: 模糊音詞典生成器
- PhoneticConfig: 拼音配置類別
- PhoneticUtils: 拼音工具函數類別
"""

from .corrector import ChineseCorrector
from .dictionary_generator import FuzzyDictionaryGenerator
from .config import PhoneticConfig
from .utils import PhoneticUtils

__all__ = [
    "ChineseCorrector",
    "FuzzyDictionaryGenerator",
    "PhoneticConfig",
    "PhoneticUtils",
]

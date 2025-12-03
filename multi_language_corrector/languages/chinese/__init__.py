"""
中文修正模組

提供針對中文 ASR 輸出的模糊音修正功能。

主要類別:
- ChineseCorrector: 中文文本修正器
- ChineseFuzzyGenerator: 模糊音變體生成器
- ChinesePhoneticConfig: 拼音配置類別
- ChinesePhoneticUtils: 拼音工具函數類別
"""

from .corrector import ChineseCorrector
from .fuzzy_generator import ChineseFuzzyGenerator
from .config import ChinesePhoneticConfig
from .utils import ChinesePhoneticUtils

__all__ = [
    "ChineseCorrector",
    "ChineseFuzzyGenerator",
    "ChinesePhoneticConfig",
    "ChinesePhoneticUtils",
]

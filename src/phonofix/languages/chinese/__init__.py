"""
中文修正模組

提供針對中文 ASR 輸出的模糊音修正功能。

主要類別:
- ChineseCorrector: 中文文本修正器
- ChineseFuzzyGenerator: 模糊音變體生成器
- ChinesePhoneticConfig: 拼音配置類別
- ChinesePhoneticUtils: 拼音工具函數類別

效能優化:
- cached_get_pinyin_string: 快取版拼音計算
- cached_get_initials: 快取版聲母計算
"""

from .engine import ChineseEngine
from .corrector import (
    ChineseCorrector,
    cached_get_pinyin_string,
    cached_get_initials,
)
from .fuzzy_generator import ChineseFuzzyGenerator
from .config import ChinesePhoneticConfig
from .utils import ChinesePhoneticUtils

__all__ = [
    "ChineseEngine",
    "ChineseCorrector",
    "ChineseFuzzyGenerator",
    "ChinesePhoneticConfig",
    "ChinesePhoneticUtils",
    "cached_get_pinyin_string",
    "cached_get_initials",
]

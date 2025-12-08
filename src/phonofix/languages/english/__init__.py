"""
英文修正模組

提供針對英文 ASR 輸出的模糊音修正功能。

主要類別:
- EnglishCorrector: 英文文本修正器
- EnglishFuzzyGenerator: 模糊音變體生成器
- EnglishPhoneticSystem: IPA 發音系統
- EnglishPhoneticConfig: 英文語音配置
- EnglishTokenizer: 英文分詞器

效能優化:
- cached_ipa_convert: 快取版 IPA 轉換
- warmup_ipa_cache: 預熱 IPA 快取 (加速首次執行)
- clear_english_cache: 清除快取
- get_english_cache_stats: 取得快取統計
"""

from .corrector import EnglishCorrector
from .fuzzy_generator import EnglishFuzzyGenerator
from .phonetic_impl import (
    EnglishPhoneticSystem, 
    cached_ipa_convert,
    warmup_ipa_cache,
    clear_english_cache,
    get_english_cache_stats,
)
from .config import EnglishPhoneticConfig
from .tokenizer import EnglishTokenizer

__all__ = [
    "EnglishCorrector",
    "EnglishFuzzyGenerator",
    "EnglishPhoneticSystem",
    "EnglishPhoneticConfig",
    "EnglishTokenizer",
    "cached_ipa_convert",
    "warmup_ipa_cache",
    "clear_english_cache",
    "get_english_cache_stats",
]

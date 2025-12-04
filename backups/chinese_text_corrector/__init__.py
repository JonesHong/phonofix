"""
Chinese Text Corrector - 中文文本校正工具包

通用的中文詞彙替換引擎,支援 ASR 後處理、地域慣用詞轉換、縮寫擴展等多種應用場景

核心功能:
1. 模糊音詞典生成 - 自動產生台式口音/模糊音變體詞典
2. 智能文本校正 - 詞彙智能替換（專有名詞、地域詞、縮寫等）
3. 同音詞過濾 - 去除拼音重複的詞彙
4. 自動校正器 - 自動生成別名並進行拼音去重

主要類別:
- ChineseTextCorrector: 文本校正器,支援多種詞彙替換場景
- ChineseTextCorrector.from_terms(): 類方法工廠 - 自動生成別名
- FuzzyDictionaryGenerator: 模糊音詞典生成器
- PhoneticConfig: 拼音配置類別
- PhoneticUtils: 拼音工具函數類別

Example:
    使用 ChineseTextCorrector.from_terms() (自動生成別名):

    >>> from chinese_text_corrector import ChineseTextCorrector

    >>> # 最簡格式 - 僅提供關鍵字,自動生成所有模糊音變體
    >>> corrector = ChineseTextCorrector.from_terms(["台北車站", "牛奶", "發揮"])
    >>> result = corrector.correct("我在北車買了流奶,他花揮了才能")
    >>> print(result)
    '我在台北車站買了牛奶,他發揮了才能'

    >>> # 完整格式 - 提供別名、關鍵字、權重
    >>> corrector = ChineseTextCorrector.from_terms({
    ...     "永和豆漿": {
    ...         "aliases": ["永豆"],
    ...         "keywords": ["吃", "喝", "買"],
    ...         "weight": 0.3
    ...     }
    ... })

    手動管理別名 (進階用法):

    >>> from chinese_text_corrector import ChineseTextCorrector, FuzzyDictionaryGenerator

    >>> # 1. 生成模糊音詞典
    >>> generator = FuzzyDictionaryGenerator()
    >>> fuzzy_dict = generator.generate_fuzzy_dictionary(["台北車站", "阿斯匹靈"])

    >>> # 2. 建立校正器
    >>> corrector = ChineseTextCorrector({
    ...     "台北車站": ["北車", "臺北車站"],
    ...     "阿斯匹靈": ["阿斯匹林", "二四批林"]
    ... })

    >>> # 3. 校正文本
    >>> result = corrector.correct("我在北車等你,醫生開了二四批林給我")
    >>> print(result)
    '我在台北車站等你,醫生開了阿斯匹靈給我'
"""

from .correction import ChineseTextCorrector
from .dictionary import FuzzyDictionaryGenerator
from .core import PhoneticConfig, PhoneticUtils

__version__ = "1.0.0"
__author__ = "JonesHong"
__all__ = [
    "ChineseTextCorrector",
    "FuzzyDictionaryGenerator",
    "PhoneticConfig",
    "PhoneticUtils",
]

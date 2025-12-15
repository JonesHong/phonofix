"""
Fuzzy Generator Protocol

定義 fuzzy generator 的最小介面（term -> variants）。
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class FuzzyGeneratorProtocol(Protocol):
    """
    模糊變體生成器介面（Protocol）。

    角色定位：
    - Engine 在建立 corrector 時，可選擇用 fuzzy generator 自動擴充 aliases
    - 生成的 variants 屬於「表面字串」候選，最終仍由 phonetic matching 決定是否命中

    注意：
    - 各語言的變體策略差異很大（中文同音字、英文拼寫規則、日文假名/romaji），但對外介面一致
    """
    def generate_variants(self, term: str, max_variants: int = 30) -> list[str]:
        """為輸入詞彙生成模糊變體"""
        ...

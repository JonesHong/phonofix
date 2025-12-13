"""
Fuzzy Generator Protocol

定義 fuzzy generator 的最小介面（term -> variants）。
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class FuzzyGeneratorProtocol(Protocol):
    def generate_variants(self, term: str, max_variants: int = 30) -> list[str]:
        """為輸入詞彙生成模糊變體"""
        ...


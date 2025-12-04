"""
分詞器介面模組

定義所有語言分詞處理必須實作的抽象基類
"""

from abc import ABC, abstractmethod
from typing import List, Tuple

class Tokenizer(ABC):
    """
    語言分詞器抽象介面 (Abstract Base Class)

    功能:
    - 定義將文本分割為處理單元 (Token) 的標準介面
    - 支援不同語言的分割策略 (如中文按字、英文按詞)
    """

    @abstractmethod
    def tokenize(self, text: str) -> List[str]:
        """
        將文本分割為 Token 列表 (中文為字，英文為詞)

        Args:
            text: 輸入文本

        Returns:
            List[str]: Token 列表
        """
        pass

    @abstractmethod
    def get_token_indices(self, text: str) -> List[Tuple[int, int]]:
        """
        取得每個 Token 在原始文本中的起始與結束索引

        這對於在修正後保留原始格式或進行精確替換非常重要。

        Args:
            text: 輸入文本

        Returns:
            List[Tuple[int, int]]: 每個 Token 的 (start_index, end_index) 列表
        """
        pass

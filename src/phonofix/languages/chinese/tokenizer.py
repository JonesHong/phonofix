"""
中文分詞器實作模組

實作基於字符 (Character-based) 的中文分詞處理。
"""

from typing import List, Tuple
from phonofix.core.tokenizer_interface import Tokenizer


class ChineseTokenizer(Tokenizer):
    """
    中文分詞器

    功能:
    - 將中文文本分割為單個字符 (Character)
    - 提供字符在原始文本中的位置索引
    - 適用於基於字的修正策略
    """

    def tokenize(self, text: str) -> List[str]:
        """
        將中文文本分割為字符列表

        由於中文修正通常基於字級別 (Character-level) 進行，
        因此這裡直接將字串轉換為字符列表。

        Args:
            text: 輸入中文文本

        Returns:
            List[str]: 字符列表
        """
        # 中文按字分詞
        return list(text)

    def get_token_indices(self, text: str) -> List[Tuple[int, int]]:
        """
        取得每個字符在原始文本中的起始與結束索引

        Args:
            text: 輸入中文文本

        Returns:
            List[Tuple[int, int]]: 每個字符的 (start_index, end_index) 列表
        """
        indices = []
        for i in range(len(text)):
            # 每個字符的範圍是 [i, i+1)
            indices.append((i, i + 1))
        return indices

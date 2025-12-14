"""
英文分詞器實作模組

實作基於正規表達式的英文分詞處理。
"""

import re
from typing import List, Tuple
from phonofix.core.tokenizer_interface import Tokenizer


class EnglishTokenizer(Tokenizer):
    """
    英文分詞器

    功能:
    - 將英文文本分割為單字 (Word)
    - 忽略標點符號與空白，僅提取單字內容
    - 提供單字在原始文本中的位置索引
    """

    def tokenize(self, text: str) -> List[str]:
        r"""
        將英文文本分割為單字列表

        使用 ASCII 正規表達式 `[A-Za-z0-9]+` 提取所有單字。
        這會忽略標點符號與非英文字符，且更適合在混合語言文本中只提取英文片段。
        例如 "Hello, world!" -> ["Hello", "world"]

        Args:
            text: 輸入英文文本

        Returns:
            List[str]: 單字列表
        """
        tokens: List[str] = []
        for match in re.finditer(r"[A-Za-z0-9]+", text):
            token = match.group(0)
            if token.isalpha() and token.isupper() and len(token) <= 5:
                tokens.extend(list(token))
            else:
                tokens.append(token)
        return tokens

    def get_token_indices(self, text: str) -> List[Tuple[int, int]]:
        """
        取得每個單字在原始文本中的起始與結束索引

        Args:
            text: 輸入英文文本

        Returns:
            List[Tuple[int, int]]: 每個單字的 (start_index, end_index) 列表
        """
        indices: List[Tuple[int, int]] = []
        for match in re.finditer(r"[A-Za-z0-9]+", text):
            start, end = match.span()
            token = match.group(0)
            if token.isalpha() and token.isupper() and len(token) <= 5:
                for offset in range(len(token)):
                    indices.append((start + offset, start + offset + 1))
            else:
                indices.append((start, end))
        return indices

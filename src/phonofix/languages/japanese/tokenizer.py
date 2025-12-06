"""
日文分詞器實作模組

實作基於 Cutlet/MeCab 的日文分詞處理。
"""

from typing import List, Tuple
from phonofix.core.tokenizer_interface import Tokenizer
from .utils import _get_cutlet


class JapaneseTokenizer(Tokenizer):
    """
    日文分詞器

    功能:
    - 將日文文本分割為單詞 (Words)
    - 使用 Cutlet (基於 Fugashi/MeCab) 進行分詞
    """

    def tokenize(self, text: str) -> List[str]:
        """
        將日文文本分割為單詞列表

        Args:
            text: 輸入日文文本

        Returns:
            List[str]: 單詞列表
        """
        if not text:
            return []
            
        cutlet = _get_cutlet()
        # Cutlet 的 romaji() 方法內部會分詞並加空格，
        # 但我們需要原始文字的 token。
        # 可以使用 cutlet.slug(text).split("-") 得到拼音 token，
        # 但若要取得原始文字 token，最好直接用 fugashi。
        # 不過為了簡化，我們可以利用 cutlet 內部的 tagger。
        
        # 這裡我們直接使用 cutlet 的 tagger (fugashi)
        tokens = []
        for word in cutlet.tagger(text):
            tokens.append(word.surface)
            
        return tokens

    def get_token_indices(self, text: str) -> List[Tuple[int, int]]:
        """
        取得每個單詞在原始文本中的起始與結束索引

        Args:
            text: 輸入日文文本

        Returns:
            List[Tuple[int, int]]: 每個單詞的 (start_index, end_index) 列表
        """
        if not text:
            return []

        cutlet = _get_cutlet()
        indices = []
        current_pos = 0
        
        # Fugashi 的 word.surface 是原始文字
        for word in cutlet.tagger(text):
            surface = word.surface
            start = current_pos
            end = current_pos + len(surface)
            indices.append((start, end))
            current_pos = end
            
        return indices

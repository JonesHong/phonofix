"""
日文分詞器實作模組

實作基於 Cutlet/MeCab 的日文分詞處理。
"""

from typing import List, Tuple

from phonofix.core.tokenizer_interface import Tokenizer
from phonofix.backend import JapanesePhoneticBackend, get_japanese_backend


class JapaneseTokenizer(Tokenizer):
    """
    日文分詞器

    功能:
    - 將日文文本分割為單詞 (Words)
    - 使用 Cutlet (基於 Fugashi/MeCab) 進行分詞
    """

    def __init__(self, backend: JapanesePhoneticBackend | None = None) -> None:
        """
        初始化日文分詞器。

        Args:
            backend: 可選 backend（未提供則取得日文 backend 單例）

        注意：
        - backend 會管理 fugashi.Tagger 的 singleton，避免每次 tokenize 都重新初始化
        """
        self._backend = backend or get_japanese_backend()

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
        # 由 backend 統一管理 fugashi 初始化與 tokenize 快取，避免重複解析成本。
        return self._backend.tokenize(text)

    def get_token_indices(self, text: str) -> List[Tuple[int, int]]:
        """
        取得每個單詞在原始文本中的起始與結束索引

        注意：會自動跳過 token 之間的空白字符

        Args:
            text: 輸入日文文本

        Returns:
            List[Tuple[int, int]]: 每個單詞的 (start_index, end_index) 列表
        """
        if not text:
            return []
        indices = []
        current_pos = 0

        # 使用 backend.tokenize() 取得 surface tokens（可共用快取）。
        for surface in self._backend.tokenize(text):

            # 在 text 中尋找 surface，從 current_pos 開始
            # 這可以處理 token 之間有空格的情況
            start = text.find(surface, current_pos)

            if start == -1:
                # 如果找不到 (理論上不應該發生，除非 fugashi 正規化了文本)，
                # 則退回到直接累加 (fallback)
                start = current_pos

            end = start + len(surface)
            indices.append((start, end))
            current_pos = end

        return indices

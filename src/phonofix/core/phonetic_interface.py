"""
發音系統介面模組

定義所有語言發音處理系統必須實作的抽象基類
"""

from abc import ABC, abstractmethod

class PhoneticSystem(ABC):
    """
    語言發音系統抽象介面 (Abstract Base Class)

    功能:
    - 定義將文字轉換為發音表示法 (Phonetic Representation) 的標準介面
    - 定義發音相似度比對的標準介面
    - 定義容錯率計算標準
    """

    @abstractmethod
    def to_phonetic(self, text: str) -> str:
        """
        將文本轉換為發音表示 (如拼音、IPA、羅馬拼音)

        Args:
            text: 輸入文本 (單字或字符)

        Returns:
            str: 發音字串
        """
        pass

    @abstractmethod
    def are_fuzzy_similar(self, phonetic1: str, phonetic2: str) -> bool:
        """
        判斷兩個發音字串是否模糊相似

        Args:
            phonetic1: 第一個發音字串
            phonetic2: 第二個發音字串

        Returns:
            bool: 若相似度在容許範圍內則返回 True
        """
        pass

    @abstractmethod
    def get_tolerance(self, length: int) -> float:
        """
        根據長度取得容錯率閾值

        Args:
            length: 發音字串或單字的長度

        Returns:
            float: 容錯率數值 (0.0 ~ 1.0)
        """
        pass

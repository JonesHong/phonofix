"""
中文發音系統實作模組

實作基於 Pinyin (拼音) 的中文發音轉換與相似度比對。
封裝了底層的 ChinesePhoneticUtils 以符合 PhoneticSystem 介面規範。
"""

from typing import TYPE_CHECKING

from multi_language_corrector.core.phonetic_interface import PhoneticSystem
from .utils import ChinesePhoneticUtils

if TYPE_CHECKING:
    from multi_language_corrector.backend.chinese_backend import ChinesePhoneticBackend


class ChinesePhoneticSystem(PhoneticSystem):
    """
    中文發音系統

    功能:
    - 將中文文本轉換為拼音字串
    - 判斷兩個拼音字串是否模糊相似 (支援聲母/韻母模糊音)
    - 提供基於長度的容錯率閾值
    
    使用方式:
    1. 舊版 API (使用 utils 內部快取):
       phonetic = ChinesePhoneticSystem()
       
    2. 新版 API (使用 Backend 單例):
       from multi_language_corrector.backend import get_chinese_backend
       backend = get_chinese_backend()
       backend.initialize()
       phonetic = ChinesePhoneticSystem(backend=backend)
    """

    def __init__(self, backend: "ChinesePhoneticBackend" = None):
        """
        初始化中文發音系統
        
        Args:
            backend: 可選的 ChinesePhoneticBackend 實例。
                     如果提供，將使用 Backend 的快取；
                     否則使用 utils 的內部快取。
        """
        self._backend = backend
        self.utils = ChinesePhoneticUtils()

    def to_phonetic(self, text: str) -> str:
        """
        將中文文本轉換為拼音字串

        Args:
            text: 輸入中文文本

        Returns:
            str: 拼音字串 (無聲調，小寫)
        """
        if self._backend:
            # 新架構：使用 Backend 的快取
            return self._backend.to_phonetic(text)
        else:
            # 舊架構：使用 utils 的內部快取
            return self.utils.get_pinyin_string(text)

    def are_fuzzy_similar(self, phonetic1: str, phonetic2: str) -> bool:
        """
        判斷兩個拼音字串是否模糊相似

        委派給 ChinesePhoneticUtils.are_fuzzy_similar 進行處理。
        注意: 這裡假設輸入的是單個音節或短語的拼音字串。

        Args:
            phonetic1: 第一個拼音字串
            phonetic2: 第二個拼音字串

        Returns:
            bool: 若相似則返回 True
        """
        # 注意: 這裡假設 phonetic1 和 phonetic2 是單個拼音音節或完整字串
        # 原始邏輯是逐音節比較的。
        # 如果傳入的是完整字串，我們可能需要拆分，但目前假設 utils 邏輯能處理
        # 或者調用者會逐字處理。
        # 實際上，utils.are_fuzzy_similar 主要是為單音節設計的。
        # 但中文修正器通常在滑動視窗上運作，所以這裡的 text 可能是單字或短語。
        
        # 為了符合介面定義，我們直接使用 utils 的邏輯
        # 但要注意多音節字串未對齊時可能會有問題
        return self.utils.are_fuzzy_similar(phonetic1, phonetic2)

    def get_tolerance(self, length: int) -> float:
        """
        根據拼音字串長度取得容錯率閾值

        Args:
            length: 拼音字串長度 (注意: 這裡是字符長度，非音節數)

        Returns:
            float: 容錯率數值
        """
        if length == 2: return 0.20
        elif length == 3: return 0.30
        return 0.40

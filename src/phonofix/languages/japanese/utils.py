"""
日文工具模組

提供日文處理相關的輔助函式，包含延遲載入 (Lazy Loading) 機制。
"""

import importlib
import logging
from typing import Any, Optional

from phonofix.utils.logger import get_logger

logger = get_logger(__name__)

_cutlet_instance: Optional[Any] = None
_fugashi_tagger: Optional[Any] = None


def _get_cutlet() -> Any:
    """
    取得 Cutlet 實例 (Lazy Loading)

    Returns:
        cutlet.Cutlet: Cutlet 實例

    Raises:
        ImportError: 如果未安裝 cutlet
    """
    global _cutlet_instance
    if _cutlet_instance is None:
        try:
            import cutlet
            # 預設使用 Hepburn 拼音，不使用外來語拼寫 (例如 'Camera' -> 'Kamera')
            # 這樣可以統一拼音維度，方便模糊比對
            _cutlet_instance = cutlet.Cutlet()
            _cutlet_instance.use_foreign_spelling = False 
        except ImportError as e:
            logger.error("無法載入 cutlet，請確認是否已安裝 'phonofix[ja]'")
            raise ImportError(
                "Missing Japanese dependencies. Please install with: pip install 'phonofix[ja]'"
            ) from e
    return _cutlet_instance


def _get_fugashi() -> Any:
    """
    取得 Fugashi Tagger 實例 (Lazy Loading)
    
    通常 Cutlet 內部會處理，但如果需要直接存取分詞器可使用此函式。

    Returns:
        fugashi.Tagger: Fugashi Tagger 實例
    """
    global _fugashi_tagger
    if _fugashi_tagger is None:
        try:
            import fugashi
            _fugashi_tagger = fugashi.Tagger()
        except ImportError as e:
            logger.error("無法載入 fugashi，請確認是否已安裝 'phonofix[ja]'")
            raise ImportError(
                "Missing Japanese dependencies. Please install with: pip install 'phonofix[ja]'"
            ) from e
    return _fugashi_tagger


def is_japanese_char(char: str) -> bool:
    """
    判斷字元是否為日文 (平假名、片假名)
    
    注意：漢字 (Kanji) 與中文重疊，此處不包含漢字判斷。
    漢字的語言歸屬通常由上下文決定。

    Args:
        char: 單個字元

    Returns:
        bool: 是否為平假名或片假名
    """
    if not char:
        return False
        
    code = ord(char)
    
    # 平假名 (Hiragana): 0x3040 - 0x309F
    if 0x3040 <= code <= 0x309F:
        return True
        
    # 片假名 (Katakana): 0x30A0 - 0x30FF
    if 0x30A0 <= code <= 0x30FF:
        return True
        
    return False

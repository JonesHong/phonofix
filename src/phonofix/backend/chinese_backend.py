"""
中文語音後端 (ChinesePhoneticBackend)

負責 pypinyin 的拼音轉換快取管理。
實作為執行緒安全的單例模式。

注意：此模組使用延遲導入 (Lazy Import) 機制，
僅在實際使用中文功能時才會載入 pypinyin。
如果未安裝中文依賴，將在首次使用時拋出清楚的 ImportError。

安裝中文支援:
    pip install "phonofix[ch]"
"""

import threading
from functools import lru_cache
from typing import Dict, Any, Optional, Tuple

from .base import PhoneticBackend


# =============================================================================
# 全域狀態
# =============================================================================

_instance: Optional["ChinesePhoneticBackend"] = None
_instance_lock = threading.Lock()

# 延遲導入狀態
_pypinyin = None
_pypinyin_checked = False


def _get_pypinyin():
    """延遲載入 pypinyin 模組"""
    global _pypinyin, _pypinyin_checked
    
    if _pypinyin_checked:
        if _pypinyin is not None:
            return _pypinyin
        else:
            from phonofix.utils.lazy_imports import CHINESE_INSTALL_HINT
            raise ImportError(CHINESE_INSTALL_HINT)
    
    try:
        import pypinyin
        _pypinyin = pypinyin
        _pypinyin_checked = True
        return _pypinyin
    except ImportError:
        _pypinyin_checked = True
        from phonofix.utils.lazy_imports import CHINESE_INSTALL_HINT
        raise ImportError(CHINESE_INSTALL_HINT)


# =============================================================================
# 拼音快取 (模組層級，所有 Backend 實例共享)
# =============================================================================

@lru_cache(maxsize=50000)
def _cached_get_pinyin_string(text: str) -> str:
    """
    快取版拼音字串計算
    
    Args:
        text: 中文文字
        
    Returns:
        str: 拼音字串 (無聲調，小寫)
    """
    pypinyin = _get_pypinyin()
    pinyin_list = pypinyin.lazy_pinyin(text, style=pypinyin.NORMAL)
    return "".join(pinyin_list).lower()


@lru_cache(maxsize=50000)
def _cached_get_initials(text: str) -> Tuple[str, ...]:
    """
    快取版聲母列表計算
    
    Args:
        text: 中文文字
        
    Returns:
        Tuple[str, ...]: 聲母元組
    """
    pypinyin = _get_pypinyin()
    return tuple(pypinyin.lazy_pinyin(text, style=pypinyin.INITIALS, strict=False))


@lru_cache(maxsize=50000)
def _cached_get_finals(text: str) -> Tuple[str, ...]:
    """
    快取版韻母列表計算
    
    Args:
        text: 中文文字
        
    Returns:
        Tuple[str, ...]: 韻母元組
    """
    pypinyin = _get_pypinyin()
    return tuple(pypinyin.lazy_pinyin(text, style=pypinyin.FINALS, strict=False))


# =============================================================================
# ChinesePhoneticBackend 單例類別
# =============================================================================

class ChinesePhoneticBackend(PhoneticBackend):
    """
    中文語音後端 (單例)
    
    職責:
    - 提供拼音轉換函數
    - 管理拼音快取
    
    注意：pypinyin 不需要像 espeak-ng 那樣的初始化過程，
    但我們仍然提供 initialize() 方法以保持介面一致性。
    
    使用方式:
        backend = get_chinese_backend()  # 取得單例
        pinyin = backend.to_phonetic("你好")  # "nihao"
    """
    
    def __init__(self):
        """
        初始化後端
        
        注意：請使用 get_chinese_backend() 取得單例，不要直接呼叫此建構函數。
        """
        self._initialized = False
        self._init_lock = threading.Lock()
    
    def initialize(self) -> None:
        """
        初始化後端
        
        pypinyin 不需要特殊初始化，此方法主要用於介面一致性。
        """
        if self._initialized:
            return
        
        with self._init_lock:
            if self._initialized:
                return
            
            # pypinyin 會在首次使用時自動載入字典
            # 這裡預先觸發一次以確保載入
            _cached_get_pinyin_string("測試")
            self._initialized = True
    
    def is_initialized(self) -> bool:
        """檢查是否已初始化"""
        return self._initialized
    
    def to_phonetic(self, text: str) -> str:
        """
        將中文文字轉換為拼音
        
        Args:
            text: 中文文字
            
        Returns:
            str: 拼音字串 (無聲調，小寫)
        """
        return _cached_get_pinyin_string(text)
    
    def get_initials(self, text: str) -> Tuple[str, ...]:
        """
        取得文字的聲母列表
        
        Args:
            text: 中文文字
            
        Returns:
            Tuple[str, ...]: 聲母元組
        """
        return _cached_get_initials(text)
    
    def get_finals(self, text: str) -> Tuple[str, ...]:
        """
        取得文字的韻母列表
        
        Args:
            text: 中文文字
            
        Returns:
            Tuple[str, ...]: 韻母元組
        """
        return _cached_get_finals(text)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        取得拼音快取統計
        
        Returns:
            Dict: 包含各快取的統計資訊
        """
        pinyin_info = _cached_get_pinyin_string.cache_info()
        initials_info = _cached_get_initials.cache_info()
        finals_info = _cached_get_finals.cache_info()
        
        return {
            "pinyin": {
                "hits": pinyin_info.hits,
                "misses": pinyin_info.misses,
                "currsize": pinyin_info.currsize,
                "maxsize": pinyin_info.maxsize,
            },
            "initials": {
                "hits": initials_info.hits,
                "misses": initials_info.misses,
                "currsize": initials_info.currsize,
                "maxsize": initials_info.maxsize,
            },
            "finals": {
                "hits": finals_info.hits,
                "misses": finals_info.misses,
                "currsize": finals_info.currsize,
                "maxsize": finals_info.maxsize,
            },
        }
    
    def clear_cache(self) -> None:
        """清除所有拼音快取"""
        _cached_get_pinyin_string.cache_clear()
        _cached_get_initials.cache_clear()
        _cached_get_finals.cache_clear()


# =============================================================================
# 便捷函數
# =============================================================================

def get_chinese_backend() -> ChinesePhoneticBackend:
    """
    取得 ChinesePhoneticBackend 單例
    
    這是取得中文語音後端的推薦方式。
    
    Returns:
        ChinesePhoneticBackend: 單例實例
    
    Example:
        backend = get_chinese_backend()
        pinyin = backend.to_phonetic("你好")  # "nihao"
    """
    global _instance
    
    if _instance is not None:
        return _instance
    
    with _instance_lock:
        if _instance is None:
            _instance = ChinesePhoneticBackend()
        return _instance

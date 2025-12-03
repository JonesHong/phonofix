"""
英文語音後端 (EnglishPhoneticBackend)

負責 espeak-ng 的初始化與 IPA 轉換快取管理。
實作為執行緒安全的單例模式。
"""

import os
import threading
import warnings
from functools import lru_cache
from typing import Dict, Any, Optional

from .base import PhoneticBackend


# =============================================================================
# 全域狀態
# =============================================================================

_instance: Optional["EnglishPhoneticBackend"] = None
_instance_lock = threading.Lock()


# =============================================================================
# 環境設定 - 自動偵測 espeak-ng
# =============================================================================

def _setup_espeak_library():
    """
    自動設定 PHONEMIZER_ESPEAK_LIBRARY 環境變數 (僅 Windows)
    
    phonemizer 在 Windows 上需要明確指定 libespeak-ng.dll 的路徑
    """
    if os.name != "nt":  # 非 Windows
        return
    
    if os.environ.get("PHONEMIZER_ESPEAK_LIBRARY"):
        return  # 已設定
    
    # 常見安裝路徑
    common_paths = [
        r"C:\Program Files\eSpeak NG\libespeak-ng.dll",
        r"C:\Program Files (x86)\eSpeak NG\libespeak-ng.dll",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = path
            return
    
    # 嘗試從 PATH 中找 espeak-ng.exe 並推測 DLL 位置
    import shutil
    espeak_exe = shutil.which("espeak-ng")
    if espeak_exe:
        dll_path = os.path.join(os.path.dirname(espeak_exe), "libespeak-ng.dll")
        if os.path.exists(dll_path):
            os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = dll_path


# =============================================================================
# 延遲載入 phonemizer
# =============================================================================

_phonemizer_available: Optional[bool] = None
_phonemize_func = None


def _get_phonemize():
    """延遲載入 phonemizer 模組"""
    global _phonemizer_available, _phonemize_func
    
    if _phonemizer_available is not None:
        if _phonemizer_available:
            return _phonemize_func
        else:
            raise RuntimeError(
                "phonemizer/espeak-ng 不可用。請確認:\n"
                "1. 已安裝 espeak-ng: https://github.com/espeak-ng/espeak-ng/releases\n"
                "2. Windows 使用者需設定環境變數 PHONEMIZER_ESPEAK_LIBRARY 指向 libespeak-ng.dll\n"
                "   例如: C:\\Program Files\\eSpeak NG\\libespeak-ng.dll"
            )
    
    try:
        from phonemizer import phonemize
        from phonemizer.backend.espeak.wrapper import EspeakWrapper
        
        # 測試是否真的可用
        EspeakWrapper.library()
        
        _phonemize_func = phonemize
        _phonemizer_available = True
        return _phonemize_func
    except Exception as e:
        _phonemizer_available = False
        raise RuntimeError(
            f"phonemizer/espeak-ng 初始化失敗: {e}\n"
            "請確認已正確安裝 espeak-ng 並設定環境變數。"
        )


# =============================================================================
# IPA 快取 (模組層級，所有 Backend 實例共享)
# =============================================================================

@lru_cache(maxsize=50000)
def _cached_ipa_convert(text: str) -> str:
    """
    快取版 IPA 轉換
    
    使用 phonemizer + espeak-ng 將英文文字轉換為 IPA
    """
    phonemize = _get_phonemize()
    
    # 忽略 phonemizer 的警告訊息
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = phonemize(
            text,
            language="en-us",
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
            with_stress=False,  # 不保留重音符號，簡化比對
        )
    
    return result.strip() if result else ""


# =============================================================================
# EnglishPhoneticBackend 單例類別
# =============================================================================

class EnglishPhoneticBackend(PhoneticBackend):
    """
    英文語音後端 (單例)
    
    職責:
    - 初始化 espeak-ng (只做一次)
    - 提供 IPA 轉換函數
    - 管理 IPA 快取
    
    使用方式:
        backend = get_english_backend()  # 取得單例
        ipa = backend.to_phonetic("hello")
    """
    
    def __init__(self):
        """
        初始化後端
        
        注意：請使用 get_english_backend() 取得單例，不要直接呼叫此建構函數。
        """
        self._initialized = False
        self._init_lock = threading.Lock()
    
    def initialize(self) -> None:
        """
        初始化 espeak-ng
        
        此方法是執行緒安全的，多次呼叫不會重複初始化。
        """
        if self._initialized:
            return
        
        with self._init_lock:
            if self._initialized:
                return
            
            # 設定環境變數
            _setup_espeak_library()
            
            # 觸發 espeak-ng 載入 (第一次呼叫會較慢)
            try:
                _cached_ipa_convert("hello")
                self._initialized = True
            except RuntimeError as e:
                raise RuntimeError(f"espeak-ng 初始化失敗: {e}")
    
    def initialize_lazy(self) -> None:
        """
        在背景執行緒初始化 espeak-ng，立即返回不阻塞
        """
        if self._initialized:
            return
        
        def _background_init():
            try:
                self.initialize()
            except Exception:
                pass
        
        thread = threading.Thread(target=_background_init, daemon=True)
        thread.start()
    
    def is_initialized(self) -> bool:
        """檢查是否已初始化"""
        return self._initialized
    
    def to_phonetic(self, text: str) -> str:
        """
        將文字轉換為 IPA
        
        如果尚未初始化，會自動初始化。
        
        Args:
            text: 輸入文字
            
        Returns:
            str: IPA 字串
        """
        if not self._initialized:
            self.initialize()
        
        return _cached_ipa_convert(text)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        取得 IPA 快取統計
        
        Returns:
            Dict: 包含 hits, misses, currsize, maxsize
        """
        info = _cached_ipa_convert.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "currsize": info.currsize,
            "maxsize": info.maxsize,
        }
    
    def clear_cache(self) -> None:
        """清除 IPA 快取"""
        _cached_ipa_convert.cache_clear()


# =============================================================================
# 便捷函數
# =============================================================================

def get_english_backend() -> EnglishPhoneticBackend:
    """
    取得 EnglishPhoneticBackend 單例
    
    這是取得英文語音後端的推薦方式。
    
    Returns:
        EnglishPhoneticBackend: 單例實例
    
    Example:
        backend = get_english_backend()
        ipa = backend.to_phonetic("hello")  # "həloʊ"
    """
    global _instance
    
    if _instance is not None:
        return _instance
    
    with _instance_lock:
        if _instance is None:
            _instance = EnglishPhoneticBackend()
        return _instance


def is_phonemizer_available() -> bool:
    """
    檢查 phonemizer 是否可用
    
    Returns:
        bool: 是否可用
    """
    try:
        _get_phonemize()
        return True
    except RuntimeError:
        return False

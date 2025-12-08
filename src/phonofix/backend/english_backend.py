"""
英文語音後端 (EnglishPhoneticBackend)

負責 espeak-ng 的初始化與 IPA 轉換快取管理。
實作為執行緒安全的單例模式。
"""

import os
import threading
import warnings
from typing import Dict, Any, Optional, List

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

# 安裝提示訊息
ENGLISH_INSTALL_HINT = (
    "缺少英文依賴。請執行:\n"
    "  pip install \"phonofix[english]\"\n"
    "或安裝完整版本:\n"
    "  pip install \"phonofix[all]\"\n\n"
    "注意: 英文支援還需要安裝 espeak-ng 系統套件:\n"
    "  Windows: https://github.com/espeak-ng/espeak-ng/releases\n"
    "  macOS: brew install espeak-ng\n"
    "  Linux: apt install espeak-ng"
)


def _get_phonemize():
    """延遲載入 phonemizer 模組"""
    global _phonemizer_available, _phonemize_func
    
    if _phonemizer_available is not None:
        if _phonemizer_available:
            return _phonemize_func
        else:
            raise RuntimeError(
                "phonemizer/espeak-ng 不可用。\n\n" + ENGLISH_INSTALL_HINT
            )
    
    try:
        from phonemizer import phonemize
        from phonemizer.backend.espeak.wrapper import EspeakWrapper
        
        # 測試是否真的可用
        EspeakWrapper.library()
        
        _phonemize_func = phonemize
        _phonemizer_available = True
        return _phonemize_func
    except ImportError as e:
        _phonemizer_available = False
        raise ImportError(ENGLISH_INSTALL_HINT)
    except Exception as e:
        _phonemizer_available = False
        raise RuntimeError(
            f"phonemizer/espeak-ng 初始化失敗: {e}\n\n" + ENGLISH_INSTALL_HINT
        )


# =============================================================================
# IPA 快取 (模組層級，所有 Backend 實例共享)
# =============================================================================

# 使用字典作為快取 (比 lru_cache 更靈活，支援批次填充)
_ipa_cache: Dict[str, str] = {}
_cache_lock = threading.Lock()
_cache_maxsize = 50000
_cache_stats = {"hits": 0, "misses": 0}


def _cached_ipa_convert(text: str) -> str:
    """
    快取版 IPA 轉換 (單一文字)
    
    使用 phonemizer + espeak-ng 將英文文字轉換為 IPA
    """
    global _cache_stats
    
    # 檢查快取
    if text in _ipa_cache:
        _cache_stats["hits"] += 1
        return _ipa_cache[text]
    
    _cache_stats["misses"] += 1
    
    # 未命中快取，執行轉換
    phonemize = _get_phonemize()
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = phonemize(
            text,
            language="en-us",
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
            with_stress=False,
        )
    
    result = result.strip() if result else ""
    
    # 存入快取
    with _cache_lock:
        if len(_ipa_cache) < _cache_maxsize:
            _ipa_cache[text] = result
    
    return result


def _batch_ipa_convert(texts: list) -> Dict[str, str]:
    """
    批次 IPA 轉換 (效能優化)
    
    一次呼叫 phonemizer 處理多個文字，避免重複啟動進程。
    批次處理比逐一呼叫快約 10 倍。
    
    Args:
        texts: 要轉換的文字列表
        
    Returns:
        Dict[str, str]: 文字 -> IPA 映射
    """
    global _cache_stats
    
    if not texts:
        return {}
    
    # 分離已快取和未快取的項目
    results = {}
    uncached = []
    
    for text in texts:
        if text in _ipa_cache:
            _cache_stats["hits"] += 1
            results[text] = _ipa_cache[text]
        else:
            uncached.append(text)
    
    if not uncached:
        return results
    
    _cache_stats["misses"] += len(uncached)
    
    # 批次轉換未快取的項目
    phonemize = _get_phonemize()
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ipas = phonemize(
            uncached,
            language="en-us",
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
            with_stress=False,
        )
    
    # 處理結果 (可能是字串或列表)
    if isinstance(ipas, str):
        ipas = [ipas]
    
    # 存入快取並建立結果
    with _cache_lock:
        for text, ipa in zip(uncached, ipas):
            ipa = ipa.strip() if ipa else ""
            if len(_ipa_cache) < _cache_maxsize:
                _ipa_cache[text] = ipa
            results[text] = ipa
    
    return results


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
    
    def to_phonetic_batch(self, texts: list) -> Dict[str, str]:
        """
        批次將文字轉換為 IPA (效能優化)
        
        一次呼叫處理多個文字，比逐一呼叫快約 10 倍。
        
        Args:
            texts: 輸入文字列表
            
        Returns:
            Dict[str, str]: 文字 -> IPA 映射
        """
        if not self._initialized:
            self.initialize()
        
        return _batch_ipa_convert(texts)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        取得 IPA 快取統計
        
        Returns:
            Dict: 包含 hits, misses, currsize, maxsize
        """
        return {
            "hits": _cache_stats["hits"],
            "misses": _cache_stats["misses"],
            "currsize": len(_ipa_cache),
            "maxsize": _cache_maxsize,
        }
    
    def clear_cache(self) -> None:
        """清除 IPA 快取"""
        global _ipa_cache, _cache_stats
        with _cache_lock:
            _ipa_cache.clear()
            _cache_stats = {"hits": 0, "misses": 0}


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

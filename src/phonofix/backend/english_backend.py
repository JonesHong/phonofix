"""
英文語音後端 (EnglishPhoneticBackend)

負責 espeak-ng 的初始化與 IPA 轉換快取管理。
實作為執行緒安全的單例模式。
"""

import os
import threading
import time
import traceback
import warnings
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from phonofix.languages.english import ENGLISH_INSTALL_HINT
from phonofix.utils.logger import get_logger

from .base import PhoneticBackend
from .stats import BackendStats, CacheStats, LazyInitStats

# =============================================================================
# 全域狀態
# =============================================================================

logger = get_logger(__name__)

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
    except ImportError:
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
_stats_lock = threading.Lock()


def _record_hits(count: int = 1) -> None:
    """
    累計快取命中次數（thread-safe）。

    注意：
    - 英文 backend 的快取統計使用全域 dict + lock 管理
    - 這裡只負責更新 hits，不做任何快取內容的變更
    """
    if count <= 0:
        return
    with _stats_lock:
        _cache_stats["hits"] += count


def _record_misses(count: int = 1) -> None:
    """
    累計快取未命中次數（thread-safe）。

    注意：
    - miss 不代表錯誤，只代表需要呼叫 phonemizer 進行一次轉換
    - miss 的成本較高，因此 stats 可用來觀察效能與 warmup 效果
    """
    if count <= 0:
        return
    with _stats_lock:
        _cache_stats["misses"] += count


def _cached_ipa_convert(text: str) -> str:
    """
    快取版 IPA 轉換 (單一文字)

    使用 phonemizer + espeak-ng 將英文文字轉換為 IPA
    """
    # 檢查快取
    if text in _ipa_cache:
        _record_hits()
        return _ipa_cache[text]

    _record_misses()

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


def _normalize_english_text_for_ipa(text: str) -> str:
    """
    英文 IPA 轉換前的輕量正規化（用於 token/canonical 對齊）

    目標：讓縮寫/數字在 batch IPA 場景下也能與 phonetic matching 對齊，避免過度依賴 surface variants。
    """
    if not text:
        return ""

    # 常見縮寫（小寫）
    common_abbreviations = {
        "js",
        "ts",
        "py",
        "rb",
        "go",
        "rs",
        "cs",
        "db",
        "ml",
        "ai",
        "ui",
        "ux",
        "api",
        "sql",
        "css",
        "xml",
        "sdk",
        "aws",
        "gcp",
    }

    normalized = text

    # 全大寫短詞：視為字母縮寫（AWS -> A W S）
    if normalized.isupper() and len(normalized) <= 5 and normalized.isalpha():
        normalized = " ".join(list(normalized))
    # 常見小寫縮寫：轉為大寫字母發音（js -> J S）
    elif normalized.lower() in common_abbreviations and normalized.isalpha():
        normalized = " ".join(list(normalized.upper()))

    # 數字簡單展開（避免 1kg / 3d 類案例直接進 phonemizer）
    normalized = (
        normalized.replace("0", "zero ")
        .replace("1", "one ")
        .replace("2", "two ")
        .replace("3", "three ")
        .replace("4", "four ")
        .replace("5", "five ")
        .replace("6", "six ")
        .replace("7", "seven ")
        .replace("8", "eight ")
        .replace("9", "nine ")
    )

    return normalized


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
    if not texts:
        return {}

    # 分離已快取和未快取的項目
    results = {}
    uncached = []
    cached_count = 0

    for text in texts:
        if text in _ipa_cache:
            cached_count += 1
            results[text] = _ipa_cache[text]
        else:
            uncached.append(text)

    _record_hits(cached_count)

    if not uncached:
        return results

    _record_misses(len(uncached))

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
        self._lazy_init_lock = threading.Lock()
        self._lazy_init_thread: Optional[threading.Thread] = None
        self._lazy_init_status: Literal["not_started", "running", "succeeded", "failed"] = "not_started"
        self._lazy_init_started_at: Optional[str] = None
        self._lazy_init_finished_at: Optional[str] = None
        self._lazy_init_duration_ms: Optional[int] = None
        self._lazy_init_error: Optional[Dict[str, str]] = None

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

        可觀測性：
        - 此方法不會拋出例外（因為在背景執行緒執行），但會把狀態與錯誤資訊
          記錄在 backend 內，可透過 `get_cache_stats()["lazy_init"]` 取得。
        - 這可避免「默默」降級：即使主流程不阻塞，也能在觀測/除錯時知道初始化是否成功。
        """
        if self._initialized:
            return

        with self._lazy_init_lock:
            if self._lazy_init_status == "running":
                return

            self._lazy_init_status = "running"
            self._lazy_init_started_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            self._lazy_init_finished_at = None
            self._lazy_init_duration_ms = None
            self._lazy_init_error = None
            started_monotonic = time.perf_counter()

        def _background_init():
            """
            背景初始化工作。

            注意：
            - 背景執行緒無法把例外傳回呼叫端，因此這裡會：
              1) 記錄 logger（可被集中式 log 收集）
              2) 將錯誤資訊寫入 lazy_init 狀態（可被 get_cache_stats 觀測）
            """
            try:
                self.initialize()
                with self._lazy_init_lock:
                    self._lazy_init_status = "succeeded"
                    self._lazy_init_finished_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                    self._lazy_init_duration_ms = int((time.perf_counter() - started_monotonic) * 1000)
                    self._lazy_init_error = None
            except Exception as exc:
                logger.exception("EnglishPhoneticBackend.initialize_lazy() 背景初始化失敗")
                with self._lazy_init_lock:
                    self._lazy_init_status = "failed"
                    self._lazy_init_finished_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                    self._lazy_init_duration_ms = int((time.perf_counter() - started_monotonic) * 1000)
                    self._lazy_init_error = {
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                        "traceback": traceback.format_exc(),
                    }

        thread = threading.Thread(target=_background_init, daemon=True, name="phonofix-english-backend-init")
        with self._lazy_init_lock:
            self._lazy_init_thread = thread
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

        return _cached_ipa_convert(_normalize_english_text_for_ipa(text))

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

        normalized = [_normalize_english_text_for_ipa(t) for t in texts]
        normalized_map = _batch_ipa_convert(normalized)
        return {orig: normalized_map.get(_normalize_english_text_for_ipa(orig), "") for orig in texts}

    def get_cache_stats(self) -> BackendStats:
        """
        取得 IPA 快取統計

        Returns:
            Dict: 包含 hits, misses, currsize, maxsize
        """
        with _stats_lock:
            hits = _cache_stats["hits"]
            misses = _cache_stats["misses"]
        with _cache_lock:
            currsize = len(_ipa_cache)
        with self._lazy_init_lock:
            lazy_init: LazyInitStats = {
                "status": self._lazy_init_status,
                "started_at": self._lazy_init_started_at,
                "finished_at": self._lazy_init_finished_at,
                "duration_ms": self._lazy_init_duration_ms,
                "error": self._lazy_init_error,
            }

        caches: dict[str, CacheStats] = {
            "ipa": {
                "hits": int(hits),
                "misses": int(misses),
                "currsize": int(currsize),
                "maxsize": int(_cache_maxsize),
            }
        }

        return BackendStats(
            initialized=bool(self._initialized),
            lazy_init=lazy_init,
            caches=caches,
        )

    def clear_cache(self) -> None:
        """清除 IPA 快取"""
        with _cache_lock:
            _ipa_cache.clear()
        with _stats_lock:
            _cache_stats["hits"] = 0
            _cache_stats["misses"] = 0


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
    except (RuntimeError, ImportError):
        return False

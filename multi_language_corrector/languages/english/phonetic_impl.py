"""
英文發音系統實作模組

實作基於 IPA (國際音標) 的英文發音轉換與相似度比對。
使用 phonemizer + espeak-ng 作為 G2P (Grapheme-to-Phoneme) 引擎。

效能優化:
- 使用 functools.lru_cache 快取 IPA 轉換結果
- 避免重複的 phonemizer 調用
- warmup_ipa_cache() 初始化 espeak-ng 引擎（推薦使用 mode="init"）

效能特性 (phonemizer vs eng-to-ipa):
- 首次載入 espeak-ng: ~2 秒 (一次性成本)
- 冷查詢 (無快取): ~170 ms/字 (較慢，但能處理 OOV)
- 快取命中: ~0.001 ms/字 (極快)

暖身策略建議:
- mode="init": 僅初始化 espeak-ng (~2秒)，推薦用於應用啟動時
- mode="none": 不暖身，首次使用時才初始化
- mode="lazy": 在背景執行緒初始化，不阻塞主執行緒

環境需求:
- 需安裝 espeak-ng 系統執行檔
- Windows 使用者需設定 PHONEMIZER_ESPEAK_LIBRARY 環境變數指向 libespeak-ng.dll
"""

import os
import re
import threading
import warnings
from functools import lru_cache
from typing import List, Optional

import Levenshtein

from multi_language_corrector.core.phonetic_interface import PhoneticSystem


# =============================================================================
# 全域狀態
# =============================================================================

_espeak_initialized = False
_init_lock = threading.Lock()


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


# 在 import phonemizer 之前設定環境
_setup_espeak_library()

# 延遲 import phonemizer，避免在環境未設定時報錯
_phonemizer_available = None
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


def is_phonemizer_available() -> bool:
    """檢查 phonemizer 是否可用"""
    try:
        _get_phonemize()
        return True
    except RuntimeError:
        return False


# =============================================================================
# IPA 快取 (Performance Critical)
# =============================================================================

@lru_cache(maxsize=50000)
def cached_ipa_convert(text: str) -> str:
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


def clear_english_cache():
    """清除 IPA 快取"""
    cached_ipa_convert.cache_clear()


def get_english_cache_stats():
    """取得 IPA 快取統計"""
    return cached_ipa_convert.cache_info()


def warmup_ipa_cache(verbose: bool = False, mode: str = "init"):
    """
    初始化 espeak-ng
    
    由於 phonemizer + espeak-ng 的特性：
    - 首次載入 espeak-ng 需要 ~2 秒
    - 之後每次冷查詢約 170ms/字
    - 快取命中後只要 ~0.001ms/字
    
    Args:
        verbose: 是否顯示進度資訊
        mode: 暖機模式
            - "init": [推薦] 僅初始化 espeak-ng (~2秒)
            - "lazy": 在背景執行緒初始化，立即返回不阻塞
            - "none": 不做任何事，首次使用時才初始化
    
    Returns:
        int: 1 表示成功或已初始化，0 表示跳過或失敗
    """
    global _espeak_initialized
    
    if mode == "none":
        return 0
    
    if mode == "init":
        if _espeak_initialized:
            if verbose:
                print("espeak-ng 已初始化，跳過")
            return 1
        
        if verbose:
            print("正在初始化 espeak-ng...")
        
        try:
            # 只呼叫一次來觸發 espeak-ng 載入
            cached_ipa_convert("hello")
            with _init_lock:
                _espeak_initialized = True
            if verbose:
                print("espeak-ng 初始化完成")
            return 1
        except Exception as e:
            if verbose:
                print(f"espeak-ng 初始化失敗: {e}")
            return 0
    
    if mode == "lazy":
        def _background_init():
            global _espeak_initialized
            try:
                cached_ipa_convert("hello")
                with _init_lock:
                    _espeak_initialized = True
            except Exception:
                pass
        
        if not _espeak_initialized:
            thread = threading.Thread(target=_background_init, daemon=True)
            thread.start()
            if verbose:
                print("espeak-ng 正在背景初始化...")
        return 1
    
    # 未知模式
    if verbose:
        print(f"警告: 未知的暖機模式 '{mode}'，使用 'init' 模式")
    return warmup_ipa_cache(verbose=verbose, mode="init")


# =============================================================================
# 英文發音系統類別
# =============================================================================

class EnglishPhoneticSystem(PhoneticSystem):
    """
    英文發音系統

    功能:
    - 將英文文本轉換為 IPA 音標字串 (使用 phonemizer + espeak-ng)
    - 處理常見的 ASR 錯誤 (如縮寫、數字)
    - 計算 IPA 字串間的編輯距離以判斷相似度
    
    使用方式:
    1. 舊版 API (使用模組層級快取):
       phonetic = EnglishPhoneticSystem()
       
    2. 新版 API (使用 Backend 單例):
       from multi_language_corrector.backend import get_english_backend
       backend = get_english_backend()
       backend.initialize()
       phonetic = EnglishPhoneticSystem(backend=backend)
    """
    
    def __init__(self, backend=None):
        """
        初始化英文發音系統
        
        Args:
            backend: 可選的 EnglishPhoneticBackend 實例。
                     如果提供，將使用 Backend 的快取；
                     否則使用模組層級的 cached_ipa_convert() 快取。
        """
        self._backend = backend

    def to_phonetic(self, text: str) -> str:
        """
        將英文文本轉換為標準化的 IPA 音標字串

        處理流程:
        1. 展開縮寫 (如 IBM -> I B M, js -> J S)
        2. 展開數字 (如 1 -> one)
        3. 使用 phonemizer + espeak-ng 轉換為 IPA
        4. 移除空格，產生連續的音素序列以便比對

        Args:
            text: 輸入英文文本

        Returns:
            str: 處理後的 IPA 字串
        """
        # 常見的縮寫列表 (小寫形式)
        COMMON_ABBREVIATIONS = {
            "js", "ts", "py", "rb", "go", "rs", "cs", "db", "ml", "ai", 
            "ui", "ux", "api", "sql", "css", "xml", "sdk"
        }

        # 縮寫的啟發式處理:
        # 如果是全大寫且長度較短 (<=5)，視為縮寫，強制分開字母發音
        if text.isupper() and len(text) <= 5 and text.isalpha():
            text = " ".join(list(text))
        # 也處理常見的小寫縮寫 (如 js, py)
        elif text.lower() in COMMON_ABBREVIATIONS and text.isalpha():
            text = " ".join(list(text.upper()))
        
        # 簡單的數字正規化
        text = text.replace("0", "zero ").replace("1", "one ").replace("2", "two ")\
                   .replace("3", "three ").replace("4", "four ").replace("5", "five ")\
                   .replace("6", "six ").replace("7", "seven ").replace("8", "eight ")\
                   .replace("9", "nine ")

        # 使用 Backend 或模組層級快取進行 IPA 轉換
        try:
            if self._backend:
                # 新架構：使用 Backend 的快取
                result = self._backend.to_phonetic(text)
            else:
                # 舊架構：使用模組層級快取
                result = cached_ipa_convert(text)
        except RuntimeError:
            # phonemizer 不可用時，返回原文的小寫版本作為 fallback
            result = text.lower()
        
        # 移除空格以進行更寬鬆的模糊比對
        result = result.replace(" ", "")
            
        return result

    def are_fuzzy_similar(self, phonetic1: str, phonetic2: str) -> bool:
        """
        判斷兩個 IPA 字串是否模糊相似

        使用 Levenshtein 編輯距離計算相似度比率。

        Args:
            phonetic1: 第一個 IPA 字串
            phonetic2: 第二個 IPA 字串

        Returns:
            bool: 若 (編輯距離 / 最大長度) <= 容錯率，則返回 True
        """
        # 計算 Levenshtein 編輯距離
        dist = Levenshtein.distance(phonetic1, phonetic2)
        
        # 根據較長字串的長度進行正規化
        max_len = max(len(phonetic1), len(phonetic2))
        min_len = min(len(phonetic1), len(phonetic2))
        
        if max_len == 0:
            return True
        
        # 長度差異檢查：如果兩個字串長度差異超過 50%，不匹配
        if min_len > 0 and (max_len - min_len) / min_len > 0.5:
            return False
        
        ratio = dist / max_len
        tolerance = self.get_tolerance(max_len)
        
        # 額外檢查：首音素必須相同或相似
        if len(phonetic1) > 0 and len(phonetic2) > 0:
            if not self._are_first_phonemes_similar(phonetic1, phonetic2):
                tolerance = min(tolerance, 0.25)
        
        return ratio <= tolerance
    
    def _are_first_phonemes_similar(self, phonetic1: str, phonetic2: str) -> bool:
        """
        檢查兩個 IPA 字串的首音素是否相似
        """
        if not phonetic1 or not phonetic2:
            return True
            
        first1 = phonetic1[0]
        first2 = phonetic2[0]
        
        if first1 == first2:
            return True
        
        # 定義相似的首音素群組
        similar_groups = [
            {"p", "b"},           # 雙唇塞音
            {"t", "d"},           # 齒齦塞音
            {"k", "g"},           # 軟顎塞音
            {"f", "v"},           # 唇齒擦音
            {"s", "z"},           # 齒齦擦音
            {"θ", "ð"},           # 齒間擦音
            {"ʃ", "ʒ"},           # 後齒齦擦音
            {"ʧ", "ʤ", "t", "d"}, # 塞擦音
            {"m", "n", "ŋ"},      # 鼻音
            {"l", "r", "ɹ"},      # 流音 (espeak 用 ɹ 表示 r)
            {"w", "ʍ"},           # 滑音
            {"i", "ɪ", "e", "ɛ"}, # 前元音
            {"u", "ʊ", "o", "ɔ"}, # 後元音
            {"a", "ɑ", "æ", "ʌ"}, # 低元音/央元音
        ]
        
        for group in similar_groups:
            if first1 in group and first2 in group:
                return True
        
        return False

    def get_tolerance(self, length: int) -> float:
        """
        根據 IPA 字串長度動態調整容錯率

        Args:
            length: IPA 字串長度

        Returns:
            float: 容錯率閾值
        """
        if length <= 3:
            return 0.15  # 短詞非常嚴格
        if length <= 5:
            return 0.25  # 中詞
        if length <= 8:
            return 0.30  # 長詞
        return 0.35  # 超長詞

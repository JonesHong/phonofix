"""
日文語音後端 (JapanesePhoneticBackend)

負責 cutlet / fugashi 的初始化與快取管理。
實作為執行緒安全的單例模式，以保持 Backend → Engine → Corrector 架構一致。
"""

from __future__ import annotations

import threading
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

from phonofix.languages.japanese import JAPANESE_INSTALL_HINT

from .base import PhoneticBackend
from .stats import BackendStats, CacheStats

_instance: Optional["JapanesePhoneticBackend"] = None
_instance_lock = threading.Lock()

_cutlet_instance: Optional[Any] = None
_fugashi_tagger: Optional[Any] = None
_init_lock = threading.Lock()


def _strip_macrons(text: str) -> str:
    """
    移除羅馬字長音符號（macrons）。

    說明：
    - cutlet 產出的 romaji 可能包含 ā/ī/ū/ē/ō 等長音符號
    - 我們在 phonetic key 層面希望維持「只含 ASCII」的可比對字串
      （避免環境/輸入法導致同一讀音出現多種 Unicode 表示）
    """
    macrons = {
        "ā": "a",
        "ī": "i",
        "ū": "u",
        "ē": "e",
        "ō": "o",
        "â": "a",
        "î": "i",
        "û": "u",
        "ê": "e",
        "ô": "o",
    }
    for m, p in macrons.items():
        text = text.replace(m, p)
    return text


def _get_cutlet() -> Any:
    """
    取得 Cutlet 實例（Lazy Loading）。

    - 只在第一次呼叫時 import 並建立 cutlet.Cutlet()
    - 未安裝日文依賴時，丟出帶有安裝指引的 ImportError
    - 使用全域 singleton，避免重複初始化造成的效能浪費
    """
    global _cutlet_instance
    if _cutlet_instance is not None:
        return _cutlet_instance

    with _init_lock:
        if _cutlet_instance is not None:
            return _cutlet_instance
        try:
            import cutlet
        except ImportError as exc:
            raise ImportError(JAPANESE_INSTALL_HINT) from exc

        inst = cutlet.Cutlet()
        inst.use_foreign_spelling = False
        _cutlet_instance = inst
        return _cutlet_instance


def _get_fugashi() -> Any:
    """
    取得 fugashi.Tagger（Lazy Loading）。

    - fugashi 依賴詞典（例如 unidic-lite），初始化成本較高，因此以 singleton 共用
    - 未安裝日文依賴時，丟出帶有安裝指引的 ImportError
    """
    global _fugashi_tagger
    if _fugashi_tagger is not None:
        return _fugashi_tagger

    with _init_lock:
        if _fugashi_tagger is not None:
            return _fugashi_tagger
        try:
            import fugashi
        except ImportError as exc:
            raise ImportError(JAPANESE_INSTALL_HINT) from exc
        _fugashi_tagger = fugashi.Tagger()
        return _fugashi_tagger


@lru_cache(maxsize=50000)
def _cached_romaji(text: str) -> str:
    """
    快取：日文文本 -> romaji（羅馬拼音）

    流程：
    - cutlet.romaji() 取得羅馬字
    - 轉小寫、移除空白
    - 去除長音符號（macrons）以穩定化
    """
    if not text:
        return ""
    cutlet = _get_cutlet()
    romaji = (cutlet.romaji(text) or "").lower()
    romaji = romaji.replace(" ", "")
    romaji = _strip_macrons(romaji)
    return romaji


@lru_cache(maxsize=50000)
def _cached_tokens(text: str) -> Tuple[str, ...]:
    """
    快取：日文文本分詞結果（surface tokens）。

    用途：
    - JapaneseTokenizer 可能需要依賴 fugashi 的斷詞結果
    - 以 lru_cache 共用結果，降低重複 tokenize 的成本
    """
    if not text:
        return tuple()
    tagger = _get_fugashi()
    return tuple(word.surface for word in tagger(text))


class JapanesePhoneticBackend(PhoneticBackend):
    """
    日文語音後端（單例）。

    職責：
    - 管理 cutlet / fugashi 的 lazy import 與初始化
    - 提供 romaji 轉換與分詞 token 化
    - 提供快取統計與清理介面（利於除錯/觀測）

    設計取捨：
    - 以「backend 單例」承擔外部依賴初始化，讓 Engine/Corrector 維持輕量
    - romaji 與 tokens 使用 lru_cache（模組層級）共用，避免每個 Engine 各自快取造成碎片化
    """

    def __init__(self) -> None:
        """建立後端實例（請透過 `get_japanese_backend()` 取得單例）。"""
        self._initialized = False
        self._init_lock = threading.Lock()

    def initialize(self) -> None:
        """
        初始化 backend（執行緒安全）。

        - 會預熱 cutlet/fugashi 與快取
        - 多次呼叫不會重複初始化
        """
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            _ = _cached_romaji("テスト")
            _ = _cached_tokens("テスト")
            self._initialized = True

    def is_initialized(self) -> bool:
        """回傳 backend 是否已完成初始化。"""
        return self._initialized

    def to_phonetic(self, text: str) -> str:
        """
        將日文文本轉為 romaji（phonetic key）。

        注意：若尚未初始化，會自動初始化（以確保依賴可用）。
        """
        if not self._initialized:
            self.initialize()
        return _cached_romaji(text)

    def tokenize(self, text: str) -> list[str]:
        """
        將日文文本分詞為 surface token 列表。

        注意：這裡回傳的是 fugashi 的 surface，不做 reading/lemma 等進階資訊。
        """
        if not self._initialized:
            self.initialize()
        return list(_cached_tokens(text))

    def get_cutlet(self) -> Any:
        """取得 cutlet 實例（確保初始化後回傳）。"""
        if not self._initialized:
            self.initialize()
        return _get_cutlet()

    def get_tagger(self) -> Any:
        """取得 fugashi.Tagger（確保初始化後回傳）。"""
        if not self._initialized:
            self.initialize()
        return _get_fugashi()

    def get_cache_stats(self) -> BackendStats:
        """回傳統一格式的快取統計（romaji/tokens）。"""
        romaji_info = _cached_romaji.cache_info()
        tokens_info = _cached_tokens.cache_info()
        caches: dict[str, CacheStats] = {
            "romaji": {
                "hits": int(romaji_info.hits),
                "misses": int(romaji_info.misses),
                "currsize": int(romaji_info.currsize),
                "maxsize": int(romaji_info.maxsize or -1),
            },
            "tokens": {
                "hits": int(tokens_info.hits),
                "misses": int(tokens_info.misses),
                "currsize": int(tokens_info.currsize),
                "maxsize": int(tokens_info.maxsize or -1),
            },
        }
        return BackendStats(
            initialized=bool(self._initialized),
            lazy_init={"status": "not_supported"},
            caches=caches,
        )

    def clear_cache(self) -> None:
        """清除 romaji/tokens 的 lru_cache（主要用於測試或效能觀測）。"""
        _cached_romaji.cache_clear()
        _cached_tokens.cache_clear()


def get_japanese_backend() -> JapanesePhoneticBackend:
    """
    取得 `JapanesePhoneticBackend` 單例（執行緒安全）。

    設計理由：
    - cutlet/fugashi 的初始化成本不低，且可安全共用
    - 以單例避免在多個 Engine/Corrector 實例間重複初始化
    """
    global _instance
    if _instance is not None:
        return _instance
    with _instance_lock:
        if _instance is None:
            _instance = JapanesePhoneticBackend()
        return _instance

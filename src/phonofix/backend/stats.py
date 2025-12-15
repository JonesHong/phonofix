"""
Backend 統計資料結構（Backend Stats）

目的：
- 統一各語言 backend 的 `get_cache_stats()` 回傳格式，避免上層（Engine / tools / tests）
  需要針對不同語言寫分支邏輯。
- 提供「可觀測性」的共同語彙：例如 lazy initialization 狀態、錯誤資訊、快取命中等。

設計原則：
- 只使用標準庫型別（TypedDict / Literal），不引入額外依賴。
- 以「可演進」為導向：若未來需要新增欄位，保持向後相容（可選欄位或新增 cache name）。
"""

from __future__ import annotations

from typing import Literal, TypedDict


class CacheStats(TypedDict):
    """
    單一快取的統計資訊。

    欄位定義：
    - hits/misses: 命中/未命中次數（語意由 backend 自行定義，但需一致可比較）
    - currsize/maxsize: 當前大小/上限（無上限時可填 -1）
    """

    hits: int
    misses: int
    currsize: int
    maxsize: int


class LazyInitError(TypedDict):
    """lazy init 失敗時的錯誤資訊（供觀測/除錯）。"""

    exception_type: str
    exception_message: str
    traceback: str


LazyInitStatus = Literal["not_supported", "not_started", "running", "succeeded", "failed"]


class LazyInitStats(TypedDict, total=False):
    """
    lazy initialization 的可觀測狀態。

    說明：
    - status:
      - not_supported: backend 不支援 lazy init（或設計上不需要）
      - not_started/running/succeeded/failed: 英文 backend 的 initialize_lazy 狀態
    - started_at/finished_at: UTC ISO8601（字串），避免時區問題
    - duration_ms: 耗時（毫秒）
    - error: 失敗資訊（成功或尚未失敗時為 None）
    """

    status: LazyInitStatus
    started_at: str | None
    finished_at: str | None
    duration_ms: int | None
    error: LazyInitError | None


class BackendStats(TypedDict):
    """
    backend 統計總覽（統一回傳格式）。

    欄位：
    - initialized: backend 是否已完成 initialize()
    - lazy_init: lazy init 狀態（不支援時 status=not_supported）
    - caches: 多個快取統計（例如 english: ipa；chinese: pinyin/initials/...；japanese: romaji/tokens）
    """

    initialized: bool
    lazy_init: LazyInitStats
    caches: dict[str, CacheStats]


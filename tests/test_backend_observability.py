"""
Backend 可觀測性測試

目的：
- 確保 `initialize_lazy()` 不會「默默」失敗
- 失敗時至少能從 `get_cache_stats()` 讀到狀態與錯誤資訊

注意：
- 此測試不依賴 phonemizer/espeak-ng 是否安裝，改用 monkeypatch 模擬初始化失敗。
"""

from __future__ import annotations

import time


def test_english_backend_initialize_lazy_is_observable(monkeypatch):
    from phonofix.backend.english_backend import EnglishPhoneticBackend

    backend = EnglishPhoneticBackend()

    def boom() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(backend, "initialize", boom)

    backend.initialize_lazy()

    # 等待背景執行緒把狀態寫回（輪詢，避免 sleep 固定太久）
    status = None
    for _ in range(200):
        status = backend.get_cache_stats()["lazy_init"]["status"]
        if status in ("failed", "succeeded"):
            break
        time.sleep(0.01)

    assert status == "failed"
    err = backend.get_cache_stats()["lazy_init"]["error"]
    assert err is not None
    assert err["exception_type"] == "RuntimeError"
    assert "boom" in err["exception_message"]


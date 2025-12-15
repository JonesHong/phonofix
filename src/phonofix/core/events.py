"""
事件模型（Event Model）

本專案的 corrector 預設不應直接輸出到 stdout。
若需要取得「本次替換了哪些片段」等資訊，請使用事件回呼（event handler）。

設計原則：
- Production favors availability：允許降級，但不允許「默默」降級。
- Evaluation favors detectability：評估/CI 模式下遇到錯誤應直接 fail。
"""

from __future__ import annotations

from typing import Callable, Literal, TypedDict


class CorrectionEvent(TypedDict, total=False):
    """
    修正事件資料結構（TypedDict, total=False）。

    用途：
    - Engine.create_corrector(on_event=...) 的 callback 會收到此事件
    - 用於記錄「替換內容」「降級狀態」「候選生成錯誤」等資訊，方便串接觀測/除錯

    設計說明：
    - `total=False` 表示事件欄位是「依 event.type 選填」
      例如 replacement 事件會有 start/end/original/replacement；degraded 事件則會有 degrade_reason 等。
    """
    type: Literal["replacement", "fuzzy_error", "degraded", "warning"]
    engine: str
    trace_id: str

    # replacement
    start: int
    end: int
    original: str
    replacement: str
    canonical: str
    alias: str
    score: float
    has_context: bool

    # pipeline / diagnostics
    stage: Literal["candidate_gen", "scoring", "normalize"]
    fallback: Literal["exact_only", "none"]
    degrade_reason: str
    exception_type: str
    exception_message: str


CorrectionEventHandler = Callable[[CorrectionEvent], None]

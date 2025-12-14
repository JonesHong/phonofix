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

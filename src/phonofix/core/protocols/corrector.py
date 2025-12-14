"""
Corrector Protocols

定義所有修正器必須實作的最小介面（Structural Subtyping）。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class CorrectorProtocol(Protocol):
    """
    修正器協議 (Corrector Protocol)

    最小介面：
    - correct(text) -> str
    """

    def correct(
        self,
        text: str,
        full_context: str | None = None,
        silent: bool = False,
        *,
        mode: str | None = None,
        fail_policy: str = "degrade",
        trace_id: str | None = None,
    ) -> str:
        """修正文本（可選完整上下文/靜默模式）"""
        ...


@runtime_checkable
class ContextAwareCorrectorProtocol(CorrectorProtocol, Protocol):
    """
    上下文感知修正器協議

    用於支援傳入完整上下文，以進行更準確的判斷（例如 keywords / exclude_when）。
    """
    pass

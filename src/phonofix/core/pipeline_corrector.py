"""
Corrector pipeline base class

目的：
- 將「correct() 管線編排」抽到 core，避免三語言 corrector.py 重複膨脹
- 將 fail_policy/mode/trace_id/事件降級流程一致化

設計：
- 以 ABC 定義必要的管線步驟（候選生成/計分/衝突解決/替換套用）
- 各語言只需要專注在「如何產生 drafts、如何計分」等差異化邏輯
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any

from phonofix.utils.logger import TimingContext


class PipelineCorrectorBase(ABC):
    """
    Corrector pipeline base

    子類必須提供：
    - 保護詞遮罩
    - exact/fuzzy drafts 生成
    - drafts 計分、衝突解決、替換套用
    - 事件 emission（fuzzy_error/degraded/replacement）
    """

    _pipeline_name: str = "Corrector.correct"

    @abstractmethod
    def _build_protection_mask(self, text: str) -> set[int]:
        """
        建立保護遮罩。

        子類應回傳「不可被替換」的字元索引集合（通常是 0-based），
        用於避免 protected_terms 或其他規則被候選生成/替換套用誤傷。
        """
        ...

    @abstractmethod
    def _generate_exact_candidate_drafts(
        self, text: str, context: str, protected_indices: set[int]
    ) -> list[dict[str, Any]]:
        """
        產生精準命中（exact-match）的候選草稿。

        典型作法：
        - 用 Aho-Corasick / index 快速找到 alias 命中
        - 對命中結果建 draft（包含 start/end/original/replacement 等必要欄位）
        """
        ...

    @abstractmethod
    def _generate_fuzzy_candidate_drafts(
        self, text: str, context: str, protected_indices: set[int]
    ) -> list[dict[str, Any]]:
        """
        產生模糊命中（fuzzy-match）的候選草稿。

        注意：
        - 這一步可能會依賴外部 backend（例如 phonemizer/espeak-ng）或較重的計算
        - PipelineCorrectorBase 會對此步驟提供 fail_policy 降級/拋錯機制
        """
        ...

    @abstractmethod
    def _score_candidate_drafts(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        對候選草稿進行計分，回傳可比較的 candidates。

        約定：
        - candidates 應包含足夠資訊供 conflict resolver 排序/去衝突
        - 分數方向（越大越好或越小越好）需與 resolver 一致
        """
        ...

    @abstractmethod
    def _resolve_conflicts(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        解決候選衝突，回傳最後要套用的 candidates。

        常見衝突：
        - span 重疊
        - 同一 span 多個候選
        """
        ...

    @abstractmethod
    def _apply_replacements(
        self,
        text: str,
        candidates: list[dict[str, Any]],
        silent: bool = False,
        *,
        trace_id: str | None = None,
    ) -> str:
        """
        將 candidates 套用到 text 上並回傳結果。

        建議實作：
        - 以「重建字串」或「由後往前替換」避免索引偏移
        - 在必要時透過 emit_replacement 送出事件（由子類決定）
        """
        ...

    @abstractmethod
    def _emit_pipeline_event(self, event: dict[str, Any], *, silent: bool) -> None:
        """
        發送 pipeline 事件（例如 fuzzy_error / degraded）。

        子類通常會把事件交給 Engine.create_corrector(on_event=...) 的 callback，
        或在 verbose 模式下寫入 logger。
        """
        ...

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
        """
        執行通用修正管線。

        參數約定：
        - `full_context`：提供完整上下文（例如 ASR 句子）；若未提供則以 text 作為 context
        - `mode`：快捷模式（evaluation=raise、production=degrade）
        - `fail_policy`：fuzzy 步驟失敗時的策略（raise 或 degrade）
        - `trace_id`：事件追蹤 ID（若未提供會自動產生）

        流程：
        1) 建立保護遮罩
        2) 產生 exact drafts
        3) 產生 fuzzy drafts（可降級）
        4) 計分
        5) 去衝突
        6) 套用替換
        """
        if not text:
            return text

        with TimingContext(self._pipeline_name, self._logger, logging.DEBUG):
            context = full_context if full_context is not None else text
            protected_indices = self._build_protection_mask(text)

            if mode == "evaluation":
                fail_policy = "raise"
            elif mode == "production":
                fail_policy = "degrade"

            trace_id_value = trace_id or uuid.uuid4().hex

            drafts: list[dict[str, Any]] = []
            drafts.extend(self._generate_exact_candidate_drafts(text, context, protected_indices))

            try:
                drafts.extend(self._generate_fuzzy_candidate_drafts(text, context, protected_indices))
            except Exception as exc:
                self._emit_pipeline_event(
                    {
                        "type": "fuzzy_error",
                        "engine": getattr(getattr(self, "_engine", None), "_engine_name", "unknown"),
                        "trace_id": trace_id_value,
                        "stage": "candidate_gen",
                        "fallback": "none" if fail_policy == "raise" else "exact_only",
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    },
                    silent=silent,
                )
                if fail_policy == "raise":
                    raise
                self._emit_pipeline_event(
                    {
                        "type": "degraded",
                        "engine": getattr(getattr(self, "_engine", None), "_engine_name", "unknown"),
                        "trace_id": trace_id_value,
                        "stage": "candidate_gen",
                        "fallback": "exact_only",
                        "degrade_reason": "fuzzy_error",
                    },
                    silent=silent,
                )
                if not silent:
                    self._logger.exception("產生 fuzzy 候選失敗，降級為 exact-only")

            candidates = self._score_candidate_drafts(drafts)
            final_candidates = self._resolve_conflicts(candidates)
            return self._apply_replacements(text, final_candidates, silent=silent, trace_id=trace_id_value)

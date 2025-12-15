"""
中文修正器模組

實作針對中文拼寫錯誤的修正邏輯（常見來源包含 ASR/LLM/手動輸入）。
核心演算法基於拼音相似度 (Pinyin Similarity) 與編輯距離 (Levenshtein Distance)。

本檔案定位）：
- `ChineseCorrector` 只負責「管線編排 + 事件輸出 + 索引初始化」
- 具體的索引/規則/計分/候選生成/替換套用拆到同目錄模組，避免單檔肥大

使用方式:
    from phonofix import ChineseEngine

    engine = ChineseEngine()
    corrector = engine.create_corrector({'台北車站': ['北車', '台北站']})
    result = corrector.correct('我在北車等你')

注意（依賴與效能）：
- 此檔案不直接 import `pypinyin`；拼音計算與快取由 `ChinesePhoneticBackend` 管理
- `pypinyin` 會在 backend 首次實際使用時才被延遲載入（避免非中文使用者被迫安裝依賴）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from phonofix.core.events import CorrectionEventHandler
from phonofix.core.pipeline_corrector import PipelineCorrectorBase
from phonofix.utils.aho_corasick import AhoCorasick
from phonofix.utils.logger import get_logger

from . import candidates as candidate_ops
from . import filters as filter_ops
from . import indexing as indexing_ops
from . import replacements as replacement_ops

if TYPE_CHECKING:
    from phonofix.languages.chinese.engine import ChineseEngine


class ChineseCorrector(PipelineCorrectorBase):
    """
    中文修正器

    功能:
    - 載入專有名詞庫並建立搜尋索引
    - 針對輸入文本進行滑動視窗掃描
    - 結合拼音模糊比對與上下文關鍵字驗證
    - 修正同音異字或近音字造成的拼寫錯誤

    建立方式:
        使用 ChineseEngine.create_corrector() 建立實例
    """

    _pipeline_name = "ChineseCorrector.correct"

    # =============================================================================
    # 建構/初始化（由 Engine 呼叫）
    # =============================================================================

    @classmethod
    def _from_engine(
        cls,
        engine: "ChineseEngine",
        term_mapping: Dict[str, Dict],
        protected_terms: Optional[set] = None,
        on_event: Optional[CorrectionEventHandler] = None,
    ) -> "ChineseCorrector":
        """
        由 ChineseEngine 調用的內部工廠方法

        此方法使用 Engine 提供的共享元件，避免重複初始化。

        Args:
            engine: ChineseEngine 實例
            term_mapping: 正規化的專有名詞映射
            protected_terms: 受保護的詞彙集合 (這些詞不會被修正)

        Returns:
            ChineseCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance._logger = get_logger("corrector.chinese")
        instance.phonetic = engine.phonetic
        instance.tokenizer = engine.tokenizer
        instance.config = engine.config
        instance.utils = engine.utils
        instance.use_canonical = True
        instance.protected_terms = protected_terms or set()
        instance._on_event = on_event
        instance._exact_matcher = None
        instance._exact_items_by_alias = {}
        instance._protected_matcher = None
        instance._fuzzy_buckets = {}

        if instance.protected_terms:
            # 使用 Aho-Corasick 建立 protected term matcher：
            # - 目的：快速標記 text 中不應被替換的 span
            # - 若 protected_terms 為空，整段 pipeline 會直接跳過（避免額外開銷）
            matcher: AhoCorasick[str] = AhoCorasick()
            for term in instance.protected_terms:
                if term:
                    matcher.add(term, term)
            matcher.build()
            instance._protected_matcher = matcher

        # =============================================================================
        # 索引建立（一次性）：search_index / exact matcher / fuzzy buckets
        # =============================================================================
        instance.search_index = indexing_ops.build_search_index(
            engine=engine,
            utils=instance.utils,
            term_mapping=term_mapping,
        )
        instance._exact_matcher, instance._exact_items_by_alias = indexing_ops.build_exact_matcher(instance.search_index)
        instance._fuzzy_buckets = indexing_ops.build_fuzzy_buckets(
            search_index=instance.search_index,
            config=instance.config,
        )
        return instance

    # =============================================================================
    # 事件輸出（由 core pipeline 呼叫）
    # =============================================================================

    def _emit_replacement(self, candidate: Dict[str, Any], *, silent: bool, trace_id: str | None) -> None:
        """
        發送 replacement 事件（並在非 silent 模式輸出日誌）。

        說明：
        - 此方法會把候選資訊整理成統一事件格式，交給 `on_event` callback
        - 日誌只在「實際有替換」時輸出，避免噪音
        """
        event = {
            "type": "replacement",
            "engine": getattr(self._engine, "_engine_name", "chinese"),
            "trace_id": trace_id,
            "start": candidate.get("start"),
            "end": candidate.get("end"),
            "original": candidate.get("original"),
            "replacement": candidate.get("replacement"),
            "canonical": candidate.get("canonical"),
            "alias": candidate.get("alias"),
            "score": candidate.get("score"),
            "has_context": candidate.get("has_context", False),
        }

        try:
            if self._on_event is not None:
                self._on_event(event)
        except Exception:
            if not silent:
                self._logger.exception("on_event 回呼執行失敗")

        if not silent and candidate.get("original") != candidate.get("replacement"):
            tag = "上下文命中" if candidate.get("has_context") else "發音修正"
            self._logger.info(
                f"[{tag}] '{candidate.get('original')}' -> '{candidate.get('replacement')}' "
                f"(Score: {candidate.get('score'):.3f})"
            )

    def _emit_pipeline_event(self, event: Dict[str, Any], *, silent: bool) -> None:
        """
        發送 pipeline 事件（例如 fuzzy_error / degraded）。

        PipelineCorrectorBase 會在 fuzzy 產生失敗時呼叫此方法，
        讓外部可以用一致的方式觀測降級狀態與錯誤原因。
        """
        try:
            if self._on_event is not None:
                self._on_event(event)
        except Exception:
            if not silent:
                self._logger.exception("on_event 回呼執行失敗")

    # =============================================================================
    # Pipeline steps（委派到拆分模組）
    # =============================================================================

    def _build_protection_mask(self, text: str) -> set[int]:
        """建立 protected_terms 的保護遮罩（避免替換到受保護區段）。"""
        return filter_ops.build_protection_mask(
            text=text,
            protected_terms=self.protected_terms,
            protected_matcher=self._protected_matcher,
        )

    def _generate_exact_candidate_drafts(
        self, text: str, context: str, protected_indices: set[int]
    ) -> list[dict[str, Any]]:
        """產生 exact-match 候選草稿（委派給 candidates 模組）。"""
        return candidate_ops.generate_exact_candidate_drafts(
            text=text,
            context=context,
            protected_indices=protected_indices,
            exact_matcher=self._exact_matcher,
            exact_items_by_alias=self._exact_items_by_alias,
            protected_terms=self.protected_terms,
        )

    def _generate_fuzzy_candidate_drafts(
        self, text: str, context: str, protected_indices: set[int]
    ) -> list[dict[str, Any]]:
        """產生 fuzzy-match 候選草稿（委派給 candidates 模組，含分桶剪枝）。"""
        return candidate_ops.generate_fuzzy_candidate_drafts(
            text=text,
            context=context,
            protected_indices=protected_indices,
            fuzzy_buckets=self._fuzzy_buckets,
            config=self.config,
            engine=self._engine,
            utils=self.utils,
            protected_terms=self.protected_terms,
        )

    def _score_candidate_drafts(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """對候選草稿計分（委派給 candidates 模組）。"""
        return candidate_ops.score_candidate_drafts(drafts=drafts, use_canonical=bool(self.use_canonical))

    def _resolve_conflicts(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """解決候選衝突（委派給 replacements 模組）。"""
        return replacement_ops.resolve_conflicts(candidates=candidates)

    def _apply_replacements(
        self,
        text: str,
        candidates: list[dict[str, Any]],
        silent: bool = False,
        *,
        trace_id: str | None = None,
    ) -> str:
        """套用候選替換並輸出事件/日誌（委派給 replacements 模組）。"""
        return replacement_ops.apply_replacements(
            text=text,
            final_candidates=candidates,
            emit_replacement=self._emit_replacement,
            silent=silent,
            trace_id=trace_id,
        )

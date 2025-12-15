"""
英文修正器模組

實作基於滑動視窗 (Sliding Window) 與語音相似度的英文專有名詞修正。

本檔案定位：
- `EnglishCorrector` 只負責「管線編排 + 事件輸出 + 索引初始化」
- 具體的索引/規則/計分/候選生成/替換套用拆到同目錄模組，避免單檔肥大

使用方式:
    from phonofix import EnglishEngine

    engine = EnglishEngine()
    corrector = engine.create_corrector({'Python': ['Pyton', 'Pyson']})
    result = corrector.correct('I use Pyton for ML')

注意（依賴與效能）：
- 此檔案不直接 import `phonemizer` / `espeak-ng`；IPA 計算與快取由 `EnglishPhoneticBackend` 管理
- backend 會在 Engine 初始化時完成必要的初始化（並提供 batch IPA 計算能力）
- corrector 的 fuzzy 掃描另做分桶 pruning，避免相似度計算退化成 O(windows * items)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from phonofix.core.events import CorrectionEventHandler
from phonofix.core.pipeline_corrector import PipelineCorrectorBase
from phonofix.utils.aho_corasick import AhoCorasick
from phonofix.utils.logger import get_logger

from . import candidates as candidate_ops
from . import filters as filter_ops
from . import indexing as indexing_ops
from . import replacements as replacement_ops

if TYPE_CHECKING:
    from phonofix.languages.english.engine import EnglishEngine


class EnglishCorrector(PipelineCorrectorBase):
    """
    英文修正器

    功能:
    - 針對英文文本進行專有名詞修正
    - 使用滑動視窗掃描文本
    - 結合 IPA 發音相似度進行模糊比對
    - 支援自動生成常見分割/聽寫變體
    - 支援 keywords 條件過濾 (需要上下文關鍵字才替換)
    - 支援 exclude_when 上下文排除 (看到排除詞時不替換)

    建立方式:
        使用 EnglishEngine.create_corrector() 建立實例
    """

    _pipeline_name = "EnglishCorrector.correct"

    # =============================================================================
    # 建構/初始化（由 Engine 呼叫）
    # =============================================================================

    @classmethod
    def _from_engine(
        cls,
        engine: "EnglishEngine",
        term_mapping: Dict[str, Dict],
        protected_terms: set[str] | None = None,
        on_event: CorrectionEventHandler | None = None,
    ) -> "EnglishCorrector":
        """
        從 Engine 建立輕量 Corrector 實例 (內部方法)

        Args:
            engine: EnglishEngine 實例
            term_mapping: 正規化的專有名詞映射 (canonical -> config dict)

        Returns:
            EnglishCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance._logger = get_logger("corrector.english")
        instance.phonetic = engine.phonetic
        instance.tokenizer = engine.tokenizer
        instance.protected_terms = protected_terms or set()
        instance._on_event = on_event

        instance._exact_matcher = None
        instance._exact_items_by_alias = {}
        instance._protected_matcher = None
        instance._fuzzy_buckets = {}

        if instance.protected_terms:
            # 使用 Aho-Corasick 建立 protected term matcher：
            # - 目的：快速標記 text 中不應被替換的 span
            matcher: AhoCorasick[str] = AhoCorasick()
            for term in instance.protected_terms:
                if term:
                    matcher.add(term, term)
            matcher.build()
            instance._protected_matcher = matcher

        # 供測試/除錯使用：alias -> canonical 的映射
        instance.term_mapping = {
            alias: canonical
            for canonical, config in term_mapping.items()
            for alias in config.get("aliases", [])
        }

        # =============================================================================
        # 索引建立（一次性）：search_index / exact matcher / fuzzy buckets
        # =============================================================================
        instance.search_index = indexing_ops.build_search_index(
            engine=engine,
            tokenizer=instance.tokenizer,
            term_mapping=term_mapping,
        )
        instance._exact_matcher, instance._exact_items_by_alias = indexing_ops.build_exact_matcher(instance.search_index)
        instance._fuzzy_buckets = indexing_ops.build_fuzzy_buckets(
            search_index=instance.search_index,
            config=engine.config,
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
            "engine": getattr(self._engine, "_engine_name", "english"),
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

        此方法的存在目的是讓 PipelineCorrectorBase 能以一致方式通知外部：
        - 發生了什麼錯誤
        - 採取了什麼降級策略
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
            tokenizer=self.tokenizer,
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
            tokenizer=self.tokenizer,
            backend=self._engine.backend,
            phonetic=self.phonetic,
            fuzzy_buckets=self._fuzzy_buckets,
            protected_terms=self.protected_terms,
        )

    def _score_candidate_drafts(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """對候選草稿計分（委派給 candidates 模組）。"""
        return candidate_ops.score_candidate_drafts(drafts=drafts)

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
            candidates=candidates,
            emit_replacement=self._emit_replacement,
            logger=self._logger,
            silent=silent,
            trace_id=trace_id,
        )

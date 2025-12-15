"""
日文修正引擎 (JapaneseEngine)

負責持有共享的日文語音系統、分詞器與模糊生成器，
並提供工廠方法建立輕量的 JapaneseCorrector 實例。
"""

from typing import Any, Callable, Dict, List, Optional

from phonofix.core.engine_interface import CorrectorEngine
from phonofix.core.events import CorrectionEventHandler
from phonofix.core.term_config import TermDictInput, normalize_term_dict
from phonofix.backend import JapanesePhoneticBackend, get_japanese_backend

from .config import JapanesePhoneticConfig
from .corrector import JapaneseCorrector
from .fuzzy_generator import JapaneseFuzzyGenerator
from .phonetic_impl import JapanesePhoneticSystem
from .tokenizer import JapaneseTokenizer


class JapaneseEngine(CorrectorEngine):
    """
    日文修正引擎。

    職責：
    - 持有日文 backend（cutlet/fugashi）與其快取
    - 建立 phonetic system / tokenizer / fuzzy generator 等共享元件
    - 將使用者輸入的 term_dict 正規化後，建立輕量的 JapaneseCorrector

    設計重點：
    - backend 單例負責外部依賴初始化，Engine 只做組裝與策略控制
    - corrector 實例保持輕量，便於建立多組字典（多 domain）
    """

    _engine_name = "japanese"

    def __init__(
        self,
        phonetic_config: Optional[JapanesePhoneticConfig] = None,
        *,
        enable_surface_variants: bool = True,
        enable_representative_variants: bool = False,
        verbose: bool = False,
        on_timing: Optional[Callable[[str, float], None]] = None,
    ):
        """
        初始化 JapaneseEngine。

        Args:
            phonetic_config: 日文語音設定（未提供則使用預設 JapanesePhoneticConfig）
            enable_surface_variants: 是否自動生成表面變體（平/片假名、romaji 規則等）
            enable_representative_variants: 是否啟用更激進的代表變體（預設關閉）
            verbose: 是否輸出較多日誌
            on_timing: 可選的計時回呼（利於效能觀測）
        """
        self._init_logger(verbose=verbose, on_timing=on_timing)

        with self._log_timing("JapaneseEngine.__init__"):
            self._backend: JapanesePhoneticBackend = get_japanese_backend()
            self._backend.initialize()

            self._phonetic = JapanesePhoneticSystem(backend=self._backend)
            self._tokenizer = JapaneseTokenizer(backend=self._backend)
            self._phonetic_config = phonetic_config or JapanesePhoneticConfig()
            self._enable_surface_variants = enable_surface_variants
            self._fuzzy_generator = JapaneseFuzzyGenerator(
                config=self._phonetic_config,
                backend=self._backend,
                enable_representative_variants=enable_representative_variants,
            )

            self._initialized = True
            self._logger.info("JapaneseEngine initialized")

    @property
    def phonetic(self) -> JapanesePhoneticSystem:
        """取得日文發音系統（romaji 轉換與相似度）。"""
        return self._phonetic

    @property
    def tokenizer(self) -> JapaneseTokenizer:
        """取得日文分詞器（透過 backend tokenize）。"""
        return self._tokenizer

    @property
    def fuzzy_generator(self) -> JapaneseFuzzyGenerator:
        """取得日文模糊變體生成器（surface variants）。"""
        return self._fuzzy_generator

    @property
    def config(self) -> JapanesePhoneticConfig:
        """取得日文語音設定（phonetic config）。"""
        return self._phonetic_config

    def is_initialized(self) -> bool:
        """檢查 Engine 與 backend 是否已完成初始化。"""
        return getattr(self, "_initialized", False) and self._backend.is_initialized()

    def get_backend_stats(self) -> Dict[str, Any]:
        """取得 backend 快取統計（romaji/tokens）。"""
        return self._backend.get_cache_stats()

    def create_corrector(
        self,
        term_dict: TermDictInput,
        protected_terms: Optional[List[str]] = None,
        on_event: Optional[CorrectionEventHandler] = None,
        **kwargs,
    ) -> JapaneseCorrector:
        """
        依據 term_dict 建立 JapaneseCorrector。

        Args:
            term_dict: 使用者輸入的字典（支援簡寫格式與完整 config 格式）
            protected_terms: 不可被替換的保護詞彙（避免誤修）
            on_event: 可選事件回呼（replacement/degraded/fuzzy_error）

        Returns:
            JapaneseCorrector: 輕量 corrector 實例
        """
        normalized_input = normalize_term_dict(term_dict)

        normalized_mapping = {}
        for term, value in normalized_input.items():
            normalized_value = self._normalize_term_value(term, value)
            if normalized_value:
                normalized_mapping[term] = normalized_value

        protected_set = set(protected_terms) if protected_terms else None
        return JapaneseCorrector._from_engine(
            engine=self,
            term_mapping=normalized_mapping,
            protected_terms=protected_set,
            on_event=on_event,
        )

    def _normalize_term_value(self, term: str, value: Any) -> Optional[Dict[str, Any]]:
        """
        將 term_dict 的 value 正規化為 internal config dict。

        主要工作：
        - 統一 aliases / keywords / exclude_when / weight 欄位
        - 產生 surface variants（可由 enable_surface_variants 控制）
        - 以 phonetic key（romaji）去重 aliases，避免字典膨脹
        """
        if isinstance(value, list):
            value = {"aliases": value}
        elif isinstance(value, dict):
            if "aliases" not in value:
                value = {**value, "aliases": []}
        else:
            value = {"aliases": []}

        merged_aliases = list(value.get("aliases", []))

        if self._enable_surface_variants:
            max_variants = int(value.get("max_variants", 30) or 30)
            with self._log_timing(f"generate_variants({term})"):
                fuzzy_variants = self._fuzzy_generator.generate_variants(term, max_variants=max_variants)
            merged_aliases.extend(list(fuzzy_variants))

        max_variants = int(value.get("max_variants", 30) or 30)
        value["aliases"] = self._filter_aliases_by_phonetic(merged_aliases, canonical=term)[:max_variants]

        if value["aliases"]:
            self._logger.debug(
                f"  [Variants] {term} -> {value['aliases'][:5]}{'...' if len(value['aliases']) > 5 else ''}"
            )

        return {
            "aliases": value["aliases"],
            "keywords": value.get("keywords", []),
            "exclude_when": value.get("exclude_when", []),
            "weight": value.get("weight", 1.0),
        }

    def _filter_aliases_by_phonetic(self, aliases: List[str], *, canonical: str) -> List[str]:
        """
        依 phonetic key（romaji）去重 aliases。

        規則：
        - 排除空字串與 canonical 本身
        - phonetic key 相同只保留第一個（依原本順序）
        """
        seen = set()
        deduped: List[str] = []
        for alias in aliases:
            if not alias or alias == canonical:
                continue
            key = self._phonetic.to_phonetic(alias)
            if not key or key in seen:
                continue
            deduped.append(alias)
            seen.add(key)
        return deduped

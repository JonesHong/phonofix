"""
英文修正引擎 (EnglishEngine)

負責持有共享的英文語音系統、分詞器和模糊生成器，
並提供工廠方法建立輕量的 EnglishCorrector 實例。
"""

from typing import Any, Callable, Dict, Optional

from phonofix.backend import EnglishPhoneticBackend, get_english_backend
from phonofix.core.engine_interface import CorrectorEngine
from phonofix.core.events import CorrectionEventHandler
from phonofix.core.term_config import TermDictInput, normalize_term_dict

from .config import EnglishPhoneticConfig
from .corrector import EnglishCorrector
from .fuzzy_generator import EnglishFuzzyGenerator
from .phonetic_impl import EnglishPhoneticSystem
from .tokenizer import EnglishTokenizer


class EnglishEngine(CorrectorEngine):
    """
    英文修正引擎。

    職責：
    - 持有英文 phonetic backend（phonemizer + espeak-ng）與其快取
    - 建立 phonetic system / tokenizer / fuzzy generator 等共享元件
    - 將使用者輸入的 term_dict 正規化後，建立輕量的 EnglishCorrector

    設計重點：
    - backend 以單例管理初始化與快取，避免多個 Engine 重複初始化
    - corrector 實例保持輕量，可快速建立多組字典（多 tenant / 多 domain）
    """

    _engine_name = "english"

    def __init__(
        self,
        phonetic_config: Optional[EnglishPhoneticConfig] = None,
        *,
        enable_surface_variants: bool = True,
        enable_representative_variants: bool = False,
        verbose: bool = False,
        on_timing: Optional[Callable[[str, float], None]] = None,
    ):
        """
        初始化 EnglishEngine。

        Args:
            phonetic_config: 英文語音設定（未提供則使用預設 EnglishPhoneticConfig）
            enable_surface_variants: 是否自動生成表面變體（常見拼寫/分隔/縮寫）
            enable_representative_variants: 是否啟用代表字/更激進的變體（預設關閉）
            verbose: 是否輸出較多日誌
            on_timing: 可選的計時回呼（利於效能觀測）
        """
        self._init_logger(verbose=verbose, on_timing=on_timing)

        with self._log_timing("EnglishEngine.__init__"):
            self._backend: EnglishPhoneticBackend = get_english_backend()
            self._backend.initialize()

            self._phonetic = EnglishPhoneticSystem(backend=self._backend)
            self._tokenizer = EnglishTokenizer()
            self._phonetic_config = phonetic_config or EnglishPhoneticConfig
            self._enable_surface_variants = enable_surface_variants
            self._fuzzy_generator = EnglishFuzzyGenerator(
                config=self._phonetic_config,
                backend=self._backend,
                enable_representative_variants=enable_representative_variants,
            )

            self._initialized = True
            self._logger.info("EnglishEngine initialized")

    @property
    def phonetic(self) -> EnglishPhoneticSystem:
        """取得英文發音系統（IPA 轉換與相似度）。"""
        return self._phonetic

    @property
    def tokenizer(self) -> EnglishTokenizer:
        """取得英文分詞器（用於滑動視窗與邊界判斷）。"""
        return self._tokenizer

    @property
    def fuzzy_generator(self) -> EnglishFuzzyGenerator:
        """取得英文模糊變體生成器（用於 auto-variants 擴充）。"""
        return self._fuzzy_generator

    @property
    def config(self) -> EnglishPhoneticConfig:
        """取得英文語音設定（phonetic config）。"""
        return self._phonetic_config

    @property
    def backend(self) -> EnglishPhoneticBackend:
        """取得英文語音 backend（進階用途：快取/批次 IPA 等）。"""
        return self._backend

    def is_initialized(self) -> bool:
        """檢查 Engine 與 backend 是否已完成初始化。"""
        return self._initialized and self._backend.is_initialized()

    def get_backend_stats(self) -> Dict[str, Any]:
        """取得 backend 快取統計（hits/misses/size）。"""
        return self._backend.get_cache_stats()

    def create_corrector(
        self,
        term_dict: TermDictInput,
        protected_terms: Optional[list[str]] = None,
        on_event: Optional[CorrectionEventHandler] = None,
        **kwargs,
    ) -> EnglishCorrector:
        """
        依據 term_dict 建立 EnglishCorrector。

        Args:
            term_dict: 使用者輸入的字典（支援簡寫格式與完整 config 格式）
            protected_terms: 不可被替換的保護詞彙（避免誤修）
            on_event: 可選事件回呼（replacement/degraded/fuzzy_error）

        Returns:
            EnglishCorrector: 輕量 corrector 實例
        """
        with self._log_timing("EnglishEngine.create_corrector"):
            protected_set = set(protected_terms) if protected_terms else None
            normalized_input = normalize_term_dict(term_dict)

            normalized_dict = {}
            for term, value in normalized_input.items():
                normalized_value = self._normalize_term_value(term, value)
                if normalized_value:
                    normalized_dict[term] = normalized_value

            self._logger.debug(f"Creating corrector with {len(normalized_dict)} terms")

            cache_stats = self._backend.get_cache_stats()
            ipa_stats = cache_stats["caches"].get("ipa", {"hits": 0, "misses": 0, "currsize": 0, "maxsize": -1})
            hit_rate = ipa_stats["hits"] / max(1, ipa_stats["hits"] + ipa_stats["misses"]) * 100
            self._logger.debug(
                f"  [Cache] ipa: hits={ipa_stats['hits']}, misses={ipa_stats['misses']}, "
                f"rate={hit_rate:.1f}%, size={ipa_stats['currsize']}"
            )

            return EnglishCorrector._from_engine(
                engine=self,
                term_mapping=normalized_dict,
                protected_terms=protected_set,
                on_event=on_event,
            )

    def _normalize_term_value(self, term: str, value: Any) -> Optional[Dict[str, Any]]:
        """
        將 term_dict 的 value 正規化為 internal config dict。

        主要工作：
        - 統一 aliases / keywords / exclude_when / weight 欄位
        - 產生 auto surface variants（可由 enable_surface_variants 控制）
        - 以 IPA 去重 aliases，避免字典膨脹（同音不同寫只留一份）
        """
        if isinstance(value, list):
            value = {"aliases": value}
        elif isinstance(value, dict):
            if "aliases" not in value:
                value = {**value, "aliases": []}
        else:
            value = {"aliases": []}

        ipa = self._backend.to_phonetic(term)
        self._logger.debug(f"  [IPA] {term} -> {ipa}")

        if self._enable_surface_variants:
            max_variants = int(value.get("max_variants", 30) or 30)
            with self._log_timing(f"generate_variants({term})"):
                auto_variants = self._fuzzy_generator.generate_variants(term, max_variants=max_variants)

            current_aliases = set(value["aliases"])
            for variant in auto_variants:
                if variant != term and variant not in current_aliases:
                    value["aliases"].append(variant)
                    current_aliases.add(variant)

        max_variants = int(value.get("max_variants", 30) or 30)
        value["aliases"] = self._filter_aliases_by_phonetic(value["aliases"])[:max_variants]

        if value["aliases"]:
            self._logger.debug(
                f"  [Variants] {term} -> {value['aliases'][:5]}{'...' if len(value['aliases']) > 5 else ''}"
            )

        return {
            "aliases": value["aliases"],
            "keywords": value.get("keywords", []),
            "exclude_when": value.get("exclude_when", []),
            "weight": value.get("weight", 0.0),
        }

    def _filter_aliases_by_phonetic(self, aliases: list[str]) -> list[str]:
        """
        依 IPA 去重 aliases（保留第一個出現的拼寫）。

        目的：
        - 避免 auto-variants 造成字典過度膨脹
        - 在 phonetic 維度相同的 aliases 中保留一個代表
        """
        if not aliases:
            return []

        ipa_map = self._backend.to_phonetic_batch(aliases)
        seen = set()
        filtered: list[str] = []
        for alias in aliases:
            ipa = ipa_map.get(alias, "")
            if ipa and ipa not in seen:
                filtered.append(alias)
                seen.add(ipa)
        return filtered

"""
中文修正引擎 (ChineseEngine)

負責持有共享的中文語音系統、分詞器和模糊生成器，
並提供工廠方法建立輕量的 ChineseCorrector 實例。
"""

from typing import Any, Callable, Dict, List, Optional

from phonofix.backend import ChinesePhoneticBackend, get_chinese_backend
from phonofix.core.term_config import TermDictInput, normalize_term_dict
from phonofix.core.engine_interface import CorrectorEngine

from .config import ChinesePhoneticConfig
from .corrector import ChineseCorrector
from .fuzzy_generator import ChineseFuzzyGenerator
from .phonetic_impl import ChinesePhoneticSystem
from .tokenizer import ChineseTokenizer
from .utils import ChinesePhoneticUtils


class ChineseEngine(CorrectorEngine):
    _engine_name = "chinese"

    def __init__(
        self,
        phonetic_config: Optional[ChinesePhoneticConfig] = None,
        *,
        enable_surface_variants: bool = False,
        enable_representative_variants: bool = False,
        verbose: bool = False,
        on_timing: Optional[Callable[[str, float], None]] = None,
    ):
        self._init_logger(verbose=verbose, on_timing=on_timing)

        with self._log_timing("ChineseEngine.__init__"):
            self._backend: ChinesePhoneticBackend = get_chinese_backend()
            self._backend.initialize()

            self._phonetic_config = phonetic_config or ChinesePhoneticConfig
            self._phonetic = ChinesePhoneticSystem(backend=self._backend)
            self._tokenizer = ChineseTokenizer()
            self._fuzzy_generator = ChineseFuzzyGenerator(
                config=self._phonetic_config,
                enable_representative_variants=enable_representative_variants,
            )
            self._utils = ChinesePhoneticUtils(config=self._phonetic_config)
            self._enable_surface_variants = enable_surface_variants

            self._initialized = True
            self._logger.info("ChineseEngine initialized")

    @property
    def phonetic(self) -> ChinesePhoneticSystem:
        return self._phonetic

    @property
    def tokenizer(self) -> ChineseTokenizer:
        return self._tokenizer

    @property
    def fuzzy_generator(self) -> ChineseFuzzyGenerator:
        return self._fuzzy_generator

    @property
    def utils(self) -> ChinesePhoneticUtils:
        return self._utils

    @property
    def config(self) -> ChinesePhoneticConfig:
        return self._phonetic_config

    @property
    def backend(self) -> ChinesePhoneticBackend:
        return self._backend

    def is_initialized(self) -> bool:
        return self._initialized

    def get_backend_stats(self) -> Dict[str, Any]:
        return self._backend.get_cache_stats()

    def create_corrector(
        self,
        term_dict: TermDictInput,
        protected_terms: Optional[List[str]] = None,
        **kwargs,
    ) -> ChineseCorrector:
        with self._log_timing("ChineseEngine.create_corrector"):
            normalized_input = normalize_term_dict(term_dict)

            normalized_dict = {}
            for term, value in normalized_input.items():
                normalized_value = self._normalize_term_value(term, value)
                if normalized_value:
                    normalized_dict[term] = normalized_value

            self._logger.debug(f"Creating corrector with {len(normalized_dict)} terms")

            cache_stats = self._backend.get_cache_stats()
            pinyin_stats = cache_stats.get("pinyin", {})
            total_hits = pinyin_stats.get("hits", 0)
            total_misses = pinyin_stats.get("misses", 0)
            hit_rate = total_hits / max(1, total_hits + total_misses) * 100
            self._logger.debug(
                f"  [Cache] pinyin: hits={total_hits}, misses={total_misses}, "
                f"rate={hit_rate:.1f}%, size={pinyin_stats.get('currsize', 0)}"
            )

            return ChineseCorrector._from_engine(
                engine=self,
                term_mapping=normalized_dict,
                protected_terms=set(protected_terms) if protected_terms else None,
            )

    def _normalize_term_value(self, term: str, value: Any) -> Optional[Dict[str, Any]]:
        if isinstance(value, list):
            value = {"aliases": value}
        elif isinstance(value, dict):
            if "aliases" not in value:
                value = {**value, "aliases": []}
        else:
            value = {"aliases": []}

        pinyin = self._utils.get_pinyin_string(term)
        self._logger.debug(f"  [Pinyin] {term} -> {pinyin}")

        merged_aliases = list(value.get("aliases", []))
        if self._enable_surface_variants:
            max_variants = int(value.get("max_variants", 30) or 30)
            with self._log_timing(f"generate_variants({term})"):
                fuzzy_variants = self._fuzzy_generator.generate_variants(term, max_variants=max_variants)
            merged_aliases.extend(list(fuzzy_variants))
        value["aliases"] = self._filter_aliases_by_pinyin(merged_aliases)

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

    def _filter_aliases_by_pinyin(self, aliases: List[str]) -> List[str]:
        seen_pinyins = set()
        filtered = []
        for alias in aliases:
            pinyin_str = self._utils.get_pinyin_string(alias)
            if pinyin_str not in seen_pinyins:
                filtered.append(alias)
                seen_pinyins.add(pinyin_str)
        return filtered

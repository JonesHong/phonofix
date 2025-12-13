"""
英文修正引擎 (EnglishEngine)

負責持有共享的英文語音系統、分詞器和模糊生成器，
並提供工廠方法建立輕量的 EnglishCorrector 實例。
"""

from typing import Any, Callable, Dict, Optional

from phonofix.backend import EnglishPhoneticBackend, get_english_backend
from phonofix.core.term_config import TermDictInput, normalize_term_dict
from phonofix.core.engine_interface import CorrectorEngine

from .config import EnglishPhoneticConfig
from .corrector import EnglishCorrector
from .fuzzy_generator import EnglishFuzzyGenerator
from .phonetic_impl import EnglishPhoneticSystem
from .tokenizer import EnglishTokenizer


class EnglishEngine(CorrectorEngine):
    _engine_name = "english"

    def __init__(
        self,
        phonetic_config: Optional[EnglishPhoneticConfig] = None,
        verbose: bool = False,
        on_timing: Optional[Callable[[str, float], None]] = None,
    ):
        self._init_logger(verbose=verbose, on_timing=on_timing)

        with self._log_timing("EnglishEngine.__init__"):
            self._backend: EnglishPhoneticBackend = get_english_backend()
            self._backend.initialize()

            self._phonetic = EnglishPhoneticSystem(backend=self._backend)
            self._tokenizer = EnglishTokenizer()
            self._fuzzy_generator = EnglishFuzzyGenerator()
            self._phonetic_config = phonetic_config or EnglishPhoneticConfig

            self._initialized = True
            self._logger.info("EnglishEngine initialized")

    @property
    def phonetic(self) -> EnglishPhoneticSystem:
        return self._phonetic

    @property
    def tokenizer(self) -> EnglishTokenizer:
        return self._tokenizer

    @property
    def fuzzy_generator(self) -> EnglishFuzzyGenerator:
        return self._fuzzy_generator

    @property
    def config(self) -> EnglishPhoneticConfig:
        return self._phonetic_config

    @property
    def backend(self) -> EnglishPhoneticBackend:
        return self._backend

    def is_initialized(self) -> bool:
        return self._initialized and self._backend.is_initialized()

    def get_backend_stats(self) -> Dict[str, Any]:
        return self._backend.get_cache_stats()

    def create_corrector(self, term_dict: TermDictInput, **kwargs) -> EnglishCorrector:
        with self._log_timing("EnglishEngine.create_corrector"):
            normalized_input = normalize_term_dict(term_dict)

            normalized_dict = {}
            for term, value in normalized_input.items():
                normalized_value = self._normalize_term_value(term, value)
                if normalized_value:
                    normalized_dict[term] = normalized_value

            self._logger.debug(f"Creating corrector with {len(normalized_dict)} terms")

            cache_stats = self._backend.get_cache_stats()
            hit_rate = cache_stats["hits"] / max(1, cache_stats["hits"] + cache_stats["misses"]) * 100
            self._logger.debug(
                f"  [Cache] hits={cache_stats['hits']}, misses={cache_stats['misses']}, "
                f"rate={hit_rate:.1f}%, size={cache_stats['currsize']}"
            )

            return EnglishCorrector._from_engine(engine=self, term_mapping=normalized_dict)

    def _normalize_term_value(self, term: str, value: Any) -> Optional[Dict[str, Any]]:
        if isinstance(value, list):
            value = {"aliases": value}
        elif isinstance(value, dict):
            if "aliases" not in value:
                value = {**value, "aliases": []}
        else:
            value = {"aliases": []}

        ipa = self._backend.to_phonetic(term)
        self._logger.debug(f"  [IPA] {term} -> {ipa}")

        max_variants = int(value.get("max_variants", 30) or 30)
        with self._log_timing(f"generate_variants({term})"):
            auto_variants = self._fuzzy_generator.generate_variants(term, max_variants=max_variants)

        current_aliases = set(value["aliases"])
        for variant in auto_variants:
            if variant != term and variant not in current_aliases:
                value["aliases"].append(variant)
                current_aliases.add(variant)

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

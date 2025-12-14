"""
日文修正引擎 (JapaneseEngine)

負責持有共享的日文語音系統、分詞器與模糊生成器，
並提供工廠方法建立輕量的 JapaneseCorrector 實例。
"""

from typing import Any, Callable, Dict, List, Optional

from phonofix.core.engine_interface import CorrectorEngine
from phonofix.core.events import CorrectionEventHandler
from phonofix.core.term_config import TermDictInput, normalize_term_dict

from .config import JapanesePhoneticConfig
from .corrector import JapaneseCorrector
from .fuzzy_generator import JapaneseFuzzyGenerator
from .phonetic_impl import JapanesePhoneticSystem
from .tokenizer import JapaneseTokenizer


class JapaneseEngine(CorrectorEngine):
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
        self._init_logger(verbose=verbose, on_timing=on_timing)

        with self._log_timing("JapaneseEngine.__init__"):
            self._phonetic = JapanesePhoneticSystem()
            self._tokenizer = JapaneseTokenizer()
            self._phonetic_config = phonetic_config or JapanesePhoneticConfig()
            self._enable_surface_variants = enable_surface_variants
            self._fuzzy_generator = JapaneseFuzzyGenerator(
                config=self._phonetic_config,
                enable_representative_variants=enable_representative_variants,
            )

            self._initialized = True
            self._logger.info("JapaneseEngine initialized")

    @property
    def phonetic(self) -> JapanesePhoneticSystem:
        return self._phonetic

    @property
    def tokenizer(self) -> JapaneseTokenizer:
        return self._tokenizer

    @property
    def fuzzy_generator(self) -> JapaneseFuzzyGenerator:
        return self._fuzzy_generator

    @property
    def config(self) -> JapanesePhoneticConfig:
        return self._phonetic_config

    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)

    def get_backend_stats(self) -> Dict[str, Any]:
        return {"engine": "japanese", "initialized": self.is_initialized()}

    def create_corrector(
        self,
        term_dict: TermDictInput,
        protected_terms: Optional[List[str]] = None,
        on_event: Optional[CorrectionEventHandler] = None,
        **kwargs,
    ) -> JapaneseCorrector:
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

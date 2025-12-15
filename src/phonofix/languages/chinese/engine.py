"""
中文修正引擎 (ChineseEngine)

負責持有共享的中文語音系統、分詞器和模糊生成器，
並提供工廠方法建立輕量的 ChineseCorrector 實例。
"""

from typing import Any, Callable, Dict, List, Optional

from phonofix.backend import ChinesePhoneticBackend, get_chinese_backend
from phonofix.core.engine_interface import CorrectorEngine
from phonofix.core.events import CorrectionEventHandler
from phonofix.core.term_config import TermDictInput, normalize_term_dict

from .config import ChinesePhoneticConfig
from .corrector import ChineseCorrector
from .fuzzy_generator import ChineseFuzzyGenerator
from .phonetic_impl import ChinesePhoneticSystem
from .tokenizer import ChineseTokenizer
from .utils import ChinesePhoneticUtils


class ChineseEngine(CorrectorEngine):
    """
    中文修正引擎。

    職責：
    - 持有中文 phonetic backend（pypinyin + 快取）
    - 建立 phonetic system / tokenizer / fuzzy generator / utils 等共享元件
    - 將使用者輸入的 term_dict 正規化後，建立輕量的 ChineseCorrector

    設計重點：
    - backend 單例負責快取與（必要時）依賴檢查
    - corrector 實例保持輕量，便於快速建立不同 domain 的字典
    """

    _engine_name = "chinese"

    def __init__(
        self,
        phonetic_config: Optional[ChinesePhoneticConfig] = None,
        *,
        enable_surface_variants: bool = True,
        enable_representative_variants: bool = False,
        verbose: bool = False,
        on_timing: Optional[Callable[[str, float], None]] = None,
    ):
        """
        初始化 ChineseEngine。

        Args:
            phonetic_config: 拼音設定（未提供則使用預設 ChinesePhoneticConfig）
            enable_surface_variants: 是否自動生成表面變體（包含黏音/懶音等）
            enable_representative_variants: 是否啟用代表字變體（較昂貴，預設關閉）
            verbose: 是否輸出較多日誌
            on_timing: 可選的計時回呼（利於效能觀測）
        """
        self._init_logger(verbose=verbose, on_timing=on_timing)

        with self._log_timing("ChineseEngine.__init__"):
            self._backend: ChinesePhoneticBackend = get_chinese_backend()
            self._backend.initialize()

            self._phonetic_config = phonetic_config or ChinesePhoneticConfig
            self._phonetic = ChinesePhoneticSystem(backend=self._backend)
            self._tokenizer = ChineseTokenizer()
            self._fuzzy_generator = ChineseFuzzyGenerator(
                config=self._phonetic_config,
                backend=self._backend,
                enable_representative_variants=enable_representative_variants,
            )
            self._utils = ChinesePhoneticUtils(config=self._phonetic_config)
            self._enable_surface_variants = enable_surface_variants

            self._initialized = True
            self._logger.info("ChineseEngine initialized")

    @property
    def phonetic(self) -> ChinesePhoneticSystem:
        """取得中文發音系統（拼音轉換與相似度）。"""
        return self._phonetic

    @property
    def tokenizer(self) -> ChineseTokenizer:
        """取得中文分詞器（用於滑動視窗與 token indices）。"""
        return self._tokenizer

    @property
    def fuzzy_generator(self) -> ChineseFuzzyGenerator:
        """取得中文模糊變體生成器（同音/近音等變體）。"""
        return self._fuzzy_generator

    @property
    def utils(self) -> ChinesePhoneticUtils:
        """取得中文語音工具（聲母/韻母/模糊音判斷等）。"""
        return self._utils

    @property
    def config(self) -> ChinesePhoneticConfig:
        """取得中文語音設定（phonetic config）。"""
        return self._phonetic_config

    @property
    def backend(self) -> ChinesePhoneticBackend:
        """取得中文語音 backend（進階用途：快取統計/清除等）。"""
        return self._backend

    def is_initialized(self) -> bool:
        """檢查 Engine 是否已完成初始化。"""
        return self._initialized

    def get_backend_stats(self) -> Dict[str, Any]:
        """取得 backend 快取統計資訊。"""
        return self._backend.get_cache_stats()

    def create_corrector(
        self,
        term_dict: TermDictInput,
        protected_terms: Optional[List[str]] = None,
        on_event: Optional[CorrectionEventHandler] = None,
        **kwargs,
    ) -> ChineseCorrector:
        """
        依據 term_dict 建立 ChineseCorrector。

        Args:
            term_dict: 使用者輸入的字典（支援簡寫格式與完整 config 格式）
            protected_terms: 不可被替換的保護詞彙（避免誤修）
            on_event: 可選事件回呼（replacement/degraded/fuzzy_error）

        Returns:
            ChineseCorrector: 輕量 corrector 實例
        """
        with self._log_timing("ChineseEngine.create_corrector"):
            normalized_input = normalize_term_dict(term_dict)

            normalized_dict = {}
            for term, value in normalized_input.items():
                normalized_value = self._normalize_term_value(term, value)
                if normalized_value:
                    normalized_dict[term] = normalized_value

            self._logger.debug(f"Creating corrector with {len(normalized_dict)} terms")

            cache_stats = self._backend.get_cache_stats()
            pinyin_stats = cache_stats["caches"].get("pinyin", {"hits": 0, "misses": 0, "currsize": 0, "maxsize": -1})
            total_hits = pinyin_stats["hits"]
            total_misses = pinyin_stats["misses"]
            hit_rate = total_hits / max(1, total_hits + total_misses) * 100
            self._logger.debug(
                f"  [Cache] pinyin: hits={total_hits}, misses={total_misses}, "
                f"rate={hit_rate:.1f}%, size={pinyin_stats['currsize']}"
            )

            return ChineseCorrector._from_engine(
                engine=self,
                term_mapping=normalized_dict,
                protected_terms=set(protected_terms) if protected_terms else None,
                on_event=on_event,
            )

    def _normalize_term_value(self, term: str, value: Any) -> Optional[Dict[str, Any]]:
        """
        將 term_dict 的 value 正規化為 internal config dict。

        主要工作：
        - 統一 aliases / keywords / exclude_when / weight 欄位
        - 產生 fuzzy variants（可由 enable_surface_variants 控制）
        - 以拼音去重 aliases，避免字典膨脹（同音不同寫只留一份）
        """
        if isinstance(value, list):
            value = {"aliases": value}
        elif isinstance(value, dict):
            if "aliases" not in value:
                value = {**value, "aliases": []}
        else:
            value = {"aliases": []}

        pinyin = self._backend.to_phonetic(term)
        self._logger.debug(f"  [Pinyin] {term} -> {pinyin}")

        merged_aliases = list(value.get("aliases", []))
        if self._enable_surface_variants:
            max_variants = int(value.get("max_variants", 30) or 30)
            with self._log_timing(f"generate_variants({term})"):
                fuzzy_variants = self._fuzzy_generator.generate_variants(term, max_variants=max_variants)
            merged_aliases.extend(list(fuzzy_variants))
        max_variants = int(value.get("max_variants", 30) or 30)
        value["aliases"] = self._filter_aliases_by_pinyin(merged_aliases)[:max_variants]

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
        """
        依拼音去重 aliases（保留第一個出現的拼寫）。

        目的：
        - 控制 auto-variants 造成的字典膨脹
        - 避免同音 alias 重複，讓索引更小、候選生成更快
        """
        seen_pinyins = set()
        filtered = []
        for alias in aliases:
            pinyin_str = self._backend.to_phonetic(alias)
            if pinyin_str not in seen_pinyins:
                filtered.append(alias)
                seen_pinyins.add(pinyin_str)
        return filtered

"""
英文修正引擎 (EnglishEngine)

負責持有共享的英文語音系統、分詞器和模糊生成器，
並提供工廠方法建立輕量的 EnglishCorrector 實例。
"""

from typing import Dict, List, Union, Any, Optional, Callable

from .base import CorrectorEngine
from phonofix.backend import get_english_backend, EnglishPhoneticBackend
from phonofix.languages.english.phonetic_impl import EnglishPhoneticSystem
from phonofix.languages.english.tokenizer import EnglishTokenizer
from phonofix.languages.english.fuzzy_generator import EnglishFuzzyGenerator
from phonofix.languages.english.config import EnglishPhoneticConfig


class EnglishEngine(CorrectorEngine):
    """
    英文修正引擎
    
    職責:
    - 初始化並持有 EnglishPhoneticBackend (單例)
    - 持有共享的 PhoneticSystem、Tokenizer、FuzzyGenerator
    - 提供工廠方法建立輕量 EnglishCorrector 實例
    
    使用方式:
        # 簡單用法
        engine = EnglishEngine()
        
        # 開啟詳細日誌
        engine = EnglishEngine(verbose=True)
        
        corrector = engine.create_corrector({"Python": ["Pyton"]})
        result = corrector.correct("I use Pyton")
    """
    
    _engine_name = "english"
    
    def __init__(
        self,
        phonetic_config: Optional[EnglishPhoneticConfig] = None,
        verbose: bool = False,
        on_timing: Optional[Callable[[str, float], None]] = None,
    ):
        """
        初始化英文修正引擎
        
        這會觸發 espeak-ng 的初始化 (約 2 秒)，但只需執行一次。
        
        Args:
            phonetic_config: 語音配置選項 (可選)
            verbose: 是否開啟詳細日誌
            on_timing: 計時回呼函數
        """
        # 初始化 Logger
        self._init_logger(verbose=verbose, on_timing=on_timing)
        
        with self._log_timing("EnglishEngine.__init__"):
            # 取得並初始化 Backend 單例
            self._backend: EnglishPhoneticBackend = get_english_backend()
            self._backend.initialize()
            
            # 建立共享元件 - 注入 Backend 以使用其快取
            self._phonetic = EnglishPhoneticSystem(backend=self._backend)
            self._tokenizer = EnglishTokenizer()
            self._fuzzy_generator = EnglishFuzzyGenerator()
            self._phonetic_config = phonetic_config or EnglishPhoneticConfig
            
            self._initialized = True
            
            self._logger.info("EnglishEngine initialized")
    
    @property
    def phonetic(self) -> EnglishPhoneticSystem:
        """取得共享的語音系統"""
        return self._phonetic
    
    @property
    def tokenizer(self) -> EnglishTokenizer:
        """取得共享的分詞器"""
        return self._tokenizer
    
    @property
    def fuzzy_generator(self) -> EnglishFuzzyGenerator:
        """取得共享的模糊生成器"""
        return self._fuzzy_generator
    
    @property
    def config(self) -> EnglishPhoneticConfig:
        """取得語音配置"""
        return self._phonetic_config
    
    @property
    def backend(self) -> EnglishPhoneticBackend:
        """取得底層 Backend"""
        return self._backend
    
    def is_initialized(self) -> bool:
        """檢查引擎是否已初始化"""
        return self._initialized and self._backend.is_initialized()
    
    def get_backend_stats(self) -> Dict[str, Any]:
        """取得 Backend 快取統計"""
        return self._backend.get_cache_stats()
    
    def create_corrector(
        self,
        term_dict: Union[List[str], Dict[str, Any]],
        **kwargs
    ) -> "EnglishCorrector":
        """
        建立輕量 EnglishCorrector 實例
        
        這個方法非常快速 (約 10ms)，因為不需要重新初始化 espeak-ng。
        
        Args:
            term_dict: 詞彙配置，支援以下格式:
                - List[str]: 純詞彙列表，自動生成別名
                  ["Python", "TensorFlow"]
                  
                - Dict[str, List[str]]: 詞彙 + 手動別名
                  {"Python": ["Pyton", "Pyson"]}
                  
                - Dict[str, dict]: 完整配置
                  {"EKG": {"aliases": ["1kg"], "keywords": ["設備"], "exclude_when": ["水"]}}
            
            **kwargs: 額外配置選項 (目前未使用)
            
        Returns:
            EnglishCorrector: 可立即使用的修正器實例
        
        Example:
            engine = EnglishEngine()
            
            # 格式 1: 純列表
            corrector = engine.create_corrector(["Python", "TensorFlow"])
            
            # 格式 2: 帶別名
            corrector = engine.create_corrector({
                "Python": ["Pyton", "Pyson"],
                "JavaScript": ["java script"]
            })
            
            # 格式 3: 完整配置 (含上下文排除條件)
            corrector = engine.create_corrector({
                "EKG": {
                    "aliases": ["1kg", "1 kg"],
                    "keywords": ["device", "heart"],
                    "exclude_when": ["weight", "kg of"],  # 看到這些詞時不修正
                }
            })
        """
        with self._log_timing("EnglishEngine.create_corrector"):
            # 延遲 import 避免循環依賴
            from phonofix.languages.english.corrector import EnglishCorrector
            
            # 標準化 term_dict 格式
            if isinstance(term_dict, list):
                term_dict = {term: {} for term in term_dict}
            
            # 處理每個詞彙
            normalized_dict = {}
            for term, value in term_dict.items():
                normalized_value = self._normalize_term_value(term, value)
                if normalized_value:
                    normalized_dict[term] = normalized_value
            
            self._logger.debug(f"Creating corrector with {len(normalized_dict)} terms")
            
            # 快取統計日誌
            cache_stats = self._backend.get_cache_stats()
            hit_rate = cache_stats['hits'] / max(1, cache_stats['hits'] + cache_stats['misses']) * 100
            self._logger.debug(
                f"  [Cache] hits={cache_stats['hits']}, misses={cache_stats['misses']}, "
                f"rate={hit_rate:.1f}%, size={cache_stats['currsize']}"
            )
            
            # 建立輕量 Corrector
            return EnglishCorrector._from_engine(
                engine=self,
                term_mapping=normalized_dict,
            )

    def _normalize_term_value(self, term: str, value: Any) -> Optional[Dict[str, Any]]:
        """
        標準化詞彙配置值
        
        Args:
            term: 詞彙
            value: 配置值 (List, Dict, 或 None)
            
        Returns:
            標準化後的配置字典
        """
        if isinstance(value, list):
            value = {"aliases": value}
        elif isinstance(value, dict):
            if "aliases" not in value:
                value = {**value, "aliases": []}
        else:
            value = {"aliases": []}
        
        # IPA 轉換日誌
        ipa = self._backend.to_phonetic(term)
        self._logger.debug(f"  [IPA] {term} -> {ipa}")
        
        # 自動生成變體 (如果需要)
        should_auto_generate = not value.get("aliases") or value.get("auto_fuzzy", False)
        
        if should_auto_generate:
            with self._log_timing(f"generate_variants({term})"):
                auto_variants = self._fuzzy_generator.generate_variants(term)
            
            # 合併別名，避免重複
            current_aliases = set(value["aliases"])
            for variant in auto_variants:
                if variant != term and variant not in current_aliases:
                    value["aliases"].append(variant)
            
            # 日誌輸出變體詳情
            if auto_variants:
                self._logger.debug(f"  [Variants] {term} -> {auto_variants[:5]}{'...' if len(auto_variants) > 5 else ''}")
        
        return {
            "aliases": value["aliases"],
            "keywords": value.get("keywords", []),
            "exclude_when": value.get("exclude_when", []),
            "weight": value.get("weight", 0.0),
        }

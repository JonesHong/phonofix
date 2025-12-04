"""
中文修正引擎 (ChineseEngine)

負責持有共享的中文語音系統、分詞器和模糊生成器，
並提供工廠方法建立輕量的 ChineseCorrector 實例。
"""

from typing import Dict, List, Union, Any, Optional, Callable

from .base import CorrectorEngine
from multi_language_corrector.backend import get_chinese_backend, ChinesePhoneticBackend
from multi_language_corrector.languages.chinese.phonetic_impl import ChinesePhoneticSystem
from multi_language_corrector.languages.chinese.tokenizer import ChineseTokenizer
from multi_language_corrector.languages.chinese.fuzzy_generator import ChineseFuzzyGenerator
from multi_language_corrector.languages.chinese.utils import ChinesePhoneticUtils
from multi_language_corrector.languages.chinese.config import ChinesePhoneticConfig


class ChineseEngine(CorrectorEngine):
    """
    中文修正引擎
    
    職責:
    - 初始化並持有 ChinesePhoneticBackend (單例)
    - 持有共享的 PhoneticSystem、Tokenizer、FuzzyGenerator、PhoneticUtils
    - 提供工廠方法建立輕量 ChineseCorrector 實例
    
    使用方式:
        # 簡單用法
        engine = ChineseEngine()
        
        # 開啟詳細日誌
        engine = ChineseEngine(verbose=True)
        
        corrector = engine.create_corrector({"台北車站": ["北車"]})
        result = corrector.correct("我在北車")
    """
    
    _engine_name = "chinese"
    
    def __init__(
        self,
        phonetic_config: Optional[ChinesePhoneticConfig] = None,
        verbose: bool = False,
        on_timing: Optional[Callable[[str, float], None]] = None,
    ):
        """
        初始化中文修正引擎
        
        Args:
            phonetic_config: 語音配置選項 (可選)
            verbose: 是否開啟詳細日誌
            on_timing: 計時回呼函數
        """
        # 初始化 Logger
        self._init_logger(verbose=verbose, on_timing=on_timing)
        
        with self._log_timing("ChineseEngine.__init__"):
            # 取得並初始化 Backend 單例
            self._backend: ChinesePhoneticBackend = get_chinese_backend()
            self._backend.initialize()
            
            # 建立共享元件 - 注入 Backend 以使用其快取
            self._phonetic_config = phonetic_config or ChinesePhoneticConfig
            self._phonetic = ChinesePhoneticSystem(backend=self._backend)
            self._tokenizer = ChineseTokenizer()
            self._fuzzy_generator = ChineseFuzzyGenerator(config=self._phonetic_config)
            self._utils = ChinesePhoneticUtils(config=self._phonetic_config)
            
            self._initialized = True
            
            self._logger.info("ChineseEngine initialized")
    
    @property
    def phonetic(self) -> ChinesePhoneticSystem:
        """取得共享的語音系統"""
        return self._phonetic
    
    @property
    def tokenizer(self) -> ChineseTokenizer:
        """取得共享的分詞器"""
        return self._tokenizer
    
    @property
    def fuzzy_generator(self) -> ChineseFuzzyGenerator:
        """取得共享的模糊生成器"""
        return self._fuzzy_generator
    
    @property
    def utils(self) -> ChinesePhoneticUtils:
        """取得共享的語音工具"""
        return self._utils
    
    @property
    def config(self) -> ChinesePhoneticConfig:
        """取得語音配置"""
        return self._phonetic_config
    
    @property
    def backend(self) -> ChinesePhoneticBackend:
        """取得底層 Backend"""
        return self._backend
    
    def is_initialized(self) -> bool:
        """檢查引擎是否已初始化"""
        return self._initialized
    
    def get_backend_stats(self) -> Dict[str, Any]:
        """取得 Backend 快取統計"""
        return self._backend.get_cache_stats()
    
    def create_corrector(
        self,
        term_dict: Union[List[str], Dict[str, Any]],
        exclusions: Optional[List[str]] = None,
        **kwargs
    ) -> "ChineseCorrector":
        """
        建立輕量 ChineseCorrector 實例
        
        Args:
            term_dict: 詞彙配置，支援以下格式:
                - List[str]: 純詞彙列表，自動生成別名
                  ["台北車站", "高雄車站"]
                  
                - Dict[str, List[str]]: 詞彙 + 手動別名
                  {"台北車站": ["北車", "台北站"]}
                  
                - Dict[str, dict]: 完整配置
                  {"台北車站": {"aliases": ["北車"], "keywords": ["車站"]}}
            
            exclusions: 全域排除詞列表 (這些詞不會被修正)
            
            **kwargs: 額外配置選項 (目前未使用)
            
        Returns:
            ChineseCorrector: 可立即使用的修正器實例
        
        Example:
            engine = ChineseEngine()
            
            # 格式 1: 純列表
            corrector = engine.create_corrector(["台北車站", "高雄車站"])
            
            # 格式 2: 帶別名
            corrector = engine.create_corrector({
                "台北車站": ["北車", "台北站"],
                "高雄車站": ["高車", "高雄站"]
            })
            
            # 格式 3: 完整配置
            corrector = engine.create_corrector({
                "台北車站": {
                    "aliases": ["北車"],
                    "keywords": ["車站", "捷運"],
                }
            })
        """
        with self._log_timing("ChineseEngine.create_corrector"):
            # 延遲 import 避免循環依賴
            from multi_language_corrector.languages.chinese.corrector import ChineseCorrector
            
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
            
            # 快取統計日誌 (ChineseBackend 有多個快取)
            cache_stats = self._backend.get_cache_stats()
            pinyin_stats = cache_stats.get('pinyin', {})
            total_hits = pinyin_stats.get('hits', 0)
            total_misses = pinyin_stats.get('misses', 0)
            hit_rate = total_hits / max(1, total_hits + total_misses) * 100
            self._logger.debug(
                f"  [Cache] pinyin: hits={total_hits}, misses={total_misses}, "
                f"rate={hit_rate:.1f}%, size={pinyin_stats.get('currsize', 0)}"
            )
            
            # 建立輕量 Corrector
            return ChineseCorrector._from_engine(
                engine=self,
                term_mapping=normalized_dict,
                exclusions=set(exclusions) if exclusions else None,
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
        
        # 拼音轉換日誌
        pinyin = self._utils.get_pinyin_string(term)
        self._logger.debug(f"  [Pinyin] {term} -> {pinyin}")
        
        # 如果沒有提供別名，自動生成
        if not value.get("aliases"):
            with self._log_timing(f"generate_variants({term})"):
                fuzzy_result = self._fuzzy_generator.generate_variants(term)
            auto_aliases = [alias for alias in fuzzy_result if alias != term]
            auto_aliases = self._filter_aliases_by_pinyin(auto_aliases)
            value["aliases"] = auto_aliases
            
            # 日誌輸出變體詳情
            if auto_aliases:
                self._logger.debug(f"  [Variants] {term} -> {auto_aliases[:5]}{'...' if len(auto_aliases) > 5 else ''}")
        else:
            value["aliases"] = self._filter_aliases_by_pinyin(value["aliases"])
        
        return {
            "aliases": value["aliases"],
            "keywords": value.get("keywords", []),
            "exclusions": value.get("exclusions", []),
            "weight": value.get("weight", 0.0),
        }
    
    def _filter_aliases_by_pinyin(self, aliases: List[str]) -> List[str]:
        """
        根據拼音過濾重複的別名
        
        Args:
            aliases: 別名列表
            
        Returns:
            過濾後的別名列表
        """
        seen_pinyins = set()
        filtered = []
        for alias in aliases:
            pinyin_str = self._utils.get_pinyin_string(alias)
            if pinyin_str not in seen_pinyins:
                filtered.append(alias)
                seen_pinyins.add(pinyin_str)
        return filtered

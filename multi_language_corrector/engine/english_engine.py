"""
英文修正引擎 (EnglishEngine)

負責持有共享的英文語音系統、分詞器和模糊生成器，
並提供工廠方法建立輕量的 EnglishCorrector 實例。
"""

from typing import Dict, List, Union, Any, Optional, TYPE_CHECKING

from .base import CorrectorEngine
from multi_language_corrector.backend import get_english_backend, EnglishPhoneticBackend
from multi_language_corrector.languages.english.phonetic_impl import EnglishPhoneticSystem
from multi_language_corrector.languages.english.tokenizer import EnglishTokenizer
from multi_language_corrector.languages.english.fuzzy_generator import EnglishFuzzyGenerator
from multi_language_corrector.languages.english.config import EnglishPhoneticConfig

if TYPE_CHECKING:
    from multi_language_corrector.languages.english.corrector import EnglishCorrector


class EnglishEngine(CorrectorEngine):
    """
    英文修正引擎
    
    職責:
    - 初始化並持有 EnglishPhoneticBackend (單例)
    - 持有共享的 PhoneticSystem、Tokenizer、FuzzyGenerator
    - 提供工廠方法建立輕量 EnglishCorrector 實例
    
    使用方式:
        engine = EnglishEngine()  # 初始化 (~2秒，只需一次)
        
        corrector1 = engine.create_corrector({"Python": ["Pyton"]})  # 快速 (~10ms)
        corrector2 = engine.create_corrector({"AWS": ["a w s"]})     # 快速 (~10ms)
        
        result = corrector1.correct("I use Pyton")
    """
    
    def __init__(self, config: Optional[EnglishPhoneticConfig] = None):
        """
        初始化英文修正引擎
        
        這會觸發 espeak-ng 的初始化 (約 2 秒)，但只需執行一次。
        
        Args:
            config: 配置選項 (可選)
        """
        # 取得並初始化 Backend 單例
        self._backend: EnglishPhoneticBackend = get_english_backend()
        self._backend.initialize()
        
        # 建立共享元件 - 注入 Backend 以使用其快取
        self._phonetic = EnglishPhoneticSystem(backend=self._backend)
        self._tokenizer = EnglishTokenizer()
        self._fuzzy_generator = EnglishFuzzyGenerator()
        self._config = config or EnglishPhoneticConfig
        
        self._initialized = True
    
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
        """取得配置"""
        return self._config
    
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
                  {"EKG": {"aliases": ["1kg"], "keywords": ["設備"], "exclusions": ["水"]}}
            
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
            
            # 格式 3: 完整配置
            corrector = engine.create_corrector({
                "EKG": {
                    "aliases": ["1kg", "1 kg"],
                    "keywords": ["device", "heart"],
                    "exclusions": ["weight", "kg of"],
                }
            })
        """
        # 延遲 import 避免循環依賴
        from multi_language_corrector.languages.english.corrector import EnglishCorrector
        
        # 處理詞彙配置
        term_mapping = {}
        keywords = {}
        exclusions = {}
        
        # 處理列表格式
        if isinstance(term_dict, list):
            for term in term_dict:
                # 自動生成變體
                variants = self._fuzzy_generator.generate_variants(term)
                term_mapping[term] = term
                for variant in variants:
                    term_mapping[variant] = term
        else:
            # 處理字典格式
            for term, value in term_dict.items():
                term_mapping[term] = term
                
                if isinstance(value, list):
                    # 格式 2
                    for alias in value:
                        term_mapping[alias] = term
                    # 自動生成額外變體
                    auto_variants = self._fuzzy_generator.generate_variants(term)
                    for variant in auto_variants:
                        if variant not in term_mapping:
                            term_mapping[variant] = term
                            
                elif isinstance(value, dict):
                    # 格式 3
                    aliases = value.get("aliases", [])
                    for alias in aliases:
                        term_mapping[alias] = term
                    
                    if value.get("auto_fuzzy", True):
                        auto_variants = self._fuzzy_generator.generate_variants(term)
                        for variant in auto_variants:
                            if variant not in term_mapping:
                                term_mapping[variant] = term
                    
                    if value.get("keywords"):
                        keywords[term] = value["keywords"]
                    if value.get("exclusions"):
                        exclusions[term] = value["exclusions"]
                        
                else:
                    # 空值或其他
                    auto_variants = self._fuzzy_generator.generate_variants(term)
                    for variant in auto_variants:
                        term_mapping[variant] = term
        
        # 建立輕量 Corrector
        return EnglishCorrector._from_engine(
            engine=self,
            term_mapping=term_mapping,
            keywords=keywords,
            exclusions=exclusions,
        )

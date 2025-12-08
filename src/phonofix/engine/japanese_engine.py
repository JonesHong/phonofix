"""
日文修正引擎 (JapaneseEngine)

負責持有共享的日文語音系統和分詞器，
並提供工廠方法建立輕量的 JapaneseCorrector 實例。
"""

from typing import Dict, List, Union, Any, Optional, Callable

from .base import CorrectorEngine
from phonofix.languages.japanese.phonetic_impl import JapanesePhoneticSystem
from phonofix.languages.japanese.tokenizer import JapaneseTokenizer
from phonofix.languages.japanese.config import JapanesePhoneticConfig


class JapaneseEngine(CorrectorEngine):
    """
    日文修正引擎
    
    職責:
    - 持有共享的 PhoneticSystem、Tokenizer
    - 提供工廠方法建立輕量 JapaneseCorrector 實例
    
    使用方式:
        # 簡單用法
        engine = JapaneseEngine()
        
        # 開啟詳細日誌
        engine = JapaneseEngine(verbose=True)
        
        corrector = engine.create_corrector({"アスピリン": ["asupirin"]})
        result = corrector.correct("頭が痛いのでasupirinを飲みました")
    """
    
    _engine_name = "japanese"
    
    def __init__(
        self,
        phonetic_config: Optional[JapanesePhoneticConfig] = None,
        verbose: bool = False,
        on_timing: Optional[Callable[[str, float], None]] = None,
    ):
        """
        初始化日文修正引擎
        
        Args:
            phonetic_config: 語音配置選項 (可選)
            verbose: 是否開啟詳細日誌
            on_timing: 計時回呼函數
        """
        # 初始化 Logger
        self._init_logger(verbose=verbose, on_timing=on_timing)
        
        with self._log_timing("JapaneseEngine.__init__"):
            # 建立共享元件
            self._phonetic = JapanesePhoneticSystem()
            self._tokenizer = JapaneseTokenizer()
            self._phonetic_config = phonetic_config or JapanesePhoneticConfig
            
            self._initialized = True
            
            self._logger.info("JapaneseEngine initialized")
    
    @property
    def phonetic(self) -> JapanesePhoneticSystem:
        """取得共享的語音系統"""
        return self._phonetic
    
    @property
    def tokenizer(self) -> JapaneseTokenizer:
        """取得共享的分詞器"""
        return self._tokenizer
    
    @property
    def config(self) -> JapanesePhoneticConfig:
        """取得語音配置"""
        return self._phonetic_config
    
    def is_initialized(self) -> bool:
        """檢查引擎是否已初始化"""
        return getattr(self, "_initialized", False)

    def get_backend_stats(self) -> Dict[str, Any]:
        """
        取得底層 Backend 的統計資訊
        
        Returns:
            Dict[str, Any]: 統計資訊
        """
        return {
            "engine": "japanese",
            "initialized": self.is_initialized()
        }

    def create_corrector(
        self,
        term_mapping: Dict[str, Union[List[str], Dict[str, Any]]],
        protected_terms: Optional[set] = None,
    ) -> "JapaneseCorrector":
        """
        建立日文修正器實例
        
        Args:
            term_mapping: 專有名詞映射字典
            protected_terms: 受保護的詞彙集合 (這些詞不會被修正)
            
        Returns:
            JapaneseCorrector: 修正器實例
        """
        from phonofix.languages.japanese.corrector import JapaneseCorrector
        
        # 標準化 term_mapping 格式
        if isinstance(term_mapping, list):
            term_mapping = {term: {} for term in term_mapping}
        
        # 處理每個詞彙
        normalized_mapping = {}
        for term, value in term_mapping.items():
            normalized_value = self._normalize_term_value(term, value)
            if normalized_value:
                normalized_mapping[term] = normalized_value
        
        # 使用工廠方法建立實例
        return JapaneseCorrector._from_engine(
            engine=self,
            term_mapping=normalized_mapping
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
        
        # 自動生成變體 (如果沒有提供別名)
        # 對於日文，如果沒有提供別名，我們假設使用者希望透過羅馬拼音修正回漢字/假名
        if not value["aliases"]:
            romaji = self._phonetic.to_phonetic(term)
            if romaji and romaji != term:
                 value["aliases"].append(romaji)
                 self._logger.debug(f"  [Auto-Gen] {term} -> {romaji}")

        return {
            "aliases": value["aliases"],
            "keywords": value.get("keywords", []),
            "exclude_when": value.get("exclude_when", []),
            "weight": value.get("weight", 1.0), # Default weight 1.0 for Japanese
        }

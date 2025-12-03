"""
統一修正引擎 (UnifiedEngine)

整合中英文修正引擎，負責：
- 持有 EnglishEngine 和 ChineseEngine
- 自動分類詞彙為中文或英文
- 提供工廠方法建立 UnifiedCorrector 實例
"""

from typing import Dict, List, Union, Any, Optional, TYPE_CHECKING

from .base import CorrectorEngine
from .english_engine import EnglishEngine
from .chinese_engine import ChineseEngine
from multi_language_corrector.router.language_router import LanguageRouter

if TYPE_CHECKING:
    from multi_language_corrector.correction.unified_corrector import UnifiedCorrector


class UnifiedEngine(CorrectorEngine):
    """
    統一修正引擎
    
    職責:
    - 整合 EnglishEngine 和 ChineseEngine
    - 自動識別詞彙語言並分類
    - 提供工廠方法建立 UnifiedCorrector 實例
    
    使用方式:
        engine = UnifiedEngine()  # 初始化 (~2秒，因為英文需要初始化 espeak-ng)
        
        corrector = engine.create_corrector({
            "台北車站": ["北車"],      # 中文
            "Python": ["Pyton"],       # 英文
        })
        
        result = corrector.correct("我在北車用Pyton寫code")
    """
    
    def __init__(self):
        """
        初始化統一修正引擎
        
        這會初始化 EnglishEngine 和 ChineseEngine，
        其中 EnglishEngine 需要約 2 秒初始化 espeak-ng。
        """
        self._english_engine = EnglishEngine()
        self._chinese_engine = ChineseEngine()
        self._router = LanguageRouter()
        self._initialized = True
    
    @property
    def english_engine(self) -> EnglishEngine:
        """取得英文修正引擎"""
        return self._english_engine
    
    @property
    def chinese_engine(self) -> ChineseEngine:
        """取得中文修正引擎"""
        return self._chinese_engine
    
    @property
    def router(self) -> LanguageRouter:
        """取得語言路由器"""
        return self._router
    
    def is_initialized(self) -> bool:
        """檢查引擎是否已初始化"""
        return (
            self._initialized
            and self._english_engine.is_initialized()
            and self._chinese_engine.is_initialized()
        )
    
    def get_backend_stats(self) -> Dict[str, Any]:
        """取得所有 Backend 的快取統計"""
        return {
            "english": self._english_engine.get_backend_stats(),
            "chinese": self._chinese_engine.get_backend_stats(),
        }
    
    def create_corrector(
        self,
        term_dict: Union[List[str], Dict[str, Any]],
        exclusions: Optional[List[str]] = None,
        **kwargs
    ) -> "UnifiedCorrector":
        """
        建立 UnifiedCorrector 實例
        
        這個方法會自動將詞彙分類為中文和英文，
        然後分別建立對應的 Corrector。
        
        Args:
            term_dict: 詞彙配置 (混合中英文)
            exclusions: 全域排除詞列表
            **kwargs: 額外配置選項
            
        Returns:
            UnifiedCorrector: 可立即使用的統一修正器
        
        Example:
            engine = UnifiedEngine()
            
            corrector = engine.create_corrector({
                # 中文詞彙
                "台北車站": ["北車"],
                
                # 英文詞彙
                "Python": ["Pyton", "Pyson"],
                "TensorFlow": ["Ten so floor"],
                
                # 帶完整配置
                "EKG": {
                    "aliases": ["1kg"],
                    "keywords": ["device"],
                    "exclusions": ["weight"],
                }
            })
        """
        # 延遲 import 避免循環依賴
        from multi_language_corrector.correction.unified_corrector import UnifiedCorrector
        
        # 標準化輸入
        if isinstance(term_dict, list):
            term_dict = {term: {} for term in term_dict}
        
        # 分類詞彙
        zh_terms = {}
        en_terms = {}
        
        for term, value in term_dict.items():
            if self._is_english_term(term):
                en_terms[term] = value
            else:
                zh_terms[term] = value
        
        # 建立子 Corrector
        zh_corrector = self._chinese_engine.create_corrector(
            zh_terms, exclusions=exclusions
        ) if zh_terms else None
        
        en_corrector = self._english_engine.create_corrector(
            en_terms
        ) if en_terms else None
        
        # 建立 UnifiedCorrector
        return UnifiedCorrector._from_engine(
            engine=self,
            zh_corrector=zh_corrector,
            en_corrector=en_corrector,
        )
    
    def _is_english_term(self, term: str) -> bool:
        """
        判斷詞彙是否為英文
        
        策略:
        - 純 ASCII 字串 -> 英文 (例如 "IBM", "TensorFlow")
        - 包含非 ASCII 字符 -> 中文 (例如 "台積電", "C語言")
        
        Args:
            term: 詞彙
            
        Returns:
            bool: 是否為英文
        """
        return all(ord(c) < 128 for c in term)

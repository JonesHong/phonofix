"""
統一修正引擎 (UnifiedEngine)

整合中英文修正引擎，負責：
- 持有 EnglishEngine 和 ChineseEngine
- 自動分類詞彙為中文或英文
- 提供工廠方法建立 UnifiedCorrector 實例
"""

from typing import Dict, List, Union, Any, Optional, Callable

from .base import CorrectorEngine
from .english_engine import EnglishEngine
from .chinese_engine import ChineseEngine
from phonofix.router.language_router import LanguageRouter
# from phonofix.utils.lazy_imports import LazyImport # LazyImport class does not exist in lazy_imports.py

# 延遲載入日文引擎，避免未安裝依賴時報錯
# 注意：這裡我們不直接 import JapaneseCorrector，而是在需要時動態 import



class UnifiedEngine(CorrectorEngine):
    """
    統一修正引擎
    
    職責:
    - 整合 EnglishEngine 和 ChineseEngine
    - 自動識別詞彙語言並分類
    - 提供工廠方法建立 UnifiedCorrector 實例
    
    使用方式:
        # 簡單用法
        engine = UnifiedEngine()
        
        # 開啟詳細日誌
        engine = UnifiedEngine(verbose=True)
        
        # 自定義計時回呼
        engine = UnifiedEngine(
            verbose=True,
            on_timing=lambda op, t: print(f"{op}: {t:.3f}s")
        )
        
        corrector = engine.create_corrector({
            "台北車站": ["北車"],      # 中文
            "Python": ["Pyton"],       # 英文
        })
        
        result = corrector.correct("我在北車用Pyton寫code")
    """
    
    _engine_name = "unified"
    
    def __init__(
        self,
        verbose: bool = False,
        on_timing: Optional[Callable[[str, float], None]] = None,
    ):
        """
        初始化統一修正引擎
        
        這會初始化 EnglishEngine 和 ChineseEngine，
        其中 EnglishEngine 需要約 2 秒初始化 espeak-ng。
        
        Args:
            verbose: 是否開啟詳細日誌 (顯示初始化時間、變體等)
            on_timing: 計時回呼函數 (operation, elapsed_seconds) -> None
        """
        # 初始化 Logger
        self._init_logger(verbose=verbose, on_timing=on_timing)
        
        with self._log_timing("UnifiedEngine.__init__"):
            self._english_engine = EnglishEngine(
                verbose=verbose, on_timing=on_timing
            )
            self._chinese_engine = ChineseEngine(
                verbose=verbose, on_timing=on_timing
            )
            self._router = LanguageRouter()
            self._initialized = True
            
            self._logger.info("UnifiedEngine initialized")
    
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
        protected_terms: Optional[List[str]] = None,
        **kwargs
    ) -> "UnifiedCorrector":
        """
        建立 UnifiedCorrector 實例
        
        這個方法會自動將詞彙分類為中文和英文，
        然後分別建立對應的 Corrector。
        
        Args:
            term_dict: 詞彙配置 (混合中英文)
            protected_terms: 受保護的詞彙列表 (這些詞不會被修正)
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
                
                # 帶完整配置 (含上下文排除條件)
                "EKG": {
                    "aliases": ["1kg"],
                    "keywords": ["device"],
                    "exclude_when": ["weight"],  # 看到這些詞時不修正
                }
            })
        """
        with self._log_timing("UnifiedEngine.create_corrector"):
            # 延遲 import 避免循環依賴
            from phonofix.correction.unified_corrector import UnifiedCorrector
            
            # 標準化輸入
            if isinstance(term_dict, list):
                term_dict = {term: {} for term in term_dict}
            
            # 分類詞彙 - 考慮別名的語言
            # 如果別名包含不同語言，則同時註冊到兩個引擎
            zh_terms = {}
            en_terms = {}
            ja_terms = {}
            cross_lingual_mappings = []  # 跨語言映射: (alias, canonical)
            
            for term, value in term_dict.items():
                # 提取別名列表
                aliases = self._extract_aliases(value)
                
                # 判斷正確詞和別名的語言
                term_is_english = self._is_english_term(term)
                term_is_japanese = self._is_japanese_term(term)
                
                has_chinese_alias = any(not self._is_english_term(a) and not self._is_japanese_term(a) for a in aliases)
                has_english_alias = any(self._is_english_term(a) for a in aliases)
                has_japanese_alias = any(self._is_japanese_term(a) for a in aliases)
                
                # 收集跨語言映射（alias 和 term 語言不同）
                for alias in aliases:
                    # 如果 alias 是跨語言的（混合中英文），直接加入映射
                    if self._is_cross_lingual(alias):
                        cross_lingual_mappings.append((alias, term))
                
                # 決定註冊到哪個引擎
                # 策略：如果別名包含該語言的詞，就註冊到該引擎
                should_register_ja = term_is_japanese or has_japanese_alias
                should_register_zh = (not term_is_english and not term_is_japanese) or has_chinese_alias
                should_register_en = term_is_english or has_english_alias
                
                if should_register_ja:
                    ja_terms[term] = value
                if should_register_zh:
                    zh_terms[term] = value
                if should_register_en:
                    en_terms[term] = value
            
            self._logger.debug(
                f"Term classification: {len(zh_terms)} Chinese, {len(en_terms)} English, {len(ja_terms)} Japanese"
            )
            if cross_lingual_mappings:
                self._logger.debug(
                    f"Cross-lingual mappings: {len(cross_lingual_mappings)}"
                )
            
            # 建立語言修正器字典
            correctors = {}
            
            if zh_terms:
                correctors['zh'] = self._chinese_engine.create_corrector(
                    zh_terms, protected_terms=protected_terms
                )
            
            if en_terms:
                correctors['en'] = self._english_engine.create_corrector(en_terms)

            if ja_terms:
                try:
                    from phonofix.languages.japanese import JapaneseCorrector
                    correctors['ja'] = JapaneseCorrector(ja_terms)
                except ImportError:
                    self._logger.warning(
                        f"Found Japanese terms {list(ja_terms.keys())} but 'phonofix[ja]' is not installed. "
                        "These terms will be ignored."
                    )
            
            # 建立 UnifiedCorrector
            unified_corrector = UnifiedCorrector._from_engine(
                engine=self,
                correctors=correctors,
            )
            
            # 設定跨語言映射
            if cross_lingual_mappings:
                unified_corrector.set_cross_lingual_mappings(cross_lingual_mappings)
            
            return unified_corrector
    
    def _is_japanese_term(self, term: str) -> bool:
        """判斷詞彙是否包含日文平假名或片假名"""
        for char in term:
            code = ord(char)
            if (0x3040 <= code <= 0x309F) or (0x30A0 <= code <= 0x30FF):
                return True
        return False

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
    
    def _is_cross_lingual(self, term: str) -> bool:
        """
        判斷詞彙是否為跨語言（同時包含中英文字符）
        
        例如:
        - "PCN的引流袋" -> True (英文 PCN + 中文 的引流袋)
        - "C語言" -> True (英文 C + 中文 語言)
        - "Python" -> False (純英文)
        - "引流袋" -> False (純中文)
        
        Args:
            term: 詞彙
            
        Returns:
            bool: 是否為跨語言
        """
        has_ascii_alpha = any(c.isalpha() and ord(c) < 128 for c in term)
        has_non_ascii = any(ord(c) >= 0x4E00 and ord(c) <= 0x9FFF for c in term)
        return has_ascii_alpha and has_non_ascii
    
    def _extract_aliases(self, value) -> list:
        """
        從詞彙配置中提取別名列表
        
        支援多種格式:
        - [] 空列表
        - ["alias1", "alias2"] 別名列表
        - {"aliases": [...], "keywords": [...]} 完整配置
        
        Args:
            value: 詞彙的配置值
            
        Returns:
            list: 別名列表
        """
        if isinstance(value, list):
            return value
        elif isinstance(value, dict):
            return value.get("aliases", [])
        return []

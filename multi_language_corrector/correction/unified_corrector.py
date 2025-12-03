"""
統一修正器模組

這是多語言修正系統的主要入口點。
負責協調語言路由與特定語言的修正器，以處理混合語言的文本。
"""

from typing import List, Dict, Union, Optional, TYPE_CHECKING
from multi_language_corrector.router.language_router import LanguageRouter
from multi_language_corrector.languages.chinese.corrector import ChineseCorrector
from multi_language_corrector.languages.english.corrector import EnglishCorrector

if TYPE_CHECKING:
    from multi_language_corrector.engine.unified_engine import UnifiedEngine


class UnifiedCorrector:
    """
    統一修正器 (Unified Corrector)

    功能:
    - 接收混合語言文本
    - 自動識別並分割不同語言的片段
    - 將片段分派給對應的語言修正器 (中文/英文)
    - 合併修正後的結果
    """
    
    # =========================================================================
    # 工廠方法
    # =========================================================================
    
    @classmethod
    def _from_engine(
        cls,
        engine: "UnifiedEngine",
        zh_corrector: ChineseCorrector,
        en_corrector: EnglishCorrector,
    ) -> "UnifiedCorrector":
        """
        由 UnifiedEngine 調用的內部工廠方法
        
        此方法使用 Engine 提供的子 Corrector，避免重複初始化。
        
        Args:
            engine: UnifiedEngine 實例
            zh_corrector: 已初始化的中文修正器
            en_corrector: 已初始化的英文修正器
            
        Returns:
            UnifiedCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance.router = engine.router
        instance.zh_corrector = zh_corrector
        instance.en_corrector = en_corrector
        
        return instance

    def __init__(self, term_dict: Union[List[str], Dict], exclusions=None):
        """
        初始化統一修正器

        初始化過程會將輸入的專有名詞庫分類為中文詞庫與英文詞庫，
        並分別初始化對應的修正器實例。

        Args:
            term_dict: 專有名詞字典或列表
            exclusions: 排除詞列表 (全域排除詞，會傳給各語言修正器)
        """
        self._engine = None  # 舊版 API 不使用 Engine
        self.router = LanguageRouter()
        
        # 將專有名詞分類為中文與英文
        zh_terms = {}
        en_terms = {}
        
        # 如果輸入是列表，則標準化為字典格式
        # 範例: ["IBM", "台積電"] -> {"IBM": {}, "台積電": {}}
        if isinstance(term_dict, list):
            term_dict = {term: {} for term in term_dict}
            
        for term, value in term_dict.items():
            # 檢查專有名詞是否為純英文 (ASCII)
            # 策略:
            # - 純 ASCII 字串 -> 英文修正器 (例如 "IBM", "TensorFlow")
            # - 包含非 ASCII 字符 (如中文) -> 中文修正器 (例如 "台積電", "C語言")
            # 注意: 混合語言詞彙 (如 "C語言") 目前歸類為中文處理
            if all(ord(c) < 128 for c in term):
                en_terms[term] = value
            else:
                zh_terms[term] = value
                
        # 初始化特定語言的修正器
        # 兩者都使用統一的 from_terms() 工廠方法
        self.zh_corrector = ChineseCorrector.from_terms(zh_terms, exclusions=exclusions)
        self.en_corrector = EnglishCorrector.from_terms(en_terms)

    def correct(self, text: str) -> str:
        """
        執行混合語言文本修正

        流程:
        1. 使用 LanguageRouter 將文本分割為語言片段 (如 [('zh', '我有一台'), ('en', 'computer')])
        2. 遍歷每個片段，根據語言標籤呼叫對應的修正器
        3. 將修正後的片段重新組合成完整字串

        限制:
        - 目前的簡單路由策略可能會將混合詞彙 (如 "C語言") 切開為 "C" (en) 和 "語言" (zh)
        - 這可能導致某些跨語言邊界的專有名詞無法正確修正
        - 但對於解決 "1kg" -> "EKG" 這類純英文/數字問題非常有效

        Args:
            text: 原始混合語言文本

        Returns:
            str: 修正後的文本
        """
        # 1. 路由分割
        # 範例輸入: "我有一台1kg的computer"
        # 分割結果: [('zh', '我有一台'), ('en', '1kg'), ('zh', '的'), ('en', 'computer')]
        segments = self.router.split_by_language(text)
        corrected_segments = []
        
        for lang, segment in segments:
            if lang == 'zh' and self.zh_corrector is not None:
                # 中文修正: "我有一台" -> "我有一台" (無變更)
                corrected_segments.append(self.zh_corrector.correct(segment))
            elif lang == 'en' and self.en_corrector is not None:
                # 英文修正: "1kg" -> "EKG" (假設 EKG 在詞庫中且符合規則)
                # 傳入完整原文作為上下文，供 keyword/exclusion 檢查
                corrected_segments.append(self.en_corrector.correct(segment, full_context=text))
            else:
                # 無對應修正器或未知語言，保持原樣
                corrected_segments.append(segment)
        
        # 2. 結果合併
        return "".join(corrected_segments)

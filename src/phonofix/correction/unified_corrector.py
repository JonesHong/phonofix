"""
統一修正器模組

這是多語言修正系統的主要入口點。
負責協調語言路由與特定語言的修正器，以處理混合語言的文本。

使用方式:
    from phonofix import UnifiedEngine
    
    engine = UnifiedEngine()
    corrector = engine.create_corrector({
        '台北車站': ['北車'],
        'Python': ['Pyton'],
    })
    result = corrector.correct('我在北車學習Pyton')
"""

import logging
from typing import List, Dict, Union, Optional, TYPE_CHECKING
from phonofix.router.language_router import LanguageRouter
from phonofix.languages.chinese.corrector import ChineseCorrector
from phonofix.languages.english.corrector import EnglishCorrector
from phonofix.utils.logger import get_logger, TimingContext

if TYPE_CHECKING:
    from phonofix.engine.unified_engine import UnifiedEngine


class UnifiedCorrector:
    """
    統一修正器 (Unified Corrector)

    功能:
    - 接收混合語言文本
    - 自動識別並分割不同語言的片段
    - 將片段分派給對應的語言修正器 (中文/英文)
    - 合併修正後的結果
    
    建立方式:
        使用 UnifiedEngine.create_corrector() 建立實例
    """
    
    @classmethod
    def _from_engine(
        cls,
        engine: "UnifiedEngine",
        zh_corrector: Optional[ChineseCorrector],
        en_corrector: Optional[EnglishCorrector],
    ) -> "UnifiedCorrector":
        """
        由 UnifiedEngine 調用的內部工廠方法
        
        此方法使用 Engine 提供的子 Corrector，避免重複初始化。
        
        Args:
            engine: UnifiedEngine 實例
            zh_corrector: 已初始化的中文修正器 (可為 None)
            en_corrector: 已初始化的英文修正器 (可為 None)
            
        Returns:
            UnifiedCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance._logger = get_logger("corrector.unified")
        instance.router = engine.router
        instance.zh_corrector = zh_corrector
        instance.en_corrector = en_corrector
        
        return instance

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
        with TimingContext("UnifiedCorrector.correct", self._logger, logging.DEBUG):
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

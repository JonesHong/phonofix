"""
統一修正器模組 (Unified Corrector)

這是多語言修正系統的主要入口點。
負責協調語言路由與特定語言的修正器，以處理混合語言的文本。

設計原則：
- 使用 Dict[str, CorrectorProtocol] 而非寫死的 zh/en
- 新增語言只需在 dict 中加入對應的 corrector
- 符合開放封閉原則 (OCP)

使用方式:
    from phonofix import UnifiedEngine
    
    engine = UnifiedEngine()
    corrector = engine.create_corrector({
        '台北車站': ['北車'],
        'Python': ['Pyton'],
    })
    result = corrector.correct('我在北車學習Pyton')
    
    # 進階：手動組合 correctors
    from phonofix.correction import UnifiedCorrector
    
    unified = UnifiedCorrector(
        correctors={'zh': zh_corrector, 'en': en_corrector},
        router=language_router,
    )
"""

import logging
from typing import Dict, Optional, TYPE_CHECKING

from phonofix.router.language_router import LanguageRouter
from phonofix.correction.protocol import CorrectorProtocol
from phonofix.utils.logger import get_logger, TimingContext

if TYPE_CHECKING:
    from phonofix.engine.unified_engine import UnifiedEngine


class UnifiedCorrector:
    """
    統一修正器 (Unified Corrector)

    功能:
    - 接收混合語言文本
    - 自動識別並分割不同語言的片段
    - 將片段分派給對應的語言修正器
    - 合併修正後的結果
    
    設計:
    - 使用 Dict[str, CorrectorProtocol] 儲存各語言修正器
    - 語言代碼與 LanguageRouter 的分割結果對應
    - 新增語言無需修改此類別
    
    建立方式:
        # 透過 UnifiedEngine（推薦）
        engine = UnifiedEngine()
        corrector = engine.create_corrector(terms)
        
        # 手動建立（進階）
        corrector = UnifiedCorrector(
            correctors={'zh': zh_corrector, 'en': en_corrector},
            router=language_router,
        )
    """
    
    def __init__(
        self,
        correctors: Dict[str, CorrectorProtocol],
        router: LanguageRouter,
    ):
        """
        初始化統一修正器
        
        Args:
            correctors: 語言代碼到修正器的映射
                例如 {'zh': ChineseCorrector, 'en': EnglishCorrector}
            router: 語言路由器，負責分割混合語言文本
        """
        self._correctors = correctors
        self.router = router
        self._logger = get_logger("corrector.unified")
        
        self._logger.debug(
            f"UnifiedCorrector initialized with languages: {list(correctors.keys())}"
        )
    
    @classmethod
    def _from_engine(
        cls,
        engine: "UnifiedEngine",
        correctors: Dict[str, CorrectorProtocol],
    ) -> "UnifiedCorrector":
        """
        由 UnifiedEngine 調用的內部工廠方法
        
        此方法使用 Engine 提供的子 Corrector，避免重複初始化。
        
        Args:
            engine: UnifiedEngine 實例
            correctors: 語言代碼到修正器的映射
            
        Returns:
            UnifiedCorrector: 輕量實例
        """
        instance = cls.__new__(cls)
        instance._engine = engine
        instance._logger = get_logger("corrector.unified")
        instance.router = engine.router
        instance._correctors = correctors
        
        instance._logger.debug(
            f"UnifiedCorrector created via engine with languages: {list(correctors.keys())}"
        )
        
        return instance
    
    @property
    def correctors(self) -> Dict[str, CorrectorProtocol]:
        """取得所有語言修正器"""
        return self._correctors
    
    @property
    def supported_languages(self) -> list:
        """取得支援的語言列表"""
        return list(self._correctors.keys())

    def correct(self, text: str) -> str:
        """
        執行混合語言文本修正

        流程:
        1. 使用 LanguageRouter 將文本分割為語言片段
           例如: [('zh', '我有一台'), ('en', 'computer')]
        2. 遍歷每個片段，根據語言標籤呼叫對應的修正器
        3. 將修正後的片段重新組合成完整字串

        限制:
        - 目前的簡單路由策略可能會將混合詞彙切開
          例如 "C語言" 切為 "C" (en) 和 "語言" (zh)
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
                if lang in self._correctors:
                    corrector = self._correctors[lang]
                    
                    # 嘗試傳入完整上下文（如果 corrector 支援）
                    # 這對於 keyword/exclude_when 判斷很重要
                    try:
                        corrected = corrector.correct(segment, full_context=text)
                    except TypeError:
                        # 如果 corrector 不接受 full_context 參數
                        corrected = corrector.correct(segment)
                    
                    corrected_segments.append(corrected)
                else:
                    # 無對應修正器，保持原樣
                    corrected_segments.append(segment)
            
            # 2. 結果合併
            return "".join(corrected_segments)
    
    def add_corrector(self, lang: str, corrector: CorrectorProtocol) -> None:
        """
        動態新增語言修正器
        
        Args:
            lang: 語言代碼 (如 'zh', 'en', 'ja', 'ko')
            corrector: 符合 CorrectorProtocol 的修正器實例
        """
        self._correctors[lang] = corrector
        self._logger.info(f"Added corrector for language: {lang}")
    
    def remove_corrector(self, lang: str) -> Optional[CorrectorProtocol]:
        """
        移除語言修正器
        
        Args:
            lang: 語言代碼
            
        Returns:
            移除的修正器實例，若不存在則返回 None
        """
        corrector = self._correctors.pop(lang, None)
        if corrector:
            self._logger.info(f"Removed corrector for language: {lang}")
        return corrector

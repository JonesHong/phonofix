"""
修正引擎抽象基類

定義所有語言修正引擎必須實作的介面。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Union, Any, Optional, Callable, TYPE_CHECKING
import logging

from phonofix.utils.logger import get_logger, TimingContext, setup_logger

if TYPE_CHECKING:
    from phonofix.correction.base import Corrector


class CorrectorEngine(ABC):
    """
    修正引擎抽象基類 (Abstract Base Class)
    
    職責:
    - 持有共享的語音系統、分詞器、模糊生成器
    - 提供工廠方法建立輕量的 Corrector 實例
    - 管理配置選項
    - 提供日誌與計時功能
    
    生命週期:
    - Engine 應在應用程式啟動時建立一次
    - 之後透過 create_corrector() 建立多個輕量 Corrector
    
    使用範例:
        # 簡單用法
        engine = ChineseEngine(verbose=True)
        
        # 進階用法 - 自定義回呼
        engine = ChineseEngine(
            verbose=True,
            on_timing=lambda op, t: print(f"{op}: {t:.3f}s")
        )
    """
    
    # 子類別應覆寫此屬性
    _engine_name: str = "base"
    
    def _init_logger(
        self,
        verbose: bool = False,
        on_timing: Optional[Callable[[str, float], None]] = None,
    ) -> None:
        """
        初始化 Logger
        
        Args:
            verbose: 是否開啟詳細日誌
            on_timing: 計時回呼函數
        """
        self._verbose = verbose
        self._timing_callback = on_timing
        
        # 設定 logger
        if verbose:
            setup_logger(level=logging.DEBUG)
        
        self._logger = get_logger(f"engine.{self._engine_name}")
    
    def _log_timing(self, operation: str) -> TimingContext:
        """
        建立計時上下文
        
        Args:
            operation: 操作名稱
            
        Returns:
            TimingContext: 計時上下文管理器
        """
        return TimingContext(
            operation=operation,
            logger=self._logger,
            level=logging.DEBUG,
            callback=self._timing_callback,
        )
    
    @abstractmethod
    def create_corrector(
        self,
        term_dict: Union[List[str], Dict[str, Any]],
        **kwargs
    ) -> "Corrector":
        """
        建立輕量 Corrector 實例
        
        Args:
            term_dict: 詞彙配置，支援以下格式:
                - List[str]: 純詞彙列表，自動生成別名
                - Dict[str, List[str]]: 詞彙 + 手動別名
                - Dict[str, dict]: 完整配置 (含 aliases, keywords, exclusions)
            **kwargs: 額外配置選項
            
        Returns:
            Corrector: 可立即使用的修正器實例
        """
        pass
    
    @abstractmethod
    def is_initialized(self) -> bool:
        """
        檢查引擎是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        pass
    
    @abstractmethod
    def get_backend_stats(self) -> Dict[str, Any]:
        """
        取得底層 Backend 的統計資訊
        
        Returns:
            Dict[str, Any]: 統計資訊
        """
        pass

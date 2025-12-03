"""
修正引擎抽象基類

定義所有語言修正引擎必須實作的介面。
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Union, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from multi_language_corrector.correction.base import Corrector


class CorrectorEngine(ABC):
    """
    修正引擎抽象基類 (Abstract Base Class)
    
    職責:
    - 持有共享的語音系統、分詞器、模糊生成器
    - 提供工廠方法建立輕量的 Corrector 實例
    - 管理配置選項
    
    生命週期:
    - Engine 應在應用程式啟動時建立一次
    - 之後透過 create_corrector() 建立多個輕量 Corrector
    """
    
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

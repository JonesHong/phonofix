"""
語音後端抽象基類

定義所有語言語音後端必須實作的介面。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class PhoneticBackend(ABC):
    """
    語音後端抽象基類 (Abstract Base Class)
    
    職責:
    - 初始化外部語音引擎 (如 espeak-ng, pypinyin)
    - 提供基礎語音轉換函數
    - 管理語音轉換快取
    
    所有實作類別都應該使用單例模式。
    """
    
    @abstractmethod
    def to_phonetic(self, text: str) -> str:
        """
        將文字轉換為語音表示
        
        Args:
            text: 輸入文字
            
        Returns:
            str: 語音表示字串 (如 IPA 或拼音)
        """
        pass
    
    @abstractmethod
    def is_initialized(self) -> bool:
        """
        檢查後端是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """
        初始化後端
        
        此方法會在首次使用時自動呼叫，也可以手動呼叫以控制初始化時機。
        """
        pass
    
    @abstractmethod
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        取得快取統計資訊
        
        Returns:
            Dict[str, Any]: 快取統計，包含 hits, misses, size 等
        """
        pass
    
    @abstractmethod
    def clear_cache(self) -> None:
        """
        清除快取
        """
        pass

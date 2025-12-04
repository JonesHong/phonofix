"""
全域配置模組

提供統一的配置類別，控制日誌、計時等行為。

使用方式:
    from phonofix import UnifiedEngine
    
    # 簡單開啟 verbose 模式
    engine = UnifiedEngine(verbose=True)
    
    # 進階: 使用標準 logging 控制
    import logging
    logging.getLogger("phonofix").setLevel(logging.DEBUG)
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Callable, Any

from .utils.logger import get_logger, setup_logger


def configure_logging(verbose: bool = False) -> None:
    """
    根據 verbose 設定配置 logging
    
    Args:
        verbose: 是否開啟詳細日誌
    """
    if verbose:
        setup_logger(level=logging.DEBUG)
    else:
        # 不主動設定，讓使用者可以透過標準 logging 控制
        pass


@dataclass
class CorrectorConfig:
    """
    修正器配置類別 (進階用途)
    
    一般使用者只需要使用 verbose=True 即可。
    此類別提供更細緻的控制選項。
    
    屬性:
        verbose: 是否開啟詳細日誌
        on_timing: 計時回呼函數 (operation: str, elapsed: float) -> None
    
    使用範例:
        # 一般用法
        engine = UnifiedEngine(verbose=True)
        
        # 進階用法 - 自定義回呼
        def my_callback(op, elapsed):
            print(f"{op} took {elapsed:.3f}s")
        
        engine = UnifiedEngine(verbose=True, on_timing=my_callback)
    """
    
    # 日誌控制
    verbose: bool = False
    
    # 計時回呼
    on_timing: Optional[Callable[[str, float], None]] = None
    
    def __post_init__(self):
        """初始化後設定 logger"""
        configure_logging(self.verbose)


# 預設配置實例 (靜默模式)
DEFAULT_CONFIG = CorrectorConfig(verbose=False)

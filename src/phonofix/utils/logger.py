"""
日誌與計時工具模組

提供統一的日誌記錄和效能計時功能。

使用方式:
    from phonofix.utils import get_logger, TimingContext
    
    logger = get_logger()
    logger.debug("Debug message")
    
    with TimingContext("create_corrector", logger):
        # 執行操作
        pass
"""

import logging
import time
from typing import Optional, Callable, Any
from contextlib import contextmanager
from functools import wraps

# 定義專屬 logger 名稱
LOGGER_NAME = "phonofix"

# 預設格式
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
TIMING_FORMAT = "[%(name)s] %(message)s"


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    取得專案 Logger
    
    Args:
        name: 子 logger 名稱 (例如 "engine.chinese")
              如果為 None，返回根 logger
    
    Returns:
        logging.Logger: Logger 實例
        
    使用範例:
        logger = get_logger()  # 取得根 logger
        logger = get_logger("engine")  # 取得 phonofix.engine
    """
    if name:
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    return logging.getLogger(LOGGER_NAME)


def setup_logger(
    level: int = logging.WARNING,
    format_string: str = DEFAULT_FORMAT,
    handler: Optional[logging.Handler] = None,
) -> logging.Logger:
    """
    設定專案 Logger
    
    這個函數用於初始化 logger，通常在應用程式啟動時呼叫一次。
    
    Args:
        level: 日誌等級 (預設 WARNING)
        format_string: 日誌格式
        handler: 自定義 handler (預設為 StreamHandler)
    
    Returns:
        logging.Logger: 設定好的 Logger
        
    使用範例:
        # 開啟 debug 模式
        setup_logger(level=logging.DEBUG)
        
        # 自定義 handler
        file_handler = logging.FileHandler("app.log")
        setup_logger(handler=file_handler)
    """
    logger = get_logger()
    logger.setLevel(level)
    
    # 避免重複添加 handler
    if not logger.handlers:
        if handler is None:
            handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(format_string))
        logger.addHandler(handler)
    
    return logger


class TimingContext:
    """
    計時上下文管理器
    
    用於測量程式碼區塊的執行時間。
    
    使用範例:
        logger = get_logger()
        
        with TimingContext("create_corrector", logger) as timer:
            # 執行操作
            pass
        
        print(f"耗時: {timer.elapsed:.3f}s")
    """
    
    def __init__(
        self,
        operation: str,
        logger: Optional[logging.Logger] = None,
        level: int = logging.DEBUG,
        callback: Optional[Callable[[str, float], None]] = None,
    ):
        """
        初始化計時上下文
        
        Args:
            operation: 操作名稱 (用於日誌訊息)
            logger: Logger 實例 (可選)
            level: 日誌等級 (預設 DEBUG)
            callback: 計時完成時的回呼函數 (operation, elapsed) -> None
        """
        self.operation = operation
        self.logger = logger
        self.level = level
        self.callback = callback
        self.start_time: float = 0
        self.elapsed: float = 0
    
    def __enter__(self) -> "TimingContext":
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.elapsed = time.perf_counter() - self.start_time
        
        if self.logger and self.logger.isEnabledFor(self.level):
            self.logger.log(
                self.level,
                f"[Timing] {self.operation}: {self.elapsed:.4f}s"
            )
        
        if self.callback:
            self.callback(self.operation, self.elapsed)
        
        return None  # 不抑制例外


def log_timing(
    operation: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
    level: int = logging.DEBUG,
):
    """
    計時裝飾器
    
    用於測量函數的執行時間。
    
    使用範例:
        @log_timing("create_corrector")
        def create_corrector(self, terms):
            # 執行操作
            pass
        
        # 或自動使用函數名稱
        @log_timing()
        def some_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        op_name = operation or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal logger
            
            # 嘗試從 self 取得 logger
            if logger is None and args:
                instance = args[0]
                if hasattr(instance, "_logger"):
                    logger = instance._logger
                elif hasattr(instance, "logger"):
                    logger = instance.logger
            
            # 使用預設 logger
            actual_logger = logger or get_logger()
            
            with TimingContext(op_name, actual_logger, level):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# =============================================================================
# 便利函數
# =============================================================================

def enable_debug_logging() -> None:
    """
    啟用 debug 日誌
    
    便利函數，快速開啟 debug 模式。
    
    使用範例:
        from phonofix.utils import enable_debug_logging
        enable_debug_logging()
    """
    setup_logger(level=logging.DEBUG)


def enable_timing_logging() -> None:
    """
    啟用計時日誌
    
    便利函數，開啟 DEBUG 等級以顯示計時資訊。
    """
    setup_logger(level=logging.DEBUG, format_string=TIMING_FORMAT)

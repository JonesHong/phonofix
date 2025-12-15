"""
修正引擎抽象基類

定義所有語言修正引擎必須實作的介面。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from phonofix.core.term_config import TermDictInput
from phonofix.utils.logger import TimingContext, get_logger, setup_logger

if TYPE_CHECKING:
    from phonofix.core.protocols.corrector import CorrectorProtocol


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
    """

    _engine_name: str = "base"

    def _init_logger(
        self,
        verbose: bool = False,
        on_timing: Optional[Callable[[str, float], None]] = None,
    ) -> None:
        """
        初始化 Engine 的 logger 與（可選的）計時回呼。

        Args:
            verbose: 是否開啟 debug 日誌（會呼叫 setup_logger(level=DEBUG)）
            on_timing: 可選計時回呼（operation, elapsed）-> None

        說明：
        - Engine 本身不假設使用者一定要配置 logging，因此提供內建的最小化設定
        - 各語言 Engine 只要在 __init__ 先呼叫此方法即可統一行為
        """
        self._verbose = verbose
        self._timing_callback = on_timing

        if verbose:
            setup_logger(level=logging.DEBUG)

        self._logger = get_logger(f"engine.{self._engine_name}")

    def _log_timing(self, operation: str) -> TimingContext:
        """
        建立計時上下文（TimingContext）。

        用途：
        - 在 Engine 初始化或 create_corrector 等關鍵路徑量測耗時
        - 若提供 on_timing callback，可將耗時送到外部 observability 系統
        """
        return TimingContext(
            operation=operation,
            logger=self._logger,
            level=logging.DEBUG,
            callback=self._timing_callback,
        )

    @abstractmethod
    def create_corrector(self, term_dict: TermDictInput, **kwargs) -> "CorrectorProtocol":
        """
        依據 term_dict 建立語言 corrector。

        注意：
        - Engine 可能會在此步驟做 term_dict 正規化與索引建立（一次性）
        - 回傳的 corrector 應保持輕量，適合在多個 domain/tenant 下快速建立
        """
        pass

    @abstractmethod
    def is_initialized(self) -> bool:
        """回傳 Engine 是否已完成初始化（包含底層 backend 的初始化狀態）。"""
        pass

    @abstractmethod
    def get_backend_stats(self) -> Dict[str, Any]:
        """回傳 backend 的快取/統計資訊（進階用途：效能觀測、debug）。"""
        pass

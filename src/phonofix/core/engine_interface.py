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
        self._verbose = verbose
        self._timing_callback = on_timing

        if verbose:
            setup_logger(level=logging.DEBUG)

        self._logger = get_logger(f"engine.{self._engine_name}")

    def _log_timing(self, operation: str) -> TimingContext:
        return TimingContext(
            operation=operation,
            logger=self._logger,
            level=logging.DEBUG,
            callback=self._timing_callback,
        )

    @abstractmethod
    def create_corrector(self, term_dict: TermDictInput, **kwargs) -> "CorrectorProtocol":
        pass

    @abstractmethod
    def is_initialized(self) -> bool:
        pass

    @abstractmethod
    def get_backend_stats(self) -> Dict[str, Any]:
        pass


"""
中文修正模組

提供基於拼音的專有名詞拼寫修正功能：將文本與詞典統一映射到「拼音維度」，
再以模糊音變體（同音/近音）進行比對並替換回 canonical 拼寫。

適用於：ASR/LLM 輸出、或使用者手動輸入造成的拼寫錯誤。

安裝中文支援:
    pip install "phonofix[ch]"

主要類別:
- ChineseCorrector: 中文文本修正器
- ChineseFuzzyGenerator: 模糊音變體生成器
- ChinesePhoneticConfig: 拼音配置類別
- ChinesePhoneticUtils: 拼音工具函數類別

效能優化:
- 拼音/聲母/音節快取統一由 `ChinesePhoneticBackend` 管理
"""

from __future__ import annotations

import importlib
from typing import Any

CHINESE_INSTALL_HINT = (
    "缺少中文依賴。請執行:\n"
    "  pip install \"phonofix[ch]\"\n"
    "或安裝完整版本:\n"
    "  pip install \"phonofix[all]\""
)
INSTALL_HINT = CHINESE_INSTALL_HINT

_LAZY_IMPORTS = {
    "ChineseEngine": (".engine", "ChineseEngine"),
    "ChineseCorrector": (".corrector", "ChineseCorrector"),
    "ChineseFuzzyGenerator": (".fuzzy_generator", "ChineseFuzzyGenerator"),
    "ChinesePhoneticConfig": (".config", "ChinesePhoneticConfig"),
    "ChinesePhoneticUtils": (".utils", "ChinesePhoneticUtils"),
}

__all__ = [
    "ChineseEngine",
    "ChineseCorrector",
    "ChineseFuzzyGenerator",
    "ChinesePhoneticConfig",
    "ChinesePhoneticUtils",
    "CHINESE_INSTALL_HINT",
    "INSTALL_HINT",
]


def __getattr__(name: str) -> Any:
    """
    延遲載入語言模組內的主要符號（PEP 562）。

    目的：
    - `from phonofix.languages.chinese import ChineseEngine` 仍可用
    - 但不在 import 階段就載入較重的模組（加速啟動、避免不必要依賴初始化）
    """
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr_name = _LAZY_IMPORTS[name]
    module = importlib.import_module(module_path, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """讓 IDE/dir() 能看到延遲載入的符號清單。"""
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))

"""
日文修正模組

提供基於羅馬拼音（Romaji）的專有名詞拼寫修正功能：將文本與詞典統一映射到「發音維度」，
再以模糊音變體（長音/促音/羅馬字變體等）進行比對並替換回 canonical 拼寫。

適用於：ASR/LLM 輸出、或使用者手動輸入造成的拼寫錯誤。

安裝日文支援:
    pip install "phonofix[ja]"

主要類別:
- JapaneseCorrector: 日文文本修正器
- JapaneseFuzzyGenerator: 模糊音變體生成器
- JapanesePhoneticSystem: 羅馬拼音系統
- JapanesePhoneticConfig: 日文語音配置
- JapaneseTokenizer: 日文分詞器
"""

from __future__ import annotations

import importlib
from typing import Any

JAPANESE_INSTALL_HINT = (
    "缺少日文依賴。請執行:\n"
    "  pip install \"phonofix[ja]\"\n"
    "或安裝完整版本:\n"
    "  pip install \"phonofix[all]\""
)
INSTALL_HINT = JAPANESE_INSTALL_HINT

_LAZY_IMPORTS = {
    "JapaneseEngine": (".engine", "JapaneseEngine"),
    "JapanesePhoneticConfig": (".config", "JapanesePhoneticConfig"),
    "JapaneseCorrector": (".corrector", "JapaneseCorrector"),
    "JapaneseFuzzyGenerator": (".fuzzy_generator", "JapaneseFuzzyGenerator"),
    "JapanesePhoneticSystem": (".phonetic_impl", "JapanesePhoneticSystem"),
    "JapaneseTokenizer": (".tokenizer", "JapaneseTokenizer"),
}

__all__ = [
    "JapaneseEngine",
    "JapanesePhoneticConfig",
    "JapaneseCorrector",
    "JapaneseFuzzyGenerator",
    "JapanesePhoneticSystem",
    "JapaneseTokenizer",
    "JAPANESE_INSTALL_HINT",
    "INSTALL_HINT",
]


def __getattr__(name: str) -> Any:
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr_name = _LAZY_IMPORTS[name]
    module = importlib.import_module(module_path, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))

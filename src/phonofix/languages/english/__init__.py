"""
英文修正模組

提供基於 IPA 的專有名詞拼寫修正功能：將文本與詞典統一映射到「發音維度」，
再以模糊音變體進行比對並替換回 canonical 拼寫。

適用於：ASR/LLM 輸出、或使用者手動輸入造成的拼寫錯誤。

安裝英文支援:
    pip install "phonofix[en]"
注意：英文語音功能依賴系統套件 espeak-ng（詳見 README）。

主要類別:
- EnglishCorrector: 英文文本修正器
- EnglishFuzzyGenerator: 模糊音變體生成器
- EnglishPhoneticSystem: IPA 發音系統
- EnglishPhoneticConfig: 英文語音配置
- EnglishTokenizer: 英文分詞器

效能優化:
- 英文 IPA 的 G2P / 初始化 / 快取皆由 Backend 單例負責（`phonofix.backend.get_english_backend`）
"""

from __future__ import annotations

import importlib
from typing import Any

ENGLISH_INSTALL_HINT = (
    "缺少英文依賴。請執行:\n"
    "  pip install \"phonofix[en]\"\n"
    "或安裝完整版本:\n"
    "  pip install \"phonofix[all]\"\n\n"
    "注意: 英文支援還需要安裝 espeak-ng 系統套件:\n"
    "  Windows: https://github.com/espeak-ng/espeak-ng/releases\n"
    "  macOS: brew install espeak-ng\n"
    "  Linux: apt install espeak-ng"
)
INSTALL_HINT = ENGLISH_INSTALL_HINT

_LAZY_IMPORTS = {
    "EnglishEngine": (".engine", "EnglishEngine"),
    "EnglishCorrector": (".corrector", "EnglishCorrector"),
    "EnglishFuzzyGenerator": (".fuzzy_generator", "EnglishFuzzyGenerator"),
    "EnglishPhoneticSystem": (".phonetic_impl", "EnglishPhoneticSystem"),
    "EnglishPhoneticConfig": (".config", "EnglishPhoneticConfig"),
    "EnglishTokenizer": (".tokenizer", "EnglishTokenizer"),
}

__all__ = [
    "EnglishEngine",
    "EnglishCorrector",
    "EnglishFuzzyGenerator",
    "EnglishPhoneticSystem",
    "EnglishPhoneticConfig",
    "EnglishTokenizer",
    "ENGLISH_INSTALL_HINT",
    "INSTALL_HINT",
]


def __getattr__(name: str) -> Any:
    """
    延遲載入語言模組內的主要符號（PEP 562）。

    目的：
    - 保持 `phonofix.languages.english` 的 import 輕量
    - 避免在 import 階段就觸發 phonemizer/espeak-ng 的初始化
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

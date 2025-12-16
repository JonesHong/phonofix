"""
phonofix - 多語言語音相似修正器 (Multi-Language Phonetic Corrector)

核心概念（以中文為基準）：
- 使用者提供專有名詞字典（canonical + aliases）
- 系統把拼寫統一轉到「發音表示」維度建立比對群體（並做 auto-fuzzy 擴充）
- 文本進來同樣轉到發音維度比對，命中後回到原文字串做替換

官方入口（穩定 API）：
- `phonofix.EnglishEngine`
- `phonofix.ChineseEngine`
- `phonofix.JapaneseEngine`

此模組刻意維持 import 輕量：
- 不在 `import phonofix` 階段就載入各語言引擎與其重依賴（phonemizer / pypinyin / cutlet / fugashi 等）。
- 透過 PEP 562 `__getattr__` 在「第一次使用到某個符號」時才延遲載入。
"""

from __future__ import annotations

import importlib
from typing import Any

# =============================================================================
# Lazy imports（PEP 562）
# =============================================================================

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Engines（官方入口，語言 package 內也會再做一次延遲載入）
    "EnglishEngine": ("phonofix.languages.english", "EnglishEngine"),
    "ChineseEngine": ("phonofix.languages.chinese", "ChineseEngine"),
    "JapaneseEngine": ("phonofix.languages.japanese", "JapaneseEngine"),
    # Backend（進階用途）
    "PhoneticBackend": ("phonofix.backend", "PhoneticBackend"),
    "EnglishPhoneticBackend": ("phonofix.backend", "EnglishPhoneticBackend"),
    "ChinesePhoneticBackend": ("phonofix.backend", "ChinesePhoneticBackend"),
    "JapanesePhoneticBackend": ("phonofix.backend", "JapanesePhoneticBackend"),
    "get_english_backend": ("phonofix.backend", "get_english_backend"),
    "get_chinese_backend": ("phonofix.backend", "get_chinese_backend"),
    "get_japanese_backend": ("phonofix.backend", "get_japanese_backend"),
    # Protocols（進階用途）
    "CorrectorProtocol": ("phonofix.core.protocols.corrector", "CorrectorProtocol"),
    "ContextAwareCorrectorProtocol": ("phonofix.core.protocols.corrector", "ContextAwareCorrectorProtocol"),
    # Events（進階用途）
    "CorrectionEvent": ("phonofix.core.events", "CorrectionEvent"),
    "CorrectionEventHandler": ("phonofix.core.events", "CorrectionEventHandler"),
}

# =============================================================================
# 日誌工具
# =============================================================================
from phonofix.utils.logger import enable_debug_logging, enable_timing_logging, get_logger

__all__ = [
    # Engines
    "EnglishEngine",
    "ChineseEngine",
    "JapaneseEngine",
    # Logging
    "get_logger",
    "enable_debug_logging",
    "enable_timing_logging",
    # Backend (advanced)
    "get_english_backend",
    "get_chinese_backend",
    "get_japanese_backend",
    "PhoneticBackend",
    "EnglishPhoneticBackend",
    "ChinesePhoneticBackend",
    "JapanesePhoneticBackend",
    # Protocols (advanced)
    "CorrectorProtocol",
    "ContextAwareCorrectorProtocol",
    # Events (advanced)
    "CorrectionEvent",
    "CorrectionEventHandler",
]

__version__ = "0.3.0"


def __getattr__(name: str) -> Any:
    """
    延遲載入頂層公開符號（PEP 562）。

    目的：
    - 讓 `import phonofix` 保持輕量、避免自動觸發重依賴初始化
    - 仍保留 `phonofix.EnglishEngine` 等穩定 API
    """
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr_name = _LAZY_IMPORTS[name]
    module = importlib.import_module(module_path)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """讓 IDE/dir() 能看到延遲載入的符號清單。"""
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))

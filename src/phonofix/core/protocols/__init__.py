"""
Protocols（契約）集中管理

此資料夾放置跨模組共用的最小介面契約（Protocols），
避免分散在 correction/ 等特定功能資料夾造成定位混淆。
"""

from .corrector import ContextAwareCorrectorProtocol, CorrectorProtocol
from .fuzzy import FuzzyGeneratorProtocol

__all__ = [
    "CorrectorProtocol",
    "ContextAwareCorrectorProtocol",
    "FuzzyGeneratorProtocol",
]


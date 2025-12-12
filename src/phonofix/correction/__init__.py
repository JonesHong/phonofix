"""
Correction 模組

包含：
- 組合型修正器（UnifiedCorrector）
- 裝飾型修正器（StreamingCorrector）
"""

from .unified_corrector import UnifiedCorrector
from .streaming_corrector import (
    StreamingCorrector,
    ChunkStreamingCorrector,
    StreamingResult,
    create_streaming_corrector,
    calculate_safe_overlap,
)

__all__ = [
    # Correctors
    'UnifiedCorrector',
    'StreamingCorrector',
    'ChunkStreamingCorrector',
    'StreamingResult',
    'create_streaming_corrector',
    'calculate_safe_overlap',
]

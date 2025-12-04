"""
Correction 模組

包含：
- Protocol 定義（CorrectorProtocol）
- 組合型修正器（UnifiedCorrector）
- 裝飾型修正器（StreamingCorrector）
"""

from .protocol import CorrectorProtocol
from .unified_corrector import UnifiedCorrector
from .streaming_corrector import (
    StreamingCorrector,
    ChunkStreamingCorrector,
    StreamingResult,
    create_streaming_corrector,
    calculate_safe_overlap,
)

__all__ = [
    # Protocol
    'CorrectorProtocol',
    
    # Correctors
    'UnifiedCorrector',
    'StreamingCorrector',
    'ChunkStreamingCorrector',
    'StreamingResult',
    'create_streaming_corrector',
    'calculate_safe_overlap',
]

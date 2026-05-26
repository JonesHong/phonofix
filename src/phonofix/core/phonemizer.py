"""Phonemizer Protocol + Phoneme dataclass (v0.4.0 Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Phoneme:
    """單一音素的不可變表示。"""

    value: str  # IPA-like / pinyin / katakana / jamo
    language: str  # zh | ja | en | ko
    weight: float = 0.0  # confusion rule 自定義權重 (default 0.0)
    # 後續 Phase 3 可加 features 欄位（articulation place / manner）


@runtime_checkable
class Phonemizer(Protocol):
    """Per-language G2P + phonetic operations."""

    language: str
    name: str

    def phonemize(self, text: str) -> list[Phoneme]:
        """Text → phoneme sequence."""
        ...

    def confusion(self, p: Phoneme) -> set[Phoneme]:
        """Get confusable phonemes for `p` (per-language confusion rules)."""
        ...

    def cost(self, a: Phoneme, b: Phoneme) -> float:
        """Distance between two phonemes (0.0 = identical, 1.0 = totally different)."""
        ...

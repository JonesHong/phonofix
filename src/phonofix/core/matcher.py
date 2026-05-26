"""PhoneticMatcher — language-agnostic matching layer (v0.4.0 Phase 2 skeleton)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional

if TYPE_CHECKING:
    from phonofix.core.phonemizer import Phonemizer  # W1 提供
    # 不直接 import DictSchema 避免循環 — 用 dict | Any annotation


class PhoneticMatcher:
    """
    語言無關 phonetic matching + active replacement + protection arbitration.

    Phase 2 = skeleton 階段，所有 method body 為 NotImplementedError；
    Phase 3 補完 Tier 1-4 演算法。
    """

    def __init__(
        self,
        phonemizer: "Phonemizer",
        dictionary: Any,  # dict | path | DictSchema instance
        on_event: Optional[Callable[[str, dict], None]] = None,
    ) -> None:
        self.phonemizer = phonemizer
        self.dictionary = dictionary
        self.on_event = on_event
        # internal: AC index, protection mask, mutation set, etc — Phase 3

    def correct(self, text: str) -> str:
        """Single-shot correction. SPEC.md §1."""
        raise NotImplementedError("Phase 3")

    def correct_batch(self, texts: Iterable[str]) -> list[str]:
        """Batch correction with shared protection cache + AC scan."""
        raise NotImplementedError("Phase 3")

    def feed(self, chunk: str) -> str:
        """Streaming correction. See SPEC.md §3 for buffer/flush semantics."""
        raise NotImplementedError("Phase 4")

    def flush(self) -> str:
        """Explicit flush of streaming buffer."""
        raise NotImplementedError("Phase 4")

    def add_terms(self, entries: Iterable[dict]) -> None:
        """Hot-reload: append + atomic swap-rebuild."""
        raise NotImplementedError("Phase 4")

    def remove_terms(self, canonical: Iterable[str]) -> None:
        """Hot-reload: remove + atomic swap-rebuild."""
        raise NotImplementedError("Phase 4")

    def explain(self, text: str) -> dict:
        """Per-candidate score breakdown. See SPEC.md §2 for output schema + 5 golden."""
        raise NotImplementedError("Phase 3")

    def diagnose(self) -> dict:
        """version / dict_size / mem_rss / backends_loaded. See SPEC.md §5."""
        raise NotImplementedError("Phase 3")

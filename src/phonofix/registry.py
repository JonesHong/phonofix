"""G2P backend + tokenizer registry — Phase 1 skeleton."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class G2PBackend(Protocol):
    """Protocol for a G2P (grapheme-to-phoneme) backend."""

    name: str
    language: str  # "zh" | "ja" | "en" | "ko"

    def phonemize(self, text: str) -> list[tuple[str, ...]]:
        """Convert text to a list of phoneme tuples (one tuple per token)."""
        ...


@runtime_checkable
class Tokenizer(Protocol):
    """Protocol for a language tokenizer."""

    name: str
    language: str  # "zh" | "ja" | "en" | "ko"
    mode: str  # "char" | "word"

    def tokenize(self, text: str) -> list[str]:
        """Segment text into tokens."""
        ...


# ---------------------------------------------------------------------------
# Internal registries
# ---------------------------------------------------------------------------

_G2P_REGISTRY: dict[str, G2PBackend] = {}
_TOKENIZER_REGISTRY: dict[str, Tokenizer] = {}


def _g2p_key(language: str, name: str) -> str:
    return f"{language}:{name}"


def _tokenizer_key(language: str, name: str) -> str:
    return f"{language}:{name}"


# ---------------------------------------------------------------------------
# G2P registration + lookup
# ---------------------------------------------------------------------------


def register_g2p(backend: G2PBackend) -> None:
    """Register a G2P backend. Key = f'{language}:{name}'.

    Phase 2 will implement; Phase 1 stub raises NotImplementedError.
    """
    raise NotImplementedError("register_g2p — Phase 2 implementation pending")


def get_g2p(language: str, name: str | None = None) -> G2PBackend:
    """Lookup a registered G2P backend.

    If *name* is None, return the default backend for *language*
    (based on DEFAULT_G2P in registry_defaults).

    Phase 2 will implement; Phase 1 stub raises NotImplementedError.
    """
    raise NotImplementedError("get_g2p — Phase 2 implementation pending")


# ---------------------------------------------------------------------------
# Tokenizer registration + lookup
# ---------------------------------------------------------------------------


def register_tokenizer(tokenizer: Tokenizer) -> None:
    """Register a tokenizer. Key = f'{language}:{name}'.

    Phase 2 will implement; Phase 1 stub raises NotImplementedError.
    """
    raise NotImplementedError("register_tokenizer — Phase 2 implementation pending")


def get_tokenizer(language: str, name: str | None = None) -> Tokenizer:
    """Lookup a registered tokenizer.

    If *name* is None, return the default tokenizer for *language*.

    Phase 2 will implement; Phase 1 stub raises NotImplementedError.
    """
    raise NotImplementedError("get_tokenizer — Phase 2 implementation pending")


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------


def list_backends() -> dict:
    """Return a snapshot of all registered backends and tokenizers.

    Phase 2 will implement; Phase 1 stub raises NotImplementedError.
    """
    raise NotImplementedError("list_backends — Phase 2 implementation pending")

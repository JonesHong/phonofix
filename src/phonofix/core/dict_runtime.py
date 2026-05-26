"""Dict runtime — atomic swap-rebuild for hot reload (Phase 4)."""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from phonofix.core.dict_schema import Term


@dataclass(frozen=True)
class DictSnapshot:
    """Immutable point-in-time dict state.

    Callers hold a snapshot reference; snapshot is never mutated after creation.
    Frozen dataclass → hashable + accidental mutation raises FrozenInstanceError.
    """

    version: int
    terms: tuple  # tuple[Term, ...] — frozen, order-stable


class DictRuntime:
    """Holds current DictSnapshot + supports atomic add/remove via swap-rebuild.

    Reader 拿 snapshot：always consistent (snapshot is immutable).
    Writer add/remove：rebuild full new snapshot + atomic pointer swap.

    Thread safety: reader-writer model.
    - Multiple readers can call get() concurrently — no lock needed (CPython GIL
      guarantees atomic pointer reads; snapshot is immutable so no torn state).
    - Writers acquire _lock before rebuilding to serialize mutations.
    """

    def __init__(
        self,
        initial_terms: Iterable[Term] = (),
        build_fn: Optional[Callable[[tuple], object]] = None,
    ) -> None:
        """
        Args:
            initial_terms: iterable of Term instances.
            build_fn: optional callable(terms_tuple) → auxiliary index object
                      (e.g. AhoCorasick engine). Stored in DictSnapshot as
                      an extra attribute when provided.
        """
        self._build_fn = build_fn
        self._lock = threading.RLock()
        self._snapshot: DictSnapshot = self._build(tuple(initial_terms), version=0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build(self, terms: tuple, version: int) -> DictSnapshot:
        """Pure function: produce a new DictSnapshot from a terms tuple."""
        snap = DictSnapshot(version=version, terms=terms)
        if self._build_fn is not None:
            # Attach auxiliary index as a non-frozen attribute via object.__setattr__
            # (DictSnapshot is frozen; auxiliary index is read-only after build)
            object.__setattr__(snap, "_aux_index", self._build_fn(terms))
        return snap

    def _next_version(self) -> int:
        """Return current version + 1 (caller must hold _lock)."""
        return self._snapshot.version + 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self) -> DictSnapshot:
        """O(1) read — returns current snapshot pointer (immutable).

        No lock required: CPython's GIL guarantees atomic pointer load,
        and DictSnapshot is frozen so readers never see torn state.
        """
        return self._snapshot

    def add_terms(self, entries: Iterable[Term]) -> DictSnapshot:
        """Atomic add — rebuild new snapshot under lock, swap pointer.

        Duplicate canonicals (entries whose canonical already exists in the
        current snapshot) are silently deduplicated: the *existing* term is
        kept and the incoming duplicate is ignored.

        Returns:
            The new DictSnapshot (also accessible via get() afterwards).
        """
        new_entries = list(entries)
        with self._lock:
            existing = {t.canonical: t for t in self._snapshot.terms}
            for term in new_entries:
                if term.canonical not in existing:
                    existing[term.canonical] = term
                # duplicate: keep existing, ignore incoming
            new_terms = tuple(existing.values())
            new_snap = self._build(new_terms, version=self._next_version())
            self._snapshot = new_snap
        return new_snap

    def remove_terms(self, canonicals: Iterable[str]) -> DictSnapshot:
        """Atomic remove by canonical string.

        Non-existent canonicals are silently ignored (no-op, no raise).

        Returns:
            The new DictSnapshot (also accessible via get() afterwards).
        """
        to_remove = set(canonicals)
        with self._lock:
            new_terms = tuple(t for t in self._snapshot.terms if t.canonical not in to_remove)
            new_snap = self._build(new_terms, version=self._next_version())
            self._snapshot = new_snap
        return new_snap

    def stats(self) -> dict:
        """Return runtime statistics for the current snapshot.

        Returns:
            dict with keys:
                version (int): current snapshot version
                term_count (int): number of terms in snapshot
                mem_bytes_estimate (int): rough in-memory size estimate in bytes
        """
        snap = self._snapshot
        # Rough estimate: sys.getsizeof(tuple) + sum of getsizeof per term
        mem = sys.getsizeof(snap.terms)
        for t in snap.terms:
            mem += sys.getsizeof(t)
            mem += sys.getsizeof(t.canonical)
            mem += sys.getsizeof(t.aliases)
            mem += sys.getsizeof(t.keywords)
        return {
            "version": snap.version,
            "term_count": len(snap.terms),
            "mem_bytes_estimate": mem,
        }

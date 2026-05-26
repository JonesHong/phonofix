"""pyahocorasick adapter — replaces self-impl utils/aho_corasick.py in Phase 3.

phonofix 場景實測（codex-review-2026-05-26.md）:
  - normal query ~7-9× faster than self-impl
  - delete-1 query ~5× faster
  - memory 100×+ smaller
"""

from __future__ import annotations

from typing import Any, Iterator

import ahocorasick


class ACEngine:
    """
    Phonofix 統一 AC 介面 — wraps pyahocorasick Automaton.

    pyahocorasick.Automaton.iter() yields (end_index_inclusive, stored_value).
    This adapter converts to phonofix unified format:
        (start, end_exclusive, matched_word, payload)

    Usage:
        ac = ACEngine()
        ac.add("北車", payload={"canonical": "台北車站"})
        ac.build()
        for start, end, word, value in ac.find_all("這是台北車站的時刻表"):
            print(start, end, word, value)
    """

    def __init__(self) -> None:
        self._automaton: ahocorasick.Automaton = ahocorasick.Automaton()
        self._built: bool = False
        self._count: int = 0

    def add(self, word: str, payload: Any = None) -> None:
        """Add pattern with optional payload.

        If the same word is added twice, the second payload overwrites the first
        (pyahocorasick default behaviour).  Empty words are silently ignored.
        """
        if not word:
            return
        # Store (word, payload) so find_all can recover the matched word from
        # end_index alone, without a second lookup pass.
        # get() raises KeyError when the key is absent; pass a sentinel default.
        prev = self._automaton.get(word, None)
        self._automaton.add_word(word, (word, payload))
        if prev is None:
            self._count += 1

    def build(self) -> None:
        """Finalize trie + compute failure links. Required before find_all."""
        self._automaton.make_automaton()
        self._built = True

    def find_all(self, text: str) -> Iterator[tuple[int, int, str, Any]]:
        """Yield (start, end_exclusive, matched_word, payload) tuples.

        Raises:
            RuntimeError: if called before build().
        """
        if not self._built:
            raise RuntimeError("ACEngine.build() must be called before find_all()")
        if self._count == 0 or not text:
            return
        for end_idx, (word, payload) in self._automaton.iter(text):
            start = end_idx - len(word) + 1
            end = end_idx + 1  # convert inclusive → exclusive
            yield start, end, word, payload

    def __len__(self) -> int:
        """Number of distinct patterns added."""
        return self._count

    @property
    def is_built(self) -> bool:
        return self._built

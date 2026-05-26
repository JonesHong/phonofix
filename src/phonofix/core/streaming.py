"""Streaming feed/flush state machine (Phase 4).

Implements SPEC.md §3 streaming contract:
- Tail buffer prevents cross-chunk boundary misses
- stdlib re (non-overlapped) per C-1 benchmark (3.2M chars/s vs regex 1.44M)
- Span-level dedup: same (start, end) offset pair emitted at most once per session
- Retroactive correction is NOT supported (SPEC §3.7)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

# scan_fn signature: (text: str) -> list[tuple[start, end, matched, replacement]]
# Caller injects this; StreamBuffer never imports PhoneticMatcher to avoid cycles.
ScanFn = Callable[[str], list[tuple[int, int, str, str]]]


@dataclass
class StreamBuffer:
    """
    Stateful streaming buffer.

    Public API::

        buf = StreamBuffer(scan_fn, max_alias_len=10, window_chars=20)
        out1 = buf.feed("chunk1")
        out2 = buf.feed("chunk2")
        tail  = buf.flush()   # emit remaining; idempotent on second call

    Parameters
    ----------
    scan_fn:
        Function ``(text) -> [(start, end, matched, replacement), ...]``
        that locates all replacement candidates in *text*.  Positions are
        0-based byte-compatible offsets into *text*.
    max_alias_len:
        Length of the longest alias in the dictionary.  Used to compute
        ``tail_size``.
    window_chars:
        Context-window radius in characters.  Added to ``max_alias_len``
        to derive ``tail_size``.
    language_mode:
        ``"char"`` (default, zh/ja/ko) or ``"word"`` (en).
        In ``"word"`` mode ``safe_prefix`` is trimmed to the last word
        boundary so no word is split mid-token.
    """

    scan_fn: ScanFn
    max_alias_len: int = 10
    window_chars: int = 20
    language_mode: str = "char"  # "char" (zh/ja/ko) | "word" (en)

    _buffer: str = field(default="", init=False, repr=False)
    # Absolute offsets of already-emitted spans for span-level dedup.
    # Key: (abs_start, abs_end) in total stream coordinates.
    _emitted_spans: set[tuple[int, int]] = field(default_factory=set, init=False, repr=False)
    # Total chars confirmed and emitted so far (= cumulative safe_prefix lengths).
    _total_offset: int = field(default=0, init=False, repr=False)
    # Whether flush() has already drained the buffer (idempotency guard).
    _flushed: bool = field(default=False, init=False, repr=False)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def tail_size(self) -> int:
        """Characters kept in the tail buffer after each feed() call."""
        return min(self.max_alias_len + self.window_chars, 512)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def feed(self, chunk: str) -> str:
        """Append *chunk*, scan, emit safely-confirmed prefix, keep tail.

        Returns the corrected text for the confirmed portion of this chunk.
        The returned length may be shorter than ``len(chunk)`` because the
        tail is held back for the next call.
        """
        self._flushed = False
        self._buffer += chunk

        # Initial safe boundary — anything beyond this is "tail" that
        # straddles into the next chunk.
        safe_end = max(len(self._buffer) - self.tail_size, 0)

        if safe_end == 0:
            return ""

        # Scan whole buffer; hits that begin inside safe region but end past
        # it are CROSSING — their starting char must stay in tail so next
        # feed() can re-scan the alias intact.
        hits = sorted(self.scan_fn(self._buffer), key=lambda h: h[0])
        for start, end, _, _ in hits:
            if start < safe_end < end:
                safe_end = start  # retract so alias-start stays in tail
                break

        if safe_end == 0:
            return ""

        # Word-mode tail-trim to last whitespace boundary.
        if self.language_mode == "word" and safe_end < len(self._buffer):
            m = re.search(r"\s+\S*$", self._buffer[:safe_end])
            if m:
                safe_end = m.start()

        if safe_end == 0:
            return ""

        output = self._apply_replacements(self._buffer[:safe_end])

        self._total_offset += safe_end
        self._buffer = self._buffer[safe_end:]
        return output

    def flush(self) -> str:
        """Emit remaining buffer (no more chunks coming).

        Idempotent — second call returns ``""`` without re-emitting.
        Caller MUST invoke ``flush()`` at end of stream; un-flushed tail
        is never emitted automatically (SPEC §3.3).
        """
        if self._flushed or not self._buffer:
            self._flushed = True
            return ""

        remaining = self._buffer
        output = self._apply_replacements(remaining)
        self._total_offset += len(remaining)
        self._buffer = ""
        self._flushed = True
        return output

    def reset(self) -> None:
        """Clear all state — for caller reuse between independent sessions."""
        self._buffer = ""
        self._emitted_spans = set()
        self._total_offset = 0
        self._flushed = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_replacements(self, text: str) -> str:
        """Run scan_fn on *text*, apply non-overlapping replacements in order.

        Span-level deduplication: any (abs_start, abs_end) pair that was
        already emitted in this session is skipped.
        """
        hits = self.scan_fn(text)
        if not hits:
            return text

        # Sort by start position to guarantee left-to-right non-overlapping
        # application (scan_fn may not guarantee ordering).
        hits = sorted(hits, key=lambda h: h[0])

        parts: list[str] = []
        cursor = 0

        for start, end, _matched, replacement in hits:
            # Absolute stream positions for dedup.
            abs_start = self._total_offset + start
            abs_end = self._total_offset + end
            span_key = (abs_start, abs_end)

            # Skip if already emitted (span-level dedup).
            if span_key in self._emitted_spans:
                continue

            # Skip overlapping hits (prior hit already advanced cursor).
            if start < cursor:
                continue

            # Append literal text between cursor and this hit.
            if start > cursor:
                parts.append(text[cursor:start])

            parts.append(replacement)
            self._emitted_spans.add(span_key)
            cursor = end

        # Append any trailing literal text.
        if cursor < len(text):
            parts.append(text[cursor:])

        return "".join(parts)

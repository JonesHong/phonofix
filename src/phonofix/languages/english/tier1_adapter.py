"""en Tier 1 adapter — Double Metaphone hash lookup, word-level scanning.

英文 confusion 重點：
- Spelling variants: Smith / Smyth, Catherine / Katherine
- ASR substitutions: night / knight, peace / piece
- LLM 同音字選錯
"""

from __future__ import annotations

import re
from typing import Iterable

try:
    from phonofix.languages.english.metaphone import metaphone_key

    _HAS_METAPHONE = True
except ImportError:
    _HAS_METAPHONE = False

# Word tokenization — split on whitespace + punctuation boundaries
_WORD_RE = re.compile(r"\b[\w']+\b", re.UNICODE)


def build_index(aliases: Iterable[str]) -> dict:
    """
    Build {metaphone_primary_key → [original aliases]} index.

    Multi-word aliases get keyed by space-joined metaphone keys.
    """
    if not _HAS_METAPHONE:
        return {}

    idx: dict[str, list[str]] = {}
    for alias in aliases:
        words = _WORD_RE.findall(alias)
        if not words:
            continue
        # Composite key: space-join primary metaphone of each word
        key_parts = []
        for w in words:
            primary, _ = metaphone_key(w)
            if primary:
                key_parts.append(primary)
        if key_parts:
            key = " ".join(key_parts)
            idx.setdefault(key, []).append(alias)
    return idx


def _scan_word_spans(text: str) -> list[tuple[int, int, str]]:
    """Return [(start, end, word), ...] of word tokens in text."""
    return [(m.start(), m.end(), m.group()) for m in _WORD_RE.finditer(text)]


def apply(text: str, index: dict) -> list[tuple[int, int, str, str]]:
    """
    Word-level sliding window. Build composite metaphone of each N-word window,
    check against index. Returns (start, end, matched_text, original_alias).
    """
    if not _HAS_METAPHONE or not index:
        return []

    word_spans = _scan_word_spans(text)
    if not word_spans:
        return []

    # Determine max window size from index keys (number of words)
    max_window = max((len(k.split()) for k in index.keys()), default=1)

    hits = []
    for window_size in range(1, max_window + 1):
        for i in range(len(word_spans) - window_size + 1):
            window = word_spans[i : i + window_size]
            words = [w for _, _, w in window]
            keys: list[str] | None = []
            for w in words:
                primary, _ = metaphone_key(w)
                if primary:
                    keys.append(primary)
                else:
                    keys = None
                    break
            if not keys:
                continue
            composite = " ".join(keys)
            if composite in index:
                for alias in index[composite]:
                    start = window[0][0]
                    end = window[-1][1]
                    matched = text[start:end]
                    if matched.lower() != alias.lower():  # skip literal-AC hits
                        hits.append((start, end, matched, alias))
    return hits

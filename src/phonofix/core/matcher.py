"""PhoneticMatcher — language-agnostic matching layer (Phase 5 integration).

v0.4.0 fuzzy wire status:
  Tier 3 — AC delete-1 expansion: WIRED  (in _build_aux_index + correct())
  Tier 2 — mutation set (phoneme swap): DEFERRED to v0.4.1
  Tier 1 — per-language hash key (zh canonical_key / ja / en metaphone): DEFERRED to v0.4.1

correct() emits:
  match.exact   — literal AC hit (is_original=True)
  match.fuzzy   — delete-1 expansion hit (is_original=False), tier="delete-1"
  match.protected — span overlaps canonical auto-protect mask
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional

from phonofix.core.ac_expansion import filter_hits
from phonofix.core.dict_runtime import DictRuntime, DictSnapshot
from phonofix.core.dict_schema import DictV2, Term, TermMode, validate_dict
from phonofix.core.event_queue import AsyncEventQueue, EventRecord, get_trace_id
from phonofix.core.streaming import StreamBuffer

if TYPE_CHECKING:
    from phonofix.core.phonemizer import Phonemizer


def _load_dict_v2(dictionary: Any) -> list[Term]:
    """
    Normalize any dictionary input into a list of Term instances.

    Accepted forms:
    - DictV2 instance                                  → terms directly
    - dict with version=2 (raw validated DictV2 dict)  → validate + terms
    - list[Term]                                       → pass through
    - dict (legacy: {canonical: {aliases:[...]}} or
      {canonical: [aliases]})                          → auto-upgrade → validate → terms
    - list[str]                                        → auto-upgrade (bare canonical list)
    - list[dict]                                       → auto-upgrade (term dict list)
    - {} (empty dict)                                  → empty terms
    """
    if isinstance(dictionary, DictV2):
        return list(dictionary.terms)

    if isinstance(dictionary, list):
        # list[Term] case
        if all(isinstance(t, Term) for t in dictionary):
            return list(dictionary)
        # list[str] or list[dict] — auto-upgrade
        return _auto_upgrade_list(dictionary)

    if isinstance(dictionary, dict):
        if not dictionary:
            return []
        # Check if it looks like a v2 raw dict
        if dictionary.get("version") == 2:
            validated = validate_dict(dictionary)
            return list(validated.terms)
        # Legacy dict: {canonical: {aliases, keywords, ...}} or {canonical: [aliases]}
        return _auto_upgrade_legacy_dict(dictionary)

    # Fallback: empty
    return []


def _auto_upgrade_list(raw_list: list) -> list[Term]:
    """Auto-upgrade list[str] or list[dict] to list[Term]."""
    terms = []
    for item in raw_list:
        if isinstance(item, str):
            # Bare canonical: no aliases → protect mode (just mark it as canonical)
            # Per PHASE2-COMPAT-DESIGN §4: bare canonical → mode=replace, aliases=[]
            # However mode=replace requires aliases. Use protect mode for bare canonicals.
            # Actually per spec: a bare canonical with no aliases is a protect entry.
            terms.append(Term(canonical=item, mode=TermMode.PROTECT))
        elif isinstance(item, dict) and "canonical" in item:
            raw_mode = item.get("mode", "replace")
            try:
                mode = TermMode(raw_mode)
            except ValueError:
                mode = TermMode.REPLACE
            aliases = list(item.get("aliases") or [])
            keywords = list(item.get("keywords") or [])
            weight = float(item.get("weight") or 0.0)
            if mode == TermMode.REPLACE and not aliases:
                # No aliases → treat as protect
                mode = TermMode.PROTECT
                aliases = []
                keywords = []
                weight = 0.0
            terms.append(
                Term(
                    canonical=item["canonical"],
                    mode=mode,
                    aliases=aliases,
                    keywords=keywords,
                    weight=weight,
                )
            )
    return terms


def _auto_upgrade_legacy_dict(d: dict) -> list[Term]:
    """Auto-upgrade legacy {canonical: {aliases/list}} dict to list[Term].

    NOTE: alias == canonical is intentionally preserved (not filtered out).
    Rationale: a caller may register the canonical as its own alias to enable
    Tier 3 delete-1 fuzzy matching on the canonical form itself.
    The canonical auto-protect mask in correct() prevents double-replacement
    when the canonical already appears literally in the input text.
    """
    terms = []
    for canonical, value in d.items():
        if not isinstance(canonical, str):
            continue
        if isinstance(value, list):
            aliases = [str(a) for a in value if isinstance(a, str)]
            keywords = []
            weight = 0.0
        elif isinstance(value, dict):
            raw_aliases = list(value.get("aliases") or [])
            aliases = [str(a) for a in raw_aliases]
            keywords = list(value.get("keywords") or [])
            weight = float(value.get("weight") or 0.0)
        else:
            aliases = []
            keywords = []
            weight = 0.0

        if aliases:
            terms.append(
                Term(
                    canonical=canonical,
                    mode=TermMode.REPLACE,
                    aliases=aliases,
                    keywords=keywords,
                    weight=weight,
                )
            )
        else:
            # No aliases → protect
            terms.append(Term(canonical=canonical, mode=TermMode.PROTECT))
    return terms


_MIN_DELETE1_PATTERN_LEN = 2  # delete-1 variants shorter than this are skipped


_TIER1_DISPATCH = {
    "zh": "phonofix.languages.chinese.tier1_adapter",
    "ja": "phonofix.languages.japanese.tier1_adapter",
    "en": "phonofix.languages.english.tier1_adapter",
    "ko": "phonofix.languages.korean.tier1_adapter",
}


def _build_aux_index(terms: tuple, language: Optional[str] = None) -> dict:
    """
    Build auxiliary indexes from a tuple of Term instances.

    Returns dict with keys:
    - "ac": ACEngine (built with delete-1 expansion, only replace-mode aliases)
    - "alias_to_term": dict mapping alias_str -> Term
    - "tier1_apply": optional per-language Tier 1 callable (text, index) -> hits
    - "tier1_index": optional per-language Tier 1 build_index result

    Delete-1 pattern minimum length: patterns shorter than _MIN_DELETE1_PATTERN_LEN
    are not registered to avoid false positives from single-character hits.
    """
    from phonofix.core.ac_expansion import expand_delete_1
    from phonofix.utils.ac_pyahocorasick import ACEngine

    alias_to_term: dict[str, Term] = {}

    for term in terms:
        if term.mode == TermMode.REPLACE:
            for alias in term.aliases:
                if alias:
                    alias_to_term[alias] = term

    # Build AC with delete-1 expansion but skip too-short delete-1 patterns
    ac = ACEngine()
    for alias in alias_to_term:
        for ep in expand_delete_1(alias):
            # Always register original-length patterns; skip short delete-1 variants
            if ep.is_original or len(ep.pattern) >= _MIN_DELETE1_PATTERN_LEN:
                ac.add(ep.pattern, payload=ep)
    ac.build()

    result: dict = {
        "ac": ac,
        "alias_to_term": alias_to_term,
    }

    # Per-language Tier 1 dispatch (zh canonical_key / ja normalized / en metaphone / ko jamo)
    if language and language in _TIER1_DISPATCH:
        try:
            import importlib

            tier1_mod = importlib.import_module(_TIER1_DISPATCH[language])
            replace_aliases = [a for a in alias_to_term.keys()]
            tier1_index = tier1_mod.build_index(replace_aliases)
            if tier1_index:
                result["tier1_apply"] = tier1_mod.apply
                result["tier1_index"] = tier1_index
        except (ImportError, AttributeError):
            pass  # language adapter not available or missing build_index/apply

    return result


class PhoneticMatcher:
    """
    Language-agnostic phonetic matching + active replacement + protection arbitration.

    v0.4.0 integration wires:
      - DictRuntime (atomic snapshot + add/remove)
      - AC delete-1 expansion (Tier 3)
      - Mutation set (Tier 2 recall gate) — optional, only when phonemizer supports it
      - Optional language-specific Tier 1 modules via phonemizer protocol
      - AsyncEventQueue for on_event delivery
    """

    VERSION = "0.4.0.dev"

    def __init__(
        self,
        phonemizer: "Phonemizer",
        dictionary: Any,  # DictV2 instance or path or dict or list[Term]
        on_event: Optional[Callable[[EventRecord], None]] = None,
        max_alias_len: int = 10,
        window_chars: int = 20,
        enable_tier5_fallback: bool = True,
    ) -> None:
        self.phonemizer = phonemizer
        # Store original dictionary reference for legacy attribute access
        self.dictionary = dictionary
        # Store on_event callable reference for legacy attribute access
        self.on_event = on_event
        self.max_alias_len = max_alias_len
        self.window_chars = window_chars
        # Tier 5: legacy fuzzy_buckets fallback for "規則外 substitution" coverage
        # Default True for v0.3.x backward-compat fuzzy parity (per Option D).
        # Caller set False if 25-48× speed is critical and skip-on-miss is acceptable.
        self.enable_tier5_fallback = enable_tier5_fallback
        self._legacy_corrector = None  # lazy-built on first call
        self._setup_dictionary(dictionary)
        self._setup_event_queue(on_event)

    def _setup_dictionary(self, dictionary: Any) -> None:
        """Load dictionary into DictRuntime + build AC + auxiliary indexes."""
        initial_terms = _load_dict_v2(dictionary)
        language = getattr(self.phonemizer, "language", None)
        # Closure binds language so add_terms/remove_terms also rebuild Tier 1
        build = lambda terms: _build_aux_index(terms, language=language)  # noqa: E731
        self._runtime = DictRuntime(
            initial_terms=initial_terms,
            build_fn=build,
        )

    def _setup_event_queue(self, on_event: Optional[Callable]) -> None:
        if on_event:
            self._event_queue: Optional[AsyncEventQueue] = AsyncEventQueue(handler=on_event)
            self._event_queue.start()
        else:
            self._event_queue = None

    def _emit(self, name: str, payload: dict) -> None:
        if self._event_queue:
            self._event_queue.emit(name, payload)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def correct(self, text: str) -> str:
        """
        Single-shot correction.

        Algorithm v0.4.0 (AC literal + Tier 3 delete-1 fuzzy fallback):
          1. snapshot = self._runtime.get() (lock-free)
          2. canonical auto-protect mask (PHASE2-COMPAT-DESIGN §1)
             Any span that already IS a canonical literal is protected.
          3. AC find_all (with delete-1 expansion already embedded in index) → raw_hits
          4. filter_hits (prefer original > delete-1 at same span)
          5. For each hit:
             - protected span → emit match.protected, skip
             - is_original hit → emit match.exact, apply replacement
             - delete-1 hit   → emit match.fuzzy (tier=delete-1), apply replacement
          6. Append remaining literal text

        Tier wire status:
          Tier 3 (AC delete-1 expansion): WIRED — handled by _build_aux_index + this method
          Tier 2 (mutation set phoneme swap): DEFERRED to v0.4.1
          Tier 1 (per-language hash key): DEFERRED to v0.4.1
        """
        if not text:
            return text

        snapshot = self._runtime.get()
        aux = getattr(snapshot, "_aux_index", None)

        if aux is None:
            return text

        ac = aux.get("ac")
        alias_to_term = aux.get("alias_to_term", {})

        if ac is None or len(ac) == 0:
            return text  # empty dict → no-op

        # Canonical auto-protect: compute protected spans
        # Any span in text that matches a canonical (from any term) is protected
        protected_spans = self._compute_protected_spans(text, snapshot)

        raw_hits = list(ac.find_all(text))
        filtered = filter_hits(raw_hits, text)

        # Merge Tier 1 per-language hits (if dispatch available)
        # Tier 1 hits use tuple payload ("tier1", alias) to distinguish from ExpandedPattern
        tier1_apply = aux.get("tier1_apply")
        tier1_index = aux.get("tier1_index")
        merged_hits: list = list(filtered)
        if tier1_apply and tier1_index:
            for t_start, t_end, t_matched, t_alias in tier1_apply(text, tier1_index):
                # Skip if overlap with existing literal/Tier3 hits (those take priority)
                if any(s < t_end and t_start < e for s, e, _, _ in filtered):
                    continue
                merged_hits.append((t_start, t_end, t_matched, ("tier1", t_alias)))
            merged_hits.sort(key=lambda h: h[0])

        out_parts = []
        cursor = 0

        for start, end, _matched, payload in merged_hits:
            # Skip if cursor has already passed this hit (overlapping)
            if start < cursor:
                continue

            # Check if this span overlaps with any protected span
            if any(p_start <= start and end <= p_end for p_start, p_end in protected_spans):
                self._emit(
                    "match.protected",
                    {
                        "start": start,
                        "end": end,
                        "matched": _matched,
                    },
                )
                continue

            # Identify hit tier from payload type
            if isinstance(payload, tuple) and len(payload) == 2 and payload[0] == "tier1":
                alias = payload[1]
                tier_label = "tier1"
            else:
                alias = payload.original_alias
                tier_label = "exact" if payload.is_original else "delete-1"

            term = alias_to_term.get(alias)
            if term is None:
                continue

            if term.mode == TermMode.REPLACE:
                # Append literal text before this hit
                if start > cursor:
                    out_parts.append(text[cursor:start])
                out_parts.append(term.canonical)

                if tier_label == "exact":
                    self._emit(
                        "match.exact",
                        {
                            "start": start,
                            "end": end,
                            "term": _matched,
                            "canonical": term.canonical,
                            "is_delete1": False,
                        },
                    )
                else:
                    # Tier 3 delete-1 OR Tier 1 per-language hash hit
                    self._emit(
                        "match.fuzzy",
                        {
                            "start": start,
                            "end": end,
                            "term": _matched,
                            "canonical": term.canonical,
                            "tier": tier_label,
                            "original_alias": alias,
                        },
                    )
                cursor = end

        # Append any remaining literal text
        if cursor < len(text):
            out_parts.append(text[cursor:])

        result = "".join(out_parts)

        # Tier 5 fallback (Option D): two-pass legacy fuzzy_buckets for "規則外
        # substitution" coverage. Legacy engine's canonical mask prevents
        # double-replacement of spans Tier 1-3 already corrected.
        if self.enable_tier5_fallback:
            legacy = self._get_legacy_corrector(snapshot)
            if legacy is not None:
                try:
                    tier5_result = legacy.correct(result)
                    if tier5_result != result:
                        self._emit(
                            "match.fuzzy",
                            {
                                "tier": "tier5",
                                "before": result,
                                "after": tier5_result,
                            },
                        )
                        return tier5_result
                except Exception:
                    pass  # Tier 5 errors are non-fatal; return Tier 1-3 result

        return result

    def _get_legacy_corrector(self, snapshot: DictSnapshot):
        """Lazy-build per-language legacy fuzzy_buckets corrector (Tier 5 fallback)."""
        if self._legacy_corrector is not None:
            return self._legacy_corrector

        lang = getattr(self.phonemizer, "language", None)
        if lang not in ("zh", "ja", "en"):
            return None  # ko/other has no legacy engine; skip

        # Convert snapshot.terms → legacy term_dict format
        # legacy expects {canonical: {"aliases": [...], "keywords": [...], "weight": w}}
        term_dict: dict = {}
        for term in snapshot.terms:
            if term.mode != TermMode.REPLACE:
                continue
            term_dict[term.canonical] = {
                "aliases": list(term.aliases),
                "keywords": list(term.keywords),
                "weight": term.weight,
            }

        if not term_dict:
            return None

        try:
            if lang == "zh":
                from phonofix.languages.chinese.engine import ChineseEngine

                engine = ChineseEngine()
                self._legacy_corrector = engine.create_corrector(term_dict)
            elif lang == "ja":
                from phonofix.languages.japanese.engine import JapaneseEngine

                engine = JapaneseEngine()
                self._legacy_corrector = engine.create_corrector(term_dict)
            elif lang == "en":
                from phonofix.languages.english.engine import EnglishEngine

                engine = EnglishEngine()
                self._legacy_corrector = engine.create_corrector(term_dict)
        except Exception:
            self._legacy_corrector = None  # legacy init failed (e.g. espeak-ng missing)

        return self._legacy_corrector

    def _compute_protected_spans(self, text: str, snapshot: DictSnapshot) -> list[tuple[int, int]]:
        """
        Canonical auto-protect mask (PHASE2-COMPAT-DESIGN §1 P0).

        Protected spans are any positions in text where:
        1. A canonical string appears literally (replace-mode: prevents re-replacing correct text)
        2. A protect-mode canonical appears (explicit protection marker)
        """
        spans: list[tuple[int, int]] = []
        for term in snapshot.terms:
            canonical = term.canonical
            idx = 0
            while True:
                pos = text.find(canonical, idx)
                if pos == -1:
                    break
                spans.append((pos, pos + len(canonical)))
                idx = pos + len(canonical)
        return spans

    def _lookup_term_by_alias(self, alias: str, snapshot: DictSnapshot) -> Optional[Term]:
        """Find Term by alias using snapshot's alias_to_term index."""
        aux = getattr(snapshot, "_aux_index", None)
        if aux:
            return aux.get("alias_to_term", {}).get(alias)
        return None

    def correct_batch(self, texts: Iterable[str]) -> list[str]:
        """Batch — share snapshot across texts (snapshot is already a cheap pointer read)."""
        return [self.correct(t) for t in texts]

    def feed(self, chunk: str) -> str:
        """Streaming — delegate to StreamBuffer."""
        if not hasattr(self, "_stream_buffer"):
            lang = getattr(self.phonemizer, "language", "zh")
            language_mode = "char" if lang in ("zh", "ja", "ko") else "word"
            self._stream_buffer = StreamBuffer(
                scan_fn=self._scan_for_streaming,
                max_alias_len=self.max_alias_len,
                window_chars=self.window_chars,
                language_mode=language_mode,
            )
        return self._stream_buffer.feed(chunk)

    def _scan_for_streaming(self, text: str) -> list[tuple[int, int, str, str]]:
        """scan_fn shim for StreamBuffer: returns (start, end, matched, replacement)."""
        if not text:
            return []

        snapshot = self._runtime.get()
        aux = getattr(snapshot, "_aux_index", None)
        if aux is None:
            return []

        ac = aux.get("ac")
        alias_to_term = aux.get("alias_to_term", {})

        if ac is None or len(ac) == 0:
            return []

        protected_spans = self._compute_protected_spans(text, snapshot)
        raw = list(ac.find_all(text))
        filtered = filter_hits(raw, text)

        out = []
        for start, end, matched, expanded in filtered:
            # Skip protected spans
            if any(p_start <= start and end <= p_end for p_start, p_end in protected_spans):
                continue
            term = alias_to_term.get(expanded.original_alias)
            if term and term.mode == TermMode.REPLACE:
                out.append((start, end, matched, term.canonical))
        return out

    def flush(self) -> str:
        if hasattr(self, "_stream_buffer"):
            return self._stream_buffer.flush()
        return ""

    def add_terms(self, entries: Iterable) -> None:
        """Hot-reload: add new terms and rebuild indexes atomically."""
        entries_list = list(entries)
        # Normalize: accept Term instances or dicts
        term_objects: list[Term] = []
        for e in entries_list:
            if isinstance(e, Term):
                term_objects.append(e)
            elif isinstance(e, dict):
                loaded = _load_dict_v2([e])
                term_objects.extend(loaded)
        if term_objects:
            self._runtime.add_terms(term_objects)

    def remove_terms(self, canonical: Iterable[str]) -> None:
        """Hot-reload: remove terms by canonical and rebuild indexes atomically."""
        self._runtime.remove_terms(list(canonical))

    def explain(self, text: str) -> dict:
        """
        Per-candidate score breakdown (SPEC.md §2 — 5 golden categories).

        v0.4.0: candidates now include tier annotation for each hit:
          - tier="exact"    → literal AC hit (is_original=True)
          - tier="delete-1" → AC delete-1 expansion hit (Tier 3 fuzzy)
        """
        snapshot = self._runtime.get()
        aux = getattr(snapshot, "_aux_index", None)

        candidates: list[dict] = []
        if aux is not None:
            ac = aux.get("ac")
            alias_to_term = aux.get("alias_to_term", {})
            if ac is not None and len(ac) > 0 and text:
                protected_spans = self._compute_protected_spans(text, snapshot)
                raw_hits = list(ac.find_all(text))
                filtered = filter_hits(raw_hits, text)
                seen_cursor = 0
                for start, end, matched, expanded in filtered:
                    if start < seen_cursor:
                        continue
                    is_protected = any(
                        p_start <= start and end <= p_end for p_start, p_end in protected_spans
                    )
                    term = alias_to_term.get(expanded.original_alias)
                    if term is None:
                        continue
                    tier = "exact" if expanded.is_original else "delete-1"
                    candidates.append(
                        {
                            "start": start,
                            "end": end,
                            "matched": matched,
                            "alias": expanded.original_alias,
                            "canonical": term.canonical,
                            "tier": tier,
                            "protected": is_protected,
                        }
                    )
                    if not is_protected and term.mode == TermMode.REPLACE:
                        seen_cursor = end

        result = self.correct(text)
        return {
            "version": self.VERSION,
            "text": text,
            "trace_id": get_trace_id(),
            "candidates": candidates,
            "result": result,
            "dict_version": snapshot.version,
            "dict_size": len(snapshot.terms),
        }

    def diagnose(self) -> dict:
        """Runtime diagnostics (SPEC.md §5 output schema)."""
        snapshot = self._runtime.get()
        aux = getattr(snapshot, "_aux_index", None)
        ac_engine = "none"
        if aux is not None and "ac" in aux and aux["ac"] is not None and len(aux["ac"]) > 0:
            # AC engine includes delete-1 expansion (Tier 3 fuzzy) built into the index
            ac_engine = "pyahocorasick+expanded"

        eq_active = False
        if self._event_queue is not None:
            thread = self._event_queue._thread
            eq_active = thread is not None and thread.is_alive()

        # Optional psutil for memory
        mem_rss_mb = 0
        try:
            import psutil

            proc = psutil.Process(os.getpid())
            mem_rss_mb = round(proc.memory_info().rss / 1024 / 1024, 2)
        except ImportError:
            pass

        return {
            "version": self.VERSION,
            "dict_version": snapshot.version,
            "dict_size": len(snapshot.terms),
            "mem_rss_mb": mem_rss_mb,
            "backends_loaded": [self.phonemizer.name] if self.phonemizer else [],
            "ac_engine": ac_engine,
            "streaming_active": hasattr(self, "_stream_buffer"),
            "event_queue_active": eq_active,
        }

    def close(self) -> None:
        """Cleanup — stop event queue. Caller should invoke at shutdown."""
        if self._event_queue:
            self._event_queue.stop()

# phonofix v0.4.0 — Public API Specification (Frozen)

> **Status**: FROZEN for Phase 1 — do NOT modify without PR + reviewer sign-off
> **Date**: 2026-05-26
> **Branch**: v0.4-dev
> **Scope**: Public Python API, event taxonomy, explain() schema, feed() streaming contract

---

## Section 1: Public API

### 1.1 `phonofix.load()`

```python
def load(
    dictionary: str | Path | dict,
    *,
    language: str | None = None,
    on_event: Callable[[str, dict], None] | None = None,
) -> PhoneticMatcher:
    ...
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `dictionary` | `str \| Path \| dict` | Yes | Path to YAML dict file (v2 schema), or pre-parsed dict object |
| `language` | `str \| None` | No | ISO 639-1 code (`"zh"`, `"ja"`, `"en"`, `"ko"`). Auto-detected from dict YAML `language:` field if omitted |
| `on_event` | `Callable[[str, dict], None] \| None` | No | Event handler; called synchronously unless `async_events=True` (Phase 4) |

**Returns**: `PhoneticMatcher` — fully initialised, ready to call `correct()`.

**Raises**:
- `phonofix.DictSchemaError` — dict YAML fails v2 schema validation
- `phonofix.UnsupportedLanguageError` — `language` not in `{"zh", "ja", "en", "ko"}`
- `FileNotFoundError` — `dictionary` path does not exist

---

### 1.2 `phonofix.PhoneticMatcher`

```python
class PhoneticMatcher:
    def __init__(
        self,
        *,
        phonemizer: BasePhonemizer,
        dictionary: str | Path | dict,
        on_event: Callable[[str, dict], None] | None = None,
        cache_size: int = 4096,
    ) -> None:
        ...
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `phonemizer` | `BasePhonemizer` | Yes | Language-specific phonemizer instance (e.g. `phonofix.phonemizers.chinese()`) |
| `dictionary` | `str \| Path \| dict` | Yes | Same as `load()` |
| `on_event` | `Callable[[str, dict], None] \| None` | No | See §4 Event Taxonomy |
| `cache_size` | `int` | No | LRU cache size per phonetic backend; default 4096 |

**Raises**: Same as `load()`.

**Thread safety**: `correct()` / `correct_batch()` / `feed()` are safe for concurrent reads. `add_terms()` / `remove_terms()` trigger an atomic swap-rebuild; concurrent reads see either old or new dict, never a partial state.

---

### 1.3 `correct()`

```python
def correct(
    self,
    text: str,
    *,
    context: dict | None = None,
) -> str:
    ...
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | `str` | Yes | Input text to correct |
| `context` | `dict \| None` | No | Caller-supplied metadata forwarded to `on_event` payloads; not used for matching logic |

**Returns**: Corrected string. If no terms matched, returns `text` unchanged (no-op, never raises on miss).

**Complexity**: O(|text| + phonetic_lookup) per call. AC scan is O(|text|).

---

### 1.4 `correct_batch()`

```python
def correct_batch(
    self,
    texts: Iterable[str],
    *,
    context: dict | None = None,
) -> list[str]:
    ...
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `texts` | `Iterable[str]` | Yes | Sequence of strings to correct |
| `context` | `dict \| None` | No | Forwarded to `on_event` payloads |

**Returns**: `list[str]` — same length as `texts`, corrected in order.

**Implementation note**: shares protection cache + AC scan across the batch. Phonetic backend LRU cache is shared. Rebuild is not triggered.

---

### 1.5 `feed()`

```python
def feed(
    self,
    chunk: str,
) -> str:
    ...
```

Streaming interface. Full contract in **Section 3**.

**Returns**: Corrected text for the *confirmed* portion of the current chunk (may be shorter than `chunk` due to tail buffering).

---

### 1.6 `add_terms()`

```python
def add_terms(
    self,
    entries: list[dict],
) -> None:
    ...
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entries` | `list[dict]` | Yes | List of term entries conforming to dict v2 schema (`mode`, `canonical`, `aliases`, etc.) |

**Behaviour**: validates all entries first (fails fast if any entry is invalid); then triggers a full AC swap-rebuild + atomic pointer switch. All subsequent `correct()` calls use the new dict.

**Raises**: `phonofix.DictSchemaError` if any entry fails v2 validation (no partial update).

**Complexity**: O(dict_size) rebuild. Callers must accept a brief memory spike during rebuild (≤ 2× steady-state dict memory). Benchmark target: ≤ 500 ms for 10K terms on reference hardware (to be confirmed in Phase 4).

**Documentation requirement**: callers must be aware that `add_terms()` / `remove_terms()` always trigger O(dict_size) rebuild. There is no incremental update path (pyahocorasick `add()` is not used post-build).

---

### 1.7 `remove_terms()`

```python
def remove_terms(
    self,
    canonicals: list[str],
) -> None:
    ...
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `canonicals` | `list[str]` | Yes | List of canonical term strings to remove |

**Behaviour**: same swap-rebuild + atomic pointer switch as `add_terms()`. Terms not found in dict are silently ignored.

---

### 1.8 `explain()`

```python
def explain(
    self,
    text: str,
    *,
    top_k: int = 5,
) -> dict:
    ...
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | `str` | Yes | Text window to explain (single phrase or sentence) |
| `top_k` | `int` | No | Max candidates to return per match window; default 5 |

**Returns**: structured dict — full schema in **Section 2**.

**Raises**: never raises on miss (returns `{"status": "no_hit", ...}`).

**LLM-friendliness**: output includes `candidate_raw_text`, `phonetic_distance`, and `context_window` so callers can construct LLM prompts without back-querying source data.

---

### 1.9 `diagnose()`

```python
def diagnose(self) -> dict:
    ...
```

**Returns**: health snapshot — full schema in **Section 5**.

**Raises**: never raises. Backend failures are reported inside the returned dict, not as exceptions.

---

## Section 2: `explain()` Output Schema + 5 Golden JSON Examples

### 2.1 Schema

```
{
  "status": str,           // "no_hit" | "exact" | "fuzzy" | "protected" | "conflict"
  "input_text": str,       // the text passed to explain()
  "context_window": str,   // ±N chars around the match span (or full input if short)
  "matches": [             // list of match records (empty if status=no_hit)
    {
      "span": {
        "start": int,      // byte offset in input_text
        "end": int         // exclusive
      },
      "candidate_raw_text": str,     // the matched alias / canonical as it appeared in input
      "canonical": str,              // corrected canonical form
      "mode": str,                   // "replace" | "protect"
      "tier": str,                   // "exact" | "fuzzy_t1" | "fuzzy_t2" | "fuzzy_t3" | "fuzzy_t4"
      "score": {
        "total": float,              // 0.0–1.0, higher = better match
        "phonetic": float,           // phonetic similarity component
        "keyword_boost": float,      // bonus from matching keywords in context
        "length_penalty": float      // penalty for span length delta
      },
      "phonetic_distance": int,      // edit distance in phoneme space (0 = exact)
      "dict_id": str | null,         // source dict identifier (filename stem or hash)
      "conflict_losers": [           // populated only when status=conflict
        {
          "candidate_raw_text": str,
          "canonical": str,
          "score": float,
          "reason": str              // e.g. "lower_score" | "shorter_span" | "lower_weight"
        }
      ]
    }
  ],
  "miss_info": {           // populated only when status=no_hit
    "text_window": str,
    "nearest_candidate": str | null, // closest candidate that did NOT cross threshold
    "nearest_score": float | null
  },
  "cache_hit": bool        // whether phonetic result came from LRU cache
}
```

**Field notes**:
- `context_window`: always ±32 chars (or full input) — sufficient for LLM prompt construction
- `candidate_raw_text`: the literal substring from `input_text`, not the alias definition
- `phonetic_distance`: measured in the language's phoneme space (pinyin syllables for zh, romaji morae for ja, phonemes for en, jamo for ko); 0 = exact phonetic match
- `score.total` is the arbiter used for conflict resolution; higher wins

---

### 2.2 Golden JSON Examples

#### Example 1 — `no_hit`

Input text has no alias or canonical match at any tier.

```json
{
  "status": "no_hit",
  "input_text": "今天天氣很好",
  "context_window": "今天天氣很好",
  "matches": [],
  "miss_info": {
    "text_window": "今天天氣很好",
    "nearest_candidate": "天氣預報",
    "nearest_score": 0.31
  },
  "cache_hit": false
}
```

---

#### Example 2 — `exact`

AC literal hit: alias `"北車"` maps to canonical `"台北車站"`.

```json
{
  "status": "exact",
  "input_text": "這是北車的時刻表",
  "context_window": "這是北車的時刻表",
  "matches": [
    {
      "span": { "start": 2, "end": 4 },
      "candidate_raw_text": "北車",
      "canonical": "台北車站",
      "mode": "replace",
      "tier": "exact",
      "score": {
        "total": 1.0,
        "phonetic": 1.0,
        "keyword_boost": 0.0,
        "length_penalty": 0.0
      },
      "phonetic_distance": 0,
      "dict_id": "tw-transport-v2",
      "conflict_losers": []
    }
  ],
  "miss_info": null,
  "cache_hit": true
}
```

---

#### Example 3 — `fuzzy`

Tier 2 phonetic hit: ASR mis-recognises `"雷霆将軍"` → canonical `"雷電将軍"` via pinyin confusion (`ting` ~ `dian`).

```json
{
  "status": "fuzzy",
  "input_text": "雷霆将軍發動了攻擊",
  "context_window": "雷霆将軍發動了攻擊",
  "matches": [
    {
      "span": { "start": 0, "end": 4 },
      "candidate_raw_text": "雷霆将軍",
      "canonical": "雷電将軍",
      "mode": "replace",
      "tier": "fuzzy_t2",
      "score": {
        "total": 0.83,
        "phonetic": 0.80,
        "keyword_boost": 0.05,
        "length_penalty": 0.0
      },
      "phonetic_distance": 1,
      "dict_id": "genshin-zh-v2",
      "conflict_losers": []
    }
  ],
  "miss_info": null,
  "cache_hit": false
}
```

---

#### Example 4 — `protected`

`mode=protect` mask matched: term `"枝節"` is protected from replacement.

```json
{
  "status": "protected",
  "input_text": "這是枝節問題，不重要",
  "context_window": "這是枝節問題，不重要",
  "matches": [
    {
      "span": { "start": 2, "end": 4 },
      "candidate_raw_text": "枝節",
      "canonical": "枝節",
      "mode": "protect",
      "tier": "exact",
      "score": {
        "total": 1.0,
        "phonetic": 1.0,
        "keyword_boost": 0.0,
        "length_penalty": 0.0
      },
      "phonetic_distance": 0,
      "dict_id": "common-zh-v2",
      "conflict_losers": []
    }
  ],
  "miss_info": null,
  "cache_hit": false
}
```

---

#### Example 5 — `conflict`

Two candidates overlap the same span; arbiter picks the higher-scoring one.

Scenario: `"魔女"` triggers both alias `"魔女"` → canonical `"巫女"` (score 0.72) and alias `"魔女"` → canonical `"魔法少女"` (score 0.68). Winner: `"巫女"`.

```json
{
  "status": "conflict",
  "input_text": "那位魔女非常厲害",
  "context_window": "那位魔女非常厲害",
  "matches": [
    {
      "span": { "start": 2, "end": 4 },
      "candidate_raw_text": "魔女",
      "canonical": "巫女",
      "mode": "replace",
      "tier": "exact",
      "score": {
        "total": 0.72,
        "phonetic": 0.65,
        "keyword_boost": 0.07,
        "length_penalty": 0.0
      },
      "phonetic_distance": 0,
      "dict_id": "anime-zh-v2",
      "conflict_losers": [
        {
          "candidate_raw_text": "魔女",
          "canonical": "魔法少女",
          "score": 0.68,
          "reason": "lower_score"
        }
      ]
    }
  ],
  "miss_info": null,
  "cache_hit": false
}
```

---

## Section 3: `feed()` Streaming Spec

### 3.1 Overview

`feed(chunk)` is the streaming entry point for ASR output. It maintains an internal buffer across calls and emits corrected text for confirmed portions of each chunk.

### 3.2 Tail Buffer

**Purpose**: prevent a term that straddles a chunk boundary from being missed.

**Tail length formula** (not hard-coded):

```
tail_size = max(len(alias) for alias in all_aliases) + context_window_chars
```

Where `context_window_chars` is the keyword context radius used for scoring (default 32 chars).

**Example**: if the longest alias is 6 chars and context window is 32, `tail_size = 38`.

**Implementation**: after each `feed()` call, the last `tail_size` characters of the processed buffer are held back and prepended to the next chunk. Only the portion *before* the tail is emitted.

**Upper bound**: `tail_size` must never exceed 512 characters. If `max(alias_length) + context_window_chars > 512`, raise `phonofix.ConfigError` at `PhoneticMatcher` init time.

### 3.3 Flush Conditions

| Trigger | Behaviour |
|---------|-----------|
| Each `feed(chunk)` call | Emit confirmed portion (chunk minus tail). No explicit flush needed per chunk. |
| Caller calls `flush()` | Emit entire remaining buffer including tail. Resets buffer to empty. |
| End of stream | Caller MUST call `flush()` to drain tail. Un-flushed tail is NOT automatically emitted. |

```python
def flush(self) -> str:
    """Drain the tail buffer. Must be called at end of stream."""
    ...
```

### 3.4 Duplicate Suppression

When the same term canonical appears multiple times across chunk boundaries within a single streaming session, each occurrence is emitted independently — **no cross-chunk deduplication by default**.

Rationale: ASR streams are continuous speech; the same entity can legitimately appear multiple times in one session.

**Within-chunk deduplication**: if the same span is matched by two overlapping patterns in a single chunk, the higher-scoring candidate wins (conflict resolution, see §4).

Callers needing session-level deduplication must implement it above `feed()` using `on_event` callbacks.

### 3.5 Overlap Semantics

**Baseline**: `feed()` uses stdlib `re` with non-overlapped matching semantics.

Rationale (evidence-based, Codex C-1 measurement):
- `stdlib re`: 3,207,900 chars/s
- `regex` (non-overlapped): 1,440,034 chars/s
- `regex(overlapped=True)`: 921,594 chars/s

Non-overlapped semantics is the default. Once a span is matched and consumed, the scan continues from `match.end()`.

**Overlapped mode**: not supported in `feed()`. If a caller needs overlapped semantics (e.g. detecting nested terms), they must call `correct()` on individual windows.

**Implication for benchmarks**: throughput numbers for `feed()` are measured with `re` non-overlapped. Any benchmark that uses `regex(overlapped=True)` is measuring a different mode and must be labelled as such.

### 3.6 Language-Specific Step Semantics

| Language | Step unit | Rationale |
|----------|-----------|-----------|
| `zh` (Chinese) | Character-level | No word delimiters; AC scan over chars |
| `ja` (Japanese) | Character-level | MeCab tokenisation optional; AC scan over chars |
| `ko` (Korean) | Character-level | Jamo-level decomposition internal; AC scan over Hangul syllable chars |
| `en` (English) | Word-level boundary-aware | AC patterns include word boundaries `\b` to prevent partial-word matches |

### 3.7 Retroactive Correction

Retroactive correction (modifying already-emitted text after a `flush()`) is **NOT supported**.

Once text is emitted from `feed()` or `flush()`, it is final. Callers that require retroactive correction must buffer emitted text themselves and call `correct()` on the full accumulated string at end of stream.

### 3.8 `feed()` State Machine

```
IDLE ──► feed(chunk) ──► [prepend tail from prev] ──► AC scan + correct
         │                                              │
         │                                     emit: chunk[:-tail_size]
         │                                     hold:  chunk[-tail_size:]
         ◄───────────────────────────────────────────────
         │
         flush() ──► emit: held tail (corrected) ──► reset buffer ──► IDLE
```

---

## Section 4: `on_event` Event Taxonomy

`on_event` is called synchronously during `correct()` / `correct_batch()` / `feed()`. Callers must not block inside the handler on the hot path (Phase 4 will add async queue option).

Signature:
```python
def on_event(event_name: str, payload: dict) -> None:
    ...
```

### 4.1 Event Types

#### `match.exact`

AC literal hit. Term found verbatim.

```json
{
  "event": "match.exact",
  "term": "北車",
  "canonical": "台北車站",
  "start": 2,
  "end": 4,
  "dict_id": "tw-transport-v2"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `term` | `str` | The matched alias text as it appeared in input |
| `canonical` | `str` | Corrected canonical form |
| `start` | `int` | Start offset (byte) in input text |
| `end` | `int` | End offset (exclusive) |
| `dict_id` | `str \| null` | Source dict identifier |

---

#### `match.fuzzy`

Tier 1–4 phonetic hit (did not match literally; matched via phonetic similarity).

```json
{
  "event": "match.fuzzy",
  "term": "雷霆将軍",
  "candidate": "雷電将軍",
  "tier": "fuzzy_t2",
  "score": 0.83,
  "phonetic_distance": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `term` | `str` | Text span from input |
| `candidate` | `str` | Canonical form selected |
| `tier` | `str` | `"fuzzy_t1"` \| `"fuzzy_t2"` \| `"fuzzy_t3"` \| `"fuzzy_t4"` |
| `score` | `float` | Total score (0.0–1.0) |
| `phonetic_distance` | `int` | Edit distance in phoneme space |

---

#### `match.protected`

`mode=protect` mask matched. Term will NOT be replaced; span is locked.

```json
{
  "event": "match.protected",
  "term": "枝節",
  "start": 2,
  "end": 4
}
```

| Field | Type | Description |
|-------|------|-------------|
| `term` | `str` | Protected term as matched in input |
| `start` | `int` | Start offset |
| `end` | `int` | End offset (exclusive) |

---

#### `conflict.resolved`

Two or more candidates competed for the same span. Arbiter resolved to one winner.

```json
{
  "event": "conflict.resolved",
  "winner": "巫女",
  "losers": [
    { "canonical": "魔法少女", "score": 0.68, "reason": "lower_score" }
  ],
  "span": { "start": 2, "end": 4 }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `winner` | `str` | Winning canonical form |
| `losers` | `list[dict]` | Each loser: `canonical`, `score`, `reason` |
| `span` | `dict` | `{"start": int, "end": int}` |

`reason` values: `"lower_score"` \| `"shorter_span"` \| `"lower_weight"`.

---

#### `miss.no_hit`

Tier 1–4 all failed for a candidate window.

```json
{
  "event": "miss.no_hit",
  "text_window": "今天天氣",
  "nearest_candidate": "天氣預報",
  "nearest_score": 0.31
}
```

| Field | Type | Description |
|-------|------|-------------|
| `text_window` | `str` | The text window that was attempted |
| `nearest_candidate` | `str \| null` | Closest candidate below threshold (or null if none) |
| `nearest_score` | `float \| null` | Score of nearest candidate |

---

#### `cache.hit` / `cache.miss`

LRU phonetic cache events. Emitted per phonetic backend lookup.

```json
{
  "event": "cache.hit",
  "backend": "zh_pinyin",
  "key": "雷霆"
}
```

```json
{
  "event": "cache.miss",
  "backend": "zh_pinyin",
  "key": "雷霆"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `backend` | `str` | Backend name: `"zh_pinyin"` \| `"ja_romaji"` \| `"en_phoneme"` \| `"ko_jamo"` |
| `key` | `str` | The text key looked up |

---

## Section 5: `diagnose()` Output

```python
def diagnose(self) -> dict:
    ...
```

**Returns**:

```json
{
  "version": "0.4.0",
  "dict_size": {
    "terms": 1234,
    "aliases": 3891,
    "protected": 42
  },
  "mem_rss_mb": 48.3,
  "backends_loaded": [
    {
      "name": "zh_pinyin",
      "language": "zh",
      "status": "ok",
      "cache_size": 4096,
      "cache_hits": 18240,
      "cache_misses": 320,
      "hit_rate": 0.983,
      "init_latency_ms": 12.4
    },
    {
      "name": "ja_romaji",
      "language": "ja",
      "status": "ok",
      "cache_size": 4096,
      "cache_hits": 4102,
      "cache_misses": 88,
      "hit_rate": 0.979,
      "init_latency_ms": 340.2
    }
  ],
  "ac_engine": {
    "type": "pyahocorasick",
    "pattern_count": 3891,
    "mem_mb": 0.07
  },
  "streaming": {
    "tail_size": 38,
    "buffer_len": 0,
    "chunks_fed": 0
  }
}
```

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `version` | `str` | phonofix package version |
| `dict_size.terms` | `int` | Number of canonical terms |
| `dict_size.aliases` | `int` | Total alias entries across all terms |
| `dict_size.protected` | `int` | Number of `mode=protect` terms |
| `mem_rss_mb` | `float` | Process RSS memory in MB (via `psutil` or `/proc/self/status`) |
| `backends_loaded` | `list[dict]` | One entry per loaded phonetic backend |
| `backends_loaded[].name` | `str` | Backend identifier |
| `backends_loaded[].language` | `str` | ISO 639-1 code |
| `backends_loaded[].status` | `str` | `"ok"` \| `"error"` \| `"not_loaded"` |
| `backends_loaded[].cache_hits` | `int` | LRU cache hits since init |
| `backends_loaded[].cache_misses` | `int` | LRU cache misses since init |
| `backends_loaded[].hit_rate` | `float` | `hits / (hits + misses)` |
| `backends_loaded[].init_latency_ms` | `float` | Backend init time in ms |
| `ac_engine.type` | `str` | AC engine name (default: `"pyahocorasick"`) |
| `ac_engine.pattern_count` | `int` | Number of patterns registered in AC |
| `ac_engine.mem_mb` | `float` | AC structure memory footprint in MB |
| `streaming.tail_size` | `int` | Current computed tail size |
| `streaming.buffer_len` | `int` | Chars currently held in tail buffer |
| `streaming.chunks_fed` | `int` | Number of `feed()` calls since last `flush()` |

**Backend error handling**: if a backend fails to init, `status` is `"error"` and a `"error_detail"` string is added to that entry. `diagnose()` never raises; it reports failures inline.

---

## Appendix A: Dict v2 Schema Summary

```yaml
version: 2
language: zh   # zh | ja | en | ko

terms:
  - canonical: "雷電将軍"
    mode: replace          # replace | protect (required)
    aliases: ["雷霆将軍"]  # required and non-empty when mode=replace
    keywords: ["原神"]     # optional: context keywords that boost score
    weight: 0.0            # optional float: tie-break weight, default 0.0

  - canonical: "枝節"
    mode: protect          # aliases / keywords / weight NOT allowed here

confusion_overrides:       # optional per-dict override of language confusion rules
  "ㄢ": ["ㄤ"]
```

**Validation rules** (enforced at `add_terms()` / `load()` entry point):
- `mode` is required on every term
- `mode=replace` requires `aliases` to be a non-empty list
- `mode=protect` must not have `aliases`, `keywords`, or `weight`
- Duplicate `canonical` values within one YAML file → `DictSchemaError`

---

## Appendix B: Backward Compatibility

The following 0.3.x entry points are retained as thin compat wrappers in v0.4.0:

```python
phonofix.ChineseEngine(...)     # → PhoneticMatcher(phonemizer=phonemizers.chinese(), ...)
phonofix.JapaneseEngine(...)    # → PhoneticMatcher(phonemizer=phonemizers.japanese(), ...)
phonofix.EnglishEngine(...)     # → PhoneticMatcher(phonemizer=phonemizers.english(), ...)
```

Each emits `DeprecationWarning` once per `__init__`. These wrappers will be removed in v0.5.0 (≥ 3 months after v0.4.0 release).

Advanced APIs `PhoneticBackend` and `PipelineCorrector` are **removed without compat wrapper** in v0.4.0 (confirmed breaking change per plan §二.5).

---

*End of SPEC.md — frozen for Phase 1. All changes require PR review.*

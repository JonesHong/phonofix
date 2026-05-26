# Phase 4 — Threading Safety Reference

> **Scope**: phonofix v0.4.0 · `PhoneticMatcher` public API thread-safety guarantees  
> **Addresses**: Codex review P1 (hot reload race) · P2 (StreamBuffer sharing) · P3 (writer serialization)

---

## Section 1: Concurrent Reader + Occasional Writer Model

### Default Operating Mode

phonofix v0.4.0 assumes **one shared `PhoneticMatcher` instance** per process with:

- **Many reader threads** calling `correct()`, `correct_batch()`, `explain()`, `diagnose()` concurrently
- **At most one writer thread** at a time calling `add_terms()` / `remove_terms()`

This is the common production pattern — e.g., a web server serving many requests from a single matcher object, with an admin endpoint that updates the dictionary.

### How It Works: Snapshot Pointer Model

The dictionary is stored as a `DictSnapshot` — an **immutable, frozen** data object that is never mutated after creation (`core/dict_runtime.py`).

```
Thread A reads:  snapshot_ptr ──► DictSnapshot v3  (immutable)
Thread B reads:  snapshot_ptr ──► DictSnapshot v3  (same snapshot, consistent)

Writer:    build DictSnapshot v4
           self._snapshot = new_snap   ← atomic pointer swap (CPython GIL)

Thread A continues reading DictSnapshot v3 — not affected
Thread C (new):  snapshot_ptr ──► DictSnapshot v4
```

**Key properties:**

- Reader grabs the snapshot pointer at call start; that pointer stays valid for the lifetime of the call.
- Writer rebuilds a **completely new** snapshot under `_lock`, then swaps the pointer.
- Because CPython's GIL guarantees atomic reference assignment, readers never see a torn snapshot.
- A reader that started before a swap finishes reading the **old** snapshot — consistent, never corrupt.
- Writer does **not** wait for readers to finish; readers do **not** wait for the writer.

### What "Atomic" Means Here

`self._snapshot = new_snap` in Python is a single bytecode `STORE_ATTR`, which executes under the GIL without releasing it. This makes the pointer swap atomic in CPython. The guarantee is CPython-specific; it holds for all CPython 3.x versions in common use.

---

## Section 2: Public API Thread-Safety Table

| API | Multi-reader concurrent | Concurrent writer | Notes |
|-----|------------------------|-------------------|-------|
| `correct(text)` | Safe | Safe | Grabs snapshot ptr at call start; reader sees old dict if swap occurs mid-call — consistent by design |
| `correct_batch(texts)` | Safe | Safe | All texts in one batch see the **same** snapshot — no partial-update view within a batch |
| `feed(chunk)` | **Single thread per buffer** | Safe | `StreamBuffer` is stateful; **do not share one buffer across threads** |
| `flush()` | **Single thread per buffer** | Safe | Same as `feed()` — stateful, per-connection |
| `explain(text)` | Safe | Safe | Read-only on current snapshot |
| `diagnose()` | Safe | Safe | Read-only snapshot stats |
| `add_terms(entries)` | — | **Single writer only** | Multiple concurrent writers will race on `_lock` + version counter; caller must serialize |
| `remove_terms(canonical)` | — | **Single writer only** | Same as `add_terms()` |

**Legend:**
- **Safe** — no caller-side lock needed
- **Single thread per buffer** — each `StreamBuffer` instance must be owned by one thread
- **Single writer only** — serialize at the caller side (e.g., `threading.Lock`)

---

## Section 3: Caller Patterns

### Pattern A: Web Server Hot Path

A single `PhoneticMatcher` instance shared by all request-handler threads (FastAPI/Flask/ASGI workers). No lock required for read methods.

```python
import phonofix

# Loaded once at startup — shared by all worker threads.
matcher = phonofix.load("dict.yaml")

# FastAPI example — each request runs in a worker thread.
@app.post("/correct")
async def correct_endpoint(text: str) -> str:
    # Safe: correct() grabs a snapshot reference internally.
    return matcher.correct(text)

@app.post("/batch")
async def batch_endpoint(texts: list[str]) -> list[str]:
    # Safe: all texts see the same snapshot within one batch.
    return matcher.correct_batch(texts)
```

### Pattern B: Streaming — One Buffer per Connection

`StreamBuffer` is stateful (it maintains a tail buffer and a dedup set). Each connection or audio stream **must** own its own buffer. Do not share.

```python
# handle_connection runs in its own thread (one per WebSocket/TCP conn).
def handle_connection(conn):
    # Create a fresh StreamBuffer for this connection.
    buf = matcher.create_stream()

    for chunk in conn:          # chunks arrive in order
        out = buf.feed(chunk)   # partial match held in tail
        if out:
            conn.send(out)

    # Drain the tail at end of stream.
    tail = buf.flush()
    if tail:
        conn.send(tail)
    # buf is discarded; no cleanup needed.
```

### Pattern C: Hot Reload from an Admin Thread

The writer `_lock` inside `DictRuntime` serializes concurrent *internal* mutations, but it does not prevent two caller threads from both calling `add_terms()` at the same time (they would each acquire the lock in turn, producing two separate swaps). If you need **atomic multi-step updates** (e.g., remove old entries then add new ones as one logical change), add a caller-side lock.

```python
import threading

# One shared matcher, one lock that guards all write operations.
admin_lock = threading.Lock()

def reload_dict(new_entries: list[dict]) -> None:
    """Replace entire dictionary atomically from the caller's perspective."""
    with admin_lock:
        # Readers are not blocked; they see old dict until the swap completes.
        matcher.add_terms(new_entries)

def hot_patch(remove: list[str], add: list[dict]) -> None:
    """Remove + add as a single logical operation."""
    with admin_lock:
        matcher.remove_terms(remove)
        matcher.add_terms(add)
        # Two swaps occur internally, but no other writer can interleave.
```

---

## Section 4: Known Limits and Anti-Patterns

### Do NOT share a StreamBuffer across threads

Each `StreamBuffer` stores a dedup set and a carry-over tail buffer. If two threads call `feed()` on the same buffer concurrently, the tail and dedup state will be corrupted. The `StreamBuffer` class provides **no internal synchronization** — this is intentional to keep the hot path allocation-free.

```python
# WRONG — two threads, one buffer
buf = matcher.create_stream()
thread1 = Thread(target=lambda: buf.feed(stream_a))
thread2 = Thread(target=lambda: buf.feed(stream_b))
# ^^^ data race on buf._buffer and buf._seen

# CORRECT — one buffer per thread
def worker(stream):
    buf = matcher.create_stream()
    for chunk in stream:
        buf.feed(chunk)
    buf.flush()
```

### Do NOT call add_terms / remove_terms from multiple threads without a lock

The internal `_lock` inside `DictRuntime` prevents torn snapshots, but it does not make **multi-step update sequences** atomic from the caller's perspective. Two concurrent writers will each succeed independently, producing two separate version increments — which is usually wrong.

```python
# WRONG — interleaved version increments
Thread-1: matcher.remove_terms(["old_term"])   # snapshot v4 → v5
Thread-2: matcher.add_terms([new_entry])        # snapshot v4 → v5 (saw v4, races)

# CORRECT — serialize with a caller-side lock (see Pattern C above)
```

### Do NOT add a lock around correct() / explain() / diagnose()

Adding a lock around read methods provides no correctness benefit and adds contention. The snapshot model is specifically designed so that **readers need no lock**.

```python
# UNNECESSARY — do not do this
with some_lock:
    result = matcher.correct(text)   # lock is never needed for reads
```

---

## Section 5: Validation Status

The threading guarantees documented here are grounded in three source files:

| Source | Guarantee |
|--------|-----------|
| `src/phonofix/core/dict_runtime.py` | `DictSnapshot` is immutable after construction; `_snapshot` pointer is swapped atomically under `_lock`; `get()` requires no lock (docstring: "CPython's GIL guarantees atomic pointer load") |
| `src/phonofix/core/streaming.py` | `StreamBuffer` is explicitly **not** thread-safe; no internal lock; designed for single-thread ownership per instance |
| `src/phonofix/languages/japanese/normalized_cache.py` | Per-window normalization uses `@lru_cache` (module-level pure function); CPython's `functools.lru_cache` is thread-safe — concurrent callers may redundantly compute on the first miss, but the cache itself is not corrupted |

**Test coverage**: `tests/test_concurrency.py` validates multi-reader + single-writer scenarios using `threading.Barrier` synchronization.

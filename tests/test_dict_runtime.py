"""Tests for DictRuntime — atomic swap-rebuild + 10K benchmark (Phase 4)."""

from __future__ import annotations

import threading
import time
from dataclasses import FrozenInstanceError

import pytest

from phonofix.core.dict_runtime import DictRuntime, DictSnapshot
from phonofix.core.dict_schema import Term, TermMode

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def make_replace(canonical: str, alias: str = "alias", weight: float = 0.0) -> Term:
    return Term(canonical=canonical, mode=TermMode.REPLACE, aliases=[alias], weight=weight)


def make_protect(canonical: str) -> Term:
    return Term(canonical=canonical, mode=TermMode.PROTECT)


def make_10k_terms(n: int = 10_000) -> list[Term]:
    """Generate n unique replace-mode terms for benchmarking."""
    return [make_replace(f"term_{i:05d}", alias=f"alias_{i:05d}") for i in range(n)]


# ---------------------------------------------------------------------------
# Basic API tests
# ---------------------------------------------------------------------------


def test_empty_runtime_get_returns_version_zero():
    rt = DictRuntime()
    snap = rt.get()
    assert snap.version == 0
    assert len(snap.terms) == 0


def test_empty_runtime_stats():
    rt = DictRuntime()
    s = rt.stats()
    assert s["version"] == 0
    assert s["term_count"] == 0
    assert s["mem_bytes_estimate"] > 0


def test_add_terms_three_entries():
    rt = DictRuntime()
    terms = [make_replace("apple"), make_replace("banana"), make_protect("cherry")]
    snap = rt.add_terms(terms)
    assert snap.version == 1
    assert len(snap.terms) == 3
    # get() should reflect the same snapshot
    assert rt.get() is snap


def test_old_snapshot_immutable_after_add():
    """Snapshot captured before add_terms must not change."""
    rt = DictRuntime()
    old_snap = rt.get()
    assert old_snap.version == 0
    rt.add_terms([make_replace("newterm")])
    # old snapshot is unchanged
    assert old_snap.version == 0
    assert len(old_snap.terms) == 0


def test_remove_terms_decrements_count():
    rt = DictRuntime(initial_terms=[make_replace("a"), make_replace("b"), make_replace("c")])
    snap = rt.remove_terms(["a"])
    assert snap.version == 1
    assert len(snap.terms) == 2
    canonicals = {t.canonical for t in snap.terms}
    assert "a" not in canonicals
    assert {"b", "c"} <= canonicals


def test_remove_nonexistent_canonical_is_noop():
    rt = DictRuntime(initial_terms=[make_replace("x")])
    snap = rt.remove_terms(["does_not_exist"])
    # version bumps, term count unchanged
    assert snap.version == 1
    assert len(snap.terms) == 1


def test_duplicate_canonical_add_deduplicates():
    """Adding a term whose canonical already exists keeps the existing one."""
    original = make_replace("dup", alias="orig_alias")
    rt = DictRuntime(initial_terms=[original])
    # Try to add another term with same canonical
    incoming = make_replace("dup", alias="new_alias")
    snap = rt.add_terms([incoming])
    canonicals = [t.canonical for t in snap.terms]
    assert canonicals.count("dup") == 1
    # The existing alias should be preserved
    kept = next(t for t in snap.terms if t.canonical == "dup")
    assert kept.aliases == ["orig_alias"]


def test_snapshot_is_frozen_and_terms_is_tuple():
    """DictSnapshot is a frozen dataclass: terms field is a tuple (not a list),
    and mutating any field raises FrozenInstanceError."""
    rt = DictRuntime(initial_terms=[make_replace("hello")])
    snap = rt.get()
    # terms must be a tuple (immutable sequence)
    assert isinstance(snap.terms, tuple)
    # frozen: attempting to reassign any field must raise
    with pytest.raises(FrozenInstanceError):
        snap.version = 99  # type: ignore[misc]


def test_stats_returns_correct_version_and_term_count():
    terms = [make_replace(f"t{i}") for i in range(5)]
    rt = DictRuntime(initial_terms=terms)
    s = rt.stats()
    assert s["version"] == 0
    assert s["term_count"] == 5


def test_stats_mem_estimate_positive():
    rt = DictRuntime(initial_terms=[make_replace("foo")])
    s = rt.stats()
    assert s["mem_bytes_estimate"] > 0


def test_stats_mem_increases_with_more_terms():
    rt_small = DictRuntime(initial_terms=[make_replace("a")])
    rt_large = DictRuntime(initial_terms=[make_replace(f"term_{i}") for i in range(100)])
    assert rt_large.stats()["mem_bytes_estimate"] > rt_small.stats()["mem_bytes_estimate"]


def test_build_fn_injected_auxiliary_index():
    """build_fn result should be attached to snapshot as _aux_index."""
    sentinel = {}

    def build_fn(terms: tuple) -> dict:
        return {"count": len(terms), "marker": sentinel}

    rt = DictRuntime(initial_terms=[make_replace("a"), make_replace("b")], build_fn=build_fn)
    snap = rt.get()
    aux = getattr(snap, "_aux_index", None)
    assert aux is not None
    assert aux["count"] == 2
    assert aux["marker"] is sentinel


def test_build_fn_called_on_add_and_remove():
    """build_fn must be called on every swap-rebuild."""
    call_log = []

    def build_fn(terms: tuple) -> int:
        call_log.append(len(terms))
        return len(terms)

    rt = DictRuntime(initial_terms=[make_replace("a")], build_fn=build_fn)
    rt.add_terms([make_replace("b")])
    rt.remove_terms(["a"])
    # initial build + add + remove = 3 calls
    assert len(call_log) == 3
    assert call_log == [1, 2, 1]


def test_version_increments_monotonically():
    rt = DictRuntime()
    rt.add_terms([make_replace("a")])
    rt.add_terms([make_replace("b")])
    rt.remove_terms(["a"])
    assert rt.get().version == 3


# ---------------------------------------------------------------------------
# Concurrency tests
# ---------------------------------------------------------------------------


def test_concurrent_read_never_returns_torn_state():
    """100 reader threads + 1 writer thread — readers must always see a valid snapshot."""
    rt = DictRuntime(initial_terms=[make_replace("base")])
    errors: list[str] = []
    stop_event = threading.Event()

    def reader():
        while not stop_event.is_set():
            snap = rt.get()
            # Snapshot must always be a DictSnapshot with non-negative version
            if not isinstance(snap, DictSnapshot):
                errors.append(f"bad type: {type(snap)}")
            if snap.version < 0:
                errors.append(f"negative version: {snap.version}")
            if not isinstance(snap.terms, tuple):
                errors.append(f"terms not tuple: {type(snap.terms)}")

    def writer():
        for i in range(50):
            rt.add_terms([make_replace(f"concurrent_{i}")])
            time.sleep(0.001)
        stop_event.set()

    readers = [threading.Thread(target=reader, daemon=True) for _ in range(100)]
    w = threading.Thread(target=writer)

    for r in readers:
        r.start()
    w.start()
    w.join()
    for r in readers:
        r.join(timeout=2)

    assert not errors, f"Concurrency errors: {errors}"


def test_thread_safety_100_readers_1_writer_no_data_race():
    """Variant: use threading.Event to synchronize start; verify final state consistent."""
    start = threading.Event()
    rt = DictRuntime(initial_terms=[make_replace(f"init_{i}") for i in range(10)])
    read_results: list[int] = []
    lock = threading.Lock()

    def reader():
        start.wait()
        for _ in range(20):
            snap = rt.get()
            with lock:
                read_results.append(len(snap.terms))

    def writer():
        start.wait()
        for i in range(10):
            rt.add_terms([make_replace(f"w_{i}", alias=f"wa_{i}")])
            time.sleep(0.0005)

    threads = [threading.Thread(target=reader, daemon=True) for _ in range(100)]
    threads.append(threading.Thread(target=writer, daemon=True))

    for t in threads:
        t.start()
    start.set()
    for t in threads:
        t.join(timeout=5)

    # All read results must be >= 10 (initial) and <= 20 (after all adds)
    assert all(10 <= r <= 20 for r in read_results), f"Out-of-range reads: {set(read_results)}"


# ---------------------------------------------------------------------------
# Benchmarks (10K terms)
# ---------------------------------------------------------------------------


def test_benchmark_build_10k_terms_under_2s():
    """Build DictRuntime with 10 000 terms; must complete within 2 seconds."""
    terms = make_10k_terms(10_000)
    t0 = time.perf_counter()
    rt = DictRuntime(initial_terms=terms)
    elapsed = time.perf_counter() - t0

    assert rt.get().version == 0
    assert len(rt.get().terms) == 10_000
    assert elapsed < 2.0, f"10K build took {elapsed:.3f}s (limit 2s)"
    print(f"\n[benchmark] 10K initial build: {elapsed * 1000:.1f} ms")


def test_benchmark_incremental_add_100_to_10k_base():
    """Add 100 new terms to a 10K base; rebuild must complete within 500 ms."""
    base = make_10k_terms(10_000)
    rt = DictRuntime(initial_terms=base)

    new_terms = [make_replace(f"new_{i}", alias=f"na_{i}") for i in range(100)]
    t0 = time.perf_counter()
    snap = rt.add_terms(new_terms)
    elapsed = time.perf_counter() - t0

    assert len(snap.terms) == 10_100
    assert snap.version == 1
    assert elapsed < 0.5, f"Incremental add 100 to 10K took {elapsed * 1000:.1f} ms (limit 500ms)"
    print(f"\n[benchmark] incremental add 100 to 10K base: {elapsed * 1000:.1f} ms")

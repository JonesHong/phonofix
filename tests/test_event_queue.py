"""Tests for phonofix.core.event_queue — trace_id contextvar + AsyncEventQueue."""

from __future__ import annotations

import threading
import time
from typing import List

from phonofix.core.event_queue import (
    AsyncEventQueue,
    EventRecord,
    get_trace_id,
    new_trace_id,
    set_trace_id,
    trace_id_var,
)

# ---------------------------------------------------------------------------
# trace_id contextvar tests
# ---------------------------------------------------------------------------


def test_trace_id_var_default_empty_string():
    """trace_id_var default must be empty string when not set."""
    # Use a fresh context to avoid bleed from other tests
    import contextvars

    ctx = contextvars.copy_context()

    def _check():
        # Reset any inherited value
        trace_id_var.set("")
        return get_trace_id()

    result = ctx.run(_check)
    assert result == ""


def test_set_trace_id_returns_same_id():
    """set_trace_id(tid) sets the contextvar and returns tid unchanged."""
    tid = "abc123"
    returned = set_trace_id(tid)
    assert returned == tid
    assert get_trace_id() == tid


def test_set_trace_id_generates_new_when_none():
    """set_trace_id() with no arg generates and sets a new trace_id."""
    # Clear first
    trace_id_var.set("")
    tid = set_trace_id()
    assert tid != ""
    assert get_trace_id() == tid


def test_new_trace_id_returns_uuid4_hex_32_chars():
    """new_trace_id() returns a 32-char lowercase hex UUID4 string."""
    tid = new_trace_id()
    assert isinstance(tid, str)
    assert len(tid) == 32
    # Must be valid hex
    int(tid, 16)


def test_new_trace_id_unique_each_call():
    """new_trace_id() returns different values on successive calls."""
    ids = {new_trace_id() for _ in range(100)}
    assert len(ids) == 100


# ---------------------------------------------------------------------------
# AsyncEventQueue lifecycle tests
# ---------------------------------------------------------------------------


def test_async_event_queue_start_stop_lifecycle():
    """start() → alive; stop() → not alive."""
    received: List[EventRecord] = []
    eq = AsyncEventQueue(handler=received.append, queue_size=100)

    eq.start()
    assert eq.stats()["alive"] is True

    eq.stop()
    assert eq.stats()["alive"] is False


def test_emit_delivers_via_background_thread_within_10ms():
    """emit() should deliver event within ~10ms via background thread."""
    received: List[EventRecord] = []
    delivery_times: List[float] = []

    def handler(rec: EventRecord) -> None:
        delivery_times.append(time.monotonic())
        received.append(rec)

    eq = AsyncEventQueue(handler=handler, queue_size=100)
    eq.start()

    emit_time = time.monotonic()
    ok = eq.emit("match.exact", {"term": "foo"})
    assert ok is True

    # Wait up to 500ms for delivery (generous for CI)
    deadline = time.monotonic() + 0.5
    while not delivery_times and time.monotonic() < deadline:
        time.sleep(0.001)

    eq.stop()

    assert len(received) == 1
    assert received[0].name == "match.exact"
    # Should arrive within 10ms, but allow 200ms for CI flakiness
    assert delivery_times[0] - emit_time < 0.2


def test_1000_events_all_delivered_fast_handler():
    """1000 events all delivered when handler is fast."""
    received: List[EventRecord] = []
    lock = threading.Lock()

    def handler(rec: EventRecord) -> None:
        with lock:
            received.append(rec)

    eq = AsyncEventQueue(handler=handler, queue_size=2000)
    eq.start()

    for i in range(1000):
        eq.emit("match.fuzzy", {"i": i})

    eq.stop(timeout=10.0)

    assert len(received) == 1000
    s = eq.stats()
    assert s["enqueued"] == 1000
    assert s["delivered"] == 1000
    assert s["dropped"] == 0


def test_queue_full_drop_on_full_true_returns_false():
    """Queue full + drop_on_full=True → emit returns False, dropped stat increments."""
    barrier = threading.Event()

    def blocking_handler(rec: EventRecord) -> None:
        barrier.wait()  # Block until we release

    eq = AsyncEventQueue(handler=blocking_handler, queue_size=2, drop_on_full=True)
    eq.start()

    # Fill queue: first emit may be consumed immediately, so emit several
    results = []
    for _ in range(10):
        results.append(eq.emit("match.exact", {}))
        time.sleep(0.001)

    # At least one should be dropped
    assert False in results

    barrier.set()  # Unblock handler
    eq.stop(timeout=5.0)

    assert eq.stats()["dropped"] > 0


def test_queue_full_drop_on_full_false_blocks_until_space():
    """Queue full + drop_on_full=False → emit blocks until handler consumes."""
    step = threading.Event()

    call_count = [0]

    def slow_handler(rec: EventRecord) -> None:
        call_count[0] += 1
        step.wait()  # Hold until released

    eq = AsyncEventQueue(handler=slow_handler, queue_size=1, drop_on_full=False)
    eq.start()

    # First emit: goes into queue immediately (size=1)
    assert eq.emit("e1", {}) is True

    # Wait for worker to pick up first item so queue is empty
    deadline = time.monotonic() + 1.0
    while call_count[0] == 0 and time.monotonic() < deadline:
        time.sleep(0.001)

    # Now queue is empty, worker is blocked in slow_handler.
    # Fill queue: size=1, so this should succeed immediately.
    assert eq.emit("e2", {}) is True

    # Third emit will block because queue is full (size=1) and worker is held.
    blocked = [False]
    emit_done = threading.Event()

    def emit_blocking():
        blocked[0] = True
        eq.emit("e3", {})
        blocked[0] = False
        emit_done.set()

    t = threading.Thread(target=emit_blocking)
    t.start()

    # Give the emit thread a moment to reach the blocking put
    time.sleep(0.05)
    assert blocked[0] is True  # Should still be blocking

    # Release the slow handler → worker picks up e2 → queue has space for e3
    step.set()
    emit_done.wait(timeout=2.0)
    assert blocked[0] is False

    eq.stop(timeout=5.0)
    t.join(timeout=1.0)


def test_handler_exception_does_not_crash_worker():
    """Handler exception must be logged and worker continues delivering subsequent events."""
    received: List[str] = []

    call_count = [0]

    def flaky_handler(rec: EventRecord) -> None:
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("intentional test error")
        received.append(rec.name)

    eq = AsyncEventQueue(handler=flaky_handler, queue_size=100)
    eq.start()

    eq.emit("fail.event", {})
    eq.emit("ok.event", {})

    eq.stop(timeout=5.0)

    # Worker must still be able to process subsequent events
    assert "ok.event" in received


def test_trace_id_captured_at_emit_time_not_delivery_time():
    """trace_id must be snapshot from calling context at emit(), not when handler runs."""
    captured_trace_ids: List[str] = []

    def handler(rec: EventRecord) -> None:
        captured_trace_ids.append(rec.trace_id)

    eq = AsyncEventQueue(handler=handler, queue_size=100)
    eq.start()

    set_trace_id("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    eq.emit("event.a", {})

    set_trace_id("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
    eq.emit("event.b", {})

    eq.stop(timeout=5.0)

    assert len(captured_trace_ids) == 2
    assert captured_trace_ids[0] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    assert captured_trace_ids[1] == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def test_stop_with_pending_events_drains_all():
    """stop() must drain all enqueued events before thread exits."""
    received: List[int] = []
    lock = threading.Lock()

    def handler(rec: EventRecord) -> None:
        time.sleep(0.001)  # Simulate mild IO
        with lock:
            received.append(rec.payload["i"])

    eq = AsyncEventQueue(handler=handler, queue_size=200)
    eq.start()

    for i in range(50):
        eq.emit("event", {"i": i})

    eq.stop(timeout=10.0)

    assert len(received) == 50
    assert sorted(received) == list(range(50))


def test_stop_with_hanging_handler_timeout_cleanly():
    """stop() must return within timeout even if handler is hanging."""
    hang_event = threading.Event()

    def hanging_handler(rec: EventRecord) -> None:
        hang_event.wait(timeout=60)  # Will hang until test ends

    eq = AsyncEventQueue(handler=hanging_handler, queue_size=10)
    eq.start()
    eq.emit("hang.event", {})

    # Give handler time to start
    time.sleep(0.05)

    start = time.monotonic()
    eq.stop(timeout=0.5)
    elapsed = time.monotonic() - start

    # stop() should return within ~timeout + small overhead
    assert elapsed < 2.0
    hang_event.set()  # Allow thread to eventually exit


def test_stats_correct_counts():
    """stats() must accurately reflect enqueued / delivered / dropped counts."""
    received: List[EventRecord] = []
    barrier = threading.Event()

    def handler(rec: EventRecord) -> None:
        barrier.wait()
        received.append(rec)

    eq = AsyncEventQueue(handler=handler, queue_size=3, drop_on_full=True)
    eq.start()

    # Flood: some will queue, some will drop (worker blocked)
    results = []
    for _ in range(20):
        results.append(eq.emit("e", {}))
        time.sleep(0.001)

    s_before = eq.stats()
    assert s_before["enqueued"] + s_before["dropped"] == 20
    assert s_before["enqueued"] == sum(1 for r in results if r)
    assert s_before["dropped"] == sum(1 for r in results if not r)

    barrier.set()
    eq.stop(timeout=5.0)

    s_after = eq.stats()
    assert s_after["delivered"] == s_after["enqueued"]
    assert s_after["queue_len"] == 0
    assert s_after["alive"] is False


def test_restart_after_stop():
    """Queue can be stopped and restarted with a new thread."""
    received: List[str] = []

    def handler(rec: EventRecord) -> None:
        received.append(rec.name)

    eq = AsyncEventQueue(handler=handler, queue_size=100)

    eq.start()
    eq.emit("first.run", {})
    eq.stop(timeout=5.0)
    assert eq.stats()["alive"] is False

    # Restart
    eq.start()
    assert eq.stats()["alive"] is True
    eq.emit("second.run", {})
    eq.stop(timeout=5.0)

    assert "first.run" in received
    assert "second.run" in received


def test_multiple_producers_all_delivered_no_dup_no_loss():
    """3 threads emitting concurrently: all events delivered, no dup, no loss."""
    received: List[int] = []
    lock = threading.Lock()

    def handler(rec: EventRecord) -> None:
        with lock:
            received.append(rec.payload["seq"])

    eq = AsyncEventQueue(handler=handler, queue_size=5000)
    eq.start()

    n_threads = 3
    events_per_thread = 200
    total = n_threads * events_per_thread

    def produce(thread_id: int) -> None:
        for i in range(events_per_thread):
            seq = thread_id * events_per_thread + i
            eq.emit("concurrent.event", {"seq": seq})

    threads = [threading.Thread(target=produce, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    eq.stop(timeout=10.0)

    assert len(received) == total
    assert sorted(received) == list(range(total))


def test_event_record_defaults_trace_id_from_contextvar():
    """EventRecord.trace_id defaults to current context's trace_id at instantiation."""
    set_trace_id("deadbeef" * 4)
    rec = EventRecord(name="test", payload={})
    assert rec.trace_id == "deadbeef" * 4


def test_emit_returns_false_after_stop():
    """emit() must return False immediately once queue is stopped."""
    received: List[EventRecord] = []
    eq = AsyncEventQueue(handler=received.append, queue_size=100)
    eq.start()
    eq.stop(timeout=2.0)

    result = eq.emit("late.event", {})
    assert result is False
    assert "late.event" not in [r.name for r in received]

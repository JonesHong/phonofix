"""on_event async/queue + trace_id contextvar (Phase 4).

Goals:
1. Async/queue: sync IO event handlers must not block hot path.
2. trace_id: contextvar auto-inherited across feed/correct calls for log correlation.
"""

from __future__ import annotations

import contextvars
import logging
import queue
import threading
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# trace_id contextvar — auto-inherited in async tasks + child threads via copy_context
# ---------------------------------------------------------------------------

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("phonofix_trace_id", default="")


def new_trace_id() -> str:
    """Generate UUID4 hex string (32 chars, no dashes)."""
    return uuid.uuid4().hex


def set_trace_id(trace_id: str | None = None) -> str:
    """Set trace_id in current context (or generate new). Returns the trace_id set."""
    tid = trace_id or new_trace_id()
    trace_id_var.set(tid)
    return tid


def get_trace_id() -> str:
    """Get current trace_id (empty string if not set)."""
    return trace_id_var.get()


# ---------------------------------------------------------------------------
# EventRecord
# ---------------------------------------------------------------------------


@dataclass
class EventRecord:
    """Single event for queue delivery."""

    name: str  # match.exact / match.fuzzy / match.protected / conflict.resolved / miss.no_hit
    payload: dict
    trace_id: str = field(default_factory=get_trace_id)


# Sentinel for graceful shutdown
_STOP_SENTINEL = object()


# ---------------------------------------------------------------------------
# AsyncEventQueue
# ---------------------------------------------------------------------------


class AsyncEventQueue:
    """
    Background-thread event delivery.

    Caller registers handler; feed events enqueue → worker thread dispatches.

    Use::

        eq = AsyncEventQueue(handler=my_handler, queue_size=1000)
        eq.start()
        eq.emit("match.exact", {...})
        eq.stop()   # graceful drain + join thread

    Thread safety:
    - ``emit()`` / ``stats()`` are safe to call from any thread.
    - ``start()`` / ``stop()`` should be called from a single controlling thread.
    - Re-entrant ``stop()`` is safe (idempotent after first call).
    """

    def __init__(
        self,
        handler: Callable[[EventRecord], None],
        queue_size: int = 1000,
        drop_on_full: bool = True,
    ) -> None:
        """
        Args:
            handler: Called in background thread for each EventRecord.
                     Must not raise uncaught exceptions (they are logged + swallowed).
            queue_size: Bounded queue capacity.
            drop_on_full: If True, ``emit()`` returns False when queue is full.
                          If False, ``emit()`` blocks until space is available.
        """
        self._handler = handler
        self._queue: queue.Queue[object] = queue.Queue(maxsize=queue_size)
        self._drop_on_full = drop_on_full

        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()  # guards _thread + _stopped
        self._stopped = True

        # atomic counters via lock
        self._stat_lock = threading.Lock()
        self._enqueued = 0
        self._delivered = 0
        self._dropped = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start background worker thread.

        Idempotent — calling start() on an already-running queue is a no-op.
        After ``stop()`` + ``start()``, a new thread is created (restart is supported).
        """
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stopped = False
            self._thread = threading.Thread(
                target=self._worker,
                name="AsyncEventQueue-worker",
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Signal stop, drain queue, join thread (or timeout).

        After stop(), no more events will be delivered. Events still in the queue
        when the sentinel is processed are drained before the thread exits.
        Subsequent calls to ``emit()`` return False (drop).
        """
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            thread = self._thread

        if thread is not None:
            try:
                self._queue.put_nowait(_STOP_SENTINEL)
            except queue.Full:
                # Queue is full; put with a short timeout to push sentinel in
                try:
                    self._queue.put(_STOP_SENTINEL, timeout=1.0)
                except queue.Full:
                    pass  # Worker will see _stopped flag and exit anyway
            thread.join(timeout=timeout)

    # ------------------------------------------------------------------
    # Emission
    # ------------------------------------------------------------------

    def emit(self, name: str, payload: dict) -> bool:
        """Enqueue event. Returns True if enqueued, False if dropped.

        Captures trace_id from the calling thread's current context at call time,
        not at delivery time — snapshot semantics.

        Args:
            name: Event name (e.g. "match.exact").
            payload: Event payload dict.

        Returns:
            True if the event was enqueued; False if dropped (queue full +
            drop_on_full=True) or if the queue has been stopped.
        """
        with self._lock:
            stopped = self._stopped

        if stopped:
            return False

        record = EventRecord(name=name, payload=payload, trace_id=get_trace_id())

        if self._drop_on_full:
            try:
                self._queue.put_nowait(record)
            except queue.Full:
                with self._stat_lock:
                    self._dropped += 1
                return False
        else:
            # Blocking put — will wait until space is available
            self._queue.put(record)

        with self._stat_lock:
            self._enqueued += 1
        return True

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return current statistics snapshot.

        Returns:
            dict with keys: enqueued, delivered, dropped, queue_len, alive.
        """
        with self._stat_lock:
            enqueued = self._enqueued
            delivered = self._delivered
            dropped = self._dropped

        thread = self._thread
        return {
            "enqueued": enqueued,
            "delivered": delivered,
            "dropped": dropped,
            "queue_len": self._queue.qsize(),
            "alive": thread is not None and thread.is_alive(),
        }

    # ------------------------------------------------------------------
    # Internal worker
    # ------------------------------------------------------------------

    def _worker(self) -> None:
        """Background thread: drain queue until sentinel or _stopped."""
        while True:
            try:
                item = self._queue.get(timeout=0.05)
            except queue.Empty:
                # Check stop flag between drains
                with self._lock:
                    if self._stopped and self._queue.empty():
                        break
                continue

            if item is _STOP_SENTINEL:
                # Drain any remaining items before exiting
                self._drain_remaining()
                break

            if not isinstance(item, EventRecord):
                # Unexpected item type — skip
                self._queue.task_done()
                continue

            try:
                self._handler(item)
            except Exception:
                logger.exception(
                    "AsyncEventQueue handler raised exception for event %r; continuing.",
                    item.name,
                )
            finally:
                self._queue.task_done()
                with self._stat_lock:
                    self._delivered += 1

    def _drain_remaining(self) -> None:
        """Deliver all remaining items currently in queue (called after sentinel)."""
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break

            if item is _STOP_SENTINEL:
                self._queue.task_done()
                continue

            if isinstance(item, EventRecord):
                try:
                    self._handler(item)
                except Exception:
                    logger.exception(
                        "AsyncEventQueue handler raised exception during drain for event %r.",
                        item.name,
                    )
                finally:
                    self._queue.task_done()
                    with self._stat_lock:
                        self._delivered += 1
            else:
                self._queue.task_done()

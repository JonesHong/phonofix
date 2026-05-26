"""Phase 5 integration tests for PhoneticMatcher.

Tests wire PhoneticMatcher.correct/correct_batch/explain/diagnose
against real DictRuntime + AC expansion + EventQueue.

Uses a minimal SimpleNamespace mock phonemizer — no real G2P backend required.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace
from typing import Any

from phonofix.core.dict_schema import Term, TermMode
from phonofix.core.event_queue import EventRecord
from phonofix.core.matcher import PhoneticMatcher

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _mock_phonemizer(language: str = "zh") -> SimpleNamespace:
    """Minimal duck-typed phonemizer for testing."""
    return SimpleNamespace(language=language, name="mock-phonemizer")


def _make_matcher(
    dictionary: Any,
    on_event=None,
    language: str = "zh",
) -> PhoneticMatcher:
    return PhoneticMatcher(
        phonemizer=_mock_phonemizer(language),
        dictionary=dictionary,
        on_event=on_event,
    )


# ---------------------------------------------------------------------------
# 1. Simple zh dict: alias → canonical replacement
# ---------------------------------------------------------------------------


def test_simple_alias_replace_zh() -> None:
    """canonical='台北車站', aliases=['北車'] → correct('我在北車') == '我在台北車站'"""
    m = _make_matcher(
        {
            "台北車站": {"aliases": ["北車"], "keywords": [], "weight": 0.0},
        }
    )
    assert m.correct("我在北車") == "我在台北車站"


def test_simple_alias_no_match() -> None:
    """Text with no alias → unchanged."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    assert m.correct("我在台北") == "我在台北"


def test_alias_at_start_of_text() -> None:
    """Alias at position 0."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    assert m.correct("北車的時刻表") == "台北車站的時刻表"


def test_alias_at_end_of_text() -> None:
    """Alias at end of string."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    assert m.correct("我要去北車") == "我要去台北車站"


def test_multiple_aliases_same_canonical() -> None:
    """Two aliases both map to the same canonical."""
    m = _make_matcher({"台北車站": {"aliases": ["北車", "北站"]}})
    assert m.correct("在北車下車") == "在台北車站下車"
    assert m.correct("搭到北站") == "搭到台北車站"


# ---------------------------------------------------------------------------
# 2. protect mode
# ---------------------------------------------------------------------------


def test_protect_mode_canonical_unchanged() -> None:
    """protect mode: canonical '枝節' in text is NOT replaced."""
    # protect-mode term has no aliases → its canonical span is protected
    m = _make_matcher(
        [
            Term(canonical="枝節", mode=TermMode.PROTECT),
        ]
    )
    result = m.correct("這個枝節問題")
    assert result == "這個枝節問題"


def test_protect_mode_does_not_interfere_with_other_replacements() -> None:
    """protect term doesn't block an unrelated replace term."""
    m = _make_matcher(
        [
            Term(canonical="枝節", mode=TermMode.PROTECT),
            Term(canonical="台北車站", mode=TermMode.REPLACE, aliases=["北車"]),
        ]
    )
    result = m.correct("枝節問題與北車時刻")
    # protect 不擋 unrelated replace；alias 應該被替換成 canonical
    # (注意：「北車」是「台北車站」的子字串，不能用 `not in result` 驗，要驗整段完整等於)
    assert result == "枝節問題與台北車站時刻"


# ---------------------------------------------------------------------------
# 3. Canonical mask P0 — prevent infinite-loop replacement
# ---------------------------------------------------------------------------


def test_canonical_mask_prevents_self_replacement() -> None:
    """
    P0 bug: if '北車' is an alias for '台北車站', and input IS '台北車站',
    the embedded '北車' must NOT be replaced again → no double-replacement.
    """
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    # The canonical '台北車站' contains the alias '北車' — should NOT be re-replaced
    result = m.correct("台北車站")
    assert result == "台北車站"


def test_canonical_mask_mixed_canonical_and_alias() -> None:
    """canonical literal in text is preserved; alias elsewhere is replaced."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    result = m.correct("台北車站和北車都是同一個地方")
    # '台北車站' span is protected; '北車' after is replaced
    assert result == "台北車站和台北車站都是同一個地方"


# ---------------------------------------------------------------------------
# 4. correct_batch consistency
# ---------------------------------------------------------------------------


def test_correct_batch_consistent_with_correct() -> None:
    """correct_batch results match individual correct() calls."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    texts = ["我在北車", "台北車站很近", "不相關文字"]
    batch = m.correct_batch(texts)
    individual = [m.correct(t) for t in texts]
    assert batch == individual


def test_correct_batch_empty_input() -> None:
    """Empty iterable → empty list."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    assert m.correct_batch([]) == []


# ---------------------------------------------------------------------------
# 5. feed + flush streaming end-to-end
# ---------------------------------------------------------------------------


def test_feed_flush_streaming_basic() -> None:
    """feed() + flush() correctly replaces alias across stream."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    # Feed in one chunk, flush remainder
    out1 = m.feed("我在")
    out2 = m.feed("北車")
    out3 = m.flush()
    full = out1 + out2 + out3
    assert "台北車站" in full or "北車" in full  # either replaced or held in buffer
    # The complete output must contain canonical
    assert "台北車站" in full


def test_feed_flush_no_match_passthrough() -> None:
    """Streaming text with no alias passes through unchanged."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    out = m.feed("台灣大學")
    out += m.flush()
    assert "台灣大學" in out


def test_flush_idempotent() -> None:
    """Second flush() call returns empty string."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    m.feed("文字")
    m.flush()
    assert m.flush() == ""


# ---------------------------------------------------------------------------
# 6. add_terms hot-reload
# ---------------------------------------------------------------------------


def test_add_terms_new_term_is_corrected() -> None:
    """After add_terms(), correct() recognizes the new term."""
    m = _make_matcher({})
    # Before add: no replacement
    assert m.correct("太積電") == "太積電"

    m.add_terms([Term(canonical="台積電", mode=TermMode.REPLACE, aliases=["太積電"])])
    assert m.correct("太積電") == "台積電"


def test_add_terms_dict_form() -> None:
    """add_terms() accepts dict-form entries."""
    m = _make_matcher({})
    m.add_terms([{"canonical": "微軟", "mode": "replace", "aliases": ["威軟"]}])
    assert m.correct("威軟公司") == "微軟公司"


# ---------------------------------------------------------------------------
# 7. remove_terms hot-reload
# ---------------------------------------------------------------------------


def test_remove_terms_stops_replacement() -> None:
    """After remove_terms(), correct() no longer replaces the removed term."""
    m = _make_matcher({"台積電": {"aliases": ["太積電"]}})
    assert m.correct("太積電") == "台積電"

    m.remove_terms(["台積電"])
    assert m.correct("太積電") == "太積電"


def test_remove_nonexistent_term_no_error() -> None:
    """remove_terms() with unknown canonical is a silent no-op."""
    m = _make_matcher({"台積電": {"aliases": ["太積電"]}})
    m.remove_terms(["不存在的詞"])  # must not raise
    assert m.correct("太積電") == "台積電"


# ---------------------------------------------------------------------------
# 8. explain()
# ---------------------------------------------------------------------------


def test_explain_returns_required_keys() -> None:
    """explain() returns dict with version/dict_size/trace_id/result."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    result = m.explain("我在北車")
    assert isinstance(result, dict)
    assert "version" in result
    assert "dict_size" in result
    assert "trace_id" in result
    assert "result" in result
    assert result["dict_size"] == 1
    assert result["result"] == "我在台北車站"


def test_explain_result_matches_correct() -> None:
    """explain()['result'] must equal correct() output."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    text = "我在北車等你"
    assert m.explain(text)["result"] == m.correct(text)


# ---------------------------------------------------------------------------
# 9. diagnose()
# ---------------------------------------------------------------------------


def test_diagnose_returns_required_keys() -> None:
    """diagnose() returns dict with ac_engine and other required fields."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    d = m.diagnose()
    assert isinstance(d, dict)
    assert "version" in d
    assert "dict_version" in d
    assert "dict_size" in d
    assert "ac_engine" in d
    assert "backends_loaded" in d


def test_diagnose_ac_engine_pyahocorasick() -> None:
    """diagnose()['ac_engine'] == 'pyahocorasick' when dict has aliases."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    assert m.diagnose()["ac_engine"] == "pyahocorasick"


def test_diagnose_dict_size() -> None:
    """diagnose()['dict_size'] reflects actual term count."""
    m = _make_matcher(
        {
            "台北車站": {"aliases": ["北車"]},
            "台積電": {"aliases": ["太積電"]},
        }
    )
    assert m.diagnose()["dict_size"] == 2


# ---------------------------------------------------------------------------
# 10. on_event handler called with EventRecord
# ---------------------------------------------------------------------------


def test_on_event_called_on_match() -> None:
    """on_event handler receives EventRecord when a match.exact event fires."""
    received: list[EventRecord] = []
    lock = threading.Lock()

    def handler(record: EventRecord) -> None:
        with lock:
            received.append(record)

    m = PhoneticMatcher(
        phonemizer=_mock_phonemizer(),
        dictionary={"台北車站": {"aliases": ["北車"]}},
        on_event=handler,
    )
    m.correct("我在北車")
    # Allow background thread time to deliver the event
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        with lock:
            if received:
                break
        time.sleep(0.01)

    m.close()
    with lock:
        assert len(received) >= 1
        assert isinstance(received[0], EventRecord)
        assert received[0].name == "match.exact"


def test_on_event_none_no_crash() -> None:
    """No on_event handler → no crash, correct() still works."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    assert m.correct("我在北車") == "我在台北車站"


# ---------------------------------------------------------------------------
# 11. close() — no exception
# ---------------------------------------------------------------------------


def test_close_no_exception() -> None:
    """close() with active event queue shuts down cleanly."""
    received: list = []

    def handler(r: EventRecord) -> None:
        received.append(r)

    m = PhoneticMatcher(
        phonemizer=_mock_phonemizer(),
        dictionary={"台北車站": {"aliases": ["北車"]}},
        on_event=handler,
    )
    m.close()  # must not raise


def test_close_without_event_queue_no_exception() -> None:
    """close() without on_event is a no-op (no exception)."""
    m = _make_matcher({"台北車站": {"aliases": ["北車"]}})
    m.close()  # must not raise

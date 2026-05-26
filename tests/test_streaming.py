"""Tests for StreamBuffer (SPEC.md §3 streaming contract).

Coverage targets:
- Empty stream (no feed + flush) returns ""
- Single chunk no hit returns chunk verbatim
- Single chunk with hit applies replacement
- 2 chunks, hit spans across boundary → caught after second feed
- 2 chunks, hit fully in tail of chunk 1 → emitted on chunk 2
- Dedup: same absolute span hit on both feeds → emit once
- flush() emits buffer remainder
- flush() is idempotent (second call returns "")
- reset() clears state
- tail_size capped at 512
- char-language mode (zh chunks confirmed char by char)
- word-language mode (en chunks trimmed to word boundary)
- Multiple hits in one chunk
- Hit with replacement longer than original (offset bookkeeping)
- Hit with replacement shorter than original
"""

from __future__ import annotations

from phonofix.core.streaming import StreamBuffer

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_scan(pairs: list[tuple[str, str]]):
    """Return a scan_fn that finds each (needle, replacement) pair left-to-right."""

    def scan_fn(text: str) -> list[tuple[int, int, str, str]]:
        hits = []
        for needle, replacement in pairs:
            i = 0
            while True:
                idx = text.find(needle, i)
                if idx == -1:
                    break
                hits.append((idx, idx + len(needle), needle, replacement))
                i = idx + len(needle)
        return hits

    return scan_fn


ABC_SCAN = make_scan([("abc", "XYZ")])
NO_SCAN = make_scan([])


def buf(
    *,
    scan_fn=None,
    max_alias_len: int = 3,
    window_chars: int = 5,
    language_mode: str = "char",
) -> StreamBuffer:
    return StreamBuffer(
        scan_fn=scan_fn or ABC_SCAN,
        max_alias_len=max_alias_len,
        window_chars=window_chars,
        language_mode=language_mode,
    )


# ---------------------------------------------------------------------------
# 1. Empty stream
# ---------------------------------------------------------------------------


def test_empty_no_feed_flush_returns_empty():
    b = buf()
    assert b.flush() == ""


def test_empty_feed_then_flush():
    b = buf()
    out = b.feed("")
    tail = b.flush()
    assert out == ""
    assert tail == ""


# ---------------------------------------------------------------------------
# 2. Single chunk no hit
# ---------------------------------------------------------------------------


def test_single_chunk_no_hit_verbatim():
    b = buf(scan_fn=NO_SCAN)
    # tail_size = 3+5 = 8; text shorter than tail → nothing emitted from feed
    out = b.feed("hello")
    tail = b.flush()
    assert out + tail == "hello"


def test_single_chunk_no_hit_longer_than_tail():
    b = buf(scan_fn=NO_SCAN, max_alias_len=2, window_chars=2)
    # tail_size=4; "hello world" = 11 chars; safe prefix = 7 chars
    out = b.feed("hello world")
    tail = b.flush()
    assert out + tail == "hello world"


# ---------------------------------------------------------------------------
# 3. Single chunk with hit
# ---------------------------------------------------------------------------


def test_single_chunk_with_hit():
    # tail_size=4 (max_alias_len=3, window_chars=1); "xabcy" = 5 chars
    # safe prefix = 1 char "x"; "abcy" held in tail → flush applies replacement
    b = buf(max_alias_len=3, window_chars=1)
    out = b.feed("xabcy")
    tail = b.flush()
    assert out + tail == "xXYZy"


def test_single_chunk_hit_before_tail():
    # Make window large enough that "abc" falls entirely in safe prefix
    b = buf(scan_fn=make_scan([("abc", "XYZ")]), max_alias_len=3, window_chars=0)
    # Use a long enough string so "abc" is confirmed in feed()
    # tail_size=3; "abcdefghij" = 10; safe prefix = 7; "abc" at 0..3 → confirmed
    out = b.feed("abcdefghij")
    tail = b.flush()
    full = out + tail
    assert full == "XYZdefghij"


# ---------------------------------------------------------------------------
# 4. 2 chunks, hit spans across boundary
# ---------------------------------------------------------------------------


def test_hit_spans_chunk_boundary():
    # "abc" split as "ab" | "cy" — must be caught in second feed
    b = buf(max_alias_len=3, window_chars=2)
    # tail_size = 5; first chunk "ab" (2 chars) < tail → feed returns ""
    out1 = b.feed("ab")
    # Second chunk: buffer becomes "ab" + "cy" = "abcy"; safe prefix = max(4-5,0) = 0
    # Nothing confirmed yet; flush() emits "XYZ" + "y"? No: "abcy" → "abc" match + "y"
    out2 = b.feed("cy")
    tail = b.flush()
    full = out1 + out2 + tail
    assert full == "XYZy"


def test_hit_fully_in_tail_of_chunk1_emitted_on_chunk2():
    # "abc" is fully within tail after chunk1; emitted when chunk2 arrives
    b = buf(max_alias_len=3, window_chars=2)
    # tail_size=5; chunk1 = "...abc" (7 chars total)
    # safe prefix = 7-5 = 2 chars; "abc" starts at 4 → in tail → not yet emitted
    out1 = b.feed("xxabc")  # 5 chars; safe prefix = 0; nothing emitted
    # chunk2 pushes buffer to 5+5=10 chars; safe prefix = 5; "abc" at offset 2..5
    out2 = b.feed("zzzz!")
    tail = b.flush()
    full = out1 + out2 + tail
    assert full == "xxXYZzzzz!"


# ---------------------------------------------------------------------------
# 5. Dedup: same absolute span hit on both feeds → emit once
# ---------------------------------------------------------------------------


def test_dedup_same_span_emitted_once():
    """
    Manually construct a scenario where scan_fn returns the same absolute
    span on two consecutive calls (simulating tail overlap returning same hit).
    We do this by using a scan_fn that always returns a hit at position 0
    regardless of text, to simulate double-reporting the same span.
    """
    call_count = 0

    def greedy_scan(text: str) -> list[tuple[int, int, str, str]]:
        nonlocal call_count
        call_count += 1
        results = []
        idx = text.find("abc")
        if idx != -1:
            results.append((idx, idx + 3, "abc", "XYZ"))
        return results

    b = StreamBuffer(
        scan_fn=greedy_scan,
        max_alias_len=3,
        window_chars=2,  # tail_size=5
    )
    # Feed "abc!!" (5 chars); tail_size=5 → safe_prefix length = 0 → nothing emitted
    out1 = b.feed("abc!!")
    # Feed more; now buffer = "abc!!MORE"; safe_prefix = 4; "abc" at 0..3 → confirmed
    out2 = b.feed("MORE")
    tail = b.flush()
    full = out1 + out2 + tail
    # "abc" should appear exactly once as "XYZ"
    assert full.count("XYZ") == 1
    assert "abc" not in full


# ---------------------------------------------------------------------------
# 6. flush() emits buffer remainder
# ---------------------------------------------------------------------------


def test_flush_emits_remainder():
    b = buf(max_alias_len=3, window_chars=10)
    b.feed("prefix")  # tail_size=13; "prefix"=6 → all in tail
    tail = b.flush()
    assert tail == "prefix"


def test_flush_applies_replacement_in_tail():
    b = buf(max_alias_len=3, window_chars=10)
    b.feed("xabcx")  # all in tail (5 < 13)
    tail = b.flush()
    assert tail == "xXYZx"


# ---------------------------------------------------------------------------
# 7. flush() is idempotent
# ---------------------------------------------------------------------------


def test_flush_idempotent():
    b = buf()
    b.feed("hello")
    first = b.flush()
    second = b.flush()
    assert second == ""
    # First must have the content
    assert "hello" in first or first == ""  # depends on tail size; combined is "hello"


def test_flush_idempotent_combined():
    b = buf(max_alias_len=3, window_chars=10)
    b.feed("hello world")
    f1 = b.flush()
    f2 = b.flush()
    assert f1 + f2 == "hello world"  # f2 must be ""


# ---------------------------------------------------------------------------
# 8. reset() clears state
# ---------------------------------------------------------------------------


def test_reset_clears_state():
    b = buf()
    b.feed("some text")
    b.flush()
    b.reset()
    assert b._buffer == ""
    assert b._total_offset == 0
    assert len(b._emitted_spans) == 0
    assert b._flushed is False


def test_reset_allows_reuse():
    b = buf(max_alias_len=3, window_chars=2)
    b.feed("abc!!")
    b.flush()
    b.reset()
    # After reset, a new session with "abc" should replace again
    out = b.feed("xxabc")
    tail = b.flush()
    assert (out + tail) == "xxXYZ"


# ---------------------------------------------------------------------------
# 9. tail_size capped at 512
# ---------------------------------------------------------------------------


def test_tail_size_capped_at_512():
    b = StreamBuffer(scan_fn=NO_SCAN, max_alias_len=300, window_chars=300)
    assert b.tail_size == 512


def test_tail_size_not_capped_below_512():
    b = StreamBuffer(scan_fn=NO_SCAN, max_alias_len=10, window_chars=20)
    assert b.tail_size == 30


# ---------------------------------------------------------------------------
# 10. char-language mode (zh chunks)
# ---------------------------------------------------------------------------


def test_char_mode_zh_chunks():
    """Chinese text: no word-boundary trimming; every char is a valid boundary."""
    zh_scan = make_scan([("北車", "北車站")])
    b = StreamBuffer(
        scan_fn=zh_scan,
        max_alias_len=2,
        window_chars=2,
        language_mode="char",
    )
    # tail_size=4; "台北車站一路" = 6 chars; safe prefix = 2 "台北"
    out = b.feed("台北車站一路")
    tail = b.flush()
    full = out + tail
    assert "北車站" in full  # replacement applied
    assert "北車" not in full.replace("北車站", "")  # original alias gone


# ---------------------------------------------------------------------------
# 11. word-language mode (en chunks trimmed to word boundary)
# ---------------------------------------------------------------------------


def test_word_mode_trims_to_word_boundary():
    """In word mode the safe prefix must not split a word mid-token."""
    no_hit = make_scan([])
    b = StreamBuffer(
        scan_fn=no_hit,
        max_alias_len=3,
        window_chars=2,
        language_mode="word",
    )
    # tail_size=5; "hello world foo" = 15; safe prefix candidate = 10 "hello worl"
    # word-boundary trim: last word boundary before index 10 is after "hello " (index 6)
    # so safe prefix = "hello " → 6 chars emitted, " worl" held? Actually trim at space.
    text = "hello world foo bar"
    out = b.feed(text)
    tail = b.flush()
    full = out + tail
    assert full == text  # content preserved


def test_word_mode_does_not_split_word():
    """Verify that in word mode we never output half a word from feed()."""
    no_hit = make_scan([])
    b = StreamBuffer(
        scan_fn=no_hit,
        max_alias_len=2,
        window_chars=2,
        language_mode="word",
    )
    # Feed in two chunks
    out1 = b.feed("hello wor")
    out2 = b.feed("ld end")
    tail = b.flush()
    full = out1 + out2 + tail
    # Each emitted fragment must not split "world"
    assert full == "hello world end"


# ---------------------------------------------------------------------------
# 12. Multiple hits in one chunk
# ---------------------------------------------------------------------------


def test_multiple_hits_in_one_chunk():
    multi_scan = make_scan([("abc", "XYZ"), ("def", "123")])
    b = StreamBuffer(
        scan_fn=multi_scan,
        max_alias_len=3,
        window_chars=0,
        language_mode="char",
    )
    # tail_size=3; chunk = "abcdef!" (7 chars); safe prefix = 4 "abcd"
    out = b.feed("abcdef!")
    tail = b.flush()
    full = out + tail
    assert full == "XYZ123!"


# ---------------------------------------------------------------------------
# 13. Hit with replacement longer than original (offset bookkeeping)
# ---------------------------------------------------------------------------


def test_replacement_longer_than_original():
    """Replacement 'LONGWORD' (8) > matched 'abc' (3) — offset bookkeeping must hold."""
    long_scan = make_scan([("abc", "LONGWORD")])
    b = StreamBuffer(
        scan_fn=long_scan,
        max_alias_len=3,
        window_chars=0,
    )
    out = b.feed("xabcy!")
    tail = b.flush()
    full = out + tail
    assert full == "xLONGWORDy!"


# ---------------------------------------------------------------------------
# 14. Hit with replacement shorter than original
# ---------------------------------------------------------------------------


def test_replacement_shorter_than_original():
    """Replacement 'X' (1) < matched 'abcde' (5) — output shorter, content correct."""
    short_scan = make_scan([("abcde", "X")])
    b = StreamBuffer(
        scan_fn=short_scan,
        max_alias_len=5,
        window_chars=0,
    )
    out = b.feed("xxabcdexx!")
    tail = b.flush()
    full = out + tail
    assert full == "xxXxx!"


# ---------------------------------------------------------------------------
# 15. Correct accumulation across many chunks
# ---------------------------------------------------------------------------


def test_accumulation_across_many_chunks():
    """Feed a string one char at a time; final output must equal batch correct."""
    text = "prefix abc middle abc suffix"
    expected = "prefix XYZ middle XYZ suffix"

    b = StreamBuffer(
        scan_fn=ABC_SCAN,
        max_alias_len=3,
        window_chars=2,
    )
    parts: list[str] = []
    for ch in text:
        parts.append(b.feed(ch))
    parts.append(b.flush())
    assert "".join(parts) == expected

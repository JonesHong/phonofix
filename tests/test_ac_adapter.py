"""Tests for pyahocorasick AC adapter (utils/ac_pyahocorasick.py).

Covers:
  - basic add + build + find_all flow
  - find_all on no-match text yields empty
  - multiple overlapping patterns
  - payload returned correctly
  - find_all before build() raises RuntimeError
  - len() correct before build
  - duplicate add overwrites payload (pyahocorasick default)
  - empty text yields empty
  - unicode CJK (Chinese, Japanese, Korean) characters
  - empty word silently ignored (len unchanged)
"""

from __future__ import annotations

import pytest

from phonofix.utils.ac_pyahocorasick import ACEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build(*patterns: tuple[str, object]) -> ACEngine:
    """Convenience: create, populate, and build an ACEngine."""
    ac = ACEngine()
    for word, payload in patterns:
        ac.add(word, payload=payload)
    ac.build()
    return ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBasicFlow:
    def test_add_build_find_all(self):
        """Basic add + build + find_all returns correct span and payload."""
        ac = _build(("北車", "taipei-station"))
        results = list(ac.find_all("這是北車附近"))
        assert len(results) == 1
        start, end, word, payload = results[0]
        assert word == "北車"
        assert payload == "taipei-station"
        assert start == 2
        assert end == 4  # exclusive

    def test_find_all_no_match_yields_empty(self):
        ac = _build(("北車", None))
        assert list(ac.find_all("完全不相關的字串")) == []

    def test_empty_text_yields_empty(self):
        ac = _build(("北車", None))
        assert list(ac.find_all("")) == []

    def test_is_built_flag(self):
        ac = ACEngine()
        assert not ac.is_built
        ac.add("foo", payload=None)
        ac.build()
        assert ac.is_built


class TestMultiplePatterns:
    def test_multiple_non_overlapping(self):
        ac = _build(("北車", "A"), ("南港", "B"))
        text = "北車南港中間"
        results = list(ac.find_all(text))
        words = {r[2] for r in results}
        assert words == {"北車", "南港"}

    def test_overlapping_patterns(self):
        """Both 'abc' and 'bc' should fire inside 'xabcy'."""
        ac = _build(("abc", 1), ("bc", 2))
        text = "xabcy"
        results = list(ac.find_all(text))
        matched_words = {r[2] for r in results}
        assert "abc" in matched_words
        assert "bc" in matched_words

    def test_pattern_at_start_and_end(self):
        ac = _build(("foo", "start"), ("bar", "end"))
        results = list(ac.find_all("fooXbar"))
        words = {r[2] for r in results}
        assert words == {"foo", "bar"}


class TestPayload:
    def test_dict_payload_returned(self):
        payload = {"canonical": "台北車站", "score": 0.9}
        ac = _build(("北車", payload))
        start, end, word, val = list(ac.find_all("去北車搭車"))[0]
        assert val == payload

    def test_none_payload_returned(self):
        ac = _build(("test", None))
        _, _, _, val = list(ac.find_all("a test b"))[0]
        assert val is None

    def test_span_indices_correct(self):
        """start + len(word) == end_exclusive."""
        ac = _build(("雷電将軍", "raiden"))
        start, end, word, _ = list(ac.find_all("稲妻の雷電将軍は"))[0]
        assert end - start == len(word)
        assert start >= 0


class TestGuards:
    def test_find_all_before_build_raises(self):
        ac = ACEngine()
        ac.add("hello", payload=None)
        with pytest.raises(RuntimeError, match="build"):
            list(ac.find_all("hello world"))

    def test_len_before_build(self):
        ac = ACEngine()
        ac.add("alpha", payload=None)
        ac.add("beta", payload=None)
        assert len(ac) == 2

    def test_len_after_build(self):
        ac = ACEngine()
        ac.add("alpha", payload=None)
        ac.build()
        assert len(ac) == 1


class TestDuplicateAndEdgeCases:
    def test_duplicate_add_overwrites_payload(self):
        """pyahocorasick overwrites on duplicate key — adapter should follow."""
        ac = ACEngine()
        ac.add("dup", payload="first")
        ac.add("dup", payload="second")
        ac.build()
        results = list(ac.find_all("dup"))
        assert len(results) == 1
        assert results[0][3] == "second"

    def test_duplicate_does_not_increment_len(self):
        ac = ACEngine()
        ac.add("dup", payload="v1")
        ac.add("dup", payload="v2")
        assert len(ac) == 1

    def test_empty_word_ignored(self):
        ac = ACEngine()
        ac.add("", payload="should-be-ignored")
        ac.build()
        assert len(ac) == 0
        assert list(ac.find_all("anything")) == []


class TestUnicode:
    def test_chinese_characters(self):
        ac = _build(("台北車站", {"id": "tpe"}))
        results = list(ac.find_all("從台北車站出發"))
        assert len(results) == 1
        assert results[0][2] == "台北車站"

    def test_japanese_hiragana_katakana(self):
        ac = _build(("エンジニア", "engineer"), ("会議", "meeting"))
        text = "エンジニアの会議"
        results = list(ac.find_all(text))
        words = {r[2] for r in results}
        assert words == {"エンジニア", "会議"}

    def test_korean_characters(self):
        ac = _build(("인공지능", "AI"))
        results = list(ac.find_all("한국의 인공지능 연구"))
        assert len(results) == 1
        assert results[0][2] == "인공지능"

    def test_mixed_cjk_and_ascii(self):
        ac = _build(("CPU", "cpu"), ("中央處理器", "cpu-zh"))
        text = "CPU即中央處理器"
        results = list(ac.find_all(text))
        words = {r[2] for r in results}
        assert words == {"CPU", "中央處理器"}

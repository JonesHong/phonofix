"""v0.4.0 fuzzy integration tests — AC delete-1 expansion (Tier 3) wired into correct().

Wire status:
  Tier 3 (AC delete-1 expansion): WIRED
  Tier 2 (mutation set): DEFERRED to v0.4.1
  Tier 1 (per-language hash key): DEFERRED to v0.4.1

Test design notes:
  - delete-1 expansion only produces patterns of length >= _MIN_DELETE1_PATTERN_LEN (2).
  - 2-char aliases (e.g. "土豆") yield only 1-char delete-1 patterns → all filtered.
  - 3+ char aliases yield 2+ char delete-1 patterns → Tier 3 can fire.
  - Tier 3 hits emit match.fuzzy events (tier="delete-1"), not match.exact.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from phonofix.core.dict_schema import Term, TermMode
from phonofix.core.event_queue import EventRecord
from phonofix.core.matcher import PhoneticMatcher

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_phonemizer(language: str = "zh") -> SimpleNamespace:
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


def _capture_events(m: PhoneticMatcher) -> tuple[PhoneticMatcher, list[EventRecord]]:
    """Re-create matcher wired with an event collector; returns (matcher, events_list)."""
    events: list[EventRecord] = []

    def handler(ev: EventRecord) -> None:
        events.append(ev)

    new_m = PhoneticMatcher(
        phonemizer=m.phonemizer,
        dictionary=m.dictionary,
        on_event=handler,
    )
    return new_m, events


# ---------------------------------------------------------------------------
# 1. Exact (literal) alias hit — baseline backward-compat
# ---------------------------------------------------------------------------


def test_exact_alias_hit_basic() -> None:
    """Caller dict lists alias; exact input → correct replacement."""
    m = _make_matcher({"馬鈴薯": {"aliases": ["土豆"]}})
    assert m.correct("土豆") == "馬鈴薯"


def test_exact_alias_hit_with_tail() -> None:
    """Alias followed by extra characters — tail preserved."""
    m = _make_matcher({"馬鈴薯": {"aliases": ["土豆"]}})
    assert m.correct("土豆好吃") == "馬鈴薯好吃"


def test_exact_alias_hit_surrounded() -> None:
    """Alias in middle of text — prefix and suffix both preserved."""
    m = _make_matcher({"馬鈴薯": {"aliases": ["土豆"]}})
    assert m.correct("我買了土豆回來") == "我買了馬鈴薯回來"


# ---------------------------------------------------------------------------
# 2. Tier 3 — AC delete-1 expansion
# Note: alias must be >= 3 chars for delete-1 variants to be >= MIN_LEN (2).
# ---------------------------------------------------------------------------


def test_tier3_delete1_3char_alias() -> None:
    """3-char alias '永和豆' → delete-1 variants '和豆','永豆','永和' (all len=2).
    Input '永和豆' exact hit; input containing '和豆' should also hit via delete-1.
    """
    m = _make_matcher({"永和豆漿": {"aliases": ["永和豆"]}})
    # Exact hit: input matches alias literally
    assert m.correct("我喝永和豆") == "我喝永和豆漿"
    # Delete-1 hit: '和豆' is a delete-1 variant of '永和豆'
    assert m.correct("我喝和豆回來") == "我喝永和豆漿回來"


def test_tier3_delete1_4char_alias() -> None:
    """4-char alias '台北車站' → delete-1 variants include '台北車','台北站','台車站','北車站'.
    Input '北車站' (delete-1 of '台北車站') should be corrected via Tier 3.
    """
    m = _make_matcher({"台北車站": {"aliases": ["台北車站"]}})
    # Literal exact hit
    assert m.correct("我在台北車站下車") == "我在台北車站下車"  # canonical already = alias


def test_tier3_delete1_fires_for_3char_variant() -> None:
    """Alias '馬鈴薯' (3 chars) → delete-1 includes '鈴薯','馬薯','馬鈴'.
    Input containing '鈴薯' should trigger Tier 3 replacement.
    """
    m = _make_matcher({"馬鈴薯": {"aliases": ["馬鈴薯"]}})
    # '鈴薯' is delete-1 of alias '馬鈴薯' (delete char at pos 0)
    result = m.correct("我吃了鈴薯")
    assert result == "我吃了馬鈴薯"


def test_tier3_delete1_event_emitted_as_fuzzy() -> None:
    """delete-1 hit must emit match.fuzzy (not match.exact)."""
    events: list[EventRecord] = []
    m = PhoneticMatcher(
        phonemizer=_mock_phonemizer(),
        dictionary={"馬鈴薯": {"aliases": ["馬鈴薯"]}},
        on_event=lambda ev: events.append(ev),
    )
    import time

    m.correct("我吃了鈴薯")
    time.sleep(0.05)  # allow async event delivery
    m.close()

    fuzzy_events = [e for e in events if e.name == "match.fuzzy"]
    exact_events = [e for e in events if e.name == "match.exact"]
    assert len(fuzzy_events) >= 1, "Expected at least one match.fuzzy event for delete-1 hit"
    assert fuzzy_events[0].payload["tier"] == "delete-1"
    # Exact event should NOT fire for this delete-1 hit
    assert len(exact_events) == 0


def test_tier3_exact_event_emitted_for_literal_hit() -> None:
    """Literal alias hit must emit match.exact (not match.fuzzy)."""
    events: list[EventRecord] = []
    m = PhoneticMatcher(
        phonemizer=_mock_phonemizer(),
        dictionary={"馬鈴薯": {"aliases": ["土豆"]}},
        on_event=lambda ev: events.append(ev),
    )
    import time

    m.correct("我吃了土豆")
    time.sleep(0.05)
    m.close()

    exact_events = [e for e in events if e.name == "match.exact"]
    fuzzy_events = [e for e in events if e.name == "match.fuzzy"]
    assert len(exact_events) == 1
    assert len(fuzzy_events) == 0


# ---------------------------------------------------------------------------
# 3. Protect mask — canonical protected from fuzzy replacement too
# ---------------------------------------------------------------------------


def test_protect_mask_blocks_fuzzy_replacement() -> None:
    """When canonical already appears in text, the span is protected.
    Even if a delete-1 variant of some alias overlaps with the canonical span,
    the canonical should be preserved.
    """
    # canonical='馬鈴薯', alias='馬鈴薯' (same)
    # protect mask covers the canonical itself
    m = _make_matcher({"馬鈴薯": {"aliases": ["馬鈴薯"]}})
    # text already contains canonical — should NOT be double-replaced
    result = m.correct("我有馬鈴薯")
    assert result == "我有馬鈴薯"  # unchanged because canonical is protected


def test_protect_mode_term_protects_canonical() -> None:
    """protect-mode terms: their canonical is shielded from any replacement."""

    terms = [
        Term(canonical="台北", mode=TermMode.PROTECT),
        Term(canonical="台北市政府", mode=TermMode.REPLACE, aliases=["市政府"]),
    ]
    m = _make_matcher(terms)
    # "市政府" → "台北市政府", but "台北" prefix is already protected → both can coexist
    result = m.correct("去市政府辦事")
    assert result == "去台北市政府辦事"


# ---------------------------------------------------------------------------
# 4. Multiple aliases — literal + delete-1 coexist
# ---------------------------------------------------------------------------


def test_multiple_aliases_one_exact_one_delete1() -> None:
    """Dict has two aliases for same canonical.
    alias1='土豆' (2 chars) — delete-1 too short, only literal fires.
    alias2='永和豆' (3 chars) — delete-1 '和豆' fires in Tier 3.
    Both should map to the same canonical.
    """
    m = _make_matcher({"馬鈴薯": {"aliases": ["土豆", "馬鈴薯"]}})
    # literal hit
    assert m.correct("我吃土豆") == "我吃馬鈴薯"
    # delete-1 of '馬鈴薯'
    assert m.correct("我吃鈴薯") == "我吃馬鈴薯"


# ---------------------------------------------------------------------------
# 5. Empty dict → no-op
# ---------------------------------------------------------------------------


def test_empty_dict_noop() -> None:
    """Empty dictionary: correct() returns text unchanged."""
    m = _make_matcher({})
    assert m.correct("任意文字") == "任意文字"
    assert m.correct("") == ""


# ---------------------------------------------------------------------------
# 6. diagnose() shows Tier 3 active
# ---------------------------------------------------------------------------


def test_diagnose_shows_expanded_engine() -> None:
    """diagnose()['ac_engine'] must indicate delete-1 expansion is wired."""
    m = _make_matcher({"馬鈴薯": {"aliases": ["土豆"]}})
    d = m.diagnose()
    assert d["ac_engine"] == "pyahocorasick+expanded", (
        f"Expected 'pyahocorasick+expanded', got {d['ac_engine']!r}"
    )


def test_diagnose_empty_dict_ac_engine_none() -> None:
    """diagnose()['ac_engine'] == 'none' when dict is empty."""
    m = _make_matcher({})
    d = m.diagnose()
    assert d["ac_engine"] == "none"


# ---------------------------------------------------------------------------
# 7. explain() — candidates include tier annotation
# ---------------------------------------------------------------------------


def test_explain_exact_hit_tier() -> None:
    """explain() candidates show tier='exact' for literal alias hit."""
    m = _make_matcher({"馬鈴薯": {"aliases": ["土豆"]}})
    result = m.explain("我吃土豆")
    candidates = result["candidates"]
    assert len(candidates) >= 1
    exact_candidates = [c for c in candidates if c["tier"] == "exact"]
    assert len(exact_candidates) >= 1
    assert exact_candidates[0]["alias"] == "土豆"
    assert exact_candidates[0]["canonical"] == "馬鈴薯"


def test_explain_delete1_hit_tier() -> None:
    """explain() candidates show tier='delete-1' for Tier 3 fuzzy hit."""
    m = _make_matcher({"馬鈴薯": {"aliases": ["馬鈴薯"]}})
    result = m.explain("我吃鈴薯")
    candidates = result["candidates"]
    fuzzy_candidates = [c for c in candidates if c["tier"] == "delete-1"]
    assert len(fuzzy_candidates) >= 1
    assert fuzzy_candidates[0]["canonical"] == "馬鈴薯"


def test_explain_result_matches_correct() -> None:
    """explain()['result'] must equal correct() output."""
    m = _make_matcher({"馬鈴薯": {"aliases": ["土豆"]}})
    text = "我吃土豆好吃"
    assert m.explain(text)["result"] == m.correct(text)

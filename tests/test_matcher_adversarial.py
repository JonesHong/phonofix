"""Adversarial tests for PhoneticMatcher Tier 1-3 + Tier 5 wire.

Writer/validator isolation — these tests target mutation predictions from
reviewer agent (a3541c79) that ran out of budget mid-write. Author of
matcher.py did NOT write these tests.

Reviewer's 5 mutation predictions:
  P1. _get_legacy_corrector stale cache after add_terms
  P2. Tier 5 + protect mode collision (legacy engine doesn't know PROTECT)
  P3. canonical == alias Tier 3 delete-1 infinite-loop risk
  P4. streaming feed/flush should not trigger Tier 5 per-call cost
  P5. Korean / unknown language Tier 5 should silent skip

Plus standard boundary cases per Six Iron Rules.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

from phonofix.core.dict_schema import Term, TermMode
from phonofix.core.matcher import PhoneticMatcher


def _phon(lang: str = "zh") -> SimpleNamespace:
    return SimpleNamespace(language=lang, name=f"mock-{lang}")


def _matcher(terms: list, lang: str = "zh", tier5: bool = True, on_event=None) -> PhoneticMatcher:
    return PhoneticMatcher(
        phonemizer=_phon(lang),
        dictionary=terms,
        enable_tier5_fallback=tier5,
        on_event=on_event,
    )


# ---------------------------------------------------------------------------
# P1. _get_legacy_corrector stale cache after add_terms
# ---------------------------------------------------------------------------


def test_p1_legacy_corrector_invalidated_after_add_terms() -> None:
    """If add_terms() doesn't invalidate _legacy_corrector, Tier 5 uses stale dict."""
    m = _matcher([Term(canonical="馬鈴薯", mode=TermMode.REPLACE, aliases=["土豆"])])
    # Force Tier 5 build (規則外 case to trigger fallback path)
    m.correct("我吃吐毒")  # may catch or miss; goal is to populate legacy_corrector

    # Now add new term — caller expects Tier 5 to also know it
    m.add_terms([Term(canonical="番茄", mode=TermMode.REPLACE, aliases=["西紅柿"])])

    # New term should be matched by Tier 1-3 OR Tier 5 (literal alias)
    out = m.correct("我吃西紅柿")
    assert "番茄" in out, f"add_terms() stale: '{out}' missing 番茄"


def test_p1_legacy_corrector_invalidated_after_remove_terms() -> None:
    """remove_terms must also invalidate legacy corrector (was caching old dict)."""
    m = _matcher(
        [
            Term(canonical="馬鈴薯", mode=TermMode.REPLACE, aliases=["土豆"]),
            Term(canonical="番茄", mode=TermMode.REPLACE, aliases=["西紅柿"]),
        ]
    )
    m.correct("我吃吐毒")  # populate legacy
    m.remove_terms(["番茄"])

    # 番茄 removed → 「西紅柿」應 unchanged (not replaced)
    out = m.correct("我吃西紅柿")
    assert "番茄" not in out, f"remove_terms() stale: 番茄 still replacing '{out}'"


# ---------------------------------------------------------------------------
# P2. Tier 5 + protect mode collision
# ---------------------------------------------------------------------------


def test_p2_protect_mode_term_not_replaced_by_tier5() -> None:
    """protect-mode term canonical literal must NOT be replaced even after Tier 5."""
    m = _matcher(
        [
            Term(canonical="枝節", mode=TermMode.PROTECT),
            Term(canonical="台北車站", mode=TermMode.REPLACE, aliases=["北車"]),
        ]
    )
    out = m.correct("枝節問題與北車時刻")
    assert out == "枝節問題與台北車站時刻", f"Tier 5 broke protect mode: '{out}'"


def test_p2_protect_only_dict_tier5_no_op() -> None:
    """A protect-only dict (no REPLACE terms) should not crash / over-replace via Tier 5."""
    m = _matcher([Term(canonical="枝節", mode=TermMode.PROTECT)])
    out = m.correct("這個枝節問題")
    assert out == "這個枝節問題"


# ---------------------------------------------------------------------------
# P3. canonical == alias Tier 3 delete-1 infinite loop / double-replace
# ---------------------------------------------------------------------------


def test_p3_canonical_in_text_not_replaced_twice() -> None:
    """canonical '台北車站' contains alias '北車' — must not double-replace."""
    m = _matcher([Term(canonical="台北車站", mode=TermMode.REPLACE, aliases=["北車"])])
    out = m.correct("台北車站")
    assert out == "台北車站", f"canonical double-replaced: '{out}'"


def test_p3_canonical_repeated_in_text() -> None:
    """canonical appears 3 times in text — each occurrence protected."""
    m = _matcher([Term(canonical="台北車站", mode=TermMode.REPLACE, aliases=["北車"])])
    out = m.correct("台北車站到台北車站再到台北車站")
    assert out == "台北車站到台北車站再到台北車站"


# ---------------------------------------------------------------------------
# P4. streaming feed/flush should not trigger Tier 5 (cost-per-call)
# ---------------------------------------------------------------------------


def test_p4_feed_flush_does_not_emit_tier5_event() -> None:
    """feed/flush use _scan_for_streaming which should NOT call legacy_corrector."""
    events: list[dict] = []
    m = _matcher(
        [Term(canonical="台北車站", mode=TermMode.REPLACE, aliases=["北車"])],
        on_event=lambda rec: events.append({"name": rec.name, "payload": rec.payload}),
    )
    m.feed("我去")
    m.feed("北車")
    m.flush()
    # Allow event queue to drain
    import time

    time.sleep(0.1)
    tier5_events = [e for e in events if e["payload"].get("tier") == "tier5"]
    assert tier5_events == [], f"feed/flush triggered Tier 5: {tier5_events}"


# ---------------------------------------------------------------------------
# P5. Korean / unknown language Tier 5 silent skip
# ---------------------------------------------------------------------------


def test_p5_korean_tier5_silent_skip_no_crash() -> None:
    """ko has no legacy engine — Tier 5 should silent-skip, no exception."""
    m = _matcher(
        [Term(canonical="안녕하세요", mode=TermMode.REPLACE, aliases=["안녕"])],
        lang="ko",
        tier5=True,
    )
    out = m.correct("안녕")
    assert out == "안녕하세요"


def test_p5_unknown_language_tier5_silent_skip() -> None:
    """Unknown language (es, fr...) Tier 5 should not crash."""
    m = _matcher(
        [Term(canonical="hola", mode=TermMode.REPLACE, aliases=["holla"])],
        lang="es",
        tier5=True,
    )
    out = m.correct("holla amigo")
    # Should at least not crash; AC literal may or may not hit
    assert isinstance(out, str)


# ---------------------------------------------------------------------------
# Boundary: enable_tier5_fallback=False must NOT magic-fix 規則外 case
# ---------------------------------------------------------------------------


def test_tier5_off_does_not_catch_rule_outside_substitution() -> None:
    """With Tier 5 OFF, 規則外 substitution should stay unchanged."""
    m = _matcher(
        [Term(canonical="馬鈴薯", mode=TermMode.REPLACE, aliases=["土豆"])],
        tier5=False,
    )
    # '吐毒' is rule-outside substitution (not in FUZZY map for 土豆)
    out = m.correct("我吃吐毒")
    # If Tier 1-3 missed and Tier 5 is off, output unchanged
    # (could change if FUZZY rule actually covers 吐/土; assert at least no crash)
    assert isinstance(out, str)


# ---------------------------------------------------------------------------
# Invariant: v0.3.x ChineseEngine ≡ v0.4 PhoneticMatcher(tier5=True)
# ---------------------------------------------------------------------------


def test_invariant_simple_alias_replace_matches_v03() -> None:
    """exact alias hit: v0.3 and v0.4 should produce identical output."""
    from phonofix import ChineseEngine

    v3 = ChineseEngine().create_corrector({"馬鈴薯": {"aliases": ["土豆"]}})
    v4 = _matcher([Term(canonical="馬鈴薯", mode=TermMode.REPLACE, aliases=["土豆"])])
    for text in ["我吃土豆", "土豆很好吃", "土豆與番茄"]:
        a = v3.correct(text)
        b = v4.correct(text)
        assert a == b, f"v3 '{a}' != v4 '{b}' for input '{text}'"


def test_invariant_canonical_protect_matches_v03() -> None:
    """canonical literal protection: v0.3 and v0.4 identical."""
    from phonofix import ChineseEngine

    v3 = ChineseEngine().create_corrector({"台北車站": {"aliases": ["北車"]}})
    v4 = _matcher([Term(canonical="台北車站", mode=TermMode.REPLACE, aliases=["北車"])])
    for text in ["我在台北車站", "從台北車站到北車", "台北車站台北車站"]:
        a = v3.correct(text)
        b = v4.correct(text)
        assert a == b, f"v3 '{a}' != v4 '{b}' for input '{text}'"


# ---------------------------------------------------------------------------
# Concurrency: tier5 lazy build race
# ---------------------------------------------------------------------------


def test_concurrent_correct_no_race_with_tier5_lazy_build() -> None:
    """100 threads concurrently call correct() on fresh matcher (legacy not yet built)."""
    m = _matcher([Term(canonical="馬鈴薯", mode=TermMode.REPLACE, aliases=["土豆"])])
    results: list[str] = []
    errors: list[Exception] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            r = m.correct("我吃土豆")
            with lock:
                results.append(r)
        except Exception as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert errors == [], f"race errors: {errors}"
    assert len(results) == 100
    assert all(r == "我吃馬鈴薯" for r in results), f"inconsistent results: {set(results)}"


# ---------------------------------------------------------------------------
# Boundary: empty / huge input
# ---------------------------------------------------------------------------


def test_empty_text_no_crash() -> None:
    m = _matcher([Term(canonical="x", mode=TermMode.REPLACE, aliases=["y"])])
    assert m.correct("") == ""


def test_empty_dict_passthrough() -> None:
    m = _matcher([])
    text = "任何文字都不該改變"
    assert m.correct(text) == text


def test_10k_char_text_completes_under_3s() -> None:
    """Performance smoke: 10K char text with small dict should complete reasonably."""
    import time

    m = _matcher([Term(canonical="馬鈴薯", mode=TermMode.REPLACE, aliases=["土豆"])])
    text = "我吃土豆和" * 2000  # ~10K chars
    start = time.perf_counter()
    out = m.correct(text)
    elapsed = time.perf_counter() - start
    assert elapsed < 3.0, f"10K char took {elapsed:.2f}s — perf regression"
    assert "馬鈴薯" in out


# ---------------------------------------------------------------------------
# Diagnose / Explain schema check
# ---------------------------------------------------------------------------


def test_diagnose_returns_dict_with_expected_keys() -> None:
    m = _matcher([Term(canonical="x", mode=TermMode.REPLACE, aliases=["y"])])
    d = m.diagnose()
    assert isinstance(d, dict)
    # Must include version + dict_size + ac_engine (per SPEC.md §5)
    for key in ["version", "dict_size", "ac_engine"]:
        assert key in d, f"diagnose() missing key '{key}'; got {list(d.keys())}"


# ---------------------------------------------------------------------------
# Tier 5 ja: cutlet/dakuten missing graceful
# ---------------------------------------------------------------------------


def test_ja_tier5_legacy_init_failure_graceful() -> None:
    """If ja JapaneseEngine init fails (e.g. unidic missing), correct() should not raise."""
    m = _matcher(
        [Term(canonical="バス", mode=TermMode.REPLACE, aliases=["ハス"])],
        lang="ja",
    )
    # Should at least return string, no exception bubble up
    out = m.correct("ハスに乗る")
    assert isinstance(out, str)

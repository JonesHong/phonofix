"""
外部依賴穩定性測試

目標：
- 外部依賴/模糊比對流程發生例外時，exact-match（Aho-Corasick surface alias）仍可工作
- 避免「模糊流程失敗 -> 整個修正失敗」的脆弱連鎖
"""

import pytest


def test_english_exact_match_survives_fuzzy_failure(monkeypatch):
    from phonofix import EnglishEngine

    engine = EnglishEngine()
    corrector = engine.create_corrector({"Python": ["Pyton"]})

    def boom(*_args, **_kwargs):
        raise RuntimeError("fuzzy failed")

    monkeypatch.setattr(corrector, "_generate_fuzzy_candidate_drafts", boom)
    assert corrector.correct("I use Pyton for ML") == "I use Python for ML"


def test_chinese_exact_match_survives_fuzzy_failure(monkeypatch):
    from phonofix import ChineseEngine

    engine = ChineseEngine()
    corrector = engine.create_corrector({"台北車站": {"aliases": ["北車"]}})

    def boom(*_args, **_kwargs):
        raise RuntimeError("fuzzy failed")

    monkeypatch.setattr(corrector, "_generate_fuzzy_candidate_drafts", boom)
    assert corrector.correct("我在北車等你") == "我在台北車站等你"


def test_japanese_exact_match_survives_fuzzy_failure(monkeypatch):
    from phonofix import JapaneseEngine

    engine = JapaneseEngine()
    corrector = engine.create_corrector({"アスピリン": ["asupirin"]})

    def boom(*_args, **_kwargs):
        raise RuntimeError("fuzzy failed")

    monkeypatch.setattr(corrector, "_generate_fuzzy_candidate_drafts", boom)
    assert corrector.correct("頭が痛いのでasupirinを飲みました") == "頭が痛いのでアスピリンを飲みました"


def test_silent_mode_keeps_events_even_on_fuzzy_failure(monkeypatch):
    from phonofix import EnglishEngine

    events = []

    def on_event(e):
        events.append(e)

    engine = EnglishEngine()
    corrector = engine.create_corrector({"Python": ["Pyton"]}, on_event=on_event)

    def boom(*_args, **_kwargs):
        raise RuntimeError("fuzzy failed")

    monkeypatch.setattr(corrector, "_generate_fuzzy_candidate_drafts", boom)
    assert corrector.correct("I use Pyton for ML", silent=True) == "I use Python for ML"
    # silent 只代表不輸出 log，不代表不可觀測；事件回呼仍應收到 fuzzy_error / degraded / replacement 等事件
    assert any(ev.get("type") in {"fuzzy_error", "degraded", "replacement"} for ev in events)


def test_fail_policy_raise_raises_and_emits_fuzzy_error(monkeypatch):
    from phonofix import EnglishEngine

    events = []

    def on_event(e):
        events.append(e)

    engine = EnglishEngine()
    corrector = engine.create_corrector({"Python": ["Pyton"]}, on_event=on_event)

    def boom(*_args, **_kwargs):
        raise RuntimeError("fuzzy failed")

    monkeypatch.setattr(corrector, "_generate_fuzzy_candidate_drafts", boom)

    with pytest.raises(RuntimeError):
        corrector.correct("I use Pyton for ML", fail_policy="raise")

    assert any(ev.get("type") == "fuzzy_error" for ev in events)
    assert not any(ev.get("type") == "degraded" for ev in events)


def test_fail_policy_degrade_emits_fuzzy_error_and_degraded(monkeypatch):
    from phonofix import EnglishEngine

    events = []

    def on_event(e):
        events.append(e)

    engine = EnglishEngine()
    corrector = engine.create_corrector({"Python": ["Pyton"]}, on_event=on_event)

    def boom(*_args, **_kwargs):
        raise RuntimeError("fuzzy failed")

    monkeypatch.setattr(corrector, "_generate_fuzzy_candidate_drafts", boom)

    assert corrector.correct("I use Pyton for ML", fail_policy="degrade") == "I use Python for ML"
    assert any(ev.get("type") == "fuzzy_error" and ev.get("fallback") == "exact_only" for ev in events)
    assert any(ev.get("type") == "degraded" and ev.get("fallback") == "exact_only" for ev in events)

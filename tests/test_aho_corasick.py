from __future__ import annotations

import pytest

from phonofix.utils.aho_corasick import AhoCorasick


def test_aho_corasick_basic_overlaps():
    ac: AhoCorasick[str] = AhoCorasick()
    ac.add("he", "he")
    ac.add("she", "she")
    ac.add("his", "his")
    ac.add("hers", "hers")
    ac.build()

    text = "ushers"
    matches = sorted(list(ac.iter_matches(text)))

    assert (1, 4, "she", "she") in matches
    assert (2, 4, "he", "he") in matches
    assert (2, 6, "hers", "hers") in matches


def test_aho_corasick_disallow_add_after_build():
    ac: AhoCorasick[str] = AhoCorasick()
    ac.add("a", "a")
    ac.build()
    with pytest.raises(RuntimeError):
        ac.add("b", "b")


"""
防回歸：當 alias 是 canonical 的子字串時，canonical 字面必須被保留。

Bug context（2026-05-25）：
- build_exact_matcher 只納入 aliases，不納入 canonical
- AC 在 input 中含 canonical 字面（如「台北車站」）時，內部 alias（如「北車」）會被 match
- 結果：「台北車站」被切成「台[北車]站」→ 替換 → 「台台北車站站」

修法：corrector 初始化時自動把 canonical 加入 protected_terms，
重用既有 protection mask 機制阻擋 alias-on-canonical-substring 替換。
"""

from __future__ import annotations

from phonofix import ChineseEngine, JapaneseEngine

# =============================================================================
# Chinese
# =============================================================================


class TestChineseCanonicalSubstringPreservation:
    """中文：alias 是 canonical 子字串時 canonical 字面保護"""

    def test_canonical_literal_not_destroyed_when_alias_is_substring(self):
        """canonical 字面 (台北車站) 不應被內部 alias (北車) 二次替換"""
        engine = ChineseEngine(verbose=False)
        corrector = engine.create_corrector({"台北車站": ["北車", "胎北車站"]})
        # canonical 字面直接出現 — 不該被改
        assert corrector.correct("這是台北車站的時刻表") == "這是台北車站的時刻表"

    def test_alias_substring_still_replaceable(self):
        """alias (北車) 在普通 context 仍應被正常替換為 canonical"""
        engine = ChineseEngine(verbose=False)
        corrector = engine.create_corrector({"台北車站": ["北車", "胎北車站"]})
        assert corrector.correct("我在北車等你") == "我在台北車站等你"

    def test_mixed_canonical_and_alias_in_same_text(self):
        """同一段含 canonical + alias，canonical 保留 + alias 被替換"""
        engine = ChineseEngine(verbose=False)
        corrector = engine.create_corrector({"台北車站": ["北車", "胎北車站"]})
        result = corrector.correct("北車跟台北車站是同一個地方")
        assert result == "台北車站跟台北車站是同一個地方"

    def test_phonetic_alias_with_canonical_substring_pattern(self):
        """ASR 同音錯字 (胎北車站) 仍應替換 + canonical 字面保留"""
        engine = ChineseEngine(verbose=False)
        corrector = engine.create_corrector({"台北車站": ["北車", "胎北車站"]})
        assert corrector.correct("胎北車站附近的店") == "台北車站附近的店"


# =============================================================================
# Japanese
# =============================================================================


class TestJapaneseCanonicalSubstringPreservation:
    """日文：alias 是 canonical 子字串時 canonical 字面保護"""

    def test_canonical_literal_not_destroyed_when_alias_is_substring(self):
        """canonical 字面 (雷電将軍) 不應被內部 alias (将軍) 二次替換"""
        engine = JapaneseEngine(enable_surface_variants=False, verbose=False)
        corrector = engine.create_corrector({"雷電将軍": ["将軍", "雷霆将軍"]})
        assert corrector.correct("雷電将軍が現れた") == "雷電将軍が現れた"

    def test_alias_substring_still_replaceable(self):
        """alias (将軍) 在普通 context 仍應被正常替換為 canonical"""
        engine = JapaneseEngine(enable_surface_variants=False, verbose=False)
        corrector = engine.create_corrector({"雷電将軍": ["将軍", "雷霆将軍"]})
        assert corrector.correct("将軍が現れた") == "雷電将軍が現れた"

    def test_mixed_canonical_and_alias_in_same_text(self):
        """日文同一段含 canonical + alias，canonical 保留 + alias 被替換"""
        engine = JapaneseEngine(enable_surface_variants=False, verbose=False)
        corrector = engine.create_corrector({"雷電将軍": ["将軍", "雷霆将軍"]})
        result = corrector.correct("将軍と雷電将軍は同じだ")
        assert result == "雷電将軍と雷電将軍は同じだ"

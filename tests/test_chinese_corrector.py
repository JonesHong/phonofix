"""
中文替換器測試
"""
import pytest

from phonofix import ChineseEngine


class TestChineseCorrector:
    """中文替換器基本功能測試"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """設置 Engine (所有測試共享)"""
        self.engine = ChineseEngine()

    def test_basic_substitution(self):
        """測試基本替換功能"""
        corrector = self.engine.create_corrector({
            "台北車站": {"aliases": ["北車"]},
            "牛奶": {}
        })

        result = corrector.correct("我在北車買了流奶")
        assert "台北車站" in result
        assert "牛奶" in result

    def test_fuzzy_matching_nl(self):
        """測試 n/l 模糊音匹配"""
        corrector = self.engine.create_corrector(["牛奶"])

        result = corrector.correct("我買了流奶")
        assert result == "我買了牛奶"

    def test_fuzzy_matching_fh(self):
        """測試 f/h 模糊音匹配"""
        corrector = self.engine.create_corrector(["發揮"])

        result = corrector.correct("他花揮了才能")
        assert result == "他發揮了才能"

    def test_abbreviation_expansion(self):
        """測試縮寫擴展"""
        corrector = self.engine.create_corrector({
            "台北車站": {"aliases": ["北車"], "weight": 0.0}
        })

        result = corrector.correct("我在北車等你")
        assert result == "我在台北車站等你"

    def test_context_keywords(self):
        """測試上下文關鍵字"""
        corrector = self.engine.create_corrector({
            "永和豆漿": {
                "aliases": ["永豆"],
                "keywords": ["吃", "喝", "買"],
                "weight": 0.3
            }
        })

        result = corrector.correct("我去買永豆")
        assert "永和豆漿" in result

    def test_protected_terms(self):
        """測試保護詞彙清單"""
        corrector = self.engine.create_corrector(
            ["台北車站"],
            protected_terms=["北側"]
        )

        result = corrector.correct("我在北側等你")
        assert "北側" in result  # 應保留，不被替換

    def test_protected_terms_overlap_span_skips_replacement(self):
        """protected_terms 只要與候選片段重疊，就必須跳過（中文）"""
        corrector = self.engine.create_corrector(
            {"台北車站": {"aliases": ["北車"]}},
            protected_terms=["北"],
        )

        assert corrector.correct("我在北車等你") == "我在北車等你"

    def test_empty_input(self):
        """測試空輸入"""
        corrector = self.engine.create_corrector(["測試"])

        result = corrector.correct("")
        assert result == ""

    def test_no_match(self):
        """測試無匹配情況"""
        corrector = self.engine.create_corrector(["台北車站"])

        result = corrector.correct("今天天氣很好")
        assert result == "今天天氣很好"

    def test_on_event_handler(self):
        """測試事件回呼（on_event）"""
        events = []

        def on_event(e):
            events.append(e)

        corrector = self.engine.create_corrector(
            {"台北車站": {"aliases": ["北車"]}},
            on_event=on_event,
        )

        result = corrector.correct("我在北車等你")
        assert result == "我在台北車站等你"
        assert any(ev.get("type") == "replacement" and ev.get("replacement") == "台北車站" for ev in events)

    def test_silent_disables_event(self):
        """測試 silent=True 不應輸出 log，但事件回呼仍可用（可觀測性）"""
        events = []

        def on_event(e):
            events.append(e)

        corrector = self.engine.create_corrector(
            {"台北車站": {"aliases": ["北車"]}},
            on_event=on_event,
        )

        result = corrector.correct("我在北車等你", silent=True)
        assert result == "我在台北車站等你"
        assert any(ev.get("type") == "replacement" and ev.get("replacement") == "台北車站" for ev in events)

    def test_on_event_exception_does_not_break(self):
        """測試 on_event 內部拋錯不應影響替換結果"""
        def on_event(_e):
            raise RuntimeError("boom")

        corrector = self.engine.create_corrector(
            {"台北車站": {"aliases": ["北車"]}},
            on_event=on_event,
        )

        assert corrector.correct("我在北車等你") == "我在台北車站等你"

    def test_keywords_and_exclude_when(self):
        """測試 keywords/exclude_when 過濾規則（exclude_when 優先）"""
        corrector = self.engine.create_corrector({
            "永和豆漿": {
                "aliases": ["永豆"],
                "keywords": ["買"],
                "exclude_when": ["不要"],
            }
        })

        assert corrector.correct("我去買永豆") == "我去買永和豆漿"
        assert corrector.correct("我不要買永豆") == "我不要買永豆"
        assert corrector.correct("我去找永豆") == "我去找永豆"

    def test_fuzzy_bucket_no_duplicate_for_empty_initial_group(self):
        """首聲母為空（母音起頭）時，分桶不應重複追加同一個 item"""
        engine = ChineseEngine(enable_surface_variants=False)
        corrector = engine.create_corrector(["安安"])

        bucket = corrector._fuzzy_buckets.get(2, {}).get("", [])
        assert bucket
        assert len(bucket) == len({id(x) for x in bucket})

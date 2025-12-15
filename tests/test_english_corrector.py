"""
英文替換器測試
"""
import pytest

from phonofix import EnglishEngine


class TestEnglishCorrector:
    """英文替換器基本功能測試"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """設置 Engine (所有測試共享，Backend 單例模式)"""
        self.engine = EnglishEngine()

    def test_basic_substitution(self):
        """測試基本替換功能"""
        corrector = self.engine.create_corrector(["Python", "TensorFlow"])

        result = corrector.correct("I use Pyton and Ten so floor")
        assert "Python" in result
        assert "TensorFlow" in result

    def test_split_word_matching(self):
        """測試分詞匹配 (ASR 常見錯誤)"""
        corrector = self.engine.create_corrector(["JavaScript"])

        result = corrector.correct("I love java script")
        assert result == "I love JavaScript"

    def test_acronym_matching(self):
        """測試縮寫匹配"""
        corrector = self.engine.create_corrector(["AWS", "GCP"])

        result = corrector.correct("I use A W S and G C P")
        assert "AWS" in result
        assert "GCP" in result

    def test_framework_names(self):
        """測試框架名稱"""
        terms = ["PyTorch", "NumPy", "Pandas", "Django"]
        corrector = self.engine.create_corrector(terms)

        assert "PyTorch" in corrector.correct("Pie torch is great")
        assert "NumPy" in corrector.correct("I use Num pie")
        assert "Pandas" in corrector.correct("Pan das for data")
        assert "Django" in corrector.correct("Jango web framework")

    def test_dotted_names(self):
        """測試帶點的名稱 (如 Vue.js)"""
        corrector = self.engine.create_corrector(["Vue.js", "Node.js"])

        result = corrector.correct("I use View JS and No JS")
        assert "Vue.js" in result
        assert "Node.js" in result

    def test_symbolic_terms_keep_trailing_characters(self):
        """含符號的 canonical 不應被重複附加符號"""
        corrector = self.engine.create_corrector({"C++": []})

        assert corrector.correct("I like C++") == "I like C++"

    def test_case_insensitive(self):
        """測試大小寫不敏感"""
        corrector = self.engine.create_corrector(["Python"])

        result = corrector.correct("pyton is great")
        assert "Python" in result

    def test_empty_input(self):
        """測試空輸入"""
        corrector = self.engine.create_corrector(["Python"])

        result = corrector.correct("")
        assert result == ""

    def test_no_match(self):
        """測試無匹配情況"""
        corrector = self.engine.create_corrector(["Python"])

        result = corrector.correct("The weather is nice today")
        assert result == "The weather is nice today"

    def test_protected_terms(self):
        """測試保護詞彙清單（英文也應生效）"""
        corrector = self.engine.create_corrector(
            {"Python": ["Pyton"]},
            protected_terms=["Pyton"],
        )

        result = corrector.correct("I use Pyton for ML")
        assert result == "I use Pyton for ML"

    def test_protected_terms_overlap_span_skips_replacement(self):
        """protected_terms 只要與候選片段重疊，就必須跳過（不要求完全相等）"""
        corrector = self.engine.create_corrector(
            {"Python": ["Pyton"]},
            protected_terms=["use Py"],
        )

        assert corrector.correct("I use Pyton for ML") == "I use Pyton for ML"

    def test_on_event_handler(self):
        """測試事件回呼（on_event）"""
        events = []

        def on_event(e):
            events.append(e)

        corrector = self.engine.create_corrector(
            {"Python": ["Pyton"]},
            on_event=on_event,
        )

        result = corrector.correct("I use Pyton for ML")
        assert result == "I use Python for ML"
        assert any(ev.get("type") == "replacement" and ev.get("replacement") == "Python" for ev in events)

    def test_trace_id_propagates_to_replacement_event(self):
        """同一次 correct() 的 replacement 事件應帶 trace_id，方便關聯同一筆處理"""
        events = []

        def on_event(e):
            events.append(e)

        corrector = self.engine.create_corrector({"Python": ["Pyton"]}, on_event=on_event)
        out = corrector.correct("I use Pyton for ML", trace_id="t-123", silent=True)
        assert out == "I use Python for ML"
        assert any(ev.get("type") == "replacement" and ev.get("trace_id") == "t-123" for ev in events)

    def test_silent_disables_event(self):
        """測試 silent=True 不應輸出 log，但事件回呼仍可用（可觀測性）"""
        events = []

        def on_event(e):
            events.append(e)

        corrector = self.engine.create_corrector(
            {"Python": ["Pyton"]},
            on_event=on_event,
        )

        result = corrector.correct("I use Pyton for ML", silent=True)
        assert result == "I use Python for ML"
        assert any(ev.get("type") == "replacement" and ev.get("replacement") == "Python" for ev in events)

    def test_on_event_exception_does_not_break(self):
        """測試 on_event 內部拋錯不應影響替換結果"""
        def on_event(_e):
            raise RuntimeError("boom")

        corrector = self.engine.create_corrector(
            {"Python": ["Pyton"]},
            on_event=on_event,
        )

        assert corrector.correct("I use Pyton for ML") == "I use Python for ML"

    def test_keywords_and_exclude_when(self):
        """測試 keywords/exclude_when 過濾規則"""
        corrector = self.engine.create_corrector({
            "EKG": {
                "aliases": ["1kg"],
                "keywords": ["device"],
                "exclude_when": ["weight"],
            }
        })

        assert corrector.correct("this device 1kg") == "this device EKG"
        assert corrector.correct("this device 1kg weight") == "this device 1kg weight"
        assert corrector.correct("this 1kg") == "this 1kg"

    def test_conflict_resolution_prefers_best_score(self):
        """測試重疊候選時依 score 選最佳（避免同區間重複替換）"""
        corrector = self.engine.create_corrector({
            "JavaScript": {"aliases": ["java script"], "weight": 0.5},
            "Script": {"aliases": ["script"], "weight": 0.0},
        })

        assert corrector.correct("I love java script") == "I love JavaScript"

    def test_short_alias_requires_token_boundaries(self):
        """短詞只允許在 token 邊界命中，避免子字串誤修正"""
        corrector = self.engine.create_corrector({"Go": ["go"]})

        assert corrector.correct("gopher uses go") == "gopher uses Go"


class TestEnglishEngineBackend:
    """英文 Engine 和 Backend 功能測試"""

    def test_engine_creation(self):
        """測試 Engine 建立"""
        engine = EnglishEngine()
        assert engine is not None

    def test_corrector_creation(self):
        """測試通過 Engine 建立 Corrector"""
        engine = EnglishEngine()
        corrector = engine.create_corrector(["Python"])
        assert corrector is not None

    def test_backend_singleton(self):
        """測試 Backend 單例模式"""
        engine1 = EnglishEngine()
        engine2 = EnglishEngine()
        # 兩個 Engine 應該共享同一個 Backend
        assert engine1._backend is engine2._backend

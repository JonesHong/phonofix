"""
效能/退化守門測試（非時間基準）

原則：
- 不用 wall-clock 閾值，避免 CI/環境波動造成 flaky
- 以「關鍵呼叫次數上限」與「分桶 pruning 行為」做回歸保護
"""

from __future__ import annotations


class DummyEnglishBackend:
    """
    測試用英文 backend：
    - 避免依賴 espeak/phonemizer 的可用性與輸出波動
    - 讓 IPA 首音素可控，便於測試首音素分桶 pruning
    """

    def __init__(self):
        self._initialized = True
        self._stats = {"hits": 0, "misses": 0, "currsize": 0, "maxsize": 999999}

    def initialize(self) -> None:
        self._initialized = True

    def is_initialized(self) -> bool:
        return self._initialized

    def clear_cache(self) -> None:
        self._stats = {"hits": 0, "misses": 0, "currsize": 0, "maxsize": 999999}

    def get_cache_stats(self):
        return dict(self._stats)

    @staticmethod
    def _ipa_for(text: str) -> str:
        # 以第一個字母決定首音素群組；長度固定，避免長度差 pruning 影響測試。
        first = (text or "p")[0].lower()
        if first in {"p", "b", "t", "d", "k", "g", "f", "v", "s", "z", "m", "n", "l", "r", "w", "i", "u", "a"}:
            return first + "aaaa"
        return "paaaa"

    def to_phonetic(self, text: str) -> str:
        self._stats["misses"] += 1
        return self._ipa_for(text)

    def to_phonetic_batch(self, texts: list):
        self._stats["misses"] += max(0, len(texts))
        return {t: self._ipa_for(t) for t in texts}


def test_english_group_pruning_limits_similarity_calls(monkeypatch):
    """
    英文 fuzzy 比對應只對「同首音素群組」的 item 呼叫 similarity。

    這個測試用大量不同首音素群組的詞做壓力：
    - 若 regression 退化成「每個 window 對所有 item 計算 similarity」，呼叫數會暴增。
    """
    monkeypatch.setattr(
        "phonofix.languages.english.engine.get_english_backend",
        lambda: DummyEnglishBackend(),
    )

    from phonofix import EnglishEngine

    engine = EnglishEngine(enable_surface_variants=False)

    # 30 個 'p' 群組 + 200 個其他群組（用來放大回歸差距）
    terms = [f"p{i}" for i in range(30)]
    terms += [f"t{i}" for i in range(50)]
    terms += [f"k{i}" for i in range(50)]
    terms += [f"s{i}" for i in range(50)]
    terms += [f"m{i}" for i in range(50)]

    corrector = engine.create_corrector(terms)

    calls = {"n": 0}

    def _counting_similarity(a, b):
        calls["n"] += 1
        # 這裡刻意讓它永遠不 match，避免產生大量候選影響其他邏輯
        return 1.0, False

    monkeypatch.setattr(corrector.phonetic, "calculate_similarity_score", _counting_similarity)

    assert corrector.correct("p0") == "p0"

    # 若分桶有效，理論上只需要對 'p' 群組的 30 個項目計算。
    # 這裡用寬鬆上限避免內部索引微調造成脆弱。
    assert calls["n"] <= 40


def test_chinese_initials_bucket_prunes_items(monkeypatch):
    """
    中文 fuzzy 產生候選時應使用「首聲母群組」分桶，避免把所有 item 都拿來算相似度。
    """
    from phonofix import ChineseEngine

    engine = ChineseEngine()
    corrector = engine.create_corrector(["牛奶"])

    # 關注點：_generate_fuzzy_candidate_drafts 只應迭代相符 group 的 items。
    # 將 buckets 人工放大：n_l_group 只有 2 個，其他群組有大量假資料。
    corrector._exact_matcher = None
    corrector._exact_items_by_alias = {}

    buckets = {
        2: {
            "n_l_group": [{"id": "keep1"}, {"id": "keep2"}],
            "c_group": [{"id": f"noise{i}"} for i in range(300)],
        }
    }
    corrector._fuzzy_buckets = buckets

    calls = {"n": 0}

    def _counting_process(*args, **kwargs):
        calls["n"] += 1
        return None

    monkeypatch.setattr(corrector, "_process_fuzzy_match_draft", _counting_process)

    assert corrector.correct("流奶") == "流奶"
    assert calls["n"] == 2

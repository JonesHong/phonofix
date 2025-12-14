"""
併發安全性測試（Thread Safety）

範圍：
- Backend 單例取得/初始化在多執行緒下不應產生多個實例或拋例外
- 同一個 corrector 實例在多執行緒下可同時呼叫 correct()（至少不 crash、結果一致）
"""

from concurrent.futures import ThreadPoolExecutor


def test_backend_singletons_are_threadsafe():
    from phonofix.backend import get_chinese_backend, get_english_backend

    def _get_ids(_):
        return id(get_english_backend()), id(get_chinese_backend())

    with ThreadPoolExecutor(max_workers=16) as ex:
        ids = list(ex.map(_get_ids, range(100)))

    english_ids = {e for e, _c in ids}
    chinese_ids = {c for _e, c in ids}
    assert len(english_ids) == 1
    assert len(chinese_ids) == 1


def test_backend_initialize_is_threadsafe():
    from phonofix.backend import get_chinese_backend, get_english_backend

    english = get_english_backend()
    chinese = get_chinese_backend()

    with ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(lambda _: english.initialize(), range(20)))
        list(ex.map(lambda _: chinese.initialize(), range(20)))

    assert english.is_initialized()
    assert chinese.is_initialized()


def test_english_corrector_correct_is_threadsafe():
    from phonofix import EnglishEngine

    engine = EnglishEngine()
    corrector = engine.create_corrector({"Python": ["Pyton"]})

    def _work(_):
        return corrector.correct("I use Pyton for ML", silent=True)

    with ThreadPoolExecutor(max_workers=12) as ex:
        results = list(ex.map(_work, range(60)))

    assert all(r == "I use Python for ML" for r in results)


def test_chinese_corrector_correct_is_threadsafe():
    from phonofix import ChineseEngine

    engine = ChineseEngine()
    corrector = engine.create_corrector({"台北車站": {"aliases": ["北車"]}})

    def _work(_):
        return corrector.correct("我在北車等你", silent=True)

    with ThreadPoolExecutor(max_workers=12) as ex:
        results = list(ex.map(_work, range(60)))

    assert all(r == "我在台北車站等你" for r in results)


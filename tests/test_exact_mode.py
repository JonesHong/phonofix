"""mode="exact" — 只跑 exact 候選，關掉 fuzzy 音近比對。

TTS 前處理的字典是手工列的、輸入是作者自己寫的，沒有拼錯的變體要收斂，
所以任何 fuzzy 命中都是誤改。下面的字串全部來自實際踩到的案例（2026-08-20，
繁體中文旁白 + 五層架構那批術語），不是造出來的邊界條件。
"""


def _en_corrector():
    from phonofix import EnglishEngine

    return EnglishEngine(enable_surface_variants=False).create_corrector({"ram": ["RAM"]})


def _zh_corrector():
    from phonofix import ChineseEngine

    return ChineseEngine(enable_surface_variants=False).create_corrector({"漲到": ["長到"]})


def test_exact_mode_still_applies_the_intended_replacement():
    """關掉 fuzzy 不能把該做的替換一起關掉。"""
    assert _en_corrector().correct("RAM 跟 CPU 線性吃滿", mode="exact") == "ram 跟 CPU 線性吃滿"
    assert (
        _zh_corrector().correct("MCP server 長到二十三個以後", mode="exact")
        == "MCP server 漲到二十三個以後"
    )


def test_exact_mode_leaves_token_boundaries_alone():
    """字典只有 RAM，PROGRAM 不該被碰 —— 預設模式本來就對，這裡確認沒退化。"""
    c = _en_corrector()
    for mode in (None, "exact"):
        assert c.correct("PROGRAM 跑起來之後 RAM 就吃滿了", mode=mode) == (
            "PROGRAM 跑起來之後 ram 就吃滿了"
        )


def test_exact_mode_stops_english_fuzzy_over_fire():
    """字典只有 RAM，「CLI、MCP」被 fuzzy 吃成「CLramCP」。"""
    c = _en_corrector()
    text = "由下往上是 Service、SDK、CLI、MCP、Skill。"
    assert "CLramCP" in c.correct(text), "前提變了：預設模式已不再 over-fire"
    assert c.correct(text, mode="exact") == text


def test_exact_mode_stops_chinese_fuzzy_over_fire():
    """字典只有「長到」，但「帳單」「沾到」音近，預設模式會一起改掉。"""
    c = _zh_corrector()
    for text in ("那就是你每輪的固定帳單", "三個都沾到，才值得做成永久 tool"):
        assert c.correct(text) != text, "前提變了：預設模式已不再 over-fire"
        assert c.correct(text, mode="exact") == text

"""
變體上限/去重/裁剪護欄

目的：避免 enable_surface_variants 啟用後，aliases 爆炸或 max_variants 失效。
"""


def test_chinese_engine_respects_max_variants_for_aliases():
    from phonofix import ChineseEngine

    engine = ChineseEngine(enable_surface_variants=False)
    corrector = engine.create_corrector(
        {
            "台北車站": {
                "aliases": ["北車", "台北站", "北車站"],
                "max_variants": 1,
            }
        }
    )

    alias_items = [
        it for it in corrector.search_index
        if it.get("canonical") == "台北車站" and it.get("is_alias") is True
    ]
    assert len(alias_items) == 1


"""
日文語音辨識校正範例

本檔案展示 JapaneseEngine 的所有核心功能：
1. 基礎用法 - Engine.create_corrector() 工廠方法
2. 模糊詞典生成 - surface variants + representative variants
3. 發音變體 - 長音、促音、助詞錯誤
4. 上下文關鍵字 - 根據前後文判斷替換 (同音異義詞)
5. 上下文排除 - 避免錯誤修正
6. 權重系統 - 控制替換優先級
7. 同音過濾 - 以 Romaji phonetic key 去重，避免詞典膨脹
8. 混合格式配置 - list/dict 混用
9. 長文章校正 - 完整段落測試

注意：自語言模組重構後，surface variants 預設關閉。
如需「自動生成別名（羅馬拼音規則/可選假名層級代表變體）」請建立 Engine 時開啟：
- enable_surface_variants=True
- enable_representative_variants=True  (較 aggressive，會生成更多候選)
"""

from _example_utils import add_repo_to_sys_path, print_case

add_repo_to_sys_path()

from phonofix import JapaneseEngine

# 全域 Engine (單例模式，避免重複初始化)
engine = JapaneseEngine(verbose=False)

# =============================================================================
# 範例 1: 基礎用法 - 自動生成 Romaji 索引
# =============================================================================
def example_1_basic_usage():
    """
    最簡單的用法：只提供正確詞彙，系統自動生成 Romaji 索引。
    """
    print("=" * 60)
    print("範例 1: 基礎用法 (Basic Usage)")
    print("=" * 60)

    # 只需提供正確的詞彙
    corrector = engine.create_corrector([
        "会議",         # kaigi
        "プロジェクト", # purojekuto
        "エンジニア",   # enjinia
        "胃カメラ",     # ikamera
    ])

    test_cases = [
        ("明日のkaigiに参加します", "羅馬拼音→漢字 (kaigi→会議)"),
        ("新しいpurojekutoが始まります", "羅馬拼音→片假名 (purojekuto→プロジェクト)"),
        ("彼は優秀なenjiniaです", "羅馬拼音→片假名 (enjinia→エンジニア)"),
        ("ikameraの検査", "羅馬拼音→漢字/片假名 (ikamera→胃カメラ)"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Basic", text, result, explanation)


# =============================================================================
# 範例 2: 手動別名 (Manual Aliases)
# =============================================================================
def example_2_manual_aliases():
    """
    手動提供別名，處理特殊拼寫或簡稱。
    """
    print("=" * 60)
    print("範例 2: 手動別名 (Manual Aliases)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "スマートフォン": ["sumaho", "smapho"],  # 簡稱: スマホ
            "パーソナルコンピュータ": ["pasokon"],  # 簡稱: パソコン
            "アスピリン": ["asupirin", "asupirinn"],  # 常見拼寫錯誤
        }
    )

    test_cases = [
        ("新しいsumahoを買いました", "簡稱/縮寫 (sumaho→スマートフォン)"),
        ("pasokonが壊れました", "簡稱/縮寫 (pasokon→パーソナルコンピュータ)"),
        ("頭痛にasupirinn", "常見拼寫錯誤 (asupirinn→アスピリン)"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Manual Aliases", text, result, explanation)


# =============================================================================
# 範例 3: 發音變體 (Phonetic Variants)
# =============================================================================
def example_3_phonetic_variants():
    """
    處理長音、促音遺漏或助詞錯誤。
    """
    print("=" * 60)
    print("範例 3: 發音變體 (Phonetic Variants)")
    print("=" * 60)

    term_list = ["通り", "切手", "こんにちは"]
    corrector = engine.create_corrector(term_list)

    test_cases = [
        ("このtoriは賑やかです", "長音遺漏 (tori→通り)"),
        ("kiteを集めています", "促音遺漏 (kite→切手)"),
        ("先生、konnichiwa", "助詞錯誤 (konnichiwa→こんにちは)"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Variants", text, result, explanation)


# =============================================================================
# 範例 4: 上下文關鍵字 (Context Keywords)
# =============================================================================
def example_4_context_keywords():
    """
    使用 keywords 進行同音異義詞辨析 (Homophone Disambiguation)。
    """
    print("=" * 60)
    print("範例 4: 上下文關鍵字 (Context Keywords)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "箸": {
                "aliases": ["hashi"],
                "keywords": ["食べる", "ご飯", "使う", "持つ"],
                "weight": 0.5,
            },
            "橋": {
                "aliases": ["hashi"],
                "keywords": ["渡る", "川", "長い", "建設"],
                "weight": 0.5,
            },
            "端": {
                "aliases": ["hashi"],
                "keywords": ["歩く", "道", "隅"],
                "weight": 0.5,
            },
        }
    )

    test_cases = [
        ("hashiを使ってご飯を食べる", "上下文: 食べる/ご飯/使う → 箸"),
        ("川のhashiを渡る", "上下文: 渡る/川 → 橋"),
        ("道のhashiを歩く", "上下文: 歩く/道/隅 → 端"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Keywords", text, result, explanation)


# =============================================================================
# 範例 5: 上下文排除 (Context Exclusion)
# =============================================================================
def example_5_exclude_when():
    """
    使用 exclude_when 避免錯誤修正。
    """
    print("=" * 60)
    print("範例 5: 上下文排除 (Context Exclusion)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "愛": {
                "aliases": ["ai"],
                "keywords": ["母", "恋", "愛情", "感じる"],
                "exclude_when": ["人工知能", "技術", "開発", "ロボット", "IT"],
            }
        }
    )

    test_cases = [
        ("母のaiを感じる", "有 keywords(母/感じる)，無 exclude_when → 替換為 愛"),
        ("最近のai技術はすごい", "有 exclude_when(技術) → 不替換"),
        ("IT企業のai開発", "有 exclude_when(IT/開発) → 不替換"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Exclusion", text, result, explanation)


# =============================================================================
# 範例 6: 權重系統 (Weight System)
# =============================================================================
def example_6_weight_system():
    """
    使用權重控制優先級。
    """
    print("=" * 60)
    print("範例 6: 權重系統 (Weight System)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "機械": {
                "aliases": ["kikai"],
                "weight": 0.8,  # 較常見，較高優先級
            },
            "機会": {
                "aliases": ["kikai"],
                "weight": 0.2,  # 較少見，較低優先級
            },
        }
    )

    test_cases = [
        ("新しいkikaiを導入する", "權重較高 → 機械"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Weight", text, result, explanation)



# =============================================================================
# 範例 7: 同音過濾 + 變體覆蓋 (Homophone Filtering)
# =============================================================================
def example_7_homophone_filtering():
    """
    展示 JapaneseFuzzyGenerator 的覆蓋範圍，以及「同 Romaji phonetic key 去重」的效果。
    """
    print("=" * 60)
    print("範例 7: 同音過濾 + 變體覆蓋 (Homophone Filtering)")
    print("=" * 60)

    from phonofix.languages.japanese.fuzzy_generator import JapaneseFuzzyGenerator

    generator_safe = JapaneseFuzzyGenerator(enable_representative_variants=False)
    generator_repr = JapaneseFuzzyGenerator(enable_representative_variants=True)

    terms = [
        "通り",
        "切手",
        "こんにちは",
        "スマートフォン",
    ]

    for term in terms:
        safe_variants = generator_safe.generate_variants(term, max_variants=20)
        repr_variants = generator_repr.generate_variants(term, max_variants=20)

        print(f"目標詞: {term}")
        print(f"安全變體數 (safe): {len(safe_variants)}")
        print(f"代表變體數 (repr): {len(repr_variants)}")
        print(f"safe 前10個: {safe_variants[:10]}")
        print(f"repr 前10個: {repr_variants[:10]}")
        print("說明: 生成階段會以 Romaji key 去重，避免同音變體造成詞典膨脹")
        print()

# =============================================================================
# 範例 8: 混合格式 (Mixed Format)
# =============================================================================
def example_8_mixed_format():
    """
    混合使用列表和字典配置。
    """
    print("=" * 60)
    print("範例 8: 混合格式 (Mixed Format)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "東京": ["tokyo"],  # 手動別名
            "大阪": {},  # 空字典 -> 自動生成變體（需開啟 enable_surface_variants）
            "京都": {  # 完整配置
                "aliases": ["kyoto"],
                "keywords": ["寺", "観光"],
                "weight": 0.5,
            },
        }
    )

    test_cases = [
        ("tokyoに行きたい", "手動別名 -> 東京"),
        ("osakaのたこ焼き", "自動生成變體 -> 大阪"),
        ("kyo toの寺を見学", "完整配置 -> 京都"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Mixed", text, result, explanation)


# =============================================================================
# 範例 9: 長文章校正 (Long Article)
# =============================================================================
def example_9_long_article():
    """
    長文章綜合測試。
    """
    print("=" * 60)
    print("範例 9: 長文章校正 (Long Article)")
    print("=" * 60)

    terms = {
        "人工知能": ["ai"],
        "開発": ["kaihatsu"],
        "未来": ["mirai"],
        "技術": ["gijutsu"],
        "社会": ["shakai"],
        "変革": ["henkaku"],
        "ロボット": ["robotto"]
    }
    
    corrector = engine.create_corrector(terms)

    article = (
        "現在、aiのgijutsuは急速に進歩しています。"
        "多くの企業が新しいrobottoのkaihatsuに取り組んでおり、"
        "これが私たちのshakaiに大きなhenkakuをもたらすでしょう。"
        "明るいmiraiのために、私たちは学び続ける必要があります。"
    )

    print("原文 (Original):")
    print(article)
    print("-" * 40)
    
    result = corrector.correct(article)
    
    print("修正後 (Corrected):")
    print(result)
    print("-" * 40)


# =============================================================================
# 主程式
# =============================================================================
if __name__ == "__main__":
    print("\n" + "ja" * 20)
    print("  日文語音辨識校正範例 (Japanese Examples)")
    print("ja" * 20 + "\n")

    examples = [
        example_1_basic_usage,
        example_2_manual_aliases,
        example_3_phonetic_variants,
        example_4_context_keywords,
        example_5_exclude_when,
        example_6_weight_system,
        example_7_homophone_filtering,
        example_8_mixed_format,
        example_9_long_article,
    ]

    for func in examples:
        try:
            func()
        except Exception as e:
            print(f"範例執行失敗: {e}")
            import traceback
            traceback.print_exc()
        print()

    print("=" * 60)
    print("所有範例執行完成!")
    print("=" * 60)

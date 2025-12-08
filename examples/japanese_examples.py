"""
日文語音辨識校正範例 (Japanese ASR Correction Examples)

本檔案展示 UnifiedEngine (Japanese) 的所有核心功能：
1. 基礎用法 - 自動生成 Romaji 索引
2. 手動別名 - 指定常見錯誤拼寫
3. 發音變體 - 長音、促音、助詞錯誤
4. 上下文關鍵字 - 根據前後文判斷替換 (同音異義詞)
5. 上下文排除 - 避免錯誤修正
6. 權重系統 - 控制替換優先級
7. 混合格式配置
8. 長文章校正
"""

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))

from phonofix import UnifiedEngine
from tools.translation_client import translate_text

# Initialize Engine
engine = UnifiedEngine()
is_translate = False


def print_case(title, text, result, explanation):
    print(f"--- {title} ---")
    print(f"原文 (Original):  {text}")
    if is_translate:
        print(f"譯文 (Trans):     {translate_text(text)}")
    print(f"修正 (Corrected): {result}")
    if is_translate:
        print(f"譯文 (Trans):     {translate_text(result)}")
    print(f"說明 (Note):      {explanation}")
    print()


# =============================================================================
# 範例 1: 基礎用法 - 自動生成 Romaji 索引
# =============================================================================
def example_1_basic_usage():
    """
    最簡單的用法：只提供正確詞彙，系統自動生成 Romaji 索引。
    The simplest usage: provide correct terms, system auto-generates Romaji index.
    """
    print("=" * 60)
    print("範例 1: 基礎用法 (Basic Usage)")
    print("=" * 60)

    # 只需提供正確的詞彙
    corrector = engine.create_corrector(
        [
            "会議",  # kaigi
            "プロジェクト",  # purojekuto
            "エンジニア",  # enjinia
            "胃カメラ",  # ikamera
        ]
    )

    test_cases = [
        ("明日のkaigiに参加します", "Romaji -> Kanji (kaigi -> 会議)"),
        (
            "新しいpurojekutoが始まります",
            "Romaji -> Katakana (purojekuto -> プロジェクト)",
        ),
        ("彼は優秀なenjiniaです", "Romaji -> Katakana (enjinia -> エンジニア)"),
        ("ikameraの検査", "Romaji -> Kanji/Katakana (ikamera -> 胃カメラ)"),
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
    Manually provide aliases for special spellings or abbreviations.
    """
    print("=" * 60)
    print("範例 2: 手動別名 (Manual Aliases)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "スマートフォン": ["sumaho", "smapho"],  # Abbreviation: スマホ
            "パーソナルコンピュータ": ["pasokon"],  # Abbreviation: パソコン
            "アスピリン": ["asupirin", "asupirinn"],  # Common typo
        }
    )

    test_cases = [
        ("新しいsumahoを買いました", "Abbreviation (sumaho -> スマートフォン)"),
        ("pasokonが壊れました", "Abbreviation (pasokon -> パーソナルコンピュータ)"),
        ("頭痛にasupirinn", "Typo correction (asupirinn -> アスピリン)"),
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
    Handling missing long vowels, gemination, or particle errors.
    """
    print("=" * 60)
    print("範例 3: 發音變體 (Phonetic Variants)")
    print("=" * 60)

    # term_map = {
    #     "通り": ["tori"],       # Missing long vowel (toori -> tori)
    #     "切手": ["kite"],       # Missing gemination (kitte -> kite)
    #     "こんにちは": ["konnichiwa"], # Particle wa/ha mismatch
    # }
    term_list = ["通り", "切手", "こんにちは"]
    corrector = engine.create_corrector(term_list)

    test_cases = [
        ("このtoriは賑やかです", "Long vowel correction (tori -> 通り)"),
        ("kiteを集めています", "Gemination correction (kite -> 切手)"),
        ("先生、konnichiwa", "Particle correction (konnichiwa -> こんにちは)"),
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
    Using keywords to disambiguate homophones.
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
        ("hashiを使ってご飯を食べる", "Context: 食べる -> 箸 (Chopsticks)"),
        ("川のhashiを渡る", "Context: 渡る/川 -> 橋 (Bridge)"),
        ("道のhashiを歩く", "Context: 歩く/道 -> 端 (Edge)"),
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
    Using exclude_when to prevent incorrect corrections.
    """
    print("=" * 60)
    print("範例 5: 上下文排除 (Context Exclusion)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "愛": {
                "aliases": ["ai"],
                "exclude_when": [
                    "人工知能",
                    "ロボット",
                    "IT",
                ],  # Don't correct 'ai' to '愛' in IT context
            }
        }
    )

    test_cases = [
        ("母のaiを感じる", "No exclusion -> 愛 (Love)"),
        (
            "最近のai技術はすごい",
            "Excluded by '技術' (implied) or just 'ai' stays 'ai'? Wait, 'ai' matches '愛'. If excluded, it stays 'ai'.",
        ),
        # Note: In our simple implementation, if excluded, it returns original token.
        ("IT企業のai開発", "Excluded by 'IT' -> ai (Artificial Intelligence)"),
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
    Using weights to control priority.
    """
    print("=" * 60)
    print("範例 6: 權重系統 (Weight System)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "機械": {"aliases": ["kikai"], "weight": 0.8},  # Higher priority (Machine)
            "機会": {
                "aliases": ["kikai"],
                "weight": 0.2,  # Lower priority (Opportunity)
            },
        }
    )

    test_cases = [
        ("新しいkikaiを導入する", "High weight -> 機械 (Machine)"),
        # Note: Without keywords, weight decides.
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Weight", text, result, explanation)


# =============================================================================
# 範例 7: 発音変体展示 (Phonetic Variants)
# =============================================================================
def example_7_phonetic_variants():
    """
    展示 JapaneseFuzzyGenerator 生成的發音變體。
    Show generated phonetic variants for given terms.
    """
    print("=" * 60)
    print("範例 7: 発音変体展示 (Phonetic Variants)")
    print("=" * 60)

    from phonofix.languages.japanese.fuzzy_generator import JapaneseFuzzyGenerator

    generator = JapaneseFuzzyGenerator()

    terms = [
        "通り",
        "切手",
        "こんにちは",
        "東京",
        "大阪",
        "京都",
        "スマートフォン",
    ]

    for term in terms:
        variants = generator.generate_variants(term)
        print(f"目標詞: {term}")
        print(f"生成的變體數: {len(variants)}")
        print(f"前10個變體: {variants[:10]}")
        print(f"說明: 展示自動生成的 ASR 誤聽拼寫變體")
        print()


# =============================================================================
# 範例 8: 混合格式 (Mixed Format)
# =============================================================================
def example_8_mixed_format():
    """
    混合使用列表和字典配置。
    Mixing list and dictionary configurations.
    """
    print("=" * 60)
    print("範例 8: 混合格式 (Mixed Format)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "東京": ["tokyo"],  # Simple list
            "大阪": {},  # Empty dict (Auto-generate)
            "京都": {  # Full config
                "aliases": ["kyoto"],
                "keywords": ["寺", "観光"],
                "weight": 0.5,
            },
        }
    )

    test_cases = [
        ("tokyoに行きたい", "Simple list -> 東京"),
        ("osakaのたこ焼き", "Auto-gen -> 大阪"),
        ("kyo toの寺を見学", "Full config -> 京都"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Mixed", text, result, explanation)


# =============================================================================
# 範例 8: 長文章校正 (Long Article)
# =============================================================================
def example_8_long_article():
    """
    長文章綜合測試。
    Comprehensive test with a longer article.
    """
    print("=" * 60)
    print("範例 8: 長文章校正 (Long Article)")
    print("=" * 60)

    terms = {
        "人工知能": ["ai"],
        "開発": ["kaihatsu"],
        "未来": ["mirai"],
        "技術": ["gijutsu"],
        "社会": ["shakai"],
        "変革": ["henkaku"],
        "ロボット": ["robotto"],
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
    print(f"譯文: {translate_text(article)}")
    print("-" * 40)

    result = corrector.correct(article)

    print("修正後 (Corrected):")
    print(result)
    print(f"譯文: {translate_text(result)}")
    print("-" * 40)


# =============================================================================
# 主程式
# =============================================================================
if __name__ == "__main__":
    print("\n" + "🇯🇵" * 20)
    print("  日文語音辨識校正範例 (Japanese Examples)")
    print("🇯🇵" * 20 + "\n")

    examples = [
        example_1_basic_usage,
        example_2_manual_aliases,
        example_3_phonetic_variants,
        example_4_context_keywords,
        example_5_exclude_when,
        example_6_weight_system,
        example_7_phonetic_variants,
        example_8_mixed_format,
        example_8_long_article,
    ]

    for func in examples:
        try:
            func()
        except Exception as e:
            print(f"❌ 範例執行失敗: {e}")
            import traceback

            traceback.print_exc()
        print()

    print("=" * 60)
    print("✅ 所有範例執行完成!")
    print("=" * 60)

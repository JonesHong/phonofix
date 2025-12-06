"""
中文語音辨識校正範例

本檔案展示 ChineseEngine 的所有核心功能：
1. 基礎用法 - Engine.create_corrector() 工廠方法
2. 模糊詞典生成 - 自動生成同音/近音變體
3. 同音字過濾 - 避免無意義的替換
4. 台灣口音支援 - n/l, r/l, f/h 混淆
5. 上下文關鍵字 - 根據前後文判斷替換
6. 權重系統 - 控制替換優先級
7. 豁免排除 - exclude_when 上下文排除條件
8. 長文章校正 - 完整段落測試
"""

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))

from phonofix import ChineseEngine

# 全域 Engine (單例模式，避免重複初始化)
engine = ChineseEngine(verbose=False)


def print_case(title, text, result, explanation):
    """統一的輸出格式"""
    print(f"--- {title} ---")
    print(f"原文 (Original):  {text}")
    print(f"修正 (Corrected): {result}")
    print(f"說明 (Note):      {explanation}")
    print()


# =============================================================================
# 範例 1: 基礎用法 - 自動生成別名
# =============================================================================
def example_1_basic_usage():
    """
    最簡單的用法：只提供關鍵字列表，系統自動生成所有模糊音變體
    """
    print("=" * 60)
    print("範例 1: 基礎用法 (Basic Usage)")
    print("=" * 60)

    # 只需提供正確的詞彙，系統會自動生成同音/近音的錯誤變體
    corrector = engine.create_corrector(
        [
            "台北車站",  # 自動生成: 胎北車站, 太北車站, 臺北車站...
            "牛奶",  # 自動生成: 流奶, 留奶...
            "發揮",  # 自動生成: 花揮, 法揮...
            "學校",  # 自動生成: 些校, 雪校...
            "然後",  # 自動生成: 蘭後, 藍後...
        ]
    )

    test_cases = [
        ("我在台北車站等你", "無需修正"),
        ("我在胎北車站等你", "同音字替換 胎→台"),
        ("買了流奶回家", "近音字替換 流→牛"),
        ("他充分花揮了才能", "同音字替換 花揮→發揮"),
        ("蘭後去些校", "多詞修正 蘭後→然後, 些校→學校"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Basic", text, result, explanation)


# =============================================================================
# 範例 2: 手動提供別名 + 拼音去重
# =============================================================================
def example_2_manual_aliases():
    """
    手動提供別名，系統會自動去除拼音相同的重複項
    適用於：需要特定簡稱或縮寫的情況
    """
    print("=" * 60)
    print("範例 2: 手動別名 (Manual Aliases)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            # "北車" 是縮寫，拼音與 "台北車站" 不同，所以需要手動添加
            "台北車站": [
                "北車",
                "台北車站",
                "臺北車站",
            ],  # 後兩個拼音相同，只保留第一個
            # 專業術語的各種錯誤寫法
            "阿斯匹靈": ["阿斯匹林", "二四批林", "阿司匹靈"],
        }
    )

    test_cases = [
        ("我在北車等你", "簡稱 北車→台北車站"),
        ("醫生開了二四批林", "錯誤發音 二四批林→阿斯匹靈"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Manual Aliases", text, result, explanation)


# =============================================================================
# 範例 3: 台灣口音特色 (n/l, r/l, f/h 混淆)
# =============================================================================
def example_3_taiwan_accent():
    """
    台灣口音常見的子音混淆：
    - n/l 混淆: 牛(niu) ↔ 流(liu)
    - r/l 混淆: 然(ran) ↔ 蘭(lan)
    - f/h 混淆: 發(fa) ↔ 花(hua)
    """
    print("=" * 60)
    print("範例 3: 台灣口音 (Taiwan Accent)")
    print("=" * 60)

    corrector = engine.create_corrector(
        [
            "牛奶",  # n/l: 流奶
            "然後",  # r/l: 蘭後
            "發揮",  # f/h: 花揮
            "腦袋",  # n/l: 老袋
        ]
    )

    test_cases = [
        ("買了流奶回家", "n/l混淆: 流→牛"),
        ("蘭後我們去吃飯", "r/l混淆: 蘭→然"),
        ("充分花揮才能", "f/h混淆: 花→發"),
        ("他老袋不太靈光", "n/l混淆: 老→腦"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Taiwan Accent", text, result, explanation)


# =============================================================================
# 範例 4: 上下文關鍵字 (keywords)
# =============================================================================
def example_4_context_keywords():
    """
    使用 keywords 進行上下文判斷：
    - 當多個詞彙有相似的別名時，根據上下文決定替換哪個
    - keywords 是「必要條件」：必須至少匹配一個關鍵字才會替換
    - 沒有 keywords 的詞彙仍可透過一般發音匹配替換
    """
    print("=" * 60)
    print("範例 4: 上下文關鍵字 (Context Keywords)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "永和豆漿": {
                "aliases": ["永豆", "勇豆", "永鬥"],
                "keywords": ["吃", "喝", "買", "宵夜", "早餐"],  # 食物相關
                "weight": 0.3,  # 較高優先級
            },
            "勇者鬥惡龍": {
                "aliases": ["勇鬥", "永鬥"],
                "keywords": ["玩", "遊戲", "攻略", "破關"],  # 遊戲相關
                "weight": 0.2,
            },
        }
    )

    test_cases = [
        ("我去買勇鬥當宵夜", "食物關鍵字: 買+宵夜 → 永和豆漿"),
        ("這款永鬥的攻略很難找", "遊戲關鍵字: 攻略 → 勇者鬥惡龍"),
        ("勇鬥很好吃", "食物關鍵字: 吃 → 永和豆漿 (雖然輸入是勇鬥)"),
        ("我們去吃勇鬥當消夜,吃完再去我家找攻略一起玩永豆通宵阿", "混合情境"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Keywords", text, result, explanation)


# =============================================================================
# 範例 5: 上下文排除 (exclude_when)
# =============================================================================
def example_5_exclude_when():
    """
    使用 exclude_when 根據上下文阻止特定情況的替換：
    - exclude_when 是「否決條件」：只要匹配任一排除條件就不替換
    - exclude_when 優先於 keywords

    注意：exclude_when 是關鍵字匹配，不需要完整詞彙
    """
    print("=" * 60)
    print("範例 5: 上下文排除 (Context Exclusion)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "心電圖設備": {
                "aliases": ["心電圖社北", "心電圖社備"],  # 語音辨識可能的錯誤
                "keywords": ["醫院", "檢查", "醫療"],  # 醫療相關
                "exclude_when": ["公司", "銷售", "新創"],  # 商業相關 -> 不修正
            }
        }
    )

    test_cases = [
        ("醫院有心電圖社備", "有 keywords(醫院)，無 exclude_when → 替換"),
        ("心電圖社備公司成立", "有 exclude_when(公司) → 不替換"),
        ("心電圖社北銷售部門", "有 exclude_when(銷售) → 不替換"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Exclusion", text, result, explanation)


# =============================================================================
# 範例 6: 權重系統 (weight)
# =============================================================================
def example_6_weight_system():
    """
    使用權重控制替換優先級：
    - 預設權重 0.15
    - 權重越高，同音/近音匹配時優先使用
    - 權重也影響模糊匹配的門檻
    """
    print("=" * 60)
    print("範例 6: 權重系統 (Weight System)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "台北車站": {"aliases": ["北車"], "weight": 0.5},  # 高權重，重要地標
            "台北市": {"aliases": [], "weight": 0.1},  # 低權重
        }
    )

    # 權重影響距離計算: 較高權重的詞彙更容易被匹配
    text = "我在北車等你"
    result = corrector.correct(text)
    print_case("Weight", text, result, "權重 0.5 的台北車站優先匹配")


# =============================================================================
# 範例 7: 同音字過濾
# =============================================================================
def example_7_homophone_filtering():
    """
    自動過濾無意義的同音字替換：
    - 台北車站 的別名不會包含 太北車站、抬北車站 等（拼音相同）
    - 這避免了「正確→正確」的無意義替換
    """
    print("=" * 60)
    print("範例 7: 同音過濾 (Homophone Filtering)")
    print("=" * 60)

    from phonofix.languages.chinese.fuzzy_generator import (
        ChineseFuzzyGenerator,
    )

    generator = ChineseFuzzyGenerator()

    # 生成變體
    term = "台北車站"
    all_variants = generator.generate_variants(term)

    # filter_homophones 接受一個列表，過濾同音詞
    filter_result = generator.filter_homophones([term] + all_variants)

    print(f"目標詞: {term}")
    print(f"生成的變體數: {len(all_variants)}")
    print(f"過濾後保留數量: {len(filter_result['kept'])}")
    print(f"被過濾的同音詞數量: {len(filter_result['filtered'])}")
    print(f"保留的變體 (前10個): {filter_result['kept'][:10]}")
    print(f"說明: 同音詞被過濾，避免無意義替換")
    print()


# =============================================================================
# 範例 8: 混合格式配置
# =============================================================================
def example_8_mixed_format():
    """
    在同一個 term_mapping 中混用不同格式：
    - 純列表: 自動生成別名
    - 空字典: 自動生成別名
    - 別名列表: 手動指定別名
    - 完整配置: 別名 + keywords + exclude_when + weight
    """
    print("=" * 60)
    print("範例 8: 混合格式 (Mixed Format)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            # 格式 1: 手動指定別名列表
            "台北車站": ["北車"],
            # 格式 2: 空字典 → 自動生成別名
            "牛奶": {},
            # 格式 3: 完整配置
            "永和豆漿": {
                "aliases": ["永豆"],
                "keywords": ["吃", "喝", "買"],
                "weight": 0.3,
            },
            # 格式 4: 只指定 keywords，自動生成別名
            "發揮": {"keywords": ["充分", "才能"], "weight": 0.2},
            "Python": {
                "aliases": ["Pyton", "Pyson", "派森"],
                "keywords": ["程式", "代碼", "coding", "code"],
            },
            "C語言": {"aliases": ["C語法", "西語言"], "keywords": ["程式", "指標", "記憶體"]},
            "App": ["APP", "欸屁屁", "A屁屁"],
        }
    )

    text = "我在北車買了流奶和永豆,他充分花揮了才能。我正在寫Pyson程式。你有玩過西語言的遊戲欸屁屁嗎？西語言真的很難學。C語法跟派森的程式差別好多。"
    result = corrector.correct(text)
    print_case("Mixed", text, result, "混合格式綜合測試")


# =============================================================================
# 範例 9: 長文章修正
# =============================================================================
def example_9_long_article():
    """
    完整段落測試：展示多種錯誤類型的同時修正
    """
    print("=" * 60)
    print("範例 9: 長文章校正 (Long Article)")
    print("=" * 60)

    term_list = [
        "聖靈",
        "道成肉身",
        "聖經",
        "新約",
        "舊約",
        "新舊約",
        "榮光",
        "使徒",
        "福音",
        "默示",
        "感孕",
        "充滿",
        "章節",
        "恩典",
        "上帝",
        "這就是",
        "太初",
        "放縱",
        "父獨生子",
    ]
    protected_terms = ["什麼是", "道成的文字"]

    corrector = engine.create_corrector(term_list, protected_terms=protected_terms)
    article = (
        "什麼是上帝的道那你應該知道這本聖經就是上帝的道上帝的話就是上帝的道"
        "沒有錯我在說道太出與上帝同在道是聖林帶到人間的所以聖林借著莫氏就約的先知跟新約的使徒 "
        "寫一下這一本新就月生經這個是文字的道叫做真理那聖林又把道帶到人間"
        "就是借著馬利亞聖林敢運生下了倒成肉生的耶穌基督就是基督降生在地上"
        "這是道就是倒成了肉生對不對所以道被帶到人間都是聖林帶下來的 "
        "都是勝領帶下來的道成的文字就是這本新舊月聖經道成的路生就是耶穌基督自己道成的文字"
        "是真理那道成的路生呢安點注意再聽我講一次道成的文字是真理道成的路生是安點"
        "所以約翰福音第一張十四節道成的路生匆忙 充滿有恩典有真理我們也見過他的農光"
        "就是副獨生子的農光現在請你注意聽一下的話道成的文字是真理這個我們都在追求很多地方"
        "姐妹都很追求讀很好的書很好但是道成的肉身是恩點你可能忽略了這兩者都是攻擊性的武器"
        "都是攻擊性的武器除了你在上帝的話題當中要建造之外你也要明白恩典來我簡單講一句話"
        "就是沒有恩典的真理是冷酷的再聽我講一次沒有恩典的真理是冷酷的是會定人的罪的"
        "是會挑人家的錯誤的是像法律塞人一樣的但是當然反之沒有真理的恩典 "
        "沒有真理的恩典是為叫人放重的沒有錯所以這兩者你必須多了解"
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
    print("\n" + "🇹🇼" * 20)
    print("  中文語音辨識校正範例 (Chinese Examples)")
    print("🇹🇼" * 20 + "\n")

    examples = [
        example_1_basic_usage,
        example_2_manual_aliases,
        example_3_taiwan_accent,
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
            print(f"❌ 範例執行失敗: {e}")
            import traceback

            traceback.print_exc()
        print()

    print("=" * 60)
    print("✅ 所有範例執行完成!")
    print("=" * 60)

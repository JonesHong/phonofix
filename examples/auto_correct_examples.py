"""
auto_correct 功能範例
展示 ChineseTextCorrector.from_terms() 類方法的各種使用方式
"""

from chinese_text_corrector import ChineseTextCorrector


def example_1_simple_list():
    """範例 1: 最簡格式 - 僅提供關鍵字列表,自動生成別名"""
    print("=" * 60)
    print("範例 1: 最簡格式 - 自動生成別名")
    print("=" * 60)

    # 僅提供關鍵字,自動生成所有可能的模糊音變體
    corrector = ChineseTextCorrector.from_terms(["台北車站", "牛奶", "發揮"])

    test_cases = [
        "我在北車等你",
        "買了流奶回家",
        "他充分花揮了才能"
    ]

    for text in test_cases:
        result = corrector.correct(text)
        print(f"原句: {text}")
        print(f"結果: {result}")
    print()


def example_2_dict_with_aliases():
    """範例 2: 提供部分別名,系統會進行拼音去重"""
    print("=" * 60)
    print("範例 2: 提供部分別名 (拼音去重)")
    print("=" * 60)

    # 提供部分別名,系統會過濾掉拼音相同的
    corrector = ChineseTextCorrector.from_terms({
        "台北車站": ["北車", "台北車站", "臺北車站"],  # 後兩個拼音相同,只保留第一個
        "阿斯匹靈": ["阿斯匹林", "二四批林"]
    })

    test_cases = [
        "我在北車買藥",
        "醫生開了二四批林"
    ]

    for text in test_cases:
        result = corrector.correct(text)
        print(f"原句: {text}")
        print(f"結果: {result}")
    print()


def example_3_full_format():
    """範例 3: 完整格式 - 提供別名、關鍵字、權重"""
    print("=" * 60)
    print("範例 3: 完整格式 (別名 + 關鍵字 + 權重)")
    print("=" * 60)

    # 完整配置
    corrector = ChineseTextCorrector.from_terms({
        "永和豆漿": {
            "aliases": ["永豆", "勇豆"],
            "keywords": ["吃", "喝", "買", "宵夜"],
            "weight": 0.3
        },
        "勇者鬥惡龍": {
            "aliases": ["勇鬥", "永鬥"],
            "keywords": ["玩", "遊戲", "攻略"],
            "weight": 0.2
        }
    })

    test_cases = [
        ("我去買勇鬥當宵夜", "應該修正為「永和豆漿」(命中「買」和「宵夜」)"),
        ("這款永豆的攻略很難找", "應該修正為「勇者鬥惡龍」(命中「攻略」)")
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print(f"原句: {text}")
        print(f"結果: {result}")
        print(f"說明: {explanation}")
    print()


def example_4_mixed_format():
    """範例 4: 混合格式 - 有些自動生成,有些手動提供"""
    print("=" * 60)
    print("範例 4: 混合格式")
    print("=" * 60)

    # 混合使用不同格式
    corrector = ChineseTextCorrector.from_terms({
        "台北車站": ["北車"],  # 手動提供別名
        "牛奶": {},  # 空字典,自動生成別名
        "發揮": {  # 提供關鍵字和權重,自動生成別名
            "keywords": ["充分", "才能"],
            "weight": 0.2
        }
    })

    test_cases = [
        "我在北車買了流奶,他充分花揮了才能"
    ]

    for text in test_cases:
        result = corrector.correct(text)
        print(f"原句: {text}")
        print(f"結果: {result}")
    print()


def example_5_with_exclusions():
    """範例 5: 使用豁免清單"""
    print("=" * 60)
    print("範例 5: 使用豁免清單")
    print("=" * 60)

    # 排除某些詞不進行修正
    corrector = ChineseTextCorrector.from_terms(
        ["台北車站"],
        exclusions=["北車站", "車站"]  # 這些詞不會被修正
    )

    test_cases = [
        "我在北車等你",  # 會修正
        "我在北車站等你",  # 不會修正 (豁免)
        "我在車站等你"  # 不會修正 (豁免)
    ]

    for text in test_cases:
        result = corrector.correct(text)
        print(f"原句: {text}")
        print(f"結果: {result}")
    print()


def example_6_comprehensive():
    """範例 6: 綜合範例 - 多種配置混用"""
    print("=" * 60)
    print("範例 6: 綜合範例")
    print("=" * 60)

    corrector = ChineseTextCorrector.from_terms({
        # 自動生成別名
        "台北車站": {},
        "牛奶": {},
        "學校": {},
        "然後": {},
        "發揮": {},

        # 手動提供別名 + 上下文
        "永和豆漿": {
            "aliases": ["永豆"],
            "keywords": ["吃", "喝", "買"],
            "weight": 0.3
        }
    })

    text = "我在北車買了流奶和永豆,蘭後去些校,他充分花揮了才能。"
    result = corrector.correct(text)

    print(f"原句: {text}")
    print(f"結果: {result}")
    print()


if __name__ == "__main__":
    print("\n🚀 ChineseTextCorrector.from_terms() 功能範例\n")

    try:
        example_1_simple_list()
        example_2_dict_with_aliases()
        example_3_full_format()
        example_4_mixed_format()
        example_5_with_exclusions()
        example_6_comprehensive()

        print("=" * 60)
        print("✅ 所有範例執行完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()

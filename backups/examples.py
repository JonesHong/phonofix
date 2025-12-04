"""
Chinese Text Corrector - 完整使用範例

展示所有功能的使用方式:
1. 模糊音詞典生成
2. 同音詞過濾
3. ASR 文本校正 (多種情境)
"""

import json
from phonofix.languages.chinese.corrector import (
    ChineseCorrector,
    FuzzyDictionaryGenerator,
)


def example_1_fuzzy_dictionary_generation():
    """範例 1: 模糊音詞典生成"""
    print("=" * 60)
    print("範例 1: 模糊音詞典生成")
    print("=" * 60)

    # 建立生成器
    generator = FuzzyDictionaryGenerator()

    # 輸入關鍵字列表
    input_terms = [
        "台北車站",
        "阿斯匹靈",
        "永和豆漿",
        "發揮",
        "牛奶",
        "肌肉",
        "歡迎光臨",
        "不知道",  # 懶音
        "這樣",  # 懶音 (zhe yang -> jiang)
        "新年快樂",
        "學校",
        "鞋子",
        "然後",  # r -> l/n
        "確認",  # que -> qie, ren -> len
        "測試",  # 捲舌音
    ]

    # 生成模糊音詞典
    fuzzy_dict = generator.generate_fuzzy_variants(input_terms)

    # 輸出結果
    print(json.dumps(fuzzy_dict, indent=2, ensure_ascii=False))
    print()


def example_2_homophone_filtering():
    """範例 2: 同音詞過濾"""
    print("=" * 60)
    print("範例 2: 同音詞過濾")
    print("=" * 60)

    generator = FuzzyDictionaryGenerator()

    # 這裡有許多「同音字」: 測試、側試、策試 (拼音都是 ce shi)
    # 還有不同的音: 車試 (che shi)
    test_list = ["測試", "側試", "策試", "測是", "車試", "車是", "台北車站"]

    result = generator .filter_homophones(test_list)

    print("原始列表:")
    print(json.dumps(test_list, indent=2, ensure_ascii=False))
    print("\n過濾結果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()


def example_3_canonical_normalization():
    """範例 3: 歸一化模式 (修正為標準詞)"""
    print("=" * 60)
    print("範例 3: 歸一化模式 (修正為標準詞)")
    print("=" * 60)

    # 詞庫定義
    term_mapping = {
        "台北車站": ["北車", "臺北車站", "台北火車站"],
        "台大醫院": ["台大"],
        "阿斯匹靈": ["二四批林", "阿斯匹林"],
    }

    exclusions = ["北側", "南側", "東側", "西側"]

    # V2 固定為歸一化模式，不需要 use_canonical_normalization 參數
    corrector = ChineseCorrector(term_mapping, exclusions=exclusions)

    # 測試案例
    test_cases = [
        "醫生開了二四批林給我。",
        "我們約在北側出口見面。",
        "我們約在北車的北側出口見面。",
        "電影裡的飛車追逐很精彩。",  # 不應修正
        "我去過台大看病,然後去北側搭車。",
    ]

    for text in test_cases:
        print(f"原句: {text}")
        result = corrector.correct(text)
        print(f"結果: {result}\n")


def example_4_alias_preservation():
    """
    範例 4: 別名保留模式 (V2 已移除)
    
    說明: V2 版本固定使用歸一化模式，所有別名都會被修正為標準詞。
    若需保留簡稱，請將簡稱設為標準詞 (字典的 key)。
    """
    print("=" * 60)
    print("範例 4: V2 固定歸一化模式 說明")
    print("=" * 60)

    # V2 版本: 若需保留簡稱，請將簡稱設為 key
    # 例如: 想保留 "北車"，則將 "北車" 設為 key
    term_mapping = {
        "北車": ["台北車站", "臺北車站"],  # "北車" 是標準詞
        "台大": ["台大醫院"],  # "台大" 是標準詞
    }

    exclusions = ["北側"]

    corrector = ChineseCorrector(term_mapping, exclusions=exclusions)

    text = "我去過台大醫院看病,然後去北側搭車。"
    print(f"原句: {text}")
    result = corrector.correct(text)
    print(f"結果: {result}")
    print("說明: '台大醫院' -> '台大' (因為 '台大' 是標準詞)\n")


def example_5_context_based_correction():
    """範例 5: 上下文關鍵字校正"""
    print("=" * 60)
    print("範例 5: 上下文關鍵字校正")
    print("=" * 60)

    # 使用完整格式定義詞庫 (含關鍵字)
    term_mapping = {
        "永和豆漿": {
            "aliases": ["永豆"],
            "keywords": ["吃", "喝", "買", "宵夜", "早餐", "豆漿", "油條"],
        },
        "勇者鬥惡龍": {
            "aliases": ["勇鬥"],
            "keywords": ["玩", "遊戲", "電動", "攻略", "RPG"],
        },
    }

    corrector = ChineseCorrector(term_mapping)

    test_cases = [
        ("我去買勇鬥當宵夜", "食物情境"),
        ("這款永豆的攻略很難找", "遊戲情境"),
        ("我們去吃勇鬥當消夜,吃完再去我家找攻略一起玩永豆通宵阿", "混合情境"),
        ("我想喝用豆", "模糊發音且有上下文"),
    ]

    for text, desc in test_cases:
        print(f"--- {desc} ---")
        print(f"原句: {text}")
        result = corrector.correct(text)
        print(f"結果: {result}\n")


def example_6_english_mixed_terms():
    """範例 6: 英文混用詞"""
    print("=" * 60)
    print("範例 6: 英文混用詞")
    print("=" * 60)

    term_mapping = {
        "Python": {
            "aliases": ["Pyton", "Pyson", "派森"],
            "keywords": ["程式", "代碼", "coding", "code"],
        },
        "C語言": {
            "aliases": ["C語法", "西語言"],
            "keywords": ["程式", "指標", "記憶體"],
        },
        "App": ["APP", "欸屁屁", "A屁屁"],
    }

    corrector = ChineseCorrector(term_mapping)

    test_cases = [
        "我正在寫Pyson程式。",
        "西語言真的很難學。C語法跟JS差別好多。",
        "你有下載那個欸屁屁嗎?",
        "這段 CODES 是用 PYTON 寫的",
    ]

    for text in test_cases:
        print(f"原句: {text}")
        result = corrector.correct(text)
        print(f"結果: {result}\n")


def example_7_taiwan_accent_features():
    """範例 7: 台灣國語特徵 (n/l, r/l, f/h 混淆)"""
    print("=" * 60)
    print("範例 7: 台灣國語特徵 (n/l, r/l, f/h 混淆)")
    print("=" * 60)

    # n/l 混淆
    print("--- n/l 混淆 ---")
    term_mapping_nl = {
        "牛奶": ["流奶", "流來", "牛來"],
        "你好": ["李好", "尼好"],
        "南方": ["蘭方"],
    }
    corrector_nl = ChineseCorrector(term_mapping_nl)

    test_nl = ["我要喝流奶。", "李好,很高興認識你。"]
    for text in test_nl:
        print(f"原句: {text}")
        result = corrector_nl.correct(text)
        print(f"結果: {result}\n")

    # r/l 混淆
    print("--- r/l 混淆 ---")
    term_mapping_rl = {
        "肉": ["樓", "漏"],
        "然後": ["蘭後", "那後"],
    }
    corrector_rl = ChineseCorrector(term_mapping_rl)

    test_rl = ["我買了一斤樓。", "我先去吃飯,覽侯再去找你。"]
    for text in test_rl:
        print(f"原句: {text}")
        result = corrector_rl.correct(text)
        print(f"結果: {result}\n")

    # f/h 混淆
    print("--- f/h 混淆 ---")
    term_mapping_fh = {
        "發揮": ["花揮", "話揮"],
        "飛機": ["輝機"],
        "風景": ["轟景"],
    }
    exclusions_fh = ["話費"]
    corrector_fh = ChineseCorrector(term_mapping_fh, exclusions=exclusions_fh)

    test_fh = [
        "他充分花揮了自己的才能。",
        "業務充分話回才能導致這個月的話費很高。",  # 不應修正
    ]
    for text in test_fh:
        print(f"原句: {text}")
        result = corrector_fh.correct(text)
        print(f"結果: {result}\n")


def example_8_final_fuzzy_matching():
    """範例 8: 韻母模糊測試 (ue/ie, uan/uang)"""
    print("=" * 60)
    print("範例 8: 韻母模糊測試")
    print("=" * 60)

    term_mapping = {
        "學校": ["些校", "鞋校"],  # xue -> xie
        "確認": ["切認", "切冷", "切嫩"],  # que -> qie
        "關係": ["光系"],  # uan -> uang
        "先生": ["香生"],  # ian -> iang
    }

    corrector = ChineseCorrector(term_mapping)

    test_cases = [
        "我在些校讀書。",
        "請切認一下這個資料。這個資料很重要需要雙重竊嫩",
        "他們的光系很好。",
    ]

    for text in test_cases:
        print(f"原句: {text}")
        result = corrector.correct(text)
        print(f"結果: {result}\n")


def example_9_comprehensive_test():
    """範例 9: 綜合測試 (多種混淆規則)"""
    print("=" * 60)
    print("範例 9: 綜合測試 (多種混淆規則)")
    print("=" * 60)

    term_mapping = {
        "台北車站": ["北車", "臺北車站"],
        "牛奶": ["流奶"],
        "然後": ["蘭後", "那後"],
        "發揮": ["花揮"],
        "學校": ["些校"],
    }

    corrector = ChineseCorrector(term_mapping)

    text = "我在北車買了流奶,蘭後去些校找朋友,他充分花揮了才能。"
    print(f"原句: {text}")
    result = corrector.correct(text)
    print(f"結果: {result}\n")


def example_10_weight_system():
    """範例 10: 權重系統測試"""
    print("=" * 60)
    print("範例 10: 權重系統測試")
    print("=" * 60)

    # 使用權重提高優先級
    term_mapping = {
        "恩典": {"aliases": ["安點"], "weight": 0.3},  # 高權重
        "上帝": {"aliases": ["上帝"], "weight": 0.1},  # 低權重
    }

    corrector = ChineseCorrector(term_mapping)

    text = "道成的路生是安點,你可能忽略了這個重要的真理。"
    print(f"原句: {text}")
    result = corrector.correct(text)
    print(f"結果: {result}\n")
    
def  example_11_long_article_test():
    """範例 11: 長文章測試"""
    
    print("=" * 60)
    print("範例 11: 長文章測試")
    print("=" * 60)
    
    # term_mapping = {
    #     "聖靈": ["聖靈"],
    #     "道成肉身": ["道成肉身", "到的路生"],
    #     "聖經": ["聖經"],
    #     "新約": ["新約", "新月"],
    #     "舊約": ["舊約", "舊月"],
    #     "新舊約": ["新舊約"],
    #     "榮光": ["榮光", "農光"],
    #     "使徒": ["使徒"],
    #     "福音": ["福音"],
    #     "默示": ["默示", "漠視"],
    #     "感孕": ["感孕"],
    #     "充滿": ["充滿", "蔥滿"],
    #     "章節": ["章節", "張捷"],
    #     "恩典": {
    #         "aliases": ["恩典", "安點"],
    #         "weight": 0.3,  # [關鍵] 恩典很重要，給予較高權重
    #     },
    #     "上帝": {"aliases": ["上帝"], "weight": 0.1},
    #     "這就是": ["這就是", "自救四"],
    #     "太初": ["太初", "大初","太粗"],
    #     "放縱": ["放縱", "方中"],
    #     "父獨生子": [],
    # }
    term_list = ['聖靈', '道成肉身', '聖經', '新約', '舊約', '新舊約', '榮光', '使徒', '福音', '默示', '感孕', '充滿', '章節', '恩典', '上帝', '這就是', '太初', '放縱', '父獨生子']
    exclusions = ["什麼是","道成的文字"]

    corrector = ChineseCorrector.from_terms(term_list, exclusions=exclusions)
    long_article = (
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
    print(f"原句: {long_article}")
    result = corrector.correct(long_article)
    print(f"結果: {result}\n")



if __name__ == "__main__":
    # 執行所有範例
    example_1_fuzzy_dictionary_generation()
    example_2_homophone_filtering()
    example_3_canonical_normalization()
    example_4_alias_preservation()
    example_5_context_based_correction()
    example_6_english_mixed_terms()
    example_7_taiwan_accent_features()
    example_8_final_fuzzy_matching()
    example_9_comprehensive_test()
    example_10_weight_system()
    example_11_long_article_test()

    print("=" * 60)
    print("所有範例執行完畢!")
    print("=" * 60)

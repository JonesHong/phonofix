"""
中文拼音模糊音配置模組

集中管理中文拼音的模糊音規則（聲母/韻母/特例/黏著詞）。
"""


class ChinesePhoneticConfig:
    """拼音配置類別 - 集中管理所有拼音模糊音規則"""

    # 聲母模糊音映射表 (Fuzzy Initials Map)
    # 定義哪些聲母屬於同一個模糊音群組，視為可互換
    # 範例: 'z' 和 'zh' 都屬於 'z_group'，因此 "zi" 和 "zhi" 的聲母被視為相似
    FUZZY_INITIALS_MAP = {
        "z": "z_group", "zh": "z_group",    # 捲舌音與平舌音混淆 (z <-> zh)
        "c": "c_group", "ch": "c_group",    # (c <-> ch)
        "s": "s_group", "sh": "s_group",    # (s <-> sh)
        "n": "n_l_group", "l": "n_l_group", # 南方口音常見混淆 (n <-> l)，如 "你" <-> "裡"
        "r": "r_l_group",                   # r 有時會被聽成 l
        "f": "f_h_group", "h": "f_h_group", # (f <-> h) 如 "發" <-> "花"
    }

    # 韻母模糊音對列表 (Fuzzy Finals Pairs)
    # 定義哪些韻母結尾容易混淆
    # 格式: (韻母1, 韻母2)
    # 範例: ("in", "ing") 表示 "yin" 和 "ying" 可以互換
    FUZZY_FINALS_PAIRS = [
        ("in", "ing"), ("en", "eng"), ("an", "ang"), # 前後鼻音混淆 (音/英, 真/爭)
        ("ian", "iang"), ("uan", "uang"), ("uan", "an"),
        ("ong", "eng"), ("ong", "on"),
        ("uo", "o"), ("uo", "ou"),
        ("ue", "ie"),
    ]

    # 雙向特殊音節映射 (Bidirectional Special Syllable Map)
    # 定義整音節的混淆規則，適用於聲韻母變化較大的情況
    # 範例: "hua" <-> "fa" (花 <-> 發)
    SPECIAL_SYLLABLE_MAP_BIDIRECTIONAL = {
        "fa": ["hua"], "hua": ["fa"],
        "fei": ["hui"], "hui": ["fei"],
        "fan": ["huan"], "huan": ["fan"],
        "feng": ["hong"], "hong": ["feng"],
        "fu": ["hu"], "hu": ["fu"],
        "xue": ["xie"], "xie": ["xue"],
        "jue": ["jie"], "jie": ["jue"],
        "que": ["qie"], "qie": ["que"],
        "nue": ["nie"], "nie": ["nue"],
        "lue": ["lie"], "lie": ["lue"],
        "ran": ["lan", "yan"], "rou": ["lou"], "re": ["le"],
        "wei": ["hui"], "wan": ["huan"],
        "er": ["e"], "e": ["er"],
        "weng": ["wen"], "wen": ["weng"],
        "yong": ["iong"], "iong": ["yong"],
        "ren": ["lun", "leng"], "nen": ["lun", "leng"],
    }

    # 單向特殊音節映射 (Unidirectional Special Syllable Map)
    # 某些混淆通常是單向的，例如 "hua" 容易被聽成 "fa"，但 "fa" 不太容易被聽成 "hua"
    # 用於更嚴格的模糊匹配場景
    SPECIAL_SYLLABLE_MAP_UNIDIRECTIONAL = {
        "hua": ["fa"], "hui": ["fei", "wei"], "huan": ["fan", "wan"], "hong": ["feng"], "fu": ["hu"],
        "xie": ["xue"], "jie": ["jue"], "qie": ["que"], "nie": ["nue"], "lie": ["lue"],
        "lan": ["ran"], "yan": ["ran"], "lou": ["rou"],
        "e": ["er"],
        "wen": ["weng"], "iong": ["yong"],
        "lun": ["ren"], "leng": ["ren"],
    }

    # 黏著詞組映射 (Sticky Phrase Map)
    # 定義常見的 ASR 連讀、吞音或口語化錯誤
    # 範例: "不知道" 常被快速念成 "不道" 或 "幫道"
    STICKY_PHRASE_MAP = {
        "歡迎光臨": ["緩光您", "歡光您"],
        "謝謝光臨": ["寫光您"],
        "不好意思": ["報意思", "鮑意思", "不意思", "報思"],
        "對不起": ["對不擠", "對七", "瑞不七"],
        "不知道": ["幫道", "不道", "苞道", "不造"],
        "為什麼": ["為什", "位什", "為某", "餵墨"],
        "什麼": ["甚", "神馬", "什"],
        "就是": ["救世", "糾是", "舊是"],
        "真的": ["珍的", "貞的", "蒸的"],
        "這樣": ["醬", "這樣", "窄樣"],
        "那樣": ["釀", "那樣"],
        "可以": ["科以", "可一", "凱"],
        "便宜": ["皮宜", "頻宜"],
        "而且": ["鵝且", "額且", "二且"],
        "然後": ["那後", "腦後", "挪"],
        "大家好": ["搭好", "大好", "家好"],
        "先生": ["鮮生", "仙", "軒", "先嗯"],
        "小姐": ["小解", "小節"],
        "根本": ["跟本", "公本"],
        "這邊": ["這嗯"],
        "今天的": ["尖的"],
        "需要": ["蕭"],
        "收您": ["SONY"], # 特例: 英文 SONY 聽起來像中文 "收您"
    }

    # 語氣詞排除列表 (Skip Particles)
    # 這些詞通常不影響語意，在比對時可以忽略或降低權重
    SKIP_PARTICLES = {
        "啦", "啊", "喔", "哦", "呢", "嘛", "呀", "欸", "誒", "咧", "耶", "嗯", "恩",
    }

    @classmethod
    def build_group_to_initials_map(cls):
        """
        建立反向查找表: 模糊音群組 -> 聲母列表

        用途: 快速查找某個群組包含哪些聲母
        範例: "z_group" -> ["z", "zh"]
        """
        group_to_initials = {}
        for init, group in cls.FUZZY_INITIALS_MAP.items():
            if group not in group_to_initials:
                group_to_initials[group] = []
            group_to_initials[group].append(init)

        # 特殊處理: r_l_group 應該包含 l，即使 FUZZY_INITIALS_MAP 中 l 映射到 n_l_group
        # 這是為了處理 r -> l 的單向或部分雙向關係
        if "r_l_group" in group_to_initials:
            if "l" not in group_to_initials["r_l_group"]:
                group_to_initials["r_l_group"].append("l")
        return group_to_initials

"""
拼音配置模組 (Phonetic Configuration)

提供中文拼音模糊匹配所需的所有配置：
- 聲母模糊映射（zh/z, ch/c, sh/s, n/l, r/l, f/h）
- 韻母模糊映射（in/ing, ue/ie, uan/uang 等）
- 特例音節映射（整個音節的特殊對應）
- 黏音/懶音短語映射（整句對整句）
"""


class PhoneticConfig:
    """
    拼音配置類

    集中管理所有拼音模糊匹配規則，供詞典生成和文本修正使用
    """

    def __init__(self, enable_sticky_phrases=True):
        """
        初始化拼音配置

        :param enable_sticky_phrases: 是否啟用黏音/懶音短語映射
        """
        self.fuzzy_initials_map = self._build_fuzzy_initials_map()
        self.fuzzy_finals_pairs = self._build_fuzzy_finals_pairs()
        self.special_syllable_map = self._build_special_syllable_map()

        if enable_sticky_phrases:
            self.sticky_phrase_map = self._build_sticky_phrase_map()
        else:
            self.sticky_phrase_map = {}

        # 建構反向群組映射
        self.group_to_initials = self._build_group_to_initials_map()

        # 口語助詞集合（可選用於過濾）
        self.skip_particles = set(
            [
                "啦",
                "啊",
                "喔",
                "哦",
                "呢",
                "嘛",
                "呀",
                "欸",
                "誒",
                "咧",
                "耶",
                "嗯",
                "恩",
            ]
        )

    def _build_fuzzy_initials_map(self):
        """
        建構聲母模糊映射
        處理捲舌音、n/l不分、r/l混淆、f/h混淆等

        :return: {聲母: 群組名稱}
        """
        return {
            "z": "z_group",
            "zh": "z_group",
            "c": "c_group",
            "ch": "c_group",
            "s": "s_group",
            "sh": "s_group",
            "n": "n_l_group",
            "l": "n_l_group",  # n/l 不分
            "r": "r_l_group",  # r 變 l
            "f": "f_h_group",
            "h": "f_h_group",  # f/h 混淆
        }

    def _build_fuzzy_finals_pairs(self):
        """
        建構韻母模糊映射對
        處理常見的韻母混淆（in/ing, ue/ie, uan/uang等）

        :return: [(韻母1, 韻母2), ...]
        """
        return [
            ("in", "ing"),
            ("en", "eng"),
            ("an", "ang"),
            ("ian", "iang"),
            ("uan", "uang"),
            ("uan", "an"),
            ("ong", "eng"),
            ("ong", "on"),
            ("uo", "o"),
            ("uo", "ou"),
            ("ue", "ie"),
        ]

    def _build_special_syllable_map(self):
        """
        建構特例音節映射表
        處理無法用聲母/韻母規則覆蓋的特殊情況

        注意：這是「單向」映射，只允許 常見誤讀 -> 正確讀音
        避免將正確的詞誤改為錯誤的讀音

        :return: {誤讀音節: [正確音節列表]}
        """
        return {
            # f/h 系列（單向：h -> f）
            "hua": ["fa"],
            "hui": ["fei", "wei"],  # 輝 -> 飛/微
            "huan": ["fan", "wan"],  # 換 -> 飯/彎
            "hong": ["feng"],
            "fu": ["hu"],
            # ue/ie 系列（單向：ie -> ue）
            "xie": ["xue"],
            "jie": ["jue"],
            "qie": ["que"],
            "nie": ["nue"],
            "lie": ["lue"],
            # r/l 系列
            "lan": ["ran"],
            "yan": ["ran"],
            "lou": ["rou"],
            # 其他
            "e": ["er"],
            "wen": ["weng"],
            "iong": ["yong"],
            # 拼音合法性修補
            "lun": ["ren"],
            "leng": ["ren"],
        }

    def _build_sticky_phrase_map(self):
        """
        建構黏音/懶音短語映射
        整句對整句的特殊對應

        :return: {標準說法: [懶音說法列表]}
        """
        return {
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
            "收您": ["SONY"],
        }

    def _build_group_to_initials_map(self):
        """
        建構反向映射：group -> 可能的聲母列表
        用於模糊匹配時快速查找同組的所有聲母

        :return: {群組名稱: [聲母列表]}
        """
        group_to_initials = {}
        for init, group in self.fuzzy_initials_map.items():
            if group not in group_to_initials:
                group_to_initials[group] = []
            group_to_initials[group].append(init)

        # l 也可能變成 r（補回去）
        if "r_l_group" in group_to_initials:
            if "l" not in group_to_initials["r_l_group"]:
                group_to_initials["r_l_group"].append("l")

        return group_to_initials


# ==========================================
# 測試範例
# ==========================================
if __name__ == "__main__":
    config = PhoneticConfig()

    print("=== PhoneticConfig 測試 ===")
    print(f"聲母群組數：{len(config.fuzzy_initials_map)}")
    print(f"韻母對數：{len(config.fuzzy_finals_pairs)}")
    print(f"特例音節數：{len(config.special_syllable_map)}")
    print(f"黏音短語數：{len(config.sticky_phrase_map)}")
    print(f"\n反向群組映射：")
    for group, initials in config.group_to_initials.items():
        print(f"  {group}: {initials}")

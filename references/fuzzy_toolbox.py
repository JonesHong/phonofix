import pypinyin
import itertools
import json
from Pinyin2Hanzi import DefaultDagParams, dag
from hanziconv import HanziConv


class ChineseFuzzyToolbox:
    def __init__(self):
        # 1. 基礎聲母模糊 (Initials)
        # - zh / z、ch / c、sh / s
        # - n / l 不分
        # - r 有時會被念成 l（台灣國語）
        self.fuzzy_initials_map = {
            "z": "z_group",
            "zh": "z_group",
            "c": "c_group",
            "ch": "c_group",
            "s": "s_group",
            "sh": "s_group",
            "n": "n_l_group",
            "l": "n_l_group",  # n/l 不分
            "r": "r_l_group",  # r 變 l（如 「日」近「力」）
            "f": "f_h_group",
            "h": "f_h_group",  # 發/花
        }

        # 建構反向群組映射
        self.group_to_initials = self._build_group_to_initials_map()

        # 2. 基礎韻母模糊 (Finals)
        # 原本只有 in/ing, en/eng, an/ang，這裡加上更多台式口音常見混讀
        self.fuzzy_finals_pairs = [
            ("in", "ing"),
            ("en", "eng"),
            ("an", "ang"),
            # ian / iang：如 「先 / 香」一帶
            ("ian", "iang"),
            # uan / uang：「關 / 光」一帶
            ("uan", "uang"),
            # uan / an：u 被吃掉，如「uan」念成「an」
            ("uan", "an"),
            # ong / eng / on：鼻音尾不清楚
            ("ong", "eng"),
            ("ong", "on"),
            # uo / o / ou：口型沒開完整
            ("uo", "o"),
            ("uo", "ou"),
            # ue / ie：「學 / 鞋」系列（xue / xie, jue / jie, que / qie, nue / nie, lue / lie）
            ("ue", "ie"),
        ]

        # 3. 特例音節映射 (Syllable Mapping)
        # 無法只靠聲母/韻母替換處理的口音，直接整個音節對應
        self.special_syllable_map = self._build_special_syllable_map()

        # 4. 黏音 / 懶音 短語映射：整句對整句
        #    標準說法 -> 常見懶讀/搞笑聽感寫法
        self.sticky_phrase_map = self._build_sticky_phrase_map()

        # 5. 口語助詞 / 雜訊字：之後做比對時可選擇忽略
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

        self.dag_params = DefaultDagParams()

    def _build_group_to_initials_map(self):
        """
        建構反向映射：group -> 可能的聲母列表
        """
        group_to_initials = {}
        for init, group in self.fuzzy_initials_map.items():
            if group not in group_to_initials:
                group_to_initials[group] = []
            group_to_initials[group].append(init)

        # l 也可能變成 r（補回去）
        if "r_l_group" in group_to_initials:
            group_to_initials["r_l_group"].append("l")

        return group_to_initials

    def _build_special_syllable_map(self):
        """
        建構特例音節映射表
        無法只靠聲母/韻母替換處理的口音，直接整個音節對應
        """
        return {
            # --- 原本的台灣國語/客家口音常見轉換 ---
            # f <-> h (基本款)
            "fa": ["hua"],  # 發 -> 花
            "hua": ["fa"],  # 花 -> 發
            "fei": ["hui"],  # 飛 -> 輝
            "hui": ["fei"],  # 輝 -> 飛
            "fan": ["huan"],  # 飯 -> 換
            "huan": ["fan"],  # 換 -> 飯
            "feng": ["hong"],  # 風 -> 轟
            "hong": ["feng"],  # 轟 -> 風
            "hu": ["fu"],  # 護 -> 負
            "fu": ["hu"],  # 負 -> 護
            # ue / ie 混 (學/鞋, 覺/結, 確/切)---
            "xue": ["xie"],
            "xie": ["xue"],
            "jue": ["jie"],
            "jie": ["jue"],
            "que": ["qie"],
            "qie": ["que"],
            "nue": ["nie"],
            "nie": ["nue"],
            "lue": ["lie"],
            "lie": ["lue"],
            # r <-> y/l (然後 -> 嚴後/蘭後)
            "ran": ["lan", "yan"],
            "rou": ["lou"],  # 肉 -> 漏
            "re": ["le"],  # 熱 -> 樂
            # w <-> h/m (微 -> 輝 / 沒)
            # 台灣國語有時候 w 會發成濁音 v，ASR 可能辨識成 f 或 h
            "wei": ["hui"],
            "wan": ["huan"],
            # --- 兒化音弱化 or 誤加 ---
            "er": ["e"],  # 兒 -> e
            "e": ["er"],  # 反過來有些人會多一個兒化
            # --- 其他常見發音飄移 ---
            "weng": ["wen"],
            "wen": ["weng"],
            "yong": ["iong"],
            "iong": ["yong"],
            # --- 拼音合法性修補 (Crucial Fixes) ---
            # 解決 r -> l 產生的非法拼音 (如 len 不存在)
            "ren": ["lun", "leng"],  # 認 -> 論 / 冷 (解決 len 非法問題)
            "nen": ["lun", "leng"],  # 嫩 -> 論 (解決 n -> l 產生 len 非法問題)
        }

    def _build_sticky_phrase_map(self):
        """
        建構黏音/懶音短語映射表
        標準說法 -> 常見懶讀/搞笑聽感寫法
        """
        return {
            # 你舉的例子：歡迎光臨 → 緩光您
            "歡迎光臨": ["緩光您", "歡光您"],
            "謝謝光臨": ["寫光您"],
            "不好意思": ["報意思", "鮑意思", "不意思", "報思"],
            "對不起": ["對不擠", "對七", "瑞不七"],  # rui bu qi 是比較含糊的講法
            "不知道": ["幫道", "不道", "苞道", "不造"],  # bu zhi dao -> bu r dao
            "為什麼": ["為什", "位什", "為某", "餵墨"],
            "什麼": ["甚", "神馬", "什"],
            "就是": ["救世", "糾是", "舊是"],  # jiu shi -> jiu si
            "真的": ["珍的", "貞的", "蒸的"],
            "這樣": ["醬", "這樣", "窄樣"],  # zhe yang -> jiang
            "那樣": ["釀", "那樣"],  # na yang -> niang
            "可以": ["科以", "可一", "凱"],  # ke yi -> kei
            "便宜": ["皮宜", "頻宜"],  # pian yi -> pin yi
            "而且": ["鵝且", "額且", "二且"],
            "然後": ["那後", "腦後", "挪"],  # ran hou -> na hou (r變n) / no
            "大家好": ["搭好", "大好", "家好"],
            "先生": ["鮮生", "仙", "軒", "先嗯"],  # xian sheng -> xian en
            "小姐": ["小解", "小節"],
            "根本": ["跟本", "公本"],  # gen ben -> gong ben
            "這邊": ["這嗯"],
            "今天的": ["尖的"],
            "需要": ["蕭"],
            "收您": ["SONY"],
        }

    def _pinyin_to_char(self, pinyin_str):
        """
        將單一拼音串轉回常見漢字。
        這裡取前 2 個高頻字，再挑第一個做代表，避免亂碼。
        """
        result = dag(self.dag_params, [pinyin_str], path_num=2)
        chars = []
        if result:
            for item in result:
                chars.append(HanziConv.toTraditional(item.path[0]))
        return chars if chars else [pinyin_str]

    def _extract_pinyin_components(self, char):
        """
        提取漢字的拼音組成部分（聲母和韻母）
        :return: (base_pinyin, initial, final)
        """
        base_pinyin_list = pypinyin.lazy_pinyin(char, style=pypinyin.NORMAL)
        if not base_pinyin_list:
            return None, None, None

        base_pinyin = base_pinyin_list[0]
        initial = pypinyin.pinyin(char, style=pypinyin.INITIALS, strict=False)[0][0]
        final = base_pinyin[len(initial) :]

        return base_pinyin, initial, final

    def _apply_special_syllable_variations(self, base_pinyin, potential_pinyins):
        """
        應用特例音節變體
        檢查是否有特例音節 (Whole Syllable Mapping)
        """
        if base_pinyin in self.special_syllable_map:
            for special_p in self.special_syllable_map[base_pinyin]:
                potential_pinyins.add(special_p)

    def _apply_initial_fuzzy_variations(self, initial, final, potential_pinyins):
        """
        應用聲母模糊變體
        根據聲母群組產生模糊音
        """
        if initial in self.fuzzy_initials_map:
            group = self.fuzzy_initials_map[initial]
            for fuzzy_init in self.group_to_initials[group]:
                potential_pinyins.add(fuzzy_init + final)

    def _apply_final_fuzzy_variations(self, potential_pinyins):
        """
        應用韻母模糊變體
        根據韻母對應表產生模糊音
        """
        current_list = list(potential_pinyins)
        for p in current_list:
            # 注意：這裡 p 是拼音字串，pypinyin 在 strict=False 時可以處理
            curr_init = pypinyin.pinyin(p, style=pypinyin.INITIALS, strict=False)[0][0]
            curr_final = p[len(curr_init) :]

            for f1, f2 in self.fuzzy_finals_pairs:
                if curr_final.endswith(f1):
                    potential_pinyins.add(curr_init + curr_final[: -len(f1)] + f2)
                elif curr_final.endswith(f2):
                    potential_pinyins.add(curr_init + curr_final[: -len(f2)] + f1)

    def _convert_pinyins_to_char_options(self, potential_pinyins, base_pinyin, char):
        """
        將拼音集合轉換為漢字選項列表
        """
        options = []
        for p in potential_pinyins:
            if p == base_pinyin:
                options.append({"pinyin": p, "char": char})
            else:
                candidate_chars = self._pinyin_to_char(p)
                repr_char = candidate_chars[0]

                # 過濾非漢字
                if "\u4e00" <= repr_char <= "\u9fff":
                    options.append({"pinyin": p, "char": repr_char})

        return options

    def _get_char_variations(self, char):
        """
        給定一個漢字：
        1. 取得它的標準拼音
        2. 根據 special_syllable_map / fuzzy_initials / fuzzy_finals
           產生一組可能的「台式口音」拼音
        3. 每個拼音再轉回一個代表漢字
        """
        # 1. 取得原拼音
        base_pinyin, initial, final = self._extract_pinyin_components(char)
        if base_pinyin is None:
            return [{"pinyin": char, "char": char}]

        potential_pinyins = set()
        potential_pinyins.add(base_pinyin)

        # 2. [優先] 檢查是否有特例音節 (Whole Syllable Mapping)
        self._apply_special_syllable_variations(base_pinyin, potential_pinyins)

        # 3. 一般聲母模糊
        self._apply_initial_fuzzy_variations(initial, final, potential_pinyins)

        # 4. 一般韻母模糊
        self._apply_final_fuzzy_variations(potential_pinyins)

        # 5. 轉成文字選項
        return self._convert_pinyins_to_char_options(
            potential_pinyins, base_pinyin, char
        )

    def _generate_char_combinations(self, char_options_list):
        """
        生成字符組合並去重
        使用拼音去重避免組合爆炸
        """
        seen_pinyins = set()
        aliases = []

        for combo in itertools.product(*char_options_list):
            alias_text = "".join([item["char"] for item in combo])
            alias_pinyin = "".join([item["pinyin"] for item in combo])

            # 拼音一樣的只留一個代表，避免爆炸
            if alias_pinyin not in seen_pinyins:
                aliases.append({"text": alias_text, "pinyin": alias_pinyin})
                seen_pinyins.add(alias_pinyin)

        return aliases, seen_pinyins

    def _add_sticky_phrase_aliases(self, term, aliases):
        """
        添加黏音/懶音短語別名
        整句對整句的特例
        """
        if term in self.sticky_phrase_map:
            alias_texts = [a["text"] for a in aliases]
            for sticky in self.sticky_phrase_map[term]:
                if sticky not in alias_texts:
                    aliases.append({"text": sticky, "pinyin": ""})

    def _prepare_final_alias_list(self, term, aliases):
        """
        準備最終的別名列表
        去重、排序，並將原詞放在第一位
        """
        # 提取文字並去重
        alias_texts = [a["text"] for a in aliases if a["text"] != term]
        alias_texts = sorted(set(alias_texts))

        # 原詞放在第一位
        return [term] + alias_texts

    def generate_optimized_dict(self, term_list):
        """
        針對每一個 term（詞/短語）產生一組「台式口音 / 黏音」別名。
        回傳格式：
        {
            "台北車站": ["台北車站", "台北車佔", ...],
            ...
        }
        """
        result = {}
        for term in term_list:
            # 1. 產生每個字的變體
            char_options_list = [self._get_char_variations(char) for char in term]

            # 2. 組合與收斂
            aliases, seen_pinyins = self._generate_char_combinations(char_options_list)

            # 確保原詞拼音已被記錄
            original_pinyin = "".join(pypinyin.lazy_pinyin(term))
            seen_pinyins.add(original_pinyin)

            # 3. 黏音 / 懶音 短語：整句對整句的特例
            self._add_sticky_phrase_aliases(term, aliases)

            # 4. 準備最終列表
            result[term] = self._prepare_final_alias_list(term, aliases)

        return result

    def _get_term_pinyin(self, term):
        """
        取得詞彙的去聲調拼音字串
        """
        pinyin_list = pypinyin.lazy_pinyin(term, style=pypinyin.NORMAL)
        return "".join(pinyin_list)

    def filter_homophones(self, term_list):
        """
        輸入一個詞彙列表，將「去聲調拼音」完全相同的詞進行過濾。
        只保留第一個出現的詞。
        """
        kept = []
        filtered = []
        seen_pinyins = set()

        for term in term_list:
            # 取得去聲調拼音
            pinyin_str = self._get_term_pinyin(term)

            if pinyin_str in seen_pinyins:
                # 拼音已存在，歸類為過濾掉的
                filtered.append(term)
            else:
                # 新拼音，保留
                kept.append(term)
                seen_pinyins.add(pinyin_str)

        return {"kept": kept, "filtered": filtered}


# ==========================================
# 執行與驗證
# ==========================================
if __name__ == "__main__":
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

    toolbox = ChineseFuzzyToolbox()
    final_dict = toolbox.generate_optimized_dict(input_terms)

    print(json.dumps(final_dict, indent=4, ensure_ascii=False))

    # === 測試新的 filter 功能 ===
    print("=== 測試同音過濾功能 ===")

    # 這裡有許多「同音字」：測試、側試、策試 (拼音都是 ce shi)
    # 還有不同的音：車試 (che shi)
    test_list = ["測試", "側試", "策試", "測是", "車試", "車是", "台北車站"]

    result = toolbox.filter_homophones(test_list)
    print("原始list: ")
    print(json.dumps(test_list, indent=4, ensure_ascii=False))
    print("過濾後: ")
    print(json.dumps(result, indent=4, ensure_ascii=False))

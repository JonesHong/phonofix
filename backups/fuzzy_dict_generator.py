"""
模糊詞典生成器 (Fuzzy Dictionary Generator)

提供近似音詞典生成功能：
- 為關鍵字生成所有可能的近似音別名
- 過濾同音詞，避免重複
"""

import pypinyin
import itertools
from Pinyin2Hanzi import DefaultDagParams, dag
from hanziconv import HanziConv
from phonetic_config import PhoneticConfig


class FuzzyDictGenerator:
    """
    模糊詞典生成器

    基於拼音模糊規則，為關鍵字生成近似音別名
    """

    def __init__(self, config=None):
        """
        初始化詞典生成器

        :param config: PhoneticConfig 實例，如果為 None 則創建新實例
        """
        self.config = config or PhoneticConfig()
        self.dag_params = DefaultDagParams()

    # ==========================================
    # 公開方法
    # ==========================================

    def generate_fuzzy_aliases(self, term_list, include_sticky=True):
        """
        為詞彙列表生成近似音別名

        :param term_list: 關鍵字列表
        :param include_sticky: 是否包含黏音短語
        :return: {原詞: [原詞, 別名1, 別名2, ...]}

        範例：
        >>> generator.generate_fuzzy_aliases(["台北車站", "牛奶"])
        {
            "台北車站": ["台北車站", "台北車暫", "台北冊站", ...],
            "牛奶": ["牛奶", "流奶", "流來", ...]
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

            # 3. 黏音/懶音短語（可選）
            if include_sticky:
                self._add_sticky_phrase_aliases(term, aliases)

            # 4. 準備最終列表
            result[term] = self._prepare_final_alias_list(term, aliases)

        return result

    def filter_homophones(self, term_list):
        """
        過濾同音詞，只保留第一個出現的詞

        :param term_list: 詞彙列表
        :return: {"kept": [...], "filtered": [...]}

        範例：
        >>> generator.filter_homophones(["測試", "側試", "策試", "車試"])
        {"kept": ["測試", "車試"], "filtered": ["側試", "策試"]}
        """
        kept = []
        filtered = []
        seen_pinyins = set()

        for term in term_list:
            pinyin_str = self._get_term_pinyin(term)

            if pinyin_str in seen_pinyins:
                filtered.append(term)
            else:
                kept.append(term)
                seen_pinyins.add(pinyin_str)

        return {"kept": kept, "filtered": filtered}

    # ==========================================
    # 私有方法：拼音處理
    # ==========================================

    def _get_term_pinyin(self, term):
        """取得詞彙的去聲調拼音字串"""
        pinyin_list = pypinyin.lazy_pinyin(term, style=pypinyin.NORMAL)
        return "".join(pinyin_list)

    def _pinyin_to_char(self, pinyin_str):
        """
        將單一拼音串轉回常見漢字
        取前 2 個高頻字，挑第一個做代表
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

    # ==========================================
    # 私有方法：變體生成
    # ==========================================

    def _apply_special_syllable_variations(self, base_pinyin, potential_pinyins):
        """應用特例音節變體"""
        if base_pinyin in self.config.special_syllable_map:
            for special_p in self.config.special_syllable_map[base_pinyin]:
                potential_pinyins.add(special_p)

    def _apply_initial_fuzzy_variations(self, initial, final, potential_pinyins):
        """應用聲母模糊變體"""
        if initial in self.config.fuzzy_initials_map:
            group = self.config.fuzzy_initials_map[initial]
            for fuzzy_init in self.config.group_to_initials[group]:
                potential_pinyins.add(fuzzy_init + final)

    def _apply_final_fuzzy_variations(self, potential_pinyins):
        """應用韻母模糊變體"""
        current_list = list(potential_pinyins)
        for p in current_list:
            curr_init = pypinyin.pinyin(p, style=pypinyin.INITIALS, strict=False)[0][0]
            curr_final = p[len(curr_init) :]

            for f1, f2 in self.config.fuzzy_finals_pairs:
                if curr_final.endswith(f1):
                    potential_pinyins.add(curr_init + curr_final[: -len(f1)] + f2)
                elif curr_final.endswith(f2):
                    potential_pinyins.add(curr_init + curr_final[: -len(f2)] + f1)

    def _convert_pinyins_to_char_options(self, potential_pinyins, base_pinyin, char):
        """將拼音集合轉換為漢字選項列表"""
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
        給定一個漢字，生成所有可能的近似音變體

        :param char: 單個漢字
        :return: [{"pinyin": "...", "char": "..."}, ...]
        """
        base_pinyin, initial, final = self._extract_pinyin_components(char)
        if base_pinyin is None:
            return [{"pinyin": char, "char": char}]

        potential_pinyins = set()
        potential_pinyins.add(base_pinyin)

        # 優先檢查特例音節
        self._apply_special_syllable_variations(base_pinyin, potential_pinyins)

        # 一般聲母模糊
        self._apply_initial_fuzzy_variations(initial, final, potential_pinyins)

        # 一般韻母模糊
        self._apply_final_fuzzy_variations(potential_pinyins)

        # 轉成文字選項
        return self._convert_pinyins_to_char_options(
            potential_pinyins, base_pinyin, char
        )

    # ==========================================
    # 私有方法：組合與整理
    # ==========================================

    def _generate_char_combinations(self, char_options_list):
        """生成字符組合並去重"""
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
        """添加黏音/懶音短語別名"""
        if term in self.config.sticky_phrase_map:
            alias_texts = [a["text"] for a in aliases]
            for sticky in self.config.sticky_phrase_map[term]:
                if sticky not in alias_texts:
                    aliases.append({"text": sticky, "pinyin": ""})

    def _prepare_final_alias_list(self, term, aliases):
        """準備最終的別名列表"""
        alias_texts = [a["text"] for a in aliases if a["text"] != term]
        alias_texts = sorted(set(alias_texts))
        return [term] + alias_texts


# ==========================================
# 測試範例
# ==========================================
if __name__ == "__main__":
    import json

    generator = FuzzyDictGenerator()

    print("=== 測試 1：生成近似音別名 ===")
    test_terms = ["台北車站", "牛奶", "發揮", "不知道"]
    fuzzy_dict = generator.generate_fuzzy_aliases(test_terms)
    print(json.dumps(fuzzy_dict, indent=2, ensure_ascii=False))
    print()

    print("=== 測試 2：過濾同音詞 ===")
    test_list = ["測試", "側試", "策試", "測是", "車試", "車是"]
    result = generator.filter_homophones(test_list)
    print(json.dumps(result, indent=2, ensure_ascii=False))

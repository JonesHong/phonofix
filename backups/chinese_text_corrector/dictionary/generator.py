"""
模糊詞典生成器模組

提供兩個主要功能:
1. 為關鍵字列表生成所有可能的台式口音/模糊音變體詞典
2. 過濾同音詞,去除拼音重複的詞彙
"""

import itertools
from Pinyin2Hanzi import DefaultDagParams, dag
from hanziconv import HanziConv
from ..core.phonetic_config import PhoneticConfig
from ..core.phonetic_utils import PhoneticUtils


class FuzzyDictionaryGenerator:
    """
    模糊詞典生成器

    功能:
    1. 生成模糊音詞典: 為每個關鍵字生成所有可能的台式口音/模糊音變體
    2. 同音詞過濾: 過濾去聲調拼音完全相同的詞彙,只保留第一個
    """

    def __init__(self, config=None):
        """
        初始化模糊詞典生成器

        Args:
            config: PhoneticConfig 實例,若為 None 則使用預設配置
        """
        self.config = config or PhoneticConfig
        self.utils = PhoneticUtils(config=self.config)
        self.dag_params = DefaultDagParams()

    def _pinyin_to_chars(self, pinyin_str, max_chars=2):
        """
        將單一拼音串轉回常見漢字

        Args:
            pinyin_str: 拼音字串
            max_chars: 最多返回幾個字 (預設 2)

        Returns:
            list: 漢字列表,若無法轉換則返回原拼音
        """
        result = dag(self.dag_params, [pinyin_str], path_num=max_chars)
        chars = []
        if result:
            for item in result:
                chars.append(HanziConv.toTraditional(item.path[0]))
        return chars if chars else [pinyin_str]

    def _get_char_variations(self, char):
        """
        為單個漢字生成所有可能的模糊音變體

        流程:
        1. 取得原始拼音
        2. 根據特例音節/聲母模糊/韻母模糊產生拼音變體
        3. 將每個拼音變體轉回代表漢字

        Args:
            char: 單個漢字

        Returns:
            list: 包含 {"pinyin": 拼音, "char": 字} 的字典列表
        """
        # 取得原拼音
        base_pinyin = self.utils.get_pinyin_string(char)

        # 檢查是否為有效漢字
        if not base_pinyin or not ('\u4e00' <= char <= '\u9fff'):
            return [{"pinyin": char, "char": char}]

        # 生成所有拼音變體 (使用雙向映射)
        potential_pinyins = self.utils.generate_fuzzy_pinyin_variants(
            base_pinyin, bidirectional=True
        )

        # 轉成文字選項
        options = []
        for p in potential_pinyins:
            if p == base_pinyin:
                options.append({"pinyin": p, "char": char})
            else:
                candidate_chars = self._pinyin_to_chars(p)
                repr_char = candidate_chars[0]

                # 過濾非漢字
                if '\u4e00' <= repr_char <= '\u9fff':
                    options.append({"pinyin": p, "char": repr_char})

        return options

    def _generate_char_combinations(self, char_options_list):
        """
        生成字符組合並去重

        使用拼音去重避免組合爆炸

        Args:
            char_options_list: 每個字的選項列表

        Returns:
            tuple: (aliases 列表, 已見過的拼音集合)
        """
        seen_pinyins = set()
        aliases = []

        for combo in itertools.product(*char_options_list):
            alias_text = "".join([item["char"] for item in combo])
            alias_pinyin = "".join([item["pinyin"] for item in combo])

            # 拼音一樣的只留一個代表,避免爆炸
            if alias_pinyin not in seen_pinyins:
                aliases.append({"text": alias_text, "pinyin": alias_pinyin})
                seen_pinyins.add(alias_pinyin)

        return aliases, seen_pinyins

    def _add_sticky_phrase_aliases(self, term, aliases):
        """
        添加黏音/懶音短語別名

        整句對整句的特例

        Args:
            term: 原始詞彙
            aliases: 當前別名列表

        Returns:
            None (直接修改 aliases)
        """
        if term in self.config.STICKY_PHRASE_MAP:
            alias_texts = [a["text"] for a in aliases]
            for sticky in self.config.STICKY_PHRASE_MAP[term]:
                if sticky not in alias_texts:
                    aliases.append({"text": sticky, "pinyin": ""})

    def _prepare_final_alias_list(self, term, aliases):
        """
        準備最終的別名列表

        去重、排序,並將原詞放在第一位

        Args:
            term: 原始詞彙
            aliases: 別名列表

        Returns:
            list: 最終的別名列表 (原詞在首位)
        """
        # 提取文字並去重
        alias_texts = [a["text"] for a in aliases if a["text"] != term]
        alias_texts = sorted(set(alias_texts))

        # 原詞放在第一位
        return [term] + alias_texts

    def generate_fuzzy_dictionary(self, term_list):
        """
        為詞彙列表生成模糊音詞典

        針對每一個詞彙產生一組「台式口音 / 黏音」別名

        Args:
            term_list: 關鍵字列表

        Returns:
            dict: {
                "原詞": ["原詞", "變體1", "變體2", ...],
                ...
            }

        Example:
            >>> generator = FuzzyDictionaryGenerator()
            >>> result = generator.generate_fuzzy_dictionary(["台北車站", "阿斯匹靈"])
            >>> print(result)
            {
                "台北車站": ["台北車站", "台北車佔", "抬北車站", ...],
                "阿斯匹靈": ["阿斯匹靈", "阿思匹靈", ...]
            }
        """
        result = {}

        for term in term_list:
            # 1. 產生每個字的變體
            char_options_list = [self._get_char_variations(char) for char in term]

            # 2. 組合與收斂
            aliases, seen_pinyins = self._generate_char_combinations(
                char_options_list
            )

            # 確保原詞拼音已被記錄
            original_pinyin = self.utils.get_pinyin_string(term)
            seen_pinyins.add(original_pinyin)

            # 3. 黏音 / 懶音短語: 整句對整句的特例
            self._add_sticky_phrase_aliases(term, aliases)

            # 4. 準備最終列表
            result[term] = self._prepare_final_alias_list(term, aliases)

        return result

    def filter_homophones(self, term_list):
        """
        過濾同音詞

        輸入一個詞彙列表,將「去聲調拼音」完全相同的詞進行過濾
        只保留第一個出現的詞

        Args:
            term_list: 詞彙列表

        Returns:
            dict: {
                "kept": [...],      # 保留的詞
                "filtered": [...]   # 過濾掉的同音詞
            }

        Example:
            >>> generator = FuzzyDictionaryGenerator()
            >>> result = generator.filter_homophones(["測試", "側試", "策試", "車試"])
            >>> print(result)
            {
                "kept": ["測試", "車試"],
                "filtered": ["側試", "策試"]
            }
        """
        kept = []
        filtered = []
        seen_pinyins = set()

        for term in term_list:
            # 取得去聲調拼音
            pinyin_str = self.utils.get_pinyin_string(term)

            if pinyin_str in seen_pinyins:
                # 拼音已存在,歸類為過濾掉的
                filtered.append(term)
            else:
                # 新拼音,保留
                kept.append(term)
                seen_pinyins.add(pinyin_str)

        return {"kept": kept, "filtered": filtered}

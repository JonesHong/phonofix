"""
中文模糊變體生成器

負責為專有名詞自動生成可能的 ASR 錯誤變體 (同音字/近音字)。
"""

import itertools
from Pinyin2Hanzi import DefaultDagParams, dag
from hanziconv import HanziConv
from .config import ChinesePhoneticConfig
from .utils import ChinesePhoneticUtils


class ChineseFuzzyGenerator:
    """
    中文模糊變體生成器

    功能:
    - 根據輸入的專有名詞，生成其可能的發音變體
    - 利用 Pinyin2Hanzi 庫反查同音字
    - 考慮聲母/韻母的模糊音規則 (如 z/zh, in/ing)
    - 用於擴充修正器的比對目標，提高召回率
    """

    def __init__(self, config=None):
        self.config = config or ChinesePhoneticConfig
        self.utils = ChinesePhoneticUtils(config=self.config)
        self.dag_params = DefaultDagParams()

    def _pinyin_to_chars(self, pinyin_str, max_chars=2):
        """
        將拼音轉換為可能的漢字 (同音字反查)

        使用 Pinyin2Hanzi 庫的 DAG (有向無環圖) 演算法找出最可能的漢字。
        
        Args:
            pinyin_str: 拼音字串 (如 "zhong")
            max_chars: 最多返回幾個候選字

        Returns:
            List[str]: 候選漢字列表 (繁體)
            範例: "zhong" -> ["中", "重"]
        """
        # 使用 DAG 演算法查詢拼音對應的漢字路徑
        result = dag(self.dag_params, [pinyin_str], path_num=max_chars)
        chars = []
        if result:
            for item in result:
                # 將簡體結果轉換為繁體
                # item.path[0] 是最可能的單字
                chars.append(HanziConv.toTraditional(item.path[0]))
        # 若查無結果，返回原始拼音
        return chars if chars else [pinyin_str]

    def _get_char_variations(self, char):
        """
        取得單個漢字的所有模糊音變體

        流程:
        1. 取得漢字的標準拼音
        2. 生成該拼音的所有模糊變體 (如 z -> zh, in -> ing)
        3. 將模糊拼音反查回代表性漢字

        Args:
            char: 輸入漢字 (如 "中")

        Returns:
            List[Dict]: 變體列表，每個元素包含 {"pinyin": 拼音, "char": 代表字}
            範例: "中" (zhong) -> 
            [
                {"pinyin": "zhong", "char": "中"}, 
                {"pinyin": "zong", "char": "宗"}  (假設 z/zh 模糊)
            ]
        """
        base_pinyin = self.utils.get_pinyin_string(char)
        # 非中文字符直接返回原樣
        if not base_pinyin or not ('\u4e00' <= char <= '\u9fff'):
            return [{"pinyin": char, "char": char}]

        # 生成所有可能的模糊拼音
        potential_pinyins = self.utils.generate_fuzzy_pinyin_variants(
            base_pinyin, bidirectional=True
        )

        options = []
        for p in potential_pinyins:
            if p == base_pinyin:
                # 原始拼音對應原始字符
                options.append({"pinyin": p, "char": char})
            else:
                # 模糊拼音需要反查一個代表字，以便後續組合成詞
                # 這裡只取第一個最可能的字作為代表
                candidate_chars = self._pinyin_to_chars(p)
                repr_char = candidate_chars[0]
                if '\u4e00' <= repr_char <= '\u9fff':
                    options.append({"pinyin": p, "char": repr_char})
        return options

    def _generate_char_combinations(self, char_options_list):
        """
        生成所有字符變體的排列組合

        Args:
            char_options_list: 每個位置的字符變體列表
            範例: [
                [{"char": "台", "pinyin": "tai"}], 
                [{"char": "積", "pinyin": "ji"}, {"char": "基", "pinyin": "ji"}]
            ]

        Returns:
            List[str]: 組合後的詞彙列表
            範例: ["台積", "台基"]
        """
        seen_pinyins = set()
        combinations = []
        
        # 使用 itertools.product 進行笛卡兒積組合
        for combo in itertools.product(*char_options_list):
            word = "".join([item["char"] for item in combo])
            pinyin = "".join([item["pinyin"] for item in combo])
            
            # 避免重複的拼音組合 (不同的字但拼音相同視為同一種模糊變體)
            if pinyin not in seen_pinyins:
                combinations.append(word)
                seen_pinyins.add(pinyin)
        return combinations

    def _add_sticky_phrase_aliases(self, term, aliases):
        """
        添加黏音/懶音短語別名

        整句對整句的特例，處理如 "不知道" -> "不道" 這種非單字對應的變體。

        Args:
            term: 原始詞彙
            aliases: 當前別名列表 (會被直接修改)

        Returns:
            None
        """
        if term in self.config.STICKY_PHRASE_MAP:
            # 取得目前已有的變體文字，避免重複
            alias_texts = [a if isinstance(a, str) else a.get("text", "") for a in aliases]
            
            for sticky in self.config.STICKY_PHRASE_MAP[term]:
                if sticky not in alias_texts:
                    # 黏音通常沒有標準拼音對應，或拼音不重要，故只存文字
                    # 若 aliases 是字串列表，直接 append
                    # 若 aliases 是 dict 列表 (舊版邏輯)，則 append dict
                    # 這裡配合 generate_fuzzy_variants 返回字串列表的邏輯
                    aliases.append(sticky)

    def _prepare_final_alias_list(self, term, aliases):
        """
        準備最終的別名列表

        去重、排序,並將原詞放在第一位

        Args:
            term: 原始詞彙
            aliases: 別名列表 (字串列表)

        Returns:
            list: 最終的別名列表 (原詞在首位)
        """
        # 移除原詞 (稍後加回第一位) 並去重
        unique_aliases = set(aliases)
        if term in unique_aliases:
            unique_aliases.remove(term)
            
        sorted_aliases = sorted(list(unique_aliases))

        # 原詞放在第一位
        return [term] + sorted_aliases

    def generate_variants(self, term):
        """
        為輸入詞彙生成模糊變體列表

        支援兩種輸入模式:
        1. 單一詞彙 (str): 返回該詞彙的變體列表 (List[str])
        2. 詞彙列表 (List[str]): 返回詞典 (Dict[str, List[str]])

        Args:
            term: 輸入詞彙 (str) 或 詞彙列表 (List[str])

        Returns:
            List[str] or Dict[str, List[str]]: 視輸入型別而定
        """
        # 模式 2: 處理詞彙列表
        if isinstance(term, list):
            result = {}
            for t in term:
                result[t] = self.generate_variants(t)
            return result

        # 模式 1: 處理單一詞彙
        # 1. 對詞彙中的每個字，生成其模糊音變體 (字級別)
        char_options_list = []
        for char in term:
            char_options_list.append(self._get_char_variations(char))
        
        # 2. 組合所有字的變體，產生新的詞彙 (詞級別)
        variants = self._generate_char_combinations(char_options_list)
        
        # 3. 處理黏音/懶音 (整詞特例)
        self._add_sticky_phrase_aliases(term, variants)
        
        # 4. 最終整理 (去重、排序、原詞置頂)
        final_variants = self._prepare_final_alias_list(term, variants)
            
        return final_variants

    def filter_homophones(self, term_list):
        """
        過濾同音詞

        輸入一個詞彙列表,將「去聲調拼音」完全相同的詞進行過濾
        只保留第一個出現的詞。這在處理大量相似詞彙時很有用，
        可以避免詞典過度膨脹。

        Args:
            term_list: 詞彙列表 (如 ["測試", "側試", "策試"])

        Returns:
            dict: {
                "kept": [...],      # 保留的詞 (如 ["測試"])
                "filtered": [...]   # 過濾掉的同音詞 (如 ["側試", "策試"])
            }
        """
        kept = []
        filtered = []
        seen_pinyins = set()

        for term in term_list:
            # 取得去聲調拼音 (如 "測試" -> "ceshi")
            pinyin_str = self.utils.get_pinyin_string(term)

            if pinyin_str in seen_pinyins:
                # 拼音已存在,歸類為過濾掉的
                filtered.append(term)
            else:
                # 新拼音,保留
                kept.append(term)
                seen_pinyins.add(pinyin_str)

        return {"kept": kept, "filtered": filtered}

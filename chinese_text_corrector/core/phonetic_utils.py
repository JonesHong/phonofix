"""
中文拼音工具函數模組

提供拼音相關的通用工具函數,包括:
- 拼音提取與轉換
- 聲母韻母分離
- 模糊音匹配檢查
- 拼音相似度計算
"""

import pypinyin
import re
from .phonetic_config import PhoneticConfig


class PhoneticUtils:
    """拼音工具類別 - 提供拼音處理的通用函數"""

    def __init__(self, config=None):
        """
        初始化拼音工具

        Args:
            config: PhoneticConfig 實例,若為 None 則使用預設配置
        """
        self.config = config or PhoneticConfig
        self.group_to_initials = self.config.build_group_to_initials_map()

    @staticmethod
    def contains_english(text):
        """
        檢查字串是否包含英文字母

        Args:
            text: 要檢查的字串

        Returns:
            bool: 是否包含英文字母
        """
        return bool(re.search(r"[a-zA-Z]", text))

    @staticmethod
    def get_pinyin(text, style=pypinyin.NORMAL):
        """
        取得文字的拼音 (去聲調)

        Args:
            text: 輸入文字
            style: pypinyin 樣式,預設為 NORMAL (去聲調)

        Returns:
            list: 拼音列表
        """
        return pypinyin.lazy_pinyin(text, style=style)

    @staticmethod
    def get_pinyin_string(text):
        """
        取得文字的拼音字串 (去聲調,小寫,連接)

        Args:
            text: 輸入文字

        Returns:
            str: 拼音字串
        """
        pinyin_list = pypinyin.lazy_pinyin(text, style=pypinyin.NORMAL)
        return "".join(pinyin_list).lower()

    @staticmethod
    def extract_initial_final(pinyin_str):
        """
        從拼音字串中提取聲母和韻母 (使用規則匹配)

        Args:
            pinyin_str: 拼音字串

        Returns:
            tuple: (聲母, 韻母)
        """
        if not pinyin_str:
            return "", ""

        # 定義所有可能的聲母 (按長度降序排列,優先匹配長的)
        initials = [
            'zh', 'ch', 'sh',  # 捲舌音 (3個字符優先)
            'b', 'p', 'm', 'f', 'd', 't', 'n', 'l',
            'g', 'k', 'h', 'j', 'q', 'x',
            'z', 'c', 's', 'r', 'y', 'w'
        ]

        # 嘗試匹配聲母
        for initial in initials:
            if pinyin_str.startswith(initial):
                final = pinyin_str[len(initial):]
                return initial, final

        # 沒有聲母,整個是韻母
        return "", pinyin_str

    def is_fuzzy_initial_match(self, init1_list, init2_list):
        """
        檢查兩個聲母列表是否模糊匹配

        允許的模糊對應:
        - z=zh, c=ch, s=sh (捲舌音)
        - n=l (n/l 不分)
        - r=l (r/l 混淆)
        - f=h (f/h 混淆)

        Args:
            init1_list: 第一個聲母列表
            init2_list: 第二個聲母列表

        Returns:
            bool: 是否模糊匹配
        """
        if len(init1_list) != len(init2_list):
            return False

        for i1, i2 in zip(init1_list, init2_list):
            if i1 == i2:
                continue

            # 若含有英文聲母,必須完全一致,不允許模糊
            if self.contains_english(str(i1)) or self.contains_english(str(i2)):
                return False

            # 檢查是否屬於同一模糊群組
            group1 = self.config.FUZZY_INITIALS_MAP.get(i1)
            group2 = self.config.FUZZY_INITIALS_MAP.get(i2)
            if group1 and group2 and group1 == group2:
                continue

            return False

        return True

    def check_finals_fuzzy_match(self, pinyin1, pinyin2):
        """
        檢查兩個拼音是否可能因韻母混淆而匹配

        例如: xian <-> xiang, guan <-> guang, xue <-> xie

        Args:
            pinyin1: 第一個拼音
            pinyin2: 第二個拼音

        Returns:
            bool: 是否韻母模糊匹配
        """
        if pinyin1 == pinyin2:
            return True

        # 提取聲母和韻母
        init1, final1 = self.extract_initial_final(pinyin1)
        init2, final2 = self.extract_initial_final(pinyin2)

        # 聲母必須相同或模糊匹配
        if init1 != init2:
            group1 = self.config.FUZZY_INITIALS_MAP.get(init1)
            group2 = self.config.FUZZY_INITIALS_MAP.get(init2)
            if not (group1 and group2 and group1 == group2):
                return False

        if final1 == final2:
            return True

        # 檢查韻母是否在模糊對應表中
        for f1, f2 in self.config.FUZZY_FINALS_PAIRS:
            if (final1.endswith(f1) and final2.endswith(f2)) or (
                final1.endswith(f2) and final2.endswith(f1)
            ):
                # 檢查去掉尾綴後的部分是否相同
                prefix1 = (
                    final1[: -len(f1)] if final1.endswith(f1) else final1[: -len(f2)]
                )
                prefix2 = (
                    final2[: -len(f2)] if final2.endswith(f2) else final2[: -len(f1)]
                )
                if prefix1 == prefix2:
                    return True

        return False

    def check_special_syllable_match(
        self, pinyin1, pinyin2, bidirectional=False
    ):
        """
        檢查兩個拼音是否在特例音節映射表中

        例如: fa <-> hua, xue <-> xie, ran <-> lan

        Args:
            pinyin1: 第一個拼音
            pinyin2: 第二個拼音
            bidirectional: 是否使用雙向映射 (預設 False,使用單向映射)

        Returns:
            bool: 是否特例音節匹配
        """
        if pinyin1 == pinyin2:
            return True

        # 選擇使用單向或雙向映射
        syllable_map = (
            self.config.SPECIAL_SYLLABLE_MAP_BIDIRECTIONAL
            if bidirectional
            else self.config.SPECIAL_SYLLABLE_MAP_UNIDIRECTIONAL
        )

        # 檢查 pinyin1 -> pinyin2
        if pinyin1 in syllable_map:
            if pinyin2 in syllable_map[pinyin1]:
                return True

        # 如果使用雙向映射,也檢查 pinyin2 -> pinyin1
        if bidirectional and pinyin2 in syllable_map:
            if pinyin1 in syllable_map[pinyin2]:
                return True

        return False

    def generate_fuzzy_pinyin_variants(self, pinyin_str, bidirectional=True):
        """
        為單個拼音生成所有可能的模糊音變體

        Args:
            pinyin_str: 原始拼音
            bidirectional: 是否使用雙向特例音節映射

        Returns:
            set: 所有可能的拼音變體集合
        """
        variants = {pinyin_str}

        # 1. 檢查特例音節 (優先)
        syllable_map = (
            self.config.SPECIAL_SYLLABLE_MAP_BIDIRECTIONAL
            if bidirectional
            else self.config.SPECIAL_SYLLABLE_MAP_UNIDIRECTIONAL
        )

        if pinyin_str in syllable_map:
            for variant in syllable_map[pinyin_str]:
                variants.add(variant)

        # 2. 提取聲母和韻母
        initial, final = self.extract_initial_final(pinyin_str)

        # 3. 聲母模糊變體
        if initial in self.config.FUZZY_INITIALS_MAP:
            group = self.config.FUZZY_INITIALS_MAP[initial]
            for fuzzy_init in self.group_to_initials[group]:
                variants.add(fuzzy_init + final)

        # 4. 韻母模糊變體
        current_variants = list(variants)
        for p in current_variants:
            curr_init, curr_final = self.extract_initial_final(p)

            for f1, f2 in self.config.FUZZY_FINALS_PAIRS:
                if curr_final.endswith(f1):
                    variants.add(curr_init + curr_final[: -len(f1)] + f2)
                elif curr_final.endswith(f2):
                    variants.add(curr_init + curr_final[: -len(f2)] + f1)

        return variants

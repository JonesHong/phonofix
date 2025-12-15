"""
中文語音工具模組

提供底層的拼音處理、模糊音判斷與字串操作工具函數。

注意：拼音轉換已統一由 `ChinesePhoneticBackend` 管理，本模組不再直接依賴 pypinyin。
"""

import re

from phonofix.backend import ChinesePhoneticBackend, get_chinese_backend

from .config import ChinesePhoneticConfig

class ChinesePhoneticUtils:
    """
    中文語音工具類別

    功能:
    - 封裝 pypinyin 的調用
    - 實作聲母 (Initials) 與韻母 (Finals) 的提取與比對
    - 實作模糊音判斷邏輯 (如捲舌音/非捲舌音, 前後鼻音)
    - 處理特殊音節映射 (如 hua <-> fa)
    """

    def __init__(self, config=None, backend: ChinesePhoneticBackend | None = None):
        """
        初始化中文語音工具。

        Args:
            config: 拼音設定（未提供則使用預設 ChinesePhoneticConfig）
            backend: 可選 backend（未提供則取得中文 backend 單例）

        注意：
        - 本工具類別不直接 import pypinyin；拼音計算由 backend 負責
        """
        self.config = config or ChinesePhoneticConfig
        self.group_to_initials = self.config.build_group_to_initials_map()
        self._backend = backend or get_chinese_backend()

    @staticmethod
    def contains_english(text):
        """
        判斷字串中是否包含英文字母。

        用途：
        - 中文文本常混入英文縮寫（例如 ICU、PCN），某些規則需要先做分流或跳過
        """
        return bool(re.search(r"[a-zA-Z]", text))

    def get_pinyin_string(self, text: str) -> str:
        """取得文本的拼音字串（無聲調、小寫，委派給 backend 快取）。"""
        return self._backend.to_phonetic(text)

    @staticmethod
    def extract_initial_final(pinyin_str):
        """
        提取拼音的聲母與韻母

        Args:
            pinyin_str: 拼音字串 (如 "zhang")

        Returns:
            (str, str): (聲母, 韻母)
            範例: "zhang" -> ("zh", "ang"), "an" -> ("", "an")
        """
        if not pinyin_str:
            return "", ""
        # 聲母列表 (注意順序: 雙字符聲母優先匹配)
        initials = [
            'zh', 'ch', 'sh',
            'b', 'p', 'm', 'f', 'd', 't', 'n', 'l',
            'g', 'k', 'h', 'j', 'q', 'x',
            'z', 'c', 's', 'r', 'y', 'w'
        ]
        for initial in initials:
            if pinyin_str.startswith(initial):
                final = pinyin_str[len(initial):]
                return initial, final
        # 若無匹配聲母，則視為零聲母，整個字串為韻母
        return "", pinyin_str

    def is_fuzzy_initial_match(self, init1_list, init2_list):
        """
        判斷兩個聲母列表是否模糊匹配

        Args:
            init1_list: 第一個聲母列表
            init2_list: 第二個聲母列表

        Returns:
            bool: 是否匹配
        """
        if len(init1_list) != len(init2_list):
            return False
        for i1, i2 in zip(init1_list, init2_list):
            if i1 == i2:
                continue
            # 檢查是否屬於同一模糊音群組
            # 範例: i1="z", i2="zh" -> 兩者皆屬 "z_group" -> 匹配
            group1 = self.config.FUZZY_INITIALS_MAP.get(i1)
            group2 = self.config.FUZZY_INITIALS_MAP.get(i2)
            if group1 and group2 and group1 == group2:
                continue
            return False
        return True

    def check_finals_fuzzy_match(self, pinyin1, pinyin2):
        """
        檢查兩個拼音是否韻母模糊匹配 (同時考慮聲母是否相容)

        邏輯:
        1. 若完全相同 -> True
        2. 檢查聲母是否相同或模糊匹配 (若聲母不合，韻母再像也沒用)
        3. 檢查韻母是否完全相同
        4. 檢查韻母是否在模糊對列表中 (如 in <-> ing)

        Args:
            pinyin1: 第一個拼音
            pinyin2: 第二個拼音

        Returns:
            bool: 是否匹配
        """
        if pinyin1 == pinyin2:
            return True

        init1, final1 = self.extract_initial_final(pinyin1)
        init2, final2 = self.extract_initial_final(pinyin2)

        # 1. 檢查聲母相容性
        if init1 != init2:
            group1 = self.config.FUZZY_INITIALS_MAP.get(init1)
            group2 = self.config.FUZZY_INITIALS_MAP.get(init2)
            # 若聲母不同且不屬於同一模糊群組，則判定為不匹配
            if not (group1 and group2 and group1 == group2):
                return False

        # 2. 檢查韻母
        if final1 == final2:
            return True

        # 3. 檢查韻母模糊對
        # 範例: final1="ing", final2="in", pair=("in", "ing")
        for f1, f2 in self.config.FUZZY_FINALS_PAIRS:
            if (final1.endswith(f1) and final2.endswith(f2)) or (
                final1.endswith(f2) and final2.endswith(f1)
            ):
                # 確保移除模糊後綴後的前綴部分一致
                # 範例: "ying" vs "yin" -> 前綴 "y" == "y" -> 匹配
                # 反例: "yang" vs "yin" -> 前綴 "y" != "y" -> 不匹配 (雖然 ang/in 沒在 pair 中，但邏輯通用)
                prefix1 = final1[: -len(f1)] if final1.endswith(f1) else final1[: -len(f2)]
                prefix2 = final2[: -len(f2)] if final2.endswith(f2) else final2[: -len(f1)]
                if prefix1 == prefix2:
                    return True
        return False

    def check_special_syllable_match(self, pinyin1, pinyin2, bidirectional=False):
        """
        檢查特殊音節映射 (整音節模糊匹配)

        Args:
            pinyin1: 第一個拼音
            pinyin2: 第二個拼音
            bidirectional: 是否使用雙向映射表

        Returns:
            bool: 是否匹配
        """
        if pinyin1 == pinyin2:
            return True
        syllable_map = (
            self.config.SPECIAL_SYLLABLE_MAP_BIDIRECTIONAL
            if bidirectional
            else self.config.SPECIAL_SYLLABLE_MAP_UNIDIRECTIONAL
        )
        # 檢查 pinyin1 -> pinyin2 的映射
        # 範例: pinyin1="hua", map["hua"]=["fa"] -> 若 pinyin2="fa" 則匹配
        if pinyin1 in syllable_map:
            if pinyin2 in syllable_map[pinyin1]:
                return True
        # 若雙向，檢查 pinyin2 -> pinyin1 的映射
        if bidirectional and pinyin2 in syllable_map:
            if pinyin1 in syllable_map[pinyin2]:
                return True
        return False

    def generate_fuzzy_pinyin_variants(self, pinyin_str, bidirectional=True):
        """
        生成拼音的所有模糊變體

        Args:
            pinyin_str: 原始拼音
            bidirectional: 是否使用雙向映射

        Returns:
            set: 模糊拼音變體集合
        """
        variants = {pinyin_str}

        # 1. 加入特殊音節映射的變體
        # 範例: "hua" -> 加入 "fa"
        syllable_map = (
            self.config.SPECIAL_SYLLABLE_MAP_BIDIRECTIONAL
            if bidirectional
            else self.config.SPECIAL_SYLLABLE_MAP_UNIDIRECTIONAL
        )
        if pinyin_str in syllable_map:
            for variant in syllable_map[pinyin_str]:
                variants.add(variant)

        # 2. 加入聲母模糊變體
        # 範例: "zhang" (init="zh", final="ang") -> 加入 "z" + "ang" = "zang"
        initial, final = self.extract_initial_final(pinyin_str)

        if initial in self.config.FUZZY_INITIALS_MAP:
            group = self.config.FUZZY_INITIALS_MAP[initial]
            for fuzzy_init in self.group_to_initials[group]:
                variants.add(fuzzy_init + final)

        current_variants = list(variants)
        for p in current_variants:
            curr_init, curr_final = self.extract_initial_final(p)
            for f1, f2 in self.config.FUZZY_FINALS_PAIRS:
                if curr_final.endswith(f1):
                    variants.add(curr_init + curr_final[: -len(f1)] + f2)
                elif curr_final.endswith(f2):
                    variants.add(curr_init + curr_final[: -len(f2)] + f1)
        return variants

    def are_fuzzy_similar(self, pinyin1, pinyin2):
        """
        判斷兩個拼音是否可視為模糊相似。

        說明：
        - 這個方法提供較高層的「是否相似」判斷，供候選生成/計分使用
        - 目前策略：韻母/聲母模糊 + 特殊音節映射任一命中即視為相似
        """
        return self.check_finals_fuzzy_match(pinyin1, pinyin2) or \
               self.check_special_syllable_match(pinyin1, pinyin2)

"""
中文文本校正器 (Chinese Text Corrector)

統一接口，整合詞典生成和文本修正功能
"""

import pypinyin
import Levenshtein
import re
from phonetic_config import PhoneticConfig
from fuzzy_dict_generator import FuzzyDictGenerator

# 從 corrector_v2.py 導入核心糾錯器
from corrector_v2 import ContextAwareCorrector


class ChineseTextCorrector:
    """
    中文文本校正器（主類別）

    整合詞典生成和文本修正功能，提供統一接口
    """

    def __init__(self, enable_sticky_phrases=True):
        """
        初始化文本校正器

        :param enable_sticky_phrases: 是否啟用黏音/懶音短語映射
        """
        self.config = PhoneticConfig(enable_sticky_phrases)
        self.dict_generator = FuzzyDictGenerator(self.config)

    # ==========================================
    # 公開方法：詞典管理
    # ==========================================

    def generate_fuzzy_aliases(self, term_list, include_sticky=True):
        """
        為詞彙列表生成近似音別名

        :param term_list: 關鍵字列表
        :param include_sticky: 是否包含黏音短語
        :return: {原詞: [原詞, 別名1, 別名2, ...]}
        """
        return self.dict_generator.generate_fuzzy_aliases(term_list, include_sticky)

    def filter_homophones(self, term_list):
        """
        過濾同音詞，只保留第一個出現的詞

        :param term_list: 詞彙列表
        :return: {"kept": [...], "filtered": [...]}
        """
        return self.dict_generator.filter_homophones(term_list)

    # ==========================================
    # 公開方法：文本修正
    # ==========================================

    def correct(self, text, term_mapping, exclusions=None, use_canonical=True):
        """
        執行文本糾錯

        :param text: 待修正文本
        :param term_mapping: 修正詞典，支持三種格式：
            1. 簡化版：{"標準詞": ["別名1", "別名2"]}
            2. 完整版：{"標準詞": {"aliases": [...], "keywords": [...], "weight": 0.5}}
        :param exclusions: 豁免清單
        :param use_canonical: True=修正為標準詞, False=修正為別名
        :return: 修正後的文本
        """
        # 使用 corrector_v2 的 ContextAwareCorrector
        corrector = ContextAwareCorrector(term_mapping, exclusions, use_canonical)
        return corrector.correct(text)

    def auto_correct(self, text, keywords, exclusions=None, auto_generate_aliases=True):
        """
        自動生成詞典並修正文本（便利方法）

        :param text: 待修正文本
        :param keywords: 支持三種格式：
            1. 列表：["台北車站", "牛奶"]
            2. 簡單詞典：{"台北車站": ["北車"], "牛奶": ["流奶"]}
            3. 完整詞典：{"台北車站": {"aliases": ["北車"], "keywords": ["捷運"], "weight": 0.5}}
        :param exclusions: 豁免清單
        :param auto_generate_aliases: 是否自動生成近似音別名
        :return: 修正後的文本

        範例：
        >>> # 格式 1：自動生成別名
        >>> corrector.auto_correct("我在北車買了流奶", ["台北車站", "牛奶"])

        >>> # 格式 2：手動指定別名
        >>> corrector.auto_correct("我在北車買了流奶", {
        ...     "台北車站": ["北車"],
        ...     "牛奶": ["流奶"]
        ... }, auto_generate_aliases=False)

        >>> # 格式 3：完整配置（支持 weight 和 keywords）
        >>> corrector.auto_correct("我在北車買了流奶", {
        ...     "台北車站": {
        ...         "aliases": ["北車"],
        ...         "keywords": ["捷運", "車站"],
        ...         "weight": 0.5
        ...     }
        ... })
        """
        # 統一格式轉換
        term_mapping = self._normalize_term_mapping(keywords, auto_generate_aliases)

        # 委託給 correct
        return self.correct(text, term_mapping, exclusions)

    # ==========================================
    # 私有方法：格式轉換
    # ==========================================

    def _normalize_term_mapping(self, input_data, auto_generate_aliases=False):
        """
        將各種格式的輸入統一轉換為標準詞典格式

        :param input_data: 輸入（列表或詞典）
        :param auto_generate_aliases: 是否自動生成近似音別名
        :return: 標準化的詞典
        """
        normalized = {}

        # 情況 1：列表輸入
        if isinstance(input_data, list):
            for term in input_data:
                if auto_generate_aliases:
                    # 生成近似音別名
                    fuzzy_dict = self.generate_fuzzy_aliases([term])
                    aliases = fuzzy_dict.get(term, [term])
                    # 移除標準詞本身
                    if term in aliases:
                        aliases.remove(term)
                else:
                    aliases = []

                normalized[term] = {"aliases": aliases, "keywords": [], "weight": 0.0}

        # 情況 2 & 3：詞典輸入
        elif isinstance(input_data, dict):
            for canonical, data in input_data.items():
                # 解析原始數據
                if isinstance(data, list):
                    # 簡單格式
                    original_aliases = data
                    keywords = []
                    weight = 0.0
                else:
                    # 完整格式
                    original_aliases = data.get("aliases", [])
                    keywords = data.get("keywords", [])
                    weight = data.get("weight", 0.0)

                # 是否擴展別名
                if auto_generate_aliases:
                    fuzzy_dict = self.generate_fuzzy_aliases([canonical])
                    fuzzy_aliases = fuzzy_dict.get(canonical, [canonical])
                    # 移除標準詞本身
                    if canonical in fuzzy_aliases:
                        fuzzy_aliases.remove(canonical)
                    # 合併原始別名和生成的別名
                    all_aliases = list(set(original_aliases + fuzzy_aliases))
                else:
                    all_aliases = original_aliases

                normalized[canonical] = {
                    "aliases": all_aliases,
                    "keywords": keywords,
                    "weight": weight,
                }

        return normalized


# ==========================================
# 測試範例
# ==========================================
if __name__ == "__main__":
    import json

    corrector = ChineseTextCorrector()

    print("=== 測試 1：詞典生成 ===")
    fuzzy_dict = corrector.generate_fuzzy_aliases(["台北車站", "牛奶"])
    print(json.dumps(fuzzy_dict, indent=2, ensure_ascii=False)[:300] + "...")
    print()

    print("=== 測試 2：文本修正（簡單格式）===")
    result = corrector.correct(
        "我在北車買了流奶", {"台北車站": ["北車"], "牛奶": ["流奶"]}
    )
    print(f"結果: {result}")
    print()

    print("=== 測試 3：auto_correct（完整格式 + 擴展別名）===")
    result = corrector.auto_correct(
        "我在北車買了流奶",
        {
            "台北車站": {
                "aliases": ["北車"],
                "keywords": ["捷運", "車站"],
                "weight": 0.5,
            },
            "牛奶": {"aliases": ["流奶"], "keywords": [], "weight": 0.0},
        },
        auto_generate_aliases=True,
    )
    print(f"結果: {result}")

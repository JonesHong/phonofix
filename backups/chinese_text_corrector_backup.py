"""
中文文本校正器 (Chinese Text Corrector)

統一接口，整合詞典生成和文本修正功能：
- 生成近似音別名詞典
- 基於拼音相似度的智能糾錯
- 上下文感知的文本修正
"""

import pypinyin
import Levenshtein
import re
from phonetic_config import PhoneticConfig
from fuzzy_dict_generator import FuzzyDictGenerator


class ChineseTextCorrector:
    """
    中文文本校正器（主類別）

    提供完整的中文文本處理功能：
    1. 詞典管理：生成近似音別名、過濾同音詞
    2. 文本修正：基於拼音相似度的智能糾錯
    """

    def __init__(self, enable_sticky_phrases=True):
        """
        初始化文本校正器

        :param enable_sticky_phrases: 是否啟用黏音/懶音短語映射
        """
        # 初始化配置
        self.config = PhoneticConfig(enable_sticky_phrases)

        # 初始化詞典生成器
        self.dict_generator = FuzzyDictGenerator(self.config)

    # ==========================================
    # 公開方法：詞典管理（委託給 FuzzyDictGenerator）
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
        :param term_mapping: 修正詞典，格式：
            {
                "標準詞": ["別名1", "別名2"],  # 簡化版
                或
                "標準詞": {
                    "aliases": ["別名1", "別名2"],
                    "keywords": ["關鍵字1", "關鍵字2"],
                    "weight": 0.5
                }  # 完整版
            }
        :param exclusions: 豁免清單，這些詞不會被修正
        :param use_canonical: True=修正為標準詞(key), False=修正為別名
        :return: 修正後的文本
        """
        # 建構搜尋索引
        search_index = self._build_search_index(term_mapping)

        # 建立豁免詞保護遮罩
        exclusion_set = set(exclusions) if exclusions else set()
        protected_indices = self._build_protection_mask(text, exclusion_set)

        # 找出所有候選修正項目
        candidates = self._find_candidates(
            text, search_index, protected_indices, exclusion_set
        )

        # 解決衝突
        final_candidates = self._resolve_conflicts(candidates)

    def _build_search_index(self, term_mapping):
        """建構搜尋索引"""
        search_index = []

        for canonical, data in term_mapping.items():
            aliases, keywords, weight = self._parse_term_data(data)
            targets = set(aliases) | {canonical}

            for term in targets:
                index_item = self._create_index_item(term, canonical, keywords, weight)
                search_index.append(index_item)

        # 依照詞長由大到小排序（長詞優先）
        search_index.sort(key=lambda x: x["len"], reverse=True)
        return search_index

    def _parse_term_data(self, data):
        """解析詞庫資料"""
        if isinstance(data, list):
            return data, [], 0.0
        else:
            return (
                data.get("aliases", []),
                data.get("keywords", []),
                data.get("weight", 0.0),
            )

    def _create_index_item(self, term, canonical, keywords, weight):
        """為單一詞彙建立索引項目"""
        pinyin_list = pypinyin.lazy_pinyin(term, style=pypinyin.NORMAL)
        pinyin_str = "".join(pinyin_list).lower()
        initials_list = pypinyin.lazy_pinyin(
            term, style=pypinyin.INITIALS, strict=False
        )

        return {
            "term": term,
            "canonical": canonical,
            "keywords": [k.lower() for k in keywords],
            "weight": weight,
            "pinyin_str": pinyin_str,
            "initials": initials_list,
            "len": len(term),
            "is_mixed": self._contains_english(term),
        }

    # ==========================================
    # 私有方法：保護遮罩
    # ==========================================

    def _build_protection_mask(self, text, exclusions):
        """建立全域保護遮罩"""
        protected_indices = set()
        for exclusion_term in exclusions:
            for match in re.finditer(re.escape(exclusion_term), text):
                for idx in range(match.start(), match.end()):
                    protected_indices.add(idx)
        return protected_indices

    def _is_segment_protected(self, start_idx, word_len, protected_indices):
        """檢查當前片段是否位於保護區"""
        for idx in range(start_idx, start_idx + word_len):
            if idx in protected_indices:
                return True
        return False

    def _is_valid_segment(self, segment):
        """檢查片段是否有效（不含標點符號）"""
        return not bool(re.search(r"[^a-zA-Z0-9\u4e00-\u9fa5]", segment))

    # ==========================================
    # 私有方法：候選搜尋
    # ==========================================

    def _find_candidates(self, text, search_index, protected_indices, exclusions):
        """遍歷搜尋索引，找出所有候選修正項目"""
        text_len = len(text)
        candidates = []

        for item in search_index:
            word_len = item["len"]
            if word_len > text_len:
                continue

            # 滑動視窗掃描
            for i in range(text_len - word_len + 1):
                if self._is_segment_protected(i, word_len, protected_indices):
                    continue

                segment = text[i : i + word_len]

                if not self._is_valid_segment(segment):
                    continue

                if segment in exclusions:
                    continue

                # 絕對匹配
                if segment == item["term"]:
                    candidate = self._process_exact_match(text, i, segment, item)
                    if candidate:
                        candidates.append(candidate)
                    continue

                # 模糊匹配
                candidate = self._process_fuzzy_match(text, i, segment, item)
                if candidate:
                    candidates.append(candidate)

        return candidates

    def _process_exact_match(self, text, start_idx, segment, item):
        """處理絕對匹配"""
        score = 0.0 - item["weight"]

        has_context = self._check_context_bonus(
            text, start_idx, start_idx + item["len"], item["keywords"]
        )
        if has_context:
            score -= 0.5

        return {
            "start": start_idx,
            "end": start_idx + item["len"],
            "original": segment,
            "replacement": item["canonical"],
            "score": score,
            "has_context": has_context,
        }

    def _process_fuzzy_match(self, text, start_idx, segment, item):
        """處理模糊匹配"""
        word_len = item["len"]
        threshold = self._get_dynamic_threshold(word_len, item["is_mixed"])

        # 計算拼音相似度
        window_pinyin_str, error_ratio, is_fuzzy_match = (
            self._calculate_pinyin_similarity(segment, item["pinyin_str"])
        )

        # 韻母模糊或特例音節匹配時放寬門檻
        if is_fuzzy_match:
            threshold = max(threshold, 0.15)

        if error_ratio > threshold:
            return None

        # 聲母檢查
        if not self._check_initials_match(segment, item):
            return None

        # 上下文檢查
        has_context = self._check_context_bonus(
            text, start_idx, start_idx + word_len, item["keywords"]
        )

        # 計算最終分數
        score = error_ratio - item["weight"]
        if has_context:
            score -= 0.5

        # 只有當內容有改變時才加入候選
        if segment == item["canonical"]:
            return None

        return {
            "start": start_idx,
            "end": start_idx + word_len,
            "original": segment,
            "replacement": item["canonical"],
            "score": score,
            "has_context": has_context,
        }

    # ==========================================
    # 私有方法：拼音相似度計算
    # ==========================================

    def _calculate_pinyin_similarity(self, segment, target_pinyin_str):
        """計算拼音相似度（增強版）"""
        window_pinyin_list = pypinyin.lazy_pinyin(segment, style=pypinyin.NORMAL)
        window_pinyin_str = "".join(window_pinyin_list).lower()
        target_pinyin_lower = target_pinyin_str.lower()

        # 檢查特例音節（只對多字詞應用）
        if (
            len(segment) >= 2
            and len(window_pinyin_list) <= 2
            and len(target_pinyin_lower) < 10
        ):
            if self._check_special_syllable_match(
                window_pinyin_str, target_pinyin_lower
            ):
                return window_pinyin_str, 0.0, True

        # 檢查韻母模糊匹配
        if self._check_finals_fuzzy_match(window_pinyin_str, target_pinyin_lower):
            return window_pinyin_str, 0.1, True

        # 計算 Levenshtein 距離
        dist = Levenshtein.distance(window_pinyin_str, target_pinyin_lower)
        max_len = max(len(window_pinyin_str), len(target_pinyin_lower))
        error_ratio = dist / max_len if max_len > 0 else 0

        return window_pinyin_str, error_ratio, False

    def _check_special_syllable_match(self, pinyin1, pinyin2):
        """檢查特例音節匹配"""
        if pinyin1 == pinyin2:
            return True

        if pinyin1 in self.config.special_syllable_map:
            if pinyin2 in self.config.special_syllable_map[pinyin1]:
                return True

        if pinyin2 in self.config.special_syllable_map:
            if pinyin1 in self.config.special_syllable_map[pinyin2]:
                return True

        return False

    def _check_finals_fuzzy_match(self, pinyin1, pinyin2):
        """檢查韻母模糊匹配"""
        if pinyin1 == pinyin2:
            return True

        try:
            init1 = (
                pypinyin.pinyin(pinyin1, style=pypinyin.INITIALS, strict=False)[0][0]
                if pinyin1
                else ""
            )
            init2 = (
                pypinyin.pinyin(pinyin2, style=pypinyin.INITIALS, strict=False)[0][0]
                if pinyin2
                else ""
            )
        except:
            return False

        # 聲母必須相同或模糊匹配
        if init1 != init2:
            group1 = self.config.fuzzy_initials_map.get(init1)
            group2 = self.config.fuzzy_initials_map.get(init2)
            if not (group1 and group2 and group1 == group2):
                return False

        # 提取韻母
        final1 = pinyin1[len(init1) :] if init1 else pinyin1
        final2 = pinyin2[len(init2) :] if init2 else pinyin2

        if final1 == final2:
            return True

        # 檢查韻母是否在模糊對應表中
        for f1, f2 in self.config.fuzzy_finals_pairs:
            if (final1.endswith(f1) and final2.endswith(f2)) or (
                final1.endswith(f2) and final2.endswith(f1)
            ):
                prefix1 = (
                    final1[: -len(f1)] if final1.endswith(f1) else final1[: -len(f2)]
                )
                prefix2 = (
                    final2[: -len(f2)] if final2.endswith(f2) else final2[: -len(f1)]
                )
                if prefix1 == prefix2:
                    return True

        return False

    def _check_initials_match(self, segment, item):
        """檢查聲母匹配（針對短中文詞）"""
        word_len = item["len"]
        if word_len <= 3 and not item["is_mixed"]:
            window_initials = pypinyin.lazy_pinyin(
                segment, style=pypinyin.INITIALS, strict=False
            )
            if not self._is_fuzzy_initial_match(window_initials, item["initials"]):
                return False
        return True

    def _is_fuzzy_initial_match(self, init1_list, init2_list):
        """聲母模糊比對"""
        if len(init1_list) != len(init2_list):
            return False

        for i1, i2 in zip(init1_list, init2_list):
            if i1 == i2:
                continue

            if self._contains_english(str(i1)) or self._contains_english(str(i2)):
                return False

            group1 = self.config.fuzzy_initials_map.get(i1)
            group2 = self.config.fuzzy_initials_map.get(i2)
            if group1 and group2 and group1 == group2:
                continue

            return False

        return True

    # ==========================================
    # 私有方法：上下文檢查
    # ==========================================

    def _check_context_bonus(self, text, start_idx, end_idx, keywords, window_size=10):
        """上下文加分檢查"""
        if not keywords:
            return False

        ctx_start = max(0, start_idx - window_size)
        ctx_end = min(len(text), end_idx + window_size)
        context_text = text[ctx_start:ctx_end].lower()

        for kw in keywords:
            if kw in context_text:
                return True

        return False

    # ==========================================
    # 私有方法：衝突解決與應用
    # ==========================================

    def _resolve_conflicts(self, candidates):
        """衝突解決"""
        candidates.sort(key=lambda x: x["score"])

        final_candidates = []
        for cand in candidates:
            is_conflict = False
            for accepted in final_candidates:
                if max(cand["start"], accepted["start"]) < min(
                    cand["end"], accepted["end"]
                ):
                    is_conflict = True
                    break

            if not is_conflict:
                final_candidates.append(cand)

        return final_candidates

    def _apply_replacements(self, text, final_candidates, use_canonical):
        """替換文字"""
        final_candidates.sort(key=lambda x: x["start"], reverse=True)
        final_text_list = list(text)

        for cand in final_candidates:
            replacement = cand["replacement"] if use_canonical else cand["original"]
            if cand["original"] != replacement:
                tag = "[上下文命中]" if cand.get("has_context") else "[發音修正]"
                print(
                    f"{tag} '{cand['original']}' -> '{replacement}' (Score: {cand['score']:.3f})"
                )
            final_text_list[cand["start"] : cand["end"]] = list(replacement)

        return "".join(final_text_list)

    # ==========================================
    # 輔助方法
    # ==========================================

    def _contains_english(self, text):
        """判斷字串是否包含英文字母"""
        return bool(re.search(r"[a-zA-Z]", text))

    def _get_dynamic_threshold(self, word_len, is_mixed=False):
        """動態決定容錯率"""
        if is_mixed:
            return 0.45
        if word_len <= 2:
            return 0.20
        elif word_len == 3:
            return 0.30
        else:
            return 0.40


# ==========================================
# 測試範例
# ==========================================
if __name__ == "__main__":
    import json

    corrector = ChineseTextCorrector()

    print("=== 測試 1：詞典生成 ===")
    fuzzy_dict = corrector.generate_fuzzy_aliases(["台北車站", "牛奶"])
    print(json.dumps(fuzzy_dict, indent=2, ensure_ascii=False))
    print()

    print("=== 測試 2：文本修正 ===")
    term_mapping = {
        "台北車站": ["北車"],
        "牛奶": ["流奶"],
    }
    text = "我在北車買了流奶"
    result = corrector.correct(text, term_mapping)
    print(f"原句: {text}")
    print(f"結果: {result}")
    print()

    print("=== 測試 3：自動修正 ===")
    text2 = "我在北車買了流奶"
    result2 = corrector.auto_correct(text2, ["台北車站", "牛奶"])
    print(f"原句: {text2}")
    print(f"結果: {result2}")

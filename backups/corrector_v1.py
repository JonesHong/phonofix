import pypinyin
import Levenshtein
import re

import pypinyin
import Levenshtein
import re


class ContextAwareCorrector:
    def __init__(self, term_mapping, exclusions=None, use_canonical_normalization=True):
        """
        初始化糾錯器
        :param term_mapping: 詞庫字典，結構支援 aliases (列表), keywords (關鍵字), weight (權重)
        :param exclusions: 豁免清單 (List)，這裡面的詞即使像熱詞也不會被修正
        :param use_canonical_normalization: True=修正為標準詞(key), False=修正為字典中定義的 alias 原詞
        """
        self.use_canonical = use_canonical_normalization
        # 將豁免詞轉為集合，提升查詢速度
        self.exclusions = set(exclusions) if exclusions else set()
        self.search_index = []

        # === 定義聲母模糊對應群組 ===
        # 用於處理捲舌音與非捲舌音的模糊比對 (如 z vs zh)
        self.fuzzy_initials_map = {
            "z": "z_group",
            "zh": "z_group",
            "c": "c_group",
            "ch": "c_group",
            "s": "s_group",
            "sh": "s_group",
        }

        # === 建構搜尋索引 (Search Index) ===
        # 遍歷傳入的 term_mapping，預先計算所有熱詞的拼音與特徵
        for canonical, data in term_mapping.items():
            # [參數解析] 判斷是簡化版(List)還是完整版(Dict)
            if isinstance(data, list):
                aliases = data
                keywords = []
                weight = 0.0  # 簡化版預設權重為 0
            else:
                aliases = data.get("aliases", [])
                keywords = data.get("keywords", [])
                weight = data.get("weight", 0.0)  # 讀取自定義權重

            # 將標準詞(canonical)與別名(aliases)合併為目標集合
            targets = set(aliases) | {canonical}

            for term in targets:
                # 預先計算目標詞的拼音 (不含聲調)
                pinyin_list = pypinyin.lazy_pinyin(term, style=pypinyin.NORMAL)
                # 轉小寫以統一格式 (解決 Python vs python)
                pinyin_str = "".join(pinyin_list).lower()

                # 預先計算聲母 (用於短詞嚴格檢查)
                initials_list = pypinyin.lazy_pinyin(
                    term, style=pypinyin.INITIALS, strict=False
                )

                # 將處理好的資料存入索引
                self.search_index.append(
                    {
                        "term": term,  # 實際詞彙 (如: Pyton)
                        "canonical": canonical,  # 標準詞 (如: Python)
                        "keywords": [k.lower() for k in keywords],  # 上下文關鍵字
                        "weight": weight,  # 優先權重 (越高分越容易被選中)
                        "pinyin_str": pinyin_str,  # 拼音字串 (用於計算編輯距離)
                        "initials": initials_list,  # 聲母列表
                        "len": len(term),  # 字數長度
                        "is_mixed": self._contains_english(term),  # 標記是否混有英文
                    }
                )

        # [排序] 依照詞長由大到小排序 (Greedy Match)
        # 確保長詞優先被比對 (例如 "台北車站" 優先於 "北車")
        self.search_index.sort(key=lambda x: x["len"], reverse=True)

    def _contains_english(self, text):
        """輔助函式：判斷字串是否包含英文字母"""
        return bool(re.search(r"[a-zA-Z]", text))

    def _get_dynamic_threshold(self, word_len, is_mixed=False):
        """
        核心邏輯：動態決定容錯率 (Threshold)
        字數越短，容錯率越低 (必須更像)；混有英文或長詞則容許較高誤差。
        """
        if is_mixed:
            return 0.45  # 英文混用通常容錯較高 (拼音差異大)
        if word_len <= 2:
            return 0.20  # 2字詞必須非常準確
        elif word_len == 3:
            return 0.30
        else:
            return 0.40  # 4字以上寬容度最高

    def _is_fuzzy_initial_match(self, init1_list, init2_list):
        """
        核心邏輯：聲母模糊比對
        檢查兩個聲母列表是否匹配 (允許 z=zh, c=ch, s=sh)。
        英文開頭不進行模糊對應。
        """
        if len(init1_list) != len(init2_list):
            return False
        for i1, i2 in zip(init1_list, init2_list):
            if i1 == i2:
                continue
            # 若含有英文聲母，必須完全一致，不允許模糊
            if self._contains_english(str(i1)) or self._contains_english(str(i2)):
                return False

            # 檢查是否屬於同一模糊群組
            group1 = self.fuzzy_initials_map.get(i1)
            group2 = self.fuzzy_initials_map.get(i2)
            if group1 and group2 and group1 == group2:
                continue
            return False
        return True

    def _check_context_bonus(
        self, full_text, start_idx, end_idx, keywords, window_size=10
    ):
        """
        核心邏輯：上下文加分檢查
        檢查目標詞前後 Window Size 範圍內是否出現指定的 keywords。
        """
        if not keywords:
            return False
        # 計算滑動視窗範圍，防止超出字串邊界
        ctx_start = max(0, start_idx - window_size)
        ctx_end = min(len(full_text), end_idx + window_size)

        context_text = full_text[ctx_start:ctx_end].lower()
        for kw in keywords:
            if kw in context_text:
                return True
        return False

    def correct(self, asr_text):
        """
        主函式：執行文字糾錯
        """
        text_len = len(asr_text)
        candidates = []

        # === 步驟 1: 建立全域保護遮罩 (Global Protection Mask) ===
        # 找出所有 "豁免詞" 在原句中的位置，將這些索引標記為 Protected。
        # 目的：防止長詞豁免中的短詞被誤修 (如 "什麼是" 豁免，防止內部的 "麼是" 被修成 "默示")
        protected_indices = set()
        if self.exclusions:
            for exclusion_term in self.exclusions:
                # 使用 re.escape 避免特殊符號導致 regex 錯誤
                for match in re.finditer(re.escape(exclusion_term), asr_text):
                    for idx in range(match.start(), match.end()):
                        protected_indices.add(idx)

        # === 步驟 2: 遍歷搜尋索引 ===
        for item in self.search_index:
            word_len = item["len"]
            if word_len > text_len:
                continue

            target_pinyin_str = item["pinyin_str"]
            threshold = self._get_dynamic_threshold(word_len, item["is_mixed"])

            # === 步驟 3: 滑動視窗掃描 ===
            for i in range(text_len - word_len + 1):

                # [檢查] 保護區遮罩
                # 如果當前視窗內的任何一個字位於保護區，整段跳過
                is_protected_segment = False
                for idx in range(i, i + word_len):
                    if idx in protected_indices:
                        is_protected_segment = True
                        break
                if is_protected_segment:
                    continue

                original_segment = asr_text[i : i + word_len]

                # [檢查] 垃圾字元過濾
                # 如果片段含有標點符號或非中英數字符，視為無效片段，跳過
                # 這能避免吃到 "。C語" 這種跨標點的錯誤
                if re.search(r"[^a-zA-Z0-9\u4e00-\u9fa5]", original_segment):
                    continue

                # [檢查] 再次確認豁免清單 (雙重保險)
                if original_segment in self.exclusions:
                    continue

                # === 情境 A: 絕對匹配 (Exact Match) ===
                # 如果字串完全等於 term，直接命中，不需要算拼音距離
                if original_segment == item["term"]:
                    final_score = 0.0

                    # [權重應用] 扣除權重 (分數越低越好)
                    final_score -= item["weight"]

                    # 檢查上下文加分
                    has_context = self._check_context_bonus(
                        asr_text, i, i + word_len, item["keywords"]
                    )
                    if has_context:
                        final_score -= 0.5  # 上下文命中獎勵

                    replacement = (
                        item["canonical"] if self.use_canonical else item["term"]
                    )
                    candidates.append(
                        {
                            "start": i,
                            "end": i + word_len,
                            "original": original_segment,
                            "replacement": replacement,
                            "score": final_score,
                            "has_context": has_context,
                        }
                    )
                    continue

                # === 情境 B: 模糊匹配 (Fuzzy Match) ===

                # [關鍵] 局部拼音計算 (Local Pinyin Calculation)
                # 針對當前視窗內的文字即時運算拼音，確保拼音與文字索引 100% 對齊。
                # 解決了全域拼音計算會因為標點符號而錯位的問題。
                window_pinyin_list = pypinyin.lazy_pinyin(
                    original_segment, style=pypinyin.NORMAL
                )
                window_pinyin_str = "".join(window_pinyin_list).lower()

                # 計算 Levenshtein 編輯距離比例
                dist = Levenshtein.distance(window_pinyin_str, target_pinyin_str)
                max_len = max(len(window_pinyin_str), len(target_pinyin_str))
                error_ratio = dist / max_len if max_len > 0 else 0

                if error_ratio <= threshold:
                    # [聲母檢查] 針對短中文詞進行嚴格聲母比對
                    if word_len <= 3 and not item["is_mixed"]:
                        window_initials = pypinyin.lazy_pinyin(
                            original_segment, style=pypinyin.INITIALS, strict=False
                        )
                        if not self._is_fuzzy_initial_match(
                            window_initials, item["initials"]
                        ):
                            continue

                    final_score = error_ratio

                    # [權重應用] 分數越低優先級越高
                    final_score -= item["weight"]

                    has_context = self._check_context_bonus(
                        asr_text, i, i + word_len, item["keywords"]
                    )

                    if has_context:
                        final_score -= 0.5

                    replacement = (
                        item["canonical"] if self.use_canonical else item["term"]
                    )

                    # 只有當內容有改變時才加入候選
                    if original_segment != replacement:
                        candidates.append(
                            {
                                "start": i,
                                "end": i + word_len,
                                "original": original_segment,
                                "replacement": replacement,
                                "score": final_score,
                                "has_context": has_context,
                            }
                        )

        # === 步驟 4: 衝突解決 (Conflict Resolution) ===
        # 依照分數排序 (越低分越好)
        candidates.sort(key=lambda x: x["score"])

        final_candidates = []
        for cand in candidates:
            is_conflict = False
            # 檢查是否與已接受的候選詞位置重疊
            for accepted in final_candidates:
                # 判斷區間重疊邏輯: max(Start1, Start2) < min(End1, End2)
                if max(cand["start"], accepted["start"]) < min(
                    cand["end"], accepted["end"]
                ):
                    is_conflict = True
                    break

            # 若無衝突則接受此修正
            if not is_conflict:
                final_candidates.append(cand)

        # === 步驟 5: 替換文字 ===
        # 從後面對前面進行替換 (Reverse)，避免 index 跑掉
        final_candidates.sort(key=lambda x: x["start"], reverse=True)
        final_text_list = list(asr_text)
        for cand in final_candidates:
            if cand["original"] != cand["replacement"]:
                tag = "[上下文命中]" if cand.get("has_context") else "[發音修正]"
                print(
                    f"{tag} '{cand['original']}' -> '{cand['replacement']}' (Score: {cand['score']:.3f})"
                )
            final_text_list[cand["start"] : cand["end"]] = list(cand["replacement"])

        return "".join(final_text_list)


# ==========================================
# 驗證修正後的結果
# ==========================================

print("=== 情境一：開啟歸一化 (True) ===")
case1_mapping = {
    "台北車站": ["北車", "臺北車站", "台北火車站"],
    "台大醫院": ["台大"],
    "阿斯匹靈": ["二四批林", "阿斯匹林"],
}

case1_exclusion = ["北側", "南側", "東側", "西側"]
# 預期：把所有別名和相近音都改成「台北車站」
c1 = ContextAwareCorrector(case1_mapping, exclusions=case1_exclusion)

# 案例：之前出錯的阿斯匹靈
# 預期：'二四批林' (score較佳) 會贏過 '四批林給' (score較差)
c1_t1 = "醫生開了二四批林給我。"
print(f"原句: {c1_t1}\n結果: {c1.correct(c1_t1)}\n")

# 案例：北側吃字問題
c1_t2_1 = "我們約在北側出口見面。"
print(f"原句: {c1_t2_1}\n結果: {c1.correct(c1_t2_1)}\n")
c1_t2_2 = "我們約在北車的北側出口見面。"
print(f"原句: {c1_t2_2}\n結果: {c1.correct(c1_t2_2)}\n")

# 案例：飛車誤殺測試
c1_t3 = "電影裡的飛車追逐很精彩。"
print(f"原句: {c1_t3}\n結果: {c1.correct(c1_t3)}\n")
# 邏輯: "飛車" (fei che) ~ "北車" (bei che). 聲母 f != b -> 跳過

# 案例：雙詞測試
c1_t4 = "我去過台大看病，然後去北側搭車。"
print(f"原句: {c1_t4}\n結果: {c1.correct(c1_t4)}\n")


print("=== 情境二：關閉歸一化 (False) ===")
case2_mapping = {
    "台北車站": ["北車"],
    "台大醫院": ["台大"],
}

case2_exclusion = ["北側"]
# 預期：只修錯字，保留簡稱。 "北側" -> "北車" (因為北側最像北車)
c2 = ContextAwareCorrector(
    case2_mapping, exclusions=case2_exclusion, use_canonical_normalization=False
)
c2_t1 = "我去過台大看病，然後去北側搭車。"
print(f"原句: {c2_t1}\n結果: {c2.correct(c2_t1)}\n")


print("=== 情境三：根據上下文關鍵字去修正 ===")
case3_mapping = {
    "永和豆漿": {
        "aliases": ["永豆"],
        "keywords": ["吃", "喝", "買", "宵夜", "早餐", "豆漿", "油條"],
    },
    "勇者鬥惡龍": {
        "aliases": ["勇鬥"],
        "keywords": ["玩", "遊戲", "電動", "攻略", "RPG"],
    },
}
c3 = ContextAwareCorrector(case3_mapping)

print("--- 食物情境 ---")
c3_t1 = "我去買勇鬥當宵夜"
print(f"原句: {c3_t1}\n結果: {c3.correct(c3_t1)}\n")
# 預期：命中 "買" 或 "宵夜"，修正為 "永和豆漿"

print("--- 遊戲情境 ---")
c3_t2 = "這款永豆的攻略很難找"
print(f"原句: {c3_t2}\n結果: {c3.correct(c3_t2)}\n")
# 預期：命中 "攻略"，修正為 "勇者鬥惡龍"

print("--- 混和食物和遊戲情境 ---")
c3_t3 = "我們去吃勇鬥當消夜，吃完再去我家找攻略一起玩永豆通宵阿"
print(f"原句: {c3_t3}\n結果: {c3.correct(c3_t3)}\n")
# 預期：命中 "攻略"，修正為 "勇者鬥惡龍"

print("--- 模糊發音且有上下文 ---")
c3_t4 = "我想喝用豆"  # 假設這裡口語說成了 "我想喝用豆" (拼音相似)
print(f"原句: {c3_t4}\n結果: {c3.correct(c3_t4)}\n")


print("=== 情境四：英文混用詞 ===")
case4_mapping = {
    "Python": {
        "aliases": ["Pyton", "Pyson", "派森"],
        "keywords": ["程式", "代碼", "coding", "code"],
    },
    "C語言": {"aliases": ["C語法", "西語言"], "keywords": ["程式", "指標", "記憶體"]},
    "App": ["APP", "欸屁屁", "A屁屁"],
}
c4 = ContextAwareCorrector(case4_mapping)

# 情境：使用者念 "Python"，ASR 輸出類似音 "Pyson"
c4_t1 = "我正在寫Pyson程式。"
print(f"原句: {c4_t1}\n結果: {c4.correct(c4_t1)}\n")
# 邏輯: Pyson (len 5) vs Python (len 6)。 Levenshtein距離近，且命中 "程式" 關鍵字。

# 情境：把 "C語言" 念成 "C語法" 或 "西語言"
c4_t2 = "西語言真的很難學。C語法跟JS差別好多。"
print(f"原句: {c4_t2}\n結果: {c4.correct(c4_t2)}\n")

c4_t3 = "你有下載那個欸屁屁嗎？"
print(f"原句: {c4_t3}\n結果: {c4.correct(c4_t3)}\n")

# 情境：ASR 輸出全大寫，但我們字典是 Title Case
c4_t4 = "這段 CODES 是用 PYTON 寫的"
# 這裡 "CODES" (命中 keyword "code"?) -> 雖然 keywords 定義是 "code"，但 "CODES" 包含 "code"，check_context 應該要能抓到
print(f"原句: {c4_t4}\n結果: {c4.correct(c4_t4)}\n")


print("=== 情境五：長文章測試 ===")
case5_mapping = {
    "聖靈": ["聖靈"],
    "道成肉身": ["道成肉身", "到的路生"],
    "聖經": ["聖經"],
    "新約": ["新約", "新月"],
    "舊約": ["舊約", "舊月"],
    "新舊約": ["新舊約"],
    "榮光": ["榮光", "農光"],
    "使徒": ["使徒"],
    "福音": ["福音"],
    "默示": ["默示", "漠視"],
    "感孕": ["感孕"],
    "充滿": ["充滿", "蔥滿"],
    "章節": ["章節", "張捷"],
    "恩典": {
        "aliases": ["恩典", "安點"],
        "weight": 0.3,  # [關鍵] 恩典很重要，給予較高權重
    },
    "上帝": {"aliases": ["上帝"], "weight": 0.1},
}

case5_exclusion = ["什麼是"]

c5 = ContextAwareCorrector(case5_mapping, exclusions=case5_exclusion)
c5_t1 = (
    "什麼是上帝的道那你應該知道這本聖經就是上帝的道上帝的話就是上帝的道"
    "沒有錯我在說道太出與上帝同在道是聖林帶到人間的所以聖林借著莫氏就約的先知跟新約的使徒 "
    "跟新月的使途寫一下這一本新就月生經這個是文字的道叫做真理那聖林又把道帶到人間"
    "就是借著馬利亞聖林敢運生下了倒成肉生的耶穌基督就是基督降生在地上"
    "這是道就是倒成了肉生對不對所以道被帶到人間都是聖林帶下來的 "
    "都是勝領帶下來的道成的文字就是這本新舊月聖經道成的路生就是耶穌基督自己道成的文字"
    "是真理那道成的路生呢安點注意再聽我講一次道成的文字是真理道成的路生是安點"
    "所以約翰福音第一張十四節道成的路生匆忙 充滿有恩典有真理我們也見過他的農光"
    "就是副獨生子的農光現在請你注意聽一下的話道成的文字是真理這個我們都在追求很多地方"
    "姐妹都很追求讀很好的書很好但是道成的肉身是恩點你可能忽略了這兩者都是攻擊性的武器"
    "都是攻擊性的武器除了你在上帝的話題當中要建造之外你也要明白恩典來我簡單講一句話"
    "就是沒有恩典的真理是冷酷的再聽我講一次沒有恩典的真理是冷酷的是會定人的罪的"
    "是會挑人家的錯誤的是像法律塞人一樣的但是當然反之沒有真理的恩典 "
    "沒有真理的恩典是為叫人放重的沒有錯所以這兩者你必須多了解"
)
print(f"原句: {c5_t1}\n結果: {c5.correct(c5_t1)}\n")


print("=== 情境六：測試 ===")
case6_mapping = {
    "修酒雷": {
        "aliases": ["修酒雷", "修酒流", "燒酒來", "削酒來", "笑酒來"],
        "keywords": ["程式", "代碼", "coding", "code"],
    },
}
c6 = ContextAwareCorrector(case6_mapping)
c6_t1 = "我要削酒來，拿給我。"
print(f"原句: {c6_t1}\n結果: {c6.correct(c6_t1)}\n")

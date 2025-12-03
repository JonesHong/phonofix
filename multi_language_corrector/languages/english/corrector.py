"""
英文修正器模組

實作基於滑動視窗 (Sliding Window) 與語音相似度的英文專有名詞修正。
"""

import re
from typing import List, Dict, Union, Optional, Set
from multi_language_corrector.core.phonetic_interface import PhoneticSystem
from multi_language_corrector.core.tokenizer_interface import Tokenizer
from .phonetic_impl import EnglishPhoneticSystem
from .tokenizer import EnglishTokenizer
from .fuzzy_generator import EnglishFuzzyGenerator
from .config import EnglishPhoneticConfig


class EnglishCorrector:
    """
    英文修正器

    功能:
    - 針對英文文本進行專有名詞修正
    - 使用滑動視窗掃描文本
    - 結合 IPA 發音相似度進行模糊比對
    - 支援自動生成 ASR 錯誤變體
    - 支援 keywords 條件過濾 (需要上下文關鍵字才替換)
    - 支援 exclusions 保護 (排除詞不被替換)
    """

    @classmethod
    def from_terms(cls, term_dict, config=None, warmup="init"):
        """
        從詞彙配置建立 EnglishCorrector 實例
        
        支援格式:
        1. List[str]: 純詞彙列表，自動生成別名
           ["Python", "TensorFlow"]
           
        2. Dict[str, List[str]]: 詞彙 + 手動別名
           {"Python": ["Pyton", "Pyson"]}
           
        3. Dict[str, dict]: 完整配置
           {"EKG": {"aliases": ["1kg"], "keywords": ["設備"], "exclusions": ["水"]}}
        
        Args:
            term_dict: 詞彙配置
            config: 額外配置選項
            warmup: IPA 快取暖機模式 ("init", "lazy", "none")
            
        Returns:
            EnglishCorrector: 初始化後的修正器實例
        """
        generator = EnglishFuzzyGenerator()
        term_mapping = {}
        keywords = {}
        exclusions = {}
        
        # 處理列表格式
        if isinstance(term_dict, list):
            for term in term_dict:
                # 自動生成變體
                variants = generator.generate_variants(term)
                term_mapping[term] = term  # 原詞映射到自己
                for variant in variants:
                    term_mapping[variant] = term
            return cls(term_mapping, keywords, exclusions, warmup=warmup)
        
        # 處理字典格式
        for term, value in term_dict.items():
            term_mapping[term] = term  # 原詞映射到自己
            
            if isinstance(value, list):
                # 格式 2: {"Python": ["Pyton", "Pyson"]}
                # 同時添加手動別名和自動生成的變體
                for alias in value:
                    term_mapping[alias] = term
                # 自動生成額外變體
                auto_variants = generator.generate_variants(term)
                for variant in auto_variants:
                    if variant not in term_mapping:
                        term_mapping[variant] = term
                        
            elif isinstance(value, dict):
                # 格式 3: 完整配置
                aliases = value.get("aliases", [])
                for alias in aliases:
                    term_mapping[alias] = term
                    
                # 自動生成額外變體 (除非明確禁用)
                if value.get("auto_fuzzy", True):
                    auto_variants = generator.generate_variants(term)
                    for variant in auto_variants:
                        if variant not in term_mapping:
                            term_mapping[variant] = term
                
                if value.get("keywords"):
                    keywords[term] = value["keywords"]
                if value.get("exclusions"):
                    exclusions[term] = value["exclusions"]
                    
            else:
                # 空值或其他: 只自動生成變體
                auto_variants = generator.generate_variants(term)
                for variant in auto_variants:
                    term_mapping[variant] = term
        
        return cls(term_mapping, keywords, exclusions, warmup=warmup)

    def __init__(
        self, 
        term_mapping: Union[List[str], Dict[str, str]],
        keywords: Optional[Dict[str, List[str]]] = None,
        exclusions: Optional[Dict[str, List[str]]] = None,
        warmup: str = "init"
    ):
        """
        初始化英文修正器

        Args:
            term_mapping: 兩種格式之一:
                - List[str]: 專有名詞列表 (如 ["Python", "TensorFlow"])
                - Dict[str, str]: 別名到標準詞的映射 (如 {"Pyton": "Python", "Python": "Python"})
            keywords: 標準詞到關鍵字列表的映射 (如 {"EKG": ["設備", "心電圖"]})
                - 如果標準詞在此映射中，則必須句子中包含至少一個關鍵字才會替換
            exclusions: 標準詞到排除關鍵字列表的映射 (如 {"EKG": ["水", "公斤"]})
                - 如果句子中包含任一排除關鍵字，則不替換
            warmup: IPA 快取暖機模式
                - "init": [推薦] 僅初始化 espeak-ng (~2秒)
                - "lazy": 在背景執行緒初始化，不阻塞主執行緒
                - "none": 不暖身，首次使用時才初始化
        """
        from .phonetic_impl import warmup_ipa_cache
        
        # 預熱 IPA 快取 (在其他初始化之前)
        # 這會預先載入常見英文單字的 IPA，避免首次校正時的延遲
        if warmup and warmup != "none":
            warmup_ipa_cache(mode=warmup)
        
        self.phonetic = EnglishPhoneticSystem()
        self.tokenizer = EnglishTokenizer()
        
        # 統一處理為 {別名: 標準詞} 格式
        if isinstance(term_mapping, list):
            self.term_mapping = {term: term for term in term_mapping}
        else:
            self.term_mapping = term_mapping
        
        # 關鍵字映射: {標準詞: [關鍵字列表]}
        self.keywords = keywords or {}
        
        # 排除關鍵字映射: {標準詞: [排除關鍵字列表]}
        self.exclusions = exclusions or {}
        
        # 預先計算所有別名的發音特徵
        # 重要：使用逐 token 計算再合併的方式，與 correct() 中的處理保持一致
        # 這樣 "view js" 會被拆成 ["view", "js"]，"js" 會被識別為縮寫並正確轉換
        aliases = list(self.term_mapping.keys())
        
        def compute_alias_ipa(alias):
            """計算 alias 的 IPA（逐 token 計算再合併）"""
            tokens = self.tokenizer.tokenize(alias)
            token_ipas = [self.phonetic.to_phonetic(t) for t in tokens]
            return ''.join(token_ipas)
        
        if len(aliases) > 20:
            # 多執行緒計算 IPA
            from concurrent.futures import ThreadPoolExecutor, as_completed
            raw_alias_phonetics = {}
            with ThreadPoolExecutor(max_workers=16) as executor:
                futures = {executor.submit(compute_alias_ipa, alias): alias for alias in aliases}
                for future in as_completed(futures):
                    alias = futures[future]
                    raw_alias_phonetics[alias] = future.result()
        else:
            # 少量 alias 直接計算
            raw_alias_phonetics = {
                alias: compute_alias_ipa(alias) 
                for alias in aliases
            }
        
        # 直接使用計算好的 IPA（不過濾）
        # 注意：英文不需要像中文那樣過濾同音字，因為：
        # 1. 中文過濾的是「不同漢字但同音」的變體（如"測試"、"側試"）
        # 2. 英文的 alias 是「同一詞的不同輸入形式」（如"React"、"re act"）
        # 這些不同形式都是合法的 ASR 輸入，不應過濾
        self.alias_phonetics = raw_alias_phonetics
        
        # 預先計算所有別名的 token 數量 (用於視窗大小匹配)
        self.alias_token_counts = {
            alias: len(self.tokenizer.tokenize(alias))
            for alias in self.term_mapping.keys()
        }
        
        # 計算專有名詞的最大 Token 長度，用於限制滑動視窗的大小
        self.max_token_len = 0
        for alias in self.term_mapping.keys():
            tokens = self.tokenizer.tokenize(alias)
            self.max_token_len = max(self.max_token_len, len(tokens))
            
        # 設定最大視窗大小
        # 允許比最大專有名詞長度多 3 個 Token，以容納 ASR 錯誤分割的情況
        # 例如: "EKG" (1 token) 可能被識別為 "one k g" (3 tokens)
        self.max_window_size = self.max_token_len + 3

    def correct(self, text: str, full_context: str = None) -> str:
        """
        執行英文文本修正

        演算法:
        1. 將文本分詞 (Tokenize)
        2. 預先計算每個 Token 的 IPA (利用快取提升效率)
        3. 使用滑動視窗 (從最大視窗大小開始遞減) 掃描 Token 序列
        4. 合併視窗內 Token 的 IPA 進行比對
        5. 檢查 exclusion (排除詞保護) 和 keyword (關鍵字條件)
        6. 若匹配成功且通過檢查，則替換原始文本並跳過已處理的 Token
        7. 若無匹配，則移動到下一個 Token

        Args:
            text: 待修正的英文文本
            full_context: 完整的原始句子 (用於 keyword 和 exclusion 檢查)
                         如果未提供，則使用 text 本身

        Returns:
            str: 修正後的文本
        """
        # 用於 keyword/exclusion 檢查的完整上下文
        context = full_context if full_context else text
        
        tokens = self.tokenizer.tokenize(text)
        indices = self.tokenizer.get_token_indices(text)
        
        if not tokens:
            return text
        
        # 預先計算每個 token 的 IPA (這會利用快取)
        # 這樣每個唯一的 token 只需要計算一次 IPA
        token_ipas = [self.phonetic.to_phonetic(token) for token in tokens]
            
        matches = [] # 儲存匹配結果: (start_index, end_index, replacement)
        
        n = len(tokens)
        i = 0
        while i < n:
            best_match = None
            best_match_canonical = None
            best_match_len = 0
            
            # 嘗試不同的視窗大小，從最大可能長度開始遞減 (Greedy Matching)
            # 範例: 如果 max_window_size=3，當前 i=0，則嘗試長度 3, 2, 1
            # 視窗 3: tokens[0:3] -> "one k g"
            # 視窗 2: tokens[0:2] -> "one k"
            # 視窗 1: tokens[0:1] -> "one"
            for length in range(min(self.max_window_size, n - i), 0, -1):
                # 重建當前視窗對應的原始文本片段
                # 使用 indices 確保獲取包含空格的原始字串
                start_char = indices[i][0]
                end_char = indices[i + length - 1][1]
                window_text = text[start_char : end_char]
                
                # 合併視窗內 Token 的 IPA (利用預先計算的結果)
                # 使用預計算的單 token IPA 合併，避免重複的 SQLite 查詢
                if length == 1:
                    # 單 token 直接使用預計算的 IPA
                    window_phonetic = token_ipas[i]
                else:
                    # 多 token: 合併預計算的 IPA (用空格連接)
                    # 這比重新計算整個字串的 IPA 快很多
                    window_phonetic = ''.join(token_ipas[i:i+length])
                
                # 與所有別名進行比對
                for alias, alias_phonetic in self.alias_phonetics.items():
                    # 檢查視窗 token 數量是否與別名相符
                    # 只允許精確匹配，避免誤匹配到不相關的前置詞
                    alias_token_count = self.alias_token_counts[alias]
                    if length != alias_token_count:
                        continue
                    
                    # 範例: alias="1kg", alias_phonetic=/i keɪ dʒi/
                    # 比較 /wʌn keɪ dʒi/ 與 /i keɪ dʒi/
                    if self.phonetic.are_fuzzy_similar(window_phonetic, alias_phonetic):
                        canonical = self.term_mapping[alias]
                        
                        # 檢查 exclusion: 如果句子包含排除關鍵字，跳過
                        if self._has_exclusion_keyword(canonical, context):
                            continue
                        
                        # 檢查 keyword: 如果標準詞需要關鍵字確認，檢查上下文
                        if not self._has_required_keyword(canonical, context):
                            continue
                        
                        best_match = alias
                        best_match_canonical = canonical
                        best_match_len = length
                        break
                
                # 如果找到匹配，則停止嘗試更小的視窗 (Greedy)
                if best_match:
                    break
            
            if best_match:
                # 記錄匹配位置與替換詞 (使用標準詞)
                start_char = indices[i][0]
                end_char = indices[i + best_match_len - 1][1]
                matches.append((start_char, end_char, best_match_canonical))
                # 跳過已匹配的 Token
                # 範例: 如果匹配了長度 3 的 "one k g"，則 i 增加 3，跳過這三個 token
                i += best_match_len
            else:
                # 無匹配，移動到下一個 Token
                i += 1
                
        # 應用所有匹配結果進行替換
        result = []
        last_pos = 0
        for start, end, replacement in matches:
            # 加入上一個匹配點到當前匹配點之間的原始文本
            result.append(text[last_pos:start])
            # 加入替換詞
            result.append(replacement)
            last_pos = end
        # 加入剩餘的文本
        result.append(text[last_pos:])
        
        return "".join(result)

    def _has_exclusion_keyword(self, canonical: str, context: str) -> bool:
        """
        檢查是否命中排除關鍵字
        
        策略:
        - 如果標準詞沒有在 exclusions_map 中，則不排除
        - 如果標準詞有排除關鍵字，且上下文包含任一排除關鍵字，則排除
        
        範例:
        - canonical="EKG", context="這瓶1kg水很重", exclusions_map={"EKG": ["水", "公斤"]}
        - "水" 在 context 中 -> 排除，返回 True
        
        Args:
            canonical: 標準詞
            context: 完整的上下文句子
            
        Returns:
            bool: 如果應該排除則返回 True
        """
        if canonical not in self.exclusions:
            return False
            
        excl_keywords = self.exclusions[canonical]
        
        for excl in excl_keywords:
            if excl in context:
                return True
        return False
    
    def _has_required_keyword(self, canonical: str, context: str) -> bool:
        """
        檢查標準詞是否滿足關鍵字條件
        
        策略:
        - 如果標準詞沒有在 keywords_map 中，則無條件通過
        - 如果標準詞有關鍵字要求，則上下文必須包含至少一個關鍵字
        
        範例:
        - canonical="EKG", context="這個1kg設備很貴", keywords_map={"EKG": ["設備"]}
        - "設備" 在 context 中 -> 通過，返回 True
        
        Args:
            canonical: 標準詞
            context: 完整的上下文句子
            
        Returns:
            bool: 如果滿足條件則返回 True
        """
        # 如果沒有關鍵字要求，直接通過
        if canonical not in self.keywords:
            return True
            
        kw_list = self.keywords[canonical]
        
        # 檢查上下文是否包含任一關鍵字
        for kw in kw_list:
            if kw in context:
                return True
                
        return False

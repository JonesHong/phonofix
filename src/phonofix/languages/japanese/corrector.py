"""
日文修正器模組

實作針對日文語音識別 (ASR) 錯誤的修正邏輯。
核心演算法基於羅馬拼音 (Romaji) 的相似度比對。
"""

from typing import Dict, List, Optional, Any

from phonofix.correction.protocol import CorrectorProtocol
from .phonetic_impl import JapanesePhoneticSystem
from .tokenizer import JapaneseTokenizer
from .config import JapanesePhoneticConfig
from phonofix.utils.logger import get_logger


class JapaneseCorrector:
    """
    日文修正器

    實作 CorrectorProtocol，負責日文文本的修正。
    
    使用方式:
        corrector = JapaneseCorrector({'アスピリン': ['asupirin']})
        result = corrector.correct('頭が痛いのでasupirinを飲みました')
    """

    def __init__(
        self,
        dictionary: Dict[str, Any],
        config: Optional[JapanesePhoneticConfig] = None
    ):
        """
        初始化日文修正器

        Args:
            dictionary: 修正字典 {正確詞: [錯誤詞別名...]}
            config: 日文配置 (可選)
        """
        self.logger = get_logger(__name__)
        self.config = config or JapanesePhoneticConfig()
        self.phonetic_system = JapanesePhoneticSystem()
        self.tokenizer = JapaneseTokenizer()
        
        # 建構搜尋索引
        # 結構: { 'romaji_alias': [Candidate, ...] }
        self.search_index = self._build_search_index(dictionary)

    def _build_search_index(self, dictionary: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """
        建構羅馬拼音搜尋索引
        """
        index = {}
        for term, value in dictionary.items():
            # 解析配置
            aliases = []
            weight = 1.0
            keywords = []
            exclude_when = []

            if isinstance(value, list):
                aliases = value
            elif isinstance(value, dict):
                aliases = value.get("aliases", [])
                weight = value.get("weight", 1.0)
                keywords = value.get("keywords", [])
                exclude_when = value.get("exclude_when", [])
            
            candidate = {
                "term": term,
                "weight": weight,
                "keywords": keywords,
                "exclude_when": exclude_when
            }

            def add_to_index(p):
                if p not in index:
                    index[p] = []
                # 避免重複添加相同的候選詞
                if candidate not in index[p]:
                    index[p].append(candidate)

            # 處理每個別名
            for alias in aliases:
                phonetic = self.phonetic_system.to_phonetic(alias)
                if phonetic:
                    add_to_index(phonetic)
            
            # 嘗試將正確詞轉拼音也加入
            term_phonetic = self.phonetic_system.to_phonetic(term)
            if term_phonetic:
                add_to_index(term_phonetic)
        
        # 根據權重排序候選詞
        for p in index:
            index[p].sort(key=lambda x: x["weight"], reverse=True)
                
        return index

    def _check_context(self, candidate: Dict, text: str) -> bool:
        """檢查上下文條件"""
        # 1. 檢查排除條件 (exclude_when)
        for exclude in candidate["exclude_when"]:
            if exclude in text:
                return False
        
        # 2. 檢查關鍵字條件 (keywords)
        # 如果有設定關鍵字，則必須至少匹配一個
        if candidate["keywords"]:
            for keyword in candidate["keywords"]:
                if keyword in text:
                    return True
            return False
            
        # 沒有設定關鍵字則視為通過
        return True

    def correct(self, text: str, full_context: str = None) -> str:
        """
        修正日文文本

        Args:
            text: 輸入文本
            full_context: 完整上下文 (用於關鍵字判斷)

        Returns:
            str: 修正後的文本
        """
        if not text or not self.search_index:
            return text
        
        # 如果沒有提供 full_context，則使用 text 本身
        context = full_context if full_context is not None else text

        # 1. 分詞
        tokens = self.tokenizer.tokenize(text)
        
        # 2. 逐詞檢查
        corrected_tokens = []
        for token in tokens:
            # 轉拼音
            phonetic = self.phonetic_system.to_phonetic(token)
            
            candidates = []
            
            # 查表 (完全匹配)
            if phonetic in self.search_index:
                candidates.extend(self.search_index[phonetic])
                
            # 模糊匹配 (如果沒有完全匹配，或為了尋找更高權重的選項)
            # 這裡簡化策略：如果沒有完全匹配，才嘗試模糊匹配
            if not candidates and len(phonetic) > 3:
                min_dist = float('inf')
                
                for index_phonetic, index_candidates in self.search_index.items():
                    if abs(len(phonetic) - len(index_phonetic)) > 2:
                        continue
                        
                    if self.phonetic_system.are_fuzzy_similar(phonetic, index_phonetic):
                        import Levenshtein
                        dist = Levenshtein.distance(phonetic, index_phonetic)
                        
                        # 收集所有模糊匹配的候選詞
                        # 這裡可以優化：只收集距離最近的
                        if dist < 3: # 設定一個絕對距離門檻
                            candidates.extend(index_candidates)

            # 選擇最佳候選詞
            best_candidate = None
            if candidates:
                # 候選詞已按權重排序，依序檢查上下文
                for cand in candidates:
                    if self._check_context(cand, context):
                        best_candidate = cand
                        break
            
            if best_candidate:
                corrected_tokens.append(best_candidate["term"])
            else:
                corrected_tokens.append(token)
        
        # 3. 重組字串
        return "".join(corrected_tokens)

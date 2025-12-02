"""
統一修正器模組

這是多語言修正系統的主要入口點。
負責協調語言路由與特定語言的修正器，以處理混合語言的文本。
"""

from typing import List, Dict, Union
from multi_language_corrector.router.language_router import LanguageRouter
from multi_language_corrector.languages.chinese.corrector import ChineseCorrector
from multi_language_corrector.languages.english.corrector import EnglishCorrector

class UnifiedCorrector:
    """
    統一修正器 (Unified Corrector)

    功能:
    - 接收混合語言文本
    - 自動識別並分割不同語言的片段
    - 將片段分派給對應的語言修正器 (中文/英文)
    - 合併修正後的結果
    """

    def __init__(self, term_dict: Union[List[str], Dict], exclusions=None):
        """
        初始化統一修正器

        初始化過程會將輸入的專有名詞庫分類為中文詞庫與英文詞庫，
        並分別初始化對應的修正器實例。

        Args:
            term_dict: 專有名詞字典或列表
            exclusions: 排除詞列表 (主要用於中文修正器)
        """
        self.router = LanguageRouter()
        
        # 將專有名詞分類為中文與英文
        self.zh_terms = {}
        self.en_terms = {}  # 改為 dict，保存標準詞與別名的對應
        
        # 如果輸入是列表，則標準化為字典格式
        # 範例: ["IBM", "台積電"] -> {"IBM": {}, "台積電": {}}
        if isinstance(term_dict, list):
            term_dict = {term: {} for term in term_dict}
            
        for term, value in term_dict.items():
            # 檢查專有名詞是否為純英文 (ASCII)
            # 策略:
            # - 純 ASCII 字串 -> 英文修正器 (例如 "IBM", "TensorFlow")
            # - 包含非 ASCII 字符 (如中文) -> 中文修正器 (例如 "台積電", "C語言")
            # 注意: 混合語言詞彙 (如 "C語言") 目前歸類為中文處理，因為中文修正器有處理混合詞的邏輯
            
            if all(ord(c) < 128 for c in term):
                self.en_terms[term] = value
            else:
                self.zh_terms[term] = value
                
        # 初始化特定語言的修正器
        # 中文修正器使用 from_terms 工廠方法
        self.zh_corrector = ChineseCorrector.from_terms(self.zh_terms, exclusions=exclusions)
        # 英文修正器需要展開別名，並傳入 keywords 和 exclusions
        en_term_config = self._build_english_term_config()
        self.en_corrector = EnglishCorrector(
            term_mapping=en_term_config["term_mapping"],
            keywords=en_term_config["keywords"],
            exclusions=en_term_config["exclusions"]
        )

    def correct(self, text: str) -> str:
        """
        執行混合語言文本修正

        流程:
        1. 使用 LanguageRouter 將文本分割為語言片段 (如 [('zh', '我有一台'), ('en', 'computer')])
        2. 遍歷每個片段，根據語言標籤呼叫對應的修正器
        3. 將修正後的片段重新組合成完整字串

        限制:
        - 目前的簡單路由策略可能會將混合詞彙 (如 "C語言") 切開為 "C" (en) 和 "語言" (zh)
        - 這可能導致某些跨語言邊界的專有名詞無法正確修正
        - 但對於解決 "1kg" -> "EKG" 這類純英文/數字問題非常有效

        Args:
            text: 原始混合語言文本

        Returns:
            str: 修正後的文本
        """
        # 1. 路由分割
        # 範例輸入: "我有一台1kg的computer"
        # 分割結果: [('zh', '我有一台'), ('en', '1kg'), ('zh', '的'), ('en', 'computer')]
        segments = self.router.split_by_language(text)
        corrected_segments = []
        
        for lang, segment in segments:
            if lang == 'zh':
                # 中文修正: "我有一台" -> "我有一台" (無變更)
                corrected_segments.append(self.zh_corrector.correct(segment))
            elif lang == 'en':
                # 英文修正: "1kg" -> "EKG" (假設 EKG 在詞庫中且符合規則)
                # 傳入完整原文作為上下文，供 keyword/exclusion 檢查
                # "computer" -> "computer"
                corrected_segments.append(self.en_corrector.correct(segment, full_context=text))
            else:
                # 未知語言 (理論上不會發生，因為 router 涵蓋了所有情況)
                corrected_segments.append(segment)
        
        # 2. 結果合併
        # 合併結果: "我有一台EKG的computer"
        return "".join(corrected_segments)

    def _build_english_term_mapping(self) -> Dict[str, str]:
        """
        建立英文詞彙的 別名 -> 標準詞 映射表

        將 {"Python": ["Pyton", "Pyson"]} 展開為:
        {"Python": "Python", "Pyton": "Python", "Pyson": "Python"}

        Returns:
            Dict[str, str]: 別名到標準詞的映射
        """
        return self._build_english_term_config()["term_mapping"]
    
    def _build_english_term_config(self) -> Dict:
        """
        建立英文詞彙的完整配置

        Returns:
            Dict: 包含 term_mapping, keywords 和 exclusions
                - term_mapping: {別名: 標準詞}
                - keywords: {標準詞: [關鍵字列表]}
                - exclusions: {標準詞: [排除關鍵字列表]}
        """
        mapping = {}
        keywords = {}
        exclusions = {}
        
        for canonical, value in self.en_terms.items():
            # 標準詞本身也要加入映射
            mapping[canonical] = canonical
            
            # 處理別名、關鍵字和排除關鍵字
            if isinstance(value, list):
                aliases = value
                kw_list = []
                excl_list = []
            elif isinstance(value, dict):
                aliases = value.get("aliases", [])
                kw_list = value.get("keywords", [])
                excl_list = value.get("exclusions", [])
            else:
                aliases = []
                kw_list = []
                excl_list = []
                
            for alias in aliases:
                mapping[alias] = canonical
            
            # 只有當有 keywords 時才加入
            if kw_list:
                keywords[canonical] = kw_list
            
            # 只有當有 exclusions 時才加入
            if excl_list:
                exclusions[canonical] = excl_list
                
        return {
            "term_mapping": mapping,
            "keywords": keywords,
            "exclusions": exclusions
        }

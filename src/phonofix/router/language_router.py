"""
語言路由模組

負責將混合語言的文本分割成單一語言的片段，以便分派給對應的修正器處理。
"""

import re
from typing import List, Tuple

class LanguageRouter:
    """
    語言路由器

    功能:
    - 識別文本中的語言邊界
    - 將文本分割為 (語言代碼, 文本片段) 的列表
    - 目前主要支援中文 (zh) 與英文 (en) 的區分
    """

    def split_by_language(self, text: str) -> List[Tuple[str, str]]:
        """
        將輸入文本路由分割為不同語言的片段

        策略:
        - 使用 ASCII 字符判斷作為主要依據
        - 連續的 ASCII 字符 (包含空格) 視為英文 ('en')
        - 非 ASCII 字符視為中文 ('zh')
        - 為了保持上下文完整性，可能會進行微調 (目前實作為簡單切分)

        Args:
            text: 原始混合語言文本

        Returns:
            List[Tuple[str, str]]: 語言片段列表，例如 [('zh', '我有一台'), ('en', 'computer'), ('zh', '。')]
        """
        segments = []
        current_lang = None
        current_buffer = []

        for char in text:
            # 簡單啟發式：ASCII 視為英文，其他視為中文
            # 這涵蓋了數字和英文單字
            # 注意：這會將 ASCII 標點符號視為英文，通常這是可接受的
            # 範例: 'a' (97) -> en, '1' (49) -> en, '中' (20013) -> zh
            if ord(char) < 128:
                lang = 'en'
            else:
                lang = 'zh'

            if lang != current_lang:
                # 語言切換點，將當前緩衝區的內容寫入片段列表
                if current_lang is not None:
                    segments.append((current_lang, "".join(current_buffer)))
                current_lang = lang
                current_buffer = [char]
            else:
                # 同一語言，繼續累積字符
                current_buffer.append(char)

        # 處理最後一個片段
        if current_buffer:
            segments.append((current_lang, "".join(current_buffer)))

        return self._merge_numeric_segments(segments)

    def _merge_numeric_segments(self, segments: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        合併純數字的英文片段到相鄰的中文片段
        
        解決如 "11位" 被拆分為 ('en', '11'), ('zh', '位') 的問題。
        如果 'en' 片段只包含數字（不含字母），且相鄰有 'zh' 片段，則合併。
        """
        if not segments:
            return []
            
        merged = []
        i = 0
        while i < len(segments):
            lang, text = segments[i]
            
            # 檢查是否為純數字（允許空格、點號，但不允許字母）
            # 這裡的邏輯是：如果它被標記為 'en'，但沒有英文字母，那它可能只是數字或符號
            # 如果它旁邊是中文，那它應該屬於中文語境
            is_numeric_en = (
                lang == 'en' and 
                not any(c.isalpha() for c in text) and 
                any(c.isdigit() for c in text)
            )
            
            if is_numeric_en:
                # 檢查前一個是否為中文 (在已合併列表中)
                prev_is_zh = (merged and merged[-1][0] == 'zh')
                
                # 檢查下一個是否為中文 (在未處理列表中)
                next_is_zh = (i + 1 < len(segments) and segments[i+1][0] == 'zh')
                
                if prev_is_zh and next_is_zh:
                    # 三明治情況：前中 + 數 + 後中 -> 合併成一個大中文片段
                    prev_lang, prev_text = merged.pop()
                    next_lang, next_text = segments[i+1]
                    merged.append(('zh', prev_text + text + next_text))
                    i += 2 # 跳過當前和下一個
                elif prev_is_zh:
                    # 前中 + 數 -> 合併
                    prev_lang, prev_text = merged.pop()
                    merged.append(('zh', prev_text + text))
                    i += 1 # 跳過當前
                elif next_is_zh:
                    # 數 + 後中 -> 合併
                    next_lang, next_text = segments[i+1]
                    merged.append(('zh', text + next_text))
                    i += 2 # 跳過當前和下一個
                else:
                    # 孤立數字，保持原樣
                    merged.append((lang, text))
                    i += 1
            else:
                # 非數字或非英文，直接加入
                merged.append((lang, text))
                i += 1
            
        return merged

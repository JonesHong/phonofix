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

        return segments

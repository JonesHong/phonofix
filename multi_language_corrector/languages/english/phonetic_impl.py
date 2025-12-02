"""
英文發音系統實作模組

實作基於 IPA (國際音標) 的英文發音轉換與相似度比對。
特別針對中文 ASR 常見的英文錯誤 (如數字混淆) 進行了優化。
"""

import eng_to_ipa as ipa
import Levenshtein
import re
from multi_language_corrector.core.phonetic_interface import PhoneticSystem

class EnglishPhoneticSystem(PhoneticSystem):
    """
    英文發音系統

    功能:
    - 將英文文本轉換為 IPA 音標字串
    - 處理常見的 ASR 錯誤 (如 '1' -> 'E')
    - 處理縮寫與數字的發音展開
    - 計算 IPA 字串間的編輯距離以判斷相似度
    """

    def to_phonetic(self, text: str) -> str:
        """
        將英文文本轉換為標準化的 IPA 音標字串

        處理流程:
        1. 修正 ASR 特有的數字/字母混淆 (如 1kg -> Ekg)
        2. 展開縮寫 (如 IBM -> I B M)
        3. 展開數字 (如 1 -> one)
        4. 使用 eng_to_ipa 庫轉換為 IPA
        5. 處理未知詞彙 (嘗試按字母發音)
        6. 移除重音符號與空格，產生連續的音素序列以便比對

        Args:
            text: 輸入英文文本

        Returns:
            str: 處理後的 IPA 字串
        """

        # 縮寫的啟發式處理:
        # 如果是全大寫且長度較短 (<=5)，視為縮寫，強制分開字母發音
        # 例如: "IBM" -> "I B M" -> /aɪ bi ɛm/
        # 若不分開，"IBM" 可能被嘗試當作一個單字發音，結果可能不準確
        if text.isupper() and len(text) <= 5 and text.isalpha():
             text = " ".join(list(text))
        
        # 簡單的數字正規化 (針對剩餘的數字)
        # 將數字轉換為對應的英文單字，以便取得正確發音
        # 例如: "2" -> "two "
        text = text.replace("0", "zero ").replace("1", "one ").replace("2", "two ")\
                   .replace("3", "three ").replace("4", "four ").replace("5", "five ")\
                   .replace("6", "six ").replace("7", "seven ").replace("8", "eight ")\
                   .replace("9", "nine ")

        # 使用 eng_to_ipa 庫轉換為 IPA 字串
        # 注意: 該庫可能返回帶有 '*' 的字串表示未知詞彙
        # 範例: "hello" -> "hɛˈloʊ"
        result = ipa.convert(text)
        
        # 清理標記並處理未知短詞 (可能是縮寫或單位)
        if '*' in result:
            # 如果詞彙未知且較短，嘗試將其拆分為單個字母進行發音轉換
            # 例如: "Ekg" -> "ekg*" -> "E k g" -> "i keɪ dʒi"
            clean_result = result.replace('*', '')
            
            # 檢查清理後的長度 (作為原始長度的近似)
            if len(clean_result) <= 3:
                # 嘗試將文本拆分為字母序列
                if " " not in text:
                    split_text = " ".join(list(text))
                    split_result = ipa.convert(split_text)
                    # 如果拆分後能成功轉換 (沒有 *)，則採用拆分後的結果
                    if '*' not in split_result:
                        result = split_result
            
            # 最終移除 '*' 標記
            result = result.replace('*', '')
            
        # 移除空格和重音符號，以進行更寬鬆的模糊比對
        # 例如: "tɛn soʊ flɔr" -> "tɛnsoʊflɔr"
        # "ˈ" (主重音), "ˌ" (次重音) -> 移除
        result = result.replace(" ", "").replace("ˈ", "").replace("ˌ", "")
            
        return result

    def are_fuzzy_similar(self, phonetic1: str, phonetic2: str) -> bool:
        """
        判斷兩個 IPA 字串是否模糊相似

        使用 Levenshtein 編輯距離計算相似度比率。

        Args:
            phonetic1: 第一個 IPA 字串
            phonetic2: 第二個 IPA 字串

        Returns:
            bool: 若 (編輯距離 / 最大長度) <= 容錯率，則返回 True
        """
        # 計算 Levenshtein 編輯距離
        dist = Levenshtein.distance(phonetic1, phonetic2)
        
        # 根據較長字串的長度進行正規化
        max_len = max(len(phonetic1), len(phonetic2))
        if max_len == 0:
            return True
        
        ratio = dist / max_len
        tolerance = self.get_tolerance(max_len)
        
        return ratio <= tolerance

    def get_tolerance(self, length: int) -> float:
        """
        根據 IPA 字串長度動態調整容錯率

        策略:
        - 短詞 (<=3): 容錯率低 (0.20)，避免誤匹配
        - 中詞 (<=5): 容錯率中 (0.30)
        - 長詞 (>5): 容錯率高 (0.40)，允許更多音素差異

        Args:
            length: IPA 字串長度

        Returns:
            float: 容錯率閾值
        """
        if length <= 3: return 0.20 # 短詞非常嚴格
        if length <= 5: return 0.30
        return 0.40

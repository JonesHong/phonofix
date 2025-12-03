"""
英文發音系統實作模組

實作基於 IPA (國際音標) 的英文發音轉換與相似度比對。
特別針對中文 ASR 常見的英文錯誤 (如數字混淆) 進行了優化。

效能優化:
- 使用 functools.lru_cache 快取 IPA 轉換結果
- 避免重複的 SQLite 資料庫查詢
- warmup_ipa_cache() 預熱常見詞彙
"""

import eng_to_ipa as ipa
import Levenshtein
import re
from functools import lru_cache
from multi_language_corrector.core.phonetic_interface import PhoneticSystem


# =============================================================================
# IPA 快取 (Performance Critical)
# =============================================================================
# eng_to_ipa.convert() 每次呼叫都存取 SQLite 資料庫，非常慢
# 使用 lru_cache 可達到 100x+ 加速

@lru_cache(maxsize=50000)
def cached_ipa_convert(text: str) -> str:
    """快取版 IPA 轉換"""
    return ipa.convert(text)


def clear_english_cache():
    """清除 IPA 快取"""
    cached_ipa_convert.cache_clear()


def get_english_cache_stats():
    """取得 IPA 快取統計"""
    return cached_ipa_convert.cache_info()


# 最常見的英文單字 (精簡版 - 用於快速暖機)
# 這些是幾乎每篇英文文章都會出現的高頻詞
_WARMUP_WORDS_FAST = [
    # 冠詞/代詞/連接詞 (最高頻)
    "the", "a", "an", "and", "or", "but", "if", "is", "are", "was", "were",
    "be", "been", "have", "has", "had", "do", "does", "did", "will", "would",
    "can", "could", "should", "may", "might", "must",
    "i", "you", "he", "she", "it", "we", "they", "this", "that", "these", "those",
    "my", "your", "his", "her", "its", "our", "their",
    "who", "what", "where", "when", "why", "how",
    # 介詞
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "about",
    # 常見動詞
    "use", "make", "get", "go", "know", "think", "see", "want", "need",
    "take", "come", "give", "find", "work", "call", "try",
    # 常見名詞
    "time", "way", "day", "thing", "man", "world", "life", "hand", "part",
    "place", "case", "point", "system", "number", "problem",
    # 常見形容詞/副詞
    "new", "good", "first", "last", "long", "great", "little", "own", "other",
    "only", "also", "just", "now", "very", "even", "still", "well",
]

# 完整的常見單字列表 (用於深度暖機)
_WARMUP_WORDS_FULL = _WARMUP_WORDS_FAST + [
    # 冠詞/代詞/連接詞
    "the", "a", "an", "and", "or", "but", "if", "then", "else",
    "this", "that", "these", "those", "it", "its", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "can", "may", "might", "must",
    "i", "you", "he", "she", "we", "they", "my", "your", "his", "her", "our", "their",
    "me", "him", "us", "them", "who", "what", "where", "when", "why", "how",
    
    # 介詞
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "about",
    "into", "through", "during", "before", "after", "above", "below", "between",
    
    # 常見動詞
    "use", "used", "using", "make", "made", "making", "get", "got", "getting",
    "go", "went", "going", "come", "came", "coming", "see", "saw", "seeing",
    "know", "knew", "knowing", "think", "thought", "thinking",
    "take", "took", "taking", "give", "gave", "giving", "find", "found", "finding",
    "want", "need", "try", "call", "work", "run", "running", "build", "building",
    "create", "created", "creating", "add", "added", "adding",
    "set", "setting", "start", "started", "starting", "stop", "stopped",
    "read", "write", "writing", "open", "close", "save", "load", "loading",
    
    # 常見名詞
    "time", "year", "people", "way", "day", "man", "thing", "woman", "life",
    "child", "world", "school", "state", "family", "student", "group", "country",
    "problem", "hand", "part", "place", "case", "week", "company", "system",
    "program", "question", "work", "government", "number", "night", "point",
    "home", "water", "room", "mother", "area", "money", "story", "fact",
    "month", "lot", "right", "study", "book", "eye", "job", "word", "business",
    "issue", "side", "kind", "head", "house", "service", "friend", "father",
    "power", "hour", "game", "line", "end", "member", "law", "car", "city",
    "community", "name", "president", "team", "minute", "idea", "kid", "body",
    "information", "back", "parent", "face", "others", "level", "office", "door",
    "health", "person", "art", "war", "history", "party", "result", "change",
    "morning", "reason", "research", "girl", "guy", "moment", "air", "teacher",
    "force", "education",
    
    # 技術相關
    "code", "data", "file", "function", "class", "method", "variable", "type",
    "string", "number", "array", "object", "list", "value", "key", "name",
    "error", "bug", "test", "testing", "debug", "debugging", "log", "logging",
    "server", "client", "request", "response", "api", "web", "app", "application",
    "database", "table", "query", "index", "user", "admin", "config", "setting",
    "input", "output", "process", "thread", "memory", "storage", "cache", "buffer",
    "network", "protocol", "port", "host", "url", "path", "route", "endpoint",
    "version", "update", "install", "deploy", "release", "build", "compile",
    "import", "export", "module", "package", "library", "framework", "tool",
    "development", "production", "environment", "container", "image", "service",
    "machine", "learning", "model", "training", "neural", "deep", "layer",
    "performance", "optimization", "algorithm", "structure", "pattern", "design",
    
    # 形容詞/副詞
    "new", "first", "last", "long", "great", "little", "own", "other", "old",
    "right", "big", "high", "different", "small", "large", "next", "early",
    "young", "important", "few", "public", "bad", "same", "able", "good", "best",
    "better", "sure", "free", "full", "special", "easy", "clear", "recent",
    "certain", "personal", "open", "red", "hard", "available", "likely", "short",
    "single", "medical", "national", "final", "main", "real", "local", "current",
    "only", "also", "just", "now", "very", "even", "still", "already", "always",
    "never", "often", "sometimes", "usually", "really", "actually", "probably",
    "maybe", "perhaps", "certainly", "definitely", "especially", "particularly",
    
    # 數字相關
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "first", "second", "third", "zero", "hundred", "thousand", "million",
]


def warmup_ipa_cache(additional_words: list = None, verbose: bool = False, mode: str = "fast"):
    """
    預熱 IPA 快取
    
    在初始化時調用此函數，可預先將常見單字的 IPA 載入快取，
    避免首次校正時的延遲。
    
    Args:
        additional_words: 額外要預熱的單字列表
        verbose: 是否顯示進度資訊
        mode: 暖機模式
            - "fast": 只預熱最常見的 ~100 個詞 (約 1-2 秒)
            - "full": 預熱完整的 ~400 個詞 (約 5-7 秒)  
            - "aggressive": 批次載入 CMU 字典前 3000 個詞 (約 0.5 秒)
            - "none": 不預熱
    
    Returns:
        int: 預熱的單字數量
    """
    if mode == "none":
        return 0
    
    # 激進模式：直接從 CMU 資料庫批次載入
    if mode == "aggressive":
        return _batch_warmup_from_db(verbose=verbose)
    
    if mode == "fast":
        words_to_cache = list(_WARMUP_WORDS_FAST)
    else:  # full
        words_to_cache = list(_WARMUP_WORDS_FULL)
    
    if additional_words:
        words_to_cache.extend(additional_words)
    
    # 去重
    words_to_cache = list(set(words_to_cache))
    
    if verbose:
        print(f"預熱 IPA 快取: {len(words_to_cache)} 個單字...")
    
    for word in words_to_cache:
        cached_ipa_convert(word)
    
    if verbose:
        stats = get_english_cache_stats()
        print(f"預熱完成: {stats.currsize} 個單字已快取")
    
    return len(words_to_cache)


def _batch_warmup_from_db(limit: int = 3000, verbose: bool = False) -> int:
    """
    從 CMU 字典資料庫批次載入 IPA 資料到快取 (使用多執行緒加速)
    
    這個方法使用多執行緒並行化 eng_to_ipa.convert() 調用，
    達到約 5x 加速效果。
    
    Args:
        limit: 最多載入多少個詞 (預設 3000，約需 2-4 秒)
        verbose: 是否顯示進度
        
    Returns:
        int: 實際載入的詞彙數量
    """
    import sqlite3
    from os.path import join, abspath, dirname
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import eng_to_ipa
    
    db_path = join(abspath(dirname(eng_to_ipa.__file__)), 'resources/CMU_dict.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 取得常見詞彙 (優先取短詞，因為短詞更常見)
        cursor.execute(
            'SELECT DISTINCT word FROM dictionary ORDER BY length(word), word LIMIT ?', 
            (limit,)
        )
        words = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if verbose:
            print(f"使用多執行緒預熱 {len(words)} 個詞彙...")
        
        # 使用多執行緒並行調用 cached_ipa_convert
        # 每個執行緒會各自建立 SQLite 連接，但並行化可達 5x+ 加速
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(cached_ipa_convert, w) for w in words]
            for _ in as_completed(futures):
                pass
        
        if verbose:
            stats = get_english_cache_stats()
            print(f"多執行緒預熱完成: {stats.currsize} 個詞彙已快取")
        
        return len(words)
        
    except Exception as e:
        if verbose:
            print(f"批次預熱失敗: {e}")
        return 0


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
        2. 展開縮寫 (如 IBM -> I B M, js -> J S)
        3. 展開數字 (如 1 -> one)
        4. 使用 eng_to_ipa 庫轉換為 IPA (使用快取)
        5. 處理未知詞彙 (嘗試按字母發音)
        6. 移除重音符號與空格，產生連續的音素序列以便比對

        Args:
            text: 輸入英文文本

        Returns:
            str: 處理後的 IPA 字串
        """
        # 常見的縮寫列表 (小寫形式)
        COMMON_ABBREVIATIONS = {'js', 'ts', 'py', 'rb', 'go', 'rs', 'cs', 'db', 'ml', 'ai', 'ui', 'ux', 'api', 'sql', 'css', 'xml', 'sdk'}

        # 縮寫的啟發式處理:
        # 如果是全大寫且長度較短 (<=5)，視為縮寫，強制分開字母發音
        # 例如: "IBM" -> "I B M" -> /aɪ bi ɛm/
        # 若不分開，"IBM" 可能被嘗試當作一個單字發音，結果可能不準確
        if text.isupper() and len(text) <= 5 and text.isalpha():
             text = " ".join(list(text))
        # 也處理常見的小寫縮寫 (如 js, py)
        elif text.lower() in COMMON_ABBREVIATIONS and text.isalpha():
            text = " ".join(list(text.upper()))
        
        # 簡單的數字正規化 (針對剩餘的數字)
        # 將數字轉換為對應的英文單字，以便取得正確發音
        # 例如: "2" -> "two "
        text = text.replace("0", "zero ").replace("1", "one ").replace("2", "two ")\
                   .replace("3", "three ").replace("4", "four ").replace("5", "five ")\
                   .replace("6", "six ").replace("7", "seven ").replace("8", "eight ")\
                   .replace("9", "nine ")

        # 使用快取版的 IPA 轉換 (大幅提升效能)
        result = cached_ipa_convert(text)
        
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
                    split_result = cached_ipa_convert(split_text)
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
        min_len = min(len(phonetic1), len(phonetic2))
        
        if max_len == 0:
            return True
        
        # 長度差異檢查：如果兩個字串長度差異超過 50%，不匹配
        # 這可以避免短詞誤匹配到長詞
        if min_len > 0 and (max_len - min_len) / min_len > 0.5:
            return False
        
        ratio = dist / max_len
        tolerance = self.get_tolerance(max_len)
        
        # 額外檢查：首音素必須相同或相似
        # 這可以避免如 "popular" 誤匹配 "Angular" 的問題
        if len(phonetic1) > 0 and len(phonetic2) > 0:
            if not self._are_first_phonemes_similar(phonetic1, phonetic2):
                # 如果首音素不相似，使用更嚴格的 tolerance
                tolerance = min(tolerance, 0.25)
        
        return ratio <= tolerance
    
    def _are_first_phonemes_similar(self, phonetic1: str, phonetic2: str) -> bool:
        """
        檢查兩個 IPA 字串的首音素是否相似
        
        這有助於避免如 "popular" (pɑpjələr) 誤匹配 "Angular" (æŋgjələr)
        """
        if not phonetic1 or not phonetic2:
            return True
            
        first1 = phonetic1[0]
        first2 = phonetic2[0]
        
        if first1 == first2:
            return True
        
        # 定義相似的首音素群組
        similar_groups = [
            {'p', 'b'},           # 雙唇塞音
            {'t', 'd'},           # 齒齦塞音
            {'k', 'g'},           # 軟顎塞音
            {'f', 'v'},           # 唇齒擦音
            {'s', 'z'},           # 齒齦擦音
            {'θ', 'ð'},           # 齒間擦音
            {'ʃ', 'ʒ'},           # 後齒齦擦音
            {'ʧ', 'ʤ'},           # 後齒齦塞擦音
            {'m', 'n', 'ŋ'},      # 鼻音
            {'l', 'r'},           # 流音
            {'w', 'ʍ'},           # 滑音
            {'i', 'ɪ', 'e', 'ɛ'}, # 前元音
            {'u', 'ʊ', 'o', 'ɔ'}, # 後元音
            {'a', 'ɑ', 'æ', 'ʌ'}, # 低元音/央元音
        ]
        
        for group in similar_groups:
            if first1 in group and first2 in group:
                return True
        
        return False

    def get_tolerance(self, length: int) -> float:
        """
        根據 IPA 字串長度動態調整容錯率

        策略 (調整為更嚴格):
        - 短詞 (<=3): 容錯率低 (0.15)，避免誤匹配
        - 中詞 (<=5): 容錯率中 (0.25)
        - 長詞 (<=8): 容錯率中高 (0.30)
        - 超長詞 (>8): 容錯率高 (0.35)

        Args:
            length: IPA 字串長度

        Returns:
            float: 容錯率閾值
        """
        if length <= 3: return 0.15  # 短詞非常嚴格
        if length <= 5: return 0.25  # 中詞
        if length <= 8: return 0.30  # 長詞
        return 0.35  # 超長詞

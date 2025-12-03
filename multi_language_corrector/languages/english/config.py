"""
英文模糊音配置模組

集中管理英文 ASR 錯誤的模式與規則。
"""


class EnglishPhoneticConfig:
    """英文語音配置類別 - 集中管理英文模糊音規則"""
    
    # 常見的字母/數字音似混淆
    # 格式: 字母 -> [可能被聽成的變體]
    # 範例: 'E' 可能被聽成 '1' (one 的發音)
    LETTER_NUMBER_CONFUSIONS = {
        'E': ['1', 'e'],      # E sounds like "one" in some accents
        'B': ['b', 'be'],
        'C': ['c', 'see', 'sea'],
        'G': ['g', 'gee'],
        'I': ['i', 'eye', 'ai'],
        'J': ['j', 'jay'],
        'K': ['k', 'kay'],
        'O': ['o', 'oh', '0'],
        'P': ['p', 'pee'],
        'Q': ['q', 'queue', 'cue'],
        'R': ['r', 'are'],
        'T': ['t', 'tee', 'tea'],
        'U': ['u', 'you'],
        'Y': ['y', 'why'],
        '2': ['two', 'to', 'too'],
        '4': ['four', 'for'],
        '8': ['eight', 'ate'],
    }
    
    # 常見拼寫錯誤模式 (正規表達式: 正確 -> 錯誤變體)
    # 格式: (pattern, replacement)
    SPELLING_PATTERNS = [
        # 雙字母簡化
        (r'(.)\1', r'\1'),           # tt -> t, ss -> s
        # 常見混淆
        (r'ph', 'f'),                # python -> fython
        (r'th', 't'),                # python -> pyton  
        (r'ow', 'o'),                # flow -> flo
        (r'ck', 'k'),                # back -> bak
        (r'tion', 'shun'),           # station -> stashun
        (r'y$', 'i'),                # happy -> happi
        (r'^ph', 'f'),               # phone -> fone
    ]
    
    # 常見 ASR 分詞模式
    # 格式: 原始詞根 -> [可能的 ASR 錯誤分詞]
    ASR_SPLIT_PATTERNS = {
        'tensor': ['ten so', 'ten sor', 'tense or'],
        'flow': ['flo', 'floor'],
        'script': ['scrip', 'scrypt'],
        'python': ['pie thon', 'pi thon', 'pyton'],
        'java': ['jav a', 'java'],
        'react': ['re act', 'reac'],
        'torch': ['tor ch', 'tourch'],
    }
    
    # IPA 相似音映射 (用於發音比對)
    # 格式: 音素 -> [可互換的相似音素]
    IPA_FUZZY_MAP = {
        'ɪ': ['i', 'ɛ'],      # bit vs beat vs bet
        'æ': ['e', 'ɛ'],      # cat vs bet
        'ɑ': ['ɔ', 'ʌ'],      # cot vs caught vs cut
        'ʊ': ['u'],           # book vs boot
        'θ': ['t', 'f'],      # think -> tink/fink
        'ð': ['d', 'z'],      # the -> de/ze
        'ŋ': ['n'],           # sing -> sin
    }
    
    # 默認容錯率 (IPA Levenshtein 距離 / 最大長度)
    DEFAULT_TOLERANCE = 0.40

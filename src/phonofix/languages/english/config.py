"""
英文模糊音配置模組

集中管理英文常見的語音相似/拼寫錯誤模式與規則。

注意：英文語音功能依賴系統套件 espeak-ng（詳見 README）。
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
        (r'er$', 'a'),               # docker -> docka
        (r'er$', 'er'),              # 保留原形
        (r'or$', 'er'),              # tensor -> tenser
        (r'le$', 'el'),              # google -> googel

        (r'que$', 'k'),              # technique -> technik
    ]

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

    # 相似音素群組 (用於首音素檢查與模糊比對)
    FUZZY_PHONEME_GROUPS = [
        {"p", "b"},           # 雙唇塞音
        {"t", "d"},           # 齒齦塞音
        {"k", "g", "ɡ"},      # 軟顎塞音（含 IPA g: ɡ）
        {"f", "v"},           # 唇齒擦音
        {"s", "z"},           # 齒齦擦音
        {"θ", "ð"},           # 齒間擦音
        {"ʃ", "ʒ"},           # 後齒齦擦音
        {"ʧ", "ʤ", "t", "d"}, # 塞擦音
        {"m", "n", "ŋ"},      # 鼻音
        {"l", "r", "ɹ"},      # 流音 (espeak 用 ɹ 表示 r)
        {"w", "ʍ"},           # 滑音
        {"i", "ɪ", "e", "ɛ"}, # 前元音
        {"u", "ʊ", "o", "ɔ"}, # 後元音
        {"a", "ɑ", "æ", "ʌ", "ɐ"}, # 低元音/央元音（含 ɐ：phonemizer 常用於弱讀 a）
    ]

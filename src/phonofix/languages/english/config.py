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
    
    # 常見分詞模式（常見來源包含 ASR/語音輸入）
    # 格式: 原始詞根 -> [可能的錯誤分詞]
    # 擴展: 涵蓋更多常見技術詞彙的錯誤分詞
    ASR_SPLIT_PATTERNS = {
        # 基礎模式
        'tensor': ['ten so', 'ten sor', 'tense or', 'ten sir'],
        'flow': ['flo', 'floor', 'flew'],
        'script': ['scrip', 'scrypt', 'scrip t'],
        'python': ['pie thon', 'pi thon', 'pyton', 'pie ton'],
        'java': ['jav a', 'java', 'jawa'],
        'react': ['re act', 'reac', 'ree act'],
        'torch': ['tor ch', 'tourch', 'torque'],
        
        # Docker/Kubernetes 相關
        'docker': ['dock er', 'doc ker', 'dauker', 'docket'],
        'kube': ['cube', 'coop', 'koop', 'cue be'],
        'kubernetes': ['cooper net ease', 'cooper net is', 'cube er net ease', 
                       'kube er net ease', 'cooper nettys', 'cube net ease'],
        'container': ['con tainer', 'contain er'],
        
        # 雲端平台
        'azure': ['a sure', 'ash er', 'as your', 'asher', 'ashore'],
        'aws': ['a w s', 'A W S'],
        'gcp': ['g c p', 'G C P', 'gee see pee'],
        
        # 資料科學
        'numpy': ['num pie', 'num py', 'numb pie', 'numb pi'],
        'pandas': ['pan das', 'pan does', 'panda s', 'panda as'],
        'scipy': ['sigh pie', 'sci pie', 'sy py'],
        
        # AI/ML
        'openai': ['open a i', 'open ai', 'open eye'],
        'chatgpt': ['chat g p t', 'chat gee pee tee', 'chad gpt', 'chat gbt'],
        'gpt': ['g p t', 'gee pee tee', 'g p tea'],
        
        # 資料庫
        'postgres': ['post gress', 'post gres', 'post grace'],
        'postgresql': ['post gress q l', 'post gres q l', 'post gray sql'],
        'mongo': ['mango', 'mon go'],
        'mongodb': ['mango d b', 'mongo d b', 'mango db'],
        'graphql': ['graph q l', 'graph ql', 'graf q l', 'graph cue el'],
        'sql': ['sequel', 's q l', 'es q l'],
        
        # Web 框架
        'django': ['jango', 'd jango', 'jan go', 'gene go'],
        'fastapi': ['fast a p i', 'fast api', 'fast a pie'],
        'flask': ['flas k', 'flask'],
        'express': ['ex press', 'express'],
        'angular': ['ang you lar', 'ang u lar', 'angle ar', 'angle lar'],
        'vue': ['view', 'v u e', 'vee you', 'vew'],
        
        # 認證/協議
        'oauth': ['o auth', 'oh auth', 'o off'],
        'https': ['h t t p s', 'http s', 'h t t p es'],
        'http': ['h t t p', 'h t tp'],
        'api': ['a p i', 'a pie', 'ay p i'],
        
        # 資料格式
        'json': ['jay son', 'jason', 'j son', 'jaysawn'],
        'xml': ['x m l', 'ex em el'],
        'yaml': ['yam l', 'yam el', 'y a m l'],
        'csv': ['c s v', 'see s v'],
        
        # 硬體
        'cpu': ['c p u', 'see pee you', 'see p u'],
        'gpu': ['g p u', 'gee pee you', 'g p you'],
        'ram': ['r a m', 'random'],
        'ssd': ['s s d', 'es s d', 'es es dee'],
        
        # 其他常見技術詞
        'typescript': ['type script', 'type scrip', 'type scrypt'],
        'javascript': ['java script', 'java scrip', 'jav a script'],
        'github': ['git hub', 'git up', 'get hub'],
        'gitlab': ['git lab', 'git lap', 'get lab'],
        'node': ['no d', 'nod', 'node'],
        'npm': ['n p m', 'en pee em'],
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

    # 相似音素群組 (用於首音素檢查與模糊比對)
    FUZZY_PHONEME_GROUPS = [
        {"p", "b"},           # 雙唇塞音
        {"t", "d"},           # 齒齦塞音
        {"k", "g"},           # 軟顎塞音
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
        {"a", "ɑ", "æ", "ʌ"}, # 低元音/央元音
    ]

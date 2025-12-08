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
        (r'er$', 'a'),               # docker -> docka
        (r'er$', 'er'),              # 保留原形
        (r'or$', 'er'),              # tensor -> tenser
                (r'le$', 'el'),              # google -> googel

        (r'que$', 'k'),              # technique -> technik
    ]
    
    # 常見 ASR 分詞模式
    # 格式: 原始詞根 -> [可能的 ASR 錯誤分詞]
    # 擴展: 涵蓋更多常見技術詞彙的 ASR 錯誤
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

    # ========== IPA 音素模糊規則系統（新增用於 Task 5.1）==========

    # 1. 清濁音混淆（Voicing Confusions）
    # 清音與濁音在某些 ASR 系統中容易混淆
    IPA_VOICING_CONFUSIONS = [
        ('p', 'b'),   # pit ↔ bit
        ('t', 'd'),   # ten ↔ den
        ('k', 'ɡ'),   # cap ↔ gap / coat ↔ goat
        ('f', 'v'),   # fan ↔ van / safe ↔ save
        ('s', 'z'),   # seal ↔ zeal / rice ↔ rise
        ('θ', 'ð'),   # think ↔ this / ether ↔ either
        ('ʃ', 'ʒ'),   # mesh ↔ measure / leash ↔ leisure
        ('tʃ', 'dʒ'), # ch ↔ j / cheap ↔ jeep / batch ↔ badge
    ]

    # 2. 長短元音混淆（Vowel Length Confusions）
    # 長元音與短元音在快速語音中容易混淆
    IPA_VOWEL_LENGTH_CONFUSIONS = [
        ('iː', 'ɪ'),  # sheep ↔ ship / beat ↔ bit
        ('uː', 'ʊ'),  # pool ↔ pull / food ↔ foot
        ('ɔː', 'ɒ'),  # bought ↔ bot (UK accent)
        ('ɑː', 'æ'),  # bath ↔ bat (UK vs US difference)
        ('ɜː', 'ə'),  # bird ↔ about (stressed vs unstressed)
        ('eɪ', 'e'),  # late ↔ let / bait ↔ bet
        ('oʊ', 'ɔ'),  # boat ↔ bought / coat ↔ caught
        ('aɪ', 'a'),  # bite ↔ bat / time ↔ tam
        ('aʊ', 'a'),  # bout ↔ bat / house ↔ has
    ]

    # 3. 相似音素混淆（Similar Phone Confusions）
    # 發音位置或方式相似的音素容易混淆
    IPA_SIMILAR_PHONE_CONFUSIONS = [
        ('θ', 'f'),   # think → fink / three → free
        ('ð', 'v'),   # this → vis / breathe → breave
        ('θ', 's'),   # think → sink / math → mass
        ('ð', 'z'),   # this → zis / bathe → baze
        ('r', 'l'),   # rice ↔ lice / right ↔ light (L2 speakers)
        ('n', 'm'),   # pan ↔ pam / sin ↔ sim
        ('ŋ', 'n'),   # sing ↔ sin / hang ↔ han
        ('w', 'v'),   # wine ↔ vine / west ↔ vest (some accents)
        ('b', 'v'),   # berry ↔ very / boat ↔ vote (some L2)
        ('p', 'f'),   # peel ↔ feel / pain ↔ fain (rare)
        ('ʃ', 's'),   # sheep ↔ seep / wash ↔ was
        ('ʒ', 'z'),   # measure ↔ mezure / vision ↔ vizon
        ('tʃ', 'ʃ'),  # choose ↔ shoes / church ↔ shurch
        ('dʒ', 'ʒ'),  # judge ↔ zhuzhe / bridge ↔ brizhe
        ('j', 'dʒ'),  # year ↔ jeer / yes ↔ jess
    ]

    # 4. 音節簡化與弱讀規則（Reduction Rules）
    # 快速語音中常見的音素省略或變化
    IPA_REDUCTION_RULES = [
        ('ə', ''),      # schwa deletion / about → bout
        ('t̬', 'd'),     # flapping / water → wader / better → bedder
        ('t', ''),      # t-deletion / interest → ineres
        ('d', ''),      # d-deletion / and → an
        ('h', ''),      # h-dropping / house → ouse (some accents)
        ('ŋɡ', 'ŋ'),    # g-dropping / singing → singin
        ('kw', 'k'),    # simplification / quick → kick
        ('str', 'sr'),  # cluster reduction / street → sreet
        ('nt', 'n'),    # cluster reduction / want → wan
        ('nd', 'n'),    # cluster reduction / and → an
        ('ld', 'l'),    # cluster reduction / old → ol
    ]

    # 5. 重音位置變化（Stress Pattern Variations）
    # 不同重音位置可能導致元音變化
    IPA_STRESS_VARIATIONS = [
        ('ˈ', 'ˌ'),  # 主重音 ↔ 次重音
        ('ˈ', ''),   # 主重音省略
        ('ˌ', ''),   # 次重音省略
    ]

    # 6. 常見二合字母發音變體（Digraph Variations）
    # 這些用於 IPA → 拼寫映射
    IPA_TO_GRAPHEME_MAP = {
        # 基本輔音（單字母）
        'p': ['p'],                     # pen
        'b': ['b'],                     # bat
        't': ['t', 'tt'],               # top, butter
        'd': ['d', 'dd'],               # dog, ladder
        'k': ['k', 'c', 'ck'],          # kit, cat, back
        'ɡ': ['g', 'gg'],               # go, egg
        'f': ['f', 'ff', 'ph'],         # fan, off, phone
        'v': ['v'],                     # van
        's': ['s', 'ss', 'c'],          # sun, pass, city
        'z': ['z', 'zz', 's'],          # zoo, buzz, is
        'm': ['m', 'mm'],               # man, hammer
        'n': ['n', 'nn'],               # net, dinner
        'l': ['l', 'll'],               # leg, bell
        'r': ['r', 'rr'],               # red, carry
        'h': ['h'],                     # hat

        # 複雜輔音
        'θ': ['th'],                    # think
        'ð': ['th'],                    # this
        'ʃ': ['sh', 'ti', 'ci', 'ch'],  # ship, station, special, chef
        'ʒ': ['s', 'si', 'zi', 'g'],    # measure, vision, azure, beige
        'tʃ': ['ch', 'tch', 't'],       # chip, catch, nature
        'dʒ': ['j', 'g', 'dge', 'dg'],  # jump, age, badge, judge
        'ŋ': ['ng', 'n'],               # sing, think
        'j': ['y', 'i'],                # yes, onion
        'w': ['w', 'u', 'o'],           # we, quick, one

        # 元音（單元音）
        'iː': ['ee', 'ea', 'e', 'ie', 'ei', 'i'],  # bee, eat, me, field, receive, ski
        'ɪ': ['i', 'y', 'e'],                      # bit, gym, pretty
        'e': ['e', 'ea'],                          # bed, bread
        'ɛ': ['e', 'ea'],                          # bed, bread (alternative notation)
        'æ': ['a'],                                # cat
        'ɑ': ['a', 'o'],                           # father, hot (US)
        'ɑː': ['a', 'ar', 'ah'],                   # father, car, ah
        'ɒ': ['o', 'a'],                           # hot, want (UK)
        'ɔ': ['o', 'aw', 'au'],                    # dog, law, caught
        'ɔː': ['or', 'aw', 'au', 'al'],            # for, saw, cause, talk
        'ʊ': ['oo', 'u', 'ou'],                    # book, put, could
        'uː': ['oo', 'u', 'ue', 'ew', 'o'],        # food, rule, blue, new, do
        'ʌ': ['u', 'o', 'ou'],                     # but, son, young
        'ɜː': ['er', 'ir', 'ur', 'or'],            # her, bird, turn, word
        'ə': ['a', 'e', 'o', 'u', 'i'],            # about, taken, lemon, focus, pencil

        # 雙元音（按頻率排序）
        'eɪ': ['a', 'ay', 'ai', 'ey', 'ea'],       # make, day, rain, they, great
        'aɪ': ['y', 'i', 'igh', 'ie'],             # my, time, high, pie
        'ɔɪ': ['oy', 'oi'],                        # boy, coin
        'oʊ': ['o', 'ow', 'oa'],                   # go, low, boat
        'aʊ': ['ou', 'ow'],                        # out, now
        'ɪə': ['ear', 'eer', 'ere'],               # hear, beer, here
        'eə': ['are', 'air', 'ear'],               # care, fair, bear
        'ʊə': ['ure', 'our'],                      # pure, tour
    }

    # 7. 音素組合優先級（用於生成拼寫時選擇最常見的組合）
    GRAPHEME_FREQUENCY_WEIGHTS = {
        'θ': {'th': 1.0},
        'ð': {'th': 1.0},
        'ʃ': {'sh': 0.7, 'ti': 0.15, 'ci': 0.1, 'ch': 0.05},
        'tʃ': {'ch': 0.8, 'tch': 0.15, 't': 0.05},
        'dʒ': {'j': 0.5, 'g': 0.3, 'dge': 0.15, 'dg': 0.05},
        'iː': {'ee': 0.4, 'ea': 0.3, 'e': 0.15, 'ie': 0.1, 'ei': 0.03, 'i': 0.02},
        'eɪ': {'ay': 0.35, 'ai': 0.3, 'a_e': 0.25, 'ey': 0.07, 'ea': 0.03},
    }

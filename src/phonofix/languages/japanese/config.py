"""
日文配置模組

定義日文發音與修正相關的配置參數。
"""

from dataclasses import dataclass


@dataclass
class JapanesePhoneticConfig:
    """
    日文發音配置

    Attributes:
        use_foreign_spelling (bool): 是否使用外來語拼寫 (例如 'Camera' vs 'Kamera')。
                                     預設為 False，統一轉為羅馬拼音以利比對。
        system (str): 拼音系統，預設為 'hepburn' (赫本式)。
    """
    use_foreign_spelling: bool = False
    system: str = "hepburn"

    # =========================================================================
    # 1. 羅馬拼音變體映射 (Romanization Variants)
    # =========================================================================
    # 處理不同羅馬拼音系統 (Hepburn vs Kunrei-shiki) 的差異
    # 以及常見的輸入法變體
    ROMANIZATION_VARIANTS = {
        "si": "shi",
        "ti": "chi",
        "tu": "tsu",
        "hu": "fu",
        "zi": "ji",
        "di": "ji",  # ぢ (di/ji)
        "du": "zu",  # づ (du/zu)
        "sya": "sha", "syu": "shu", "syo": "sho",
        "tya": "cha", "tyu": "chu", "tyo": "cho",
        "zya": "ja", "zyu": "ju", "zyo": "jo",
        "cya": "cha", "cyu": "chu", "cyo": "cho",
        "jya": "ja", "jyu": "ju", "jyo": "jo",
        # L/R 混淆 (日文不分 L/R，ASR 可能混用)
        "la": "ra", "li": "ri", "lu": "ru", "le": "re", "lo": "ro",
    }

    # =========================================================================
    # 2. 長音模糊規則 (Fuzzy Long Vowels)
    # =========================================================================
    # 定義長音與短音的對應，ASR 常忽略長音或將其正規化
    # 策略：將長音映射回短音進行模糊比對
    FUZZY_LONG_VOWELS = {
        "aa": "a",
        "ii": "i",
        "uu": "u",
        "ee": "e",
        "ei": "e",  # 先生 (sensei) -> sensee -> sense
        "oo": "o",
        "ou": "o",  # 東京 (toukyou) -> tokyo
    }

    # =========================================================================
    # 3. 助詞模糊規則 (Fuzzy Particles)
    # =========================================================================
    # 處理助詞發音與書寫差異 (wa/ha, o/wo, e/he)
    # 注意：這通常需要上下文判斷，但在模糊比對時可視為變體
    FUZZY_PARTICLES = {
        "ha": "wa", # は (ha) 作為助詞讀作 wa
        "wo": "o",  # を (wo) 讀作 o
        "he": "e",  # へ (he) 作為助詞讀作 e
    }

    # =========================================================================
    # 4. 促音模糊規則 (Fuzzy Gemination)
    # =========================================================================
    # 處理促音 (小 tsu) 遺漏或多餘
    # 策略：將雙子音映射回單子音
    FUZZY_GEMINATION = {
        "kk": "k",
        "tt": "t",
        "pp": "p",
        "ss": "s",
        "shsh": "sh", # zasshi -> zashi
        "tch": "ch",  # matchi -> machi
        "dd": "d",
        "gg": "g",
        "bb": "b",
    }
    
    # =========================================================================
    # 5. 鼻音模糊規則 (Fuzzy Nasals)
    # =========================================================================
    # 處理 n/m 混淆 (撥音ん在 b, p, m 前讀作 m)
    # 例如：新聞 (shinbun) -> shimbun
    FUZZY_NASALS = {
        "mb": "nb",
        "mp": "np",
        "mm": "nm",
    }

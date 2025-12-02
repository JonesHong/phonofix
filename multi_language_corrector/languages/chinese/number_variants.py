"""
中文數字發音變體配置

此模組定義了中文數字在不同場景下的發音變體對應。
主要用於處理 ASR 識別時數字的不同讀法。

狀態: 尚未啟用，僅作為參考配置
啟用方式: 將 ENABLE_NUMBER_VARIANTS 設為 True，並在 dictionary_generator.py 中整合

用例場景:
- 電話號碼: 1 讀作 "幺"，0 讀作 "洞"
- 軍事/無線電通訊: 7 讀作 "拐"，9 讀作 "勾"
- 一般場景: 2 可讀作 "兩"
"""

# ============================================================
# 功能開關 - 設為 True 以啟用數字變體處理
# ============================================================
ENABLE_NUMBER_VARIANTS = False


# ============================================================
# 數字變體定義
# ============================================================

# 有發音變體的數字 (共 6 個)
# 格式: { 數字: { "standard": 標準讀音, "variants": [變體讀音列表] } }
NUMBER_PHONETIC_VARIANTS = {
    "0": {
        "standard": "líng",      # 零
        "variants": ["dòng"],    # 洞 (電話/軍事)
        "chars": {
            "standard": "零",
            "variants": ["洞"]
        }
    },
    "1": {
        "standard": "yī",        # 一
        "variants": ["yāo"],     # 幺 (電話/軍事)
        "chars": {
            "standard": "一",
            "variants": ["幺"]
        }
    },
    "2": {
        "standard": "èr",        # 二
        "variants": ["liǎng"],   # 兩 (量詞前)
        "chars": {
            "standard": "二",
            "variants": ["兩"]
        }
    },
    "6": {
        "standard": "liù",       # 六
        "variants": ["lù"],      # 陸 (大寫)
        "chars": {
            "standard": "六",
            "variants": ["陸"]
        }
    },
    "7": {
        "standard": "qī",        # 七
        "variants": ["guǎi"],    # 拐 (軍事通訊)
        "chars": {
            "standard": "七",
            "variants": ["拐"]
        }
    },
    "9": {
        "standard": "jiǔ",       # 九
        "variants": ["gǒu"],     # 勾 (軍事通訊)
        "chars": {
            "standard": "九",
            "variants": ["勾"]
        }
    },
}

# 無發音變體的數字 (共 5 個) - 僅供參考，無需處理
NUMBER_NO_VARIANTS = {
    "3": "sān",   # 三/參 (同音)
    "4": "sì",    # 四/肆 (同音)
    "5": "wǔ",    # 五/伍 (同音)
    "8": "bā",    # 八/捌 (同音)
    "10": "shí",  # 十/拾 (同音)
}


# ============================================================
# 常見數字型號/術語的預設別名
# 可直接加入 term_mapping 使用
# ============================================================
COMMON_NUMBER_ALIASES = {
    # 電話/號碼類
    "110": ["幺幺洞", "一一零"],
    "119": ["幺幺勾", "一一九"],
    "120": ["幺二洞", "一二零"],
    
    # 型號類 (範例)
    "A380": ["A三八零", "A三八洞"],
    "747": ["七四七", "拐四拐"],
    
    # 可根據實際需求擴充
}


# ============================================================
# 工具函數 (未啟用)
# ============================================================

def generate_number_variants(number_str: str) -> list:
    """
    為數字字串生成所有可能的發音變體組合
    
    注意: 此函數目前未啟用
    
    Args:
        number_str: 數字字串，如 "110"
        
    Returns:
        list: 所有可能的變體組合，如 ["幺幺洞", "一一零", "幺一零", ...]
    """
    if not ENABLE_NUMBER_VARIANTS:
        return []
    
    from itertools import product
    
    # 為每個數字收集可能的字元
    char_options = []
    for digit in number_str:
        if digit in NUMBER_PHONETIC_VARIANTS:
            variant_info = NUMBER_PHONETIC_VARIANTS[digit]
            chars = [variant_info["chars"]["standard"]] + variant_info["chars"]["variants"]
            char_options.append(chars)
        elif digit.isdigit():
            # 無變體的數字，使用中文數字
            digit_map = {"3": "三", "4": "四", "5": "五", "8": "八"}
            char_options.append([digit_map.get(digit, digit)])
        else:
            # 非數字字元，保留原樣
            char_options.append([digit])
    
    # 生成所有組合
    variants = ["".join(combo) for combo in product(*char_options)]
    
    return variants


def get_variant_count(length: int) -> int:
    """
    計算 N 位數字最多可能產生的變體數量
    
    假設所有位數都是有變體的數字 (0,1,2,6,7,9)，每位 2 種選擇
    
    Args:
        length: 數字位數
        
    Returns:
        int: 最大變體數量 (2^n)
    """
    return 2 ** length


# ============================================================
# 使用說明
# ============================================================
"""
啟用步驟:

1. 將 ENABLE_NUMBER_VARIANTS 設為 True

2. 在 dictionary_generator.py 中匯入並整合:
   
   from .number_variants import (
       ENABLE_NUMBER_VARIANTS,
       NUMBER_PHONETIC_VARIANTS,
       generate_number_variants
   )

3. 在 _add_sticky_phrase_aliases 或新函數中處理數字:
   
   def _add_number_aliases(self, term_mapping):
       if not ENABLE_NUMBER_VARIANTS:
           return term_mapping
       
       for term, aliases in term_mapping.items():
           # 檢測並處理包含數字的術語
           ...

4. 或者，直接使用 COMMON_NUMBER_ALIASES 加入 term_mapping:
   
   from multi_language_corrector.languages.chinese.number_variants import COMMON_NUMBER_ALIASES
   
   term_mapping = {
       "台北車站": ["北車"],
       **COMMON_NUMBER_ALIASES,  # 加入常見數字別名
   }

注意事項:
- 變體數量會指數增長，建議限制處理的數字長度 (如 ≤5 位)
- 優先使用 COMMON_NUMBER_ALIASES 處理常見術語
- 只在確實需要時才啟用完整的變體生成
"""

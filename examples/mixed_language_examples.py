"""
混合語言校正範例

本檔案展示 UnifiedEngine 的混合語言校正功能：
1. 中英文混合文本的校正
2. 英文拼寫錯誤修正 (IPA 音標比對)
3. 英文詞彙的 keywords/exclude_when 支援
4. 跨語言上下文判斷

架構說明：
- UnifiedCorrector 自動偵測語言區塊
- 中文區塊使用 ChineseCorrector (拼音比對)
- 英文區塊使用 EnglishCorrector (IPA 音標比對)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from phonofix import UnifiedEngine

# 全域 Engine (單例模式，避免重複初始化)
engine = UnifiedEngine()


# =============================================================================
# 範例 1: 基礎混合語言校正
# =============================================================================
def example_1_basic_mixed():
    """
    基礎用法：同時處理中英文錯誤
    """
    print("=" * 60)
    print("範例 1: 基礎混合語言校正")
    print("=" * 60)

    corrector = engine.create_corrector({
        # 中文詞彙 (使用簡稱作為別名)
        "台北車站": ["北車"],
        
        # 英文詞彙 (常見拼寫錯誤)
        "Python": ["Pyton", "Pyson", "Phython"],
        "JavaScript": ["java script", "Java Script"],
        "TensorFlow": ["Ten so floor", "Tensor flow", "tensor flow"],
    })

    test_cases = [
        ("我在北車用Pyton寫code", "中文+英文同時修正"),
        ("學習Ten so floor和java script", "多個英文錯誤"),
        ("在台北車站寫Python", "已經正確，無需修正"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print(f"原句: {text}")
        print(f"結果: {result}")
        print(f"說明: {explanation}")
        print()


# =============================================================================
# 範例 2: 英文 Keywords 和 exclude_when
# =============================================================================
def example_2_english_keywords_exclude_when():
    """
    英文詞彙也支援 keywords 和 exclude_when：
    - keywords: 必須匹配才替換 (必要條件)
    - exclude_when: 匹配就不替換 (否決條件)
    """
    print("=" * 60)
    print("範例 2: 英文 Keywords 和 exclude_when")
    print("=" * 60)

    corrector = engine.create_corrector({
        "EKG": {
            "aliases": ["1 kg", "1kg", "one kg"],
            "keywords": ["設備", "心電圖", "檢查", "device", "heart", "medical"],
            "exclude_when": ["水", "公斤", "重", "weight", "kg of"],
        },
        "API": {
            "aliases": ["a p i", "A P I"],
            "keywords": ["接口", "呼叫", "call", "request", "endpoint"],
            "exclude_when": ["藥", "drug", "medicine"],
        }
    })

    test_cases = [
        # EKG 測試
        ("這個 1 kg設備很貴", "有 keywords(設備) → 替換為 EKG"),
        ("這瓶 1kg水很重", "有 exclude_when(水) → 不替換"),
        ("The 1kg device is expensive", "有 keywords(device) → 替換為 EKG"),
        ("買了 1kg的東西", "無 keywords → 不替換"),
        
        # API 測試  
        ("call a p i endpoint", "有 keywords(call+endpoint) → 替換"),
        ("這個a p i藥很有效", "有 exclude_when(藥) → 不替換"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print(f"原句: {text}")
        print(f"結果: {result}")
        print(f"說明: {explanation}")
        print()


# =============================================================================
# 範例 3: 專業術語校正
# =============================================================================
def example_3_technical_terms():
    """
    專業術語的語音辨識校正：
    - 程式語言和框架名稱
    - 縮寫和專有名詞
    """
    print("=" * 60)
    print("範例 3: 專業術語校正")
    print("=" * 60)

    corrector = engine.create_corrector({
        # 程式語言
        "Python": ["Pyton", "python", "pie thon"],
        "JavaScript": ["java script", "Java Script"],
        "TypeScript": ["type script", "Type Script", "typescript"],
        
        # 框架
        "TensorFlow": ["Ten so floor", "tensor flow"],
        "PyTorch": ["pie torch", "Pie Torch"],
        "React": ["re act", "Re Act"],
        
        # 縮寫術語 (需要上下文才替換)
        "API": {
            "aliases": ["a p i", "A P I"],
            "keywords": ["call", "接口", "request", "取得"],
        },
        "GPU": {
            "aliases": ["g p u", "G P U"],
            "keywords": ["顯卡", "運算", "cuda", "計算", "加速"],
        },
    })

    test_cases = [
        "我用Pyton和Ten so floor做機器學習",
        "前端用java script",
        "需要call a p i取得資料",
        "用g p u加速運算比較快",
    ]

    print("修正結果:")
    for text in test_cases:
        result = corrector.correct(text)
        print(f"  原句: {text}")
        print(f"  結果: {result}")
        print()


# =============================================================================
# 範例 4: exclude_when 優先級展示
# =============================================================================
def example_4_exclude_when_priority():
    """
    展示 exclude_when 的優先級：
    - 即使有 keywords 匹配，只要有 exclude_when 匹配就不替換
    """
    print("=" * 60)
    print("範例 4: exclude_when 優先級")
    print("=" * 60)

    corrector = engine.create_corrector({
        "EKG": {
            "aliases": ["1kg", "1 kg"],
            "keywords": ["設備", "device", "醫療", "medical"],
            "exclude_when": ["重", "weight", "公斤", "kilogram"],
        }
    })

    test_cases = [
        ("這個設備有 1kg重", "keywords(設備) + exclude_when(重) → 不替換"),
        ("medical device 1kg weight", "keywords(medical) + exclude_when(weight) → 不替換"),
        ("這個 1kg設備", "keywords(設備) 無 exclude_when → 替換"),
        ("1kg device here", "keywords(device) 無 exclude_when → 替換"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print(f"原句: {text}")
        print(f"結果: {result}")
        print(f"說明: {explanation}")
        print()


# =============================================================================
# 範例 5: 完整測試案例
# =============================================================================
def example_5_full_test():
    """
    完整測試案例：涵蓋所有功能的驗證
    """
    print("=" * 60)
    print("範例 5: 完整測試案例")
    print("=" * 60)

    corrector = engine.create_corrector({
        "台北車站": ["北車"],
        "Python": ["Pyton", "Pyson"],
        "TensorFlow": ["Ten so floor", "Tensor flow"],
        "EKG": {
            "aliases": ["1 kg", "1kg"],
            "keywords": ["設備", "心電圖", "檢查"],
            "exclude_when": ["水", "公斤", "重"],
        },
    })

    test_cases = [
        # 基本中文修正
        ("我在北車用Pyton寫code", "我在台北車站用Python寫code"),
        
        # 已經正確的情況
        ("這個EKG設備很貴", "這個EKG設備很貴"),
        
        # ASR error: 1kg -> EKG (有關鍵字 "設備"，無排除關鍵字)
        ("這個 1 kg設備很貴", "這個 EKG設備很貴"),
        
        # 排除關鍵字: 有 "水"，不替換
        ("這瓶 1kg水很重", "這瓶 1kg水很重"),
        
        # 排除關鍵字優先: 有 "設備" 但也有 "重"，不替換
        ("這個設備有 1kg重", "這個設備有 1kg重"),
        
        # 無關鍵字: 沒有 "設備/心電圖/檢查"，不替換
        ("買了 1kg的東西", "買了 1kg的東西"),
        
        # 有關鍵字: 有 "心電圖"，無排除關鍵字，替換
        ("做心電圖用 1kg機器", "做心電圖用 EKG機器"),
        
        # TensorFlow ASR 錯誤
        ("我正在學習Ten so floor", "我正在學習TensorFlow"),
    ]

    passed = 0
    failed = 0
    
    for input_text, expected in test_cases:
        result = corrector.correct(input_text)
        status = "✅" if result == expected else "❌"
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"Input:    {input_text}")
        print(f"Output:   {result}")
        print(f"Expected: {expected} {status}")
        print("-" * 50)
    
    print(f"\n結果: {passed} 通過, {failed} 失敗")


# =============================================================================
# 主程式
# =============================================================================
if __name__ == "__main__":
    print("\n" + "🌐" * 20)
    print("  混合語言校正範例")
    print("🌐" * 20 + "\n")

    examples = [
        ("基礎混合語言", example_1_basic_mixed),
        ("英文 Keywords/exclude_when", example_2_english_keywords_exclude_when),
        ("專業術語", example_3_technical_terms),
        ("exclude_when 優先級", example_4_exclude_when_priority),
        ("完整測試", example_5_full_test),
    ]

    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"❌ 範例 '{name}' 執行失敗: {e}")
            import traceback
            traceback.print_exc()
        print()

    print("=" * 60)
    print("✅ 所有範例執行完成!")
    print("=" * 60)

from phonofix.correction.unified_corrector import UnifiedCorrector


def test_mixed_correction():
    # Define terms
    # 注意: 自動生成的模糊變體只包含同音/近音字替換
    # 簡稱 (如 "北車") 需要手動指定
    term_mapping = {
        "台北車站": ["北車"],  # 手動指定 "北車" 作為別名
        "Python": ["Pyton", "Pyson"],  # 手動指定常見拼寫錯誤
        "TensorFlow": ["Ten so floor", "Tensor flow"],
        "EKG": {
            "aliases": ["1 kg", "1kg"],
            "keywords": ["設備", "心電圖", "檢查"],  # 必須包含這些關鍵字之一才替換
            "exclusions": ["水", "公斤", "重"],  # 有這些關鍵字就不替換
        },
    }
    # 注意: 現在 exclusions 是每個詞獨立的關鍵字，不需要全域 exclusions
    corrector = UnifiedCorrector(term_mapping)

    test_cases = [
        # 基本中文修正
        ("我在北車用Pyton寫code", "我在台北車站用Python寫code"),
        
        # 已經正確的情況
        ("這個EKG設備很貴", "這個EKG設備很貴"),
        
        # ASR error: 1kg -> EKG (有關鍵字 "設備"，無排除關鍵字)
        # 注意: 原始輸入 "1 kg" 中間有空格，替換後會保留前導空格
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

    print("=" * 50)
    print("Mixed Language Correction Test")
    print("=" * 50)
    print(f"EKG keywords: {term_mapping['EKG']['keywords']}")
    print(f"EKG exclusions: {term_mapping['EKG']['exclusions']}")
    print("=" * 50)
    
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
    
    print(f"\nResult: {passed} passed, {failed} failed")


if __name__ == "__main__":
    test_mixed_correction()

"""
英文語音辨識校正範例

本檔案展示 EnglishEngine 的所有核心功能：
1. 基礎用法 - Engine.create_corrector() 工廠方法
2. 模糊詞典生成 - surface variants + representative variants
3. 發音相似誤聽 - 專有名詞被聽成常見詞彙
4. 上下文關鍵字 - 根據前後文判斷替換 (同音異義詞)
5. 上下文排除 - 避免錯誤修正
6. 權重系統 - 控制替換優先級
7. 同音過濾 - 以 IPA phonetic key 去重，避免詞典膨脹
8. 混合格式配置 - list/dict 混用
9. 長文章校正 - 完整段落測試

注意：自語言模組重構後，surface variants 預設關閉。
如需「自動生成別名（分詞/分隔符/大小寫/可選的代表拼寫）」請建立 Engine 時開啟：
- enable_surface_variants=True
- enable_representative_variants=True  (較 aggressive，會生成更多候選)
"""

from _example_utils import add_repo_to_sys_path, print_case

add_repo_to_sys_path()

from phonofix import EnglishEngine

# 全域 Engine (單例模式，避免重複初始化)
engine = EnglishEngine(verbose=False)


# =============================================================================
# 範例 1: 基礎用法 - 自動生成 IPA 音標索引
# =============================================================================
def example_1_basic_usage():
    """
    最簡單的用法：只提供正確詞彙，系統自動透過 IPA 音標進行模糊比對。
    重點展示：ASR 將專有名詞誤聽為發音相似的常見詞彙。
    """
    print("=" * 60)
    print("範例 1: 基礎用法 (Basic Usage)")
    print("=" * 60)

    # 只需提供正確的詞彙
    corrector = engine.create_corrector(
        [
            "TensorFlow",  # ASR 可能誤聽為 "tensor flow"
            "Kubernetes",  # ASR 可能誤聽為 "cooper net ease"
            "PostgreSQL",  # ASR 可能誤聽為 "post grass sequel"
            "Django",  # ASR 可能誤聽為 "jango" (D 被吃掉)
        ]
    )

    test_cases = [
        ("Learning tensor flow for AI", "ASR 誤聽為常見詞 (tensor flow -> TensorFlow)"),
        ("Deploy on cooper net ease", "發音相似誤聽 (cooper net ease -> Kubernetes)"),
        ("Using post grass sequel database", "發音相似誤聽 (post grass sequel -> PostgreSQL)"),
        ("The jango framework is great", "首字母遺失 (jango -> Django)"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Basic", text, result, explanation)


# =============================================================================
# 範例 2: 手動別名 - 已知的 ASR 錯誤模式
# =============================================================================
def example_2_manual_aliases():
    """
    手動提供別名，處理已知的 ASR 錯誤模式。
    當你知道特定詞彙經常被誤聽為什麼時，可以直接指定。
    """
    print("=" * 60)
    print("範例 2: 手動別名 (Manual Aliases)")
    print("=" * 60)

    corrector = engine.create_corrector({
        # ASR 經常將專有名詞誤聽為發音相似的常見詞組
        "TensorFlow": ["tensor flow", "tens are flow", "ten so flow"],
        "PyTorch": ["pie torch", "pi torch", "by torch"],
        "scikit-learn": ["psychic learn", "sky kit learn", "sigh kit learn"],
    })

    test_cases = [
        ("I learned tens are flow yesterday", "誤聽為常見詞 (tens are flow -> TensorFlow)"),
        ("Training models with pie torch", "誤聽為常見詞 (pie torch -> PyTorch)"),
        ("Using psychic learn for ML", "發音相似誤聽 (psychic learn -> scikit-learn)"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Manual Aliases", text, result, explanation)


# =============================================================================
# 範例 3: 發音相似誤聽 (Phonetic Mishearing)
# =============================================================================
def example_3_phonetic_mishearing():
    """
    處理 ASR 將專有名詞誤聽為發音相似詞彙的情況。
    這是語音辨識最常見的錯誤類型。
    """
    print("=" * 60)
    print("範例 3: 發音相似誤聽 (Phonetic Mishearing)")
    print("=" * 60)

    corrector = engine.create_corrector({
        # 醫療/科學術語經常被誤聽
        "acetaminophen": ["a set a mini fan", "acid a mini fan"],
        "algorithm": ["Al Gore rhythm", "all go rhythm"],
        "Alzheimer's": ["all timers", "old timers"],
    })

    test_cases = [
        ("Take a set a mini fan for pain", "藥名誤聽 (a set a mini fan -> acetaminophen)"),
        ("The Al Gore rhythm is efficient", "術語誤聽 (Al Gore rhythm -> algorithm)"),
        ("My grandma has all timers disease", "疾病名誤聽 (all timers -> Alzheimer's)"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Phonetic", text, result, explanation)


# =============================================================================
# 範例 4: 上下文關鍵字 (Context Keywords)
# =============================================================================
def example_4_context_keywords():
    """
    使用 keywords 進行同音異義詞辨析。
    當 ASR 誤聽結果可能對應多個專有名詞時，根據上下文決定。
    """
    print("=" * 60)
    print("範例 4: 上下文關鍵字 (Context Keywords)")
    print("=" * 60)

    corrector = engine.create_corrector({
        # "cell" 可能是多種專有名詞的誤聽
        "Excel": {
            "aliases": ["egg cell", "ex cell"],
            "keywords": ["spreadsheet", "Microsoft", "table", "formula"],
            "weight": 0.5
        },
        "Axel": {
            "aliases": ["axle", "ex cell"],
            "keywords": ["jump", "skating", "figure", "triple"],
            "weight": 0.5
        },
        # "1 kg" 可能是 EKG 的誤聽
        "EKG": {
            "aliases": ["1 kg", "one kg", "e k g"],
            "keywords": ["heart", "medical", "patient", "monitor"],
            "weight": 0.5
        },
    })

    test_cases = [
        ("Open the egg cell spreadsheet", "上下文: spreadsheet -> Excel"),
        ("She landed a triple ex cell", "上下文: triple/skating -> Axel (花式滑冰跳躍)"),
        ("Check the patient's 1 kg reading", "上下文: patient -> EKG (心電圖)"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Keywords", text, result, explanation)


# =============================================================================
# 範例 5: 上下文排除 (Context Exclusion)
# =============================================================================
def example_5_exclude_when():
    """
    使用 exclude_when 避免錯誤修正。
    當上下文明確表示這不是專有名詞時，不進行替換。
    """
    print("=" * 60)
    print("範例 5: 上下文排除 (Context Exclusion)")
    print("=" * 60)

    corrector = engine.create_corrector({
        # "1 kg" 通常是 EKG 的誤聽，但在重量相關語境則不是
        "EKG": {
            "aliases": ["1 kg", "one kg"],
            "keywords": ["medical", "heart", "patient"],
            "exclude_when": ["weight", "heavy", "kilogram", "weighs", "pounds"],
        },
        # "cell" 可能是 Excel 的誤聽，但在生物學語境則不是
        "Excel": {
            "aliases": ["egg cell"],
            "keywords": ["spreadsheet", "Microsoft"],
            "exclude_when": ["biology", "membrane", "organism", "microscope"],
        }
    })

    test_cases = [
        ("The patient's 1 kg shows normal rhythm", "醫療語境 -> EKG"),
        ("This box weighs 1 kg", "排除詞 'weighs' -> 不修正 (真的是一公斤)"),
        ("Open egg cell in Microsoft", "軟體語境 -> Excel"),
        ("The egg cell under microscope", "排除詞 'microscope' -> 不修正 (真的是卵細胞)"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Exclusion", text, result, explanation)


# =============================================================================
# 範例 6: 權重系統 (Weight System)
# =============================================================================
def example_6_weight_system():
    """
    使用權重控制優先級。
    當同一個誤聽結果可能對應多個專有名詞時，高權重者優先。
    """
    print("=" * 60)
    print("範例 6: 權重系統 (Weight System)")
    print("=" * 60)

    corrector = engine.create_corrector({
        # "neural" 可能被誤聽為多個相似發音的詞
        "NumPy": {
            "aliases": ["numb pie", "num pie"],
            "weight": 0.8  # 較常見，較高優先級
        },
        "Gnome": {
            "aliases": ["numb", "num"],
            "weight": 0.2  # 較少見，較低優先級
        }
    })

    test_cases = [
        ("Import numb pie for arrays", "高權重 -> NumPy (較常見的選擇)"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Weight", text, result, explanation)



# =============================================================================
# 範例 7: 同音過濾 + 變體覆蓋 (Homophone Filtering)
# =============================================================================
def example_7_homophone_filtering():
    """
    展示 EnglishFuzzyGenerator 的覆蓋範圍，以及「同 IPA phonetic key 去重」的效果。
    """
    print("=" * 60)
    print("範例 7: 同音過濾 + 變體覆蓋 (Homophone Filtering)")
    print("=" * 60)

    from phonofix.languages.english.fuzzy_generator import EnglishFuzzyGenerator

    generator_safe = EnglishFuzzyGenerator(enable_representative_variants=False)
    generator_repr = EnglishFuzzyGenerator(enable_representative_variants=True)

    terms = [
        "TensorFlow",
        "Kubernetes",
        "PostgreSQL",
        "scikit-learn",
    ]

    for term in terms:
        safe_variants = generator_safe.generate_variants(term, max_variants=20)
        repr_variants = generator_repr.generate_variants(term, max_variants=20)

        print(f"目標詞: {term}")
        print(f"安全變體數 (safe): {len(safe_variants)}")
        print(f"代表變體數 (repr): {len(repr_variants)}")
        print(f"safe 前10個: {safe_variants[:10]}")
        print(f"repr 前10個: {repr_variants[:10]}")
        print("說明: 生成階段會以 IPA key 去重，避免同音變體造成詞典膨脹")
        print()

# =============================================================================
# 範例 8: 混合格式 (Mixed Format)
# =============================================================================
def example_8_mixed_format():
    """
    混合使用列表和字典配置。
    展示不同配置方式的靈活性。
    """
    print("=" * 60)
    print("範例 8: 混合格式 (Mixed Format)")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            # 簡單列表：只指定已知誤聽
            "PyTorch": ["pie torch", "by torch"],
            # 空字典：讓系統自動生成發音相似變體（需開啟 enable_surface_variants）
            "Matplotlib": {},
            # 完整配置：精細控制
            "scikit-learn": {
                "aliases": ["psychic learn", "sigh kit learn"],
                "keywords": ["machine learning", "classifier", "regression"],
                "weight": 0.5,
            },
        }
    )

    test_cases = [
        ("Training with pie torch", "簡單列表 -> PyTorch"),
        ("Plot with mat plot lib", "自動生成變體 -> Matplotlib"),
        ("Using psychic learn classifier", "完整配置 + 上下文 -> scikit-learn"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print_case("Mixed", text, result, explanation)


# =============================================================================
# 範例 9: 長文章校正 (Long Article)
# =============================================================================
def example_9_long_article():
    """
    長文章綜合測試。
    模擬真實的語音轉文字輸出，包含多種 ASR 誤聽。
    """
    print("=" * 60)
    print("範例 9: 長文章校正 (Long Article)")
    print("=" * 60)

    terms = {
        "TensorFlow": ["tensor flow", "tens are flow"],
        "PyTorch": ["pie torch", "by torch"],
        "scikit-learn": ["psychic learn", "sigh kit learn"],
        "Kubernetes": ["cooper net ease", "cube and at ease"],
        "PostgreSQL": ["post grass sequel", "post gress sequel"],
        "algorithm": ["Al Gore rhythm", "all go rhythm"],
    }
    
    corrector = engine.create_corrector(terms)

    article = (
        "Today I learned about tensor flow and pie torch for deep learning. "
        "The psychic learn library is great for classical machine learning. "
        "We deploy our models on cooper net ease with post grass sequel as the database. "
        "The Al Gore rhythm we developed runs very efficiently."
    )

    print("原文 (Original):")
    print(article)
    print("-" * 40)
    
    result = corrector.correct(article)
    
    print("修正後 (Corrected):")
    print(result)
    print("-" * 40)





# =============================================================================
# 主程式
# =============================================================================
if __name__ == "__main__":
    print("\n" + "🇺🇸" * 20)
    print("  英文語音辨識校正範例 (English Examples)")
    print("🇺🇸" * 20 + "\n")

    examples = [
        example_1_basic_usage,
        example_2_manual_aliases,
        example_3_phonetic_mishearing,
        example_4_context_keywords,
        example_5_exclude_when,
        example_6_weight_system,
        example_7_homophone_filtering,
        example_8_mixed_format,
        example_9_long_article,
    ]

    for func in examples:
        try:
            func()
        except Exception as e:
            print(f"範例執行失敗: {e}")
            import traceback
            traceback.print_exc()
        print()

    print("=" * 60)
    print("所有範例執行完成!")
    print("=" * 60)

#!/usr/bin/env python3
"""
測試 IPA → 拼寫反查

驗證 Task 5.3 的接受標準：
1. 對於常見詞，能反查出正確拼寫（如 "ˈpaɪθɑn" → "python"）
2. 對於生僻詞，能基於規則生成合理近似拼寫
3. 通過 20+ 個測試案例
"""

from src.phonofix.languages.english.ipa_to_spelling import IPAToSpellingMapper

def test_ipa_to_spelling():
    """測試 IPA → 拼寫反查"""
    mapper = IPAToSpellingMapper()

    # 測試案例：涵蓋各種音素組合
    test_cases = [
        # 常見專有名詞
        {
            "ipa": "ˈpaɪθɑn",
            "expected": "python",
            "category": "Programming Language"
        },
        {
            "ipa": "ˈdʒɑvə",
            "expected": "java",
            "category": "Programming Language"
        },
        {
            "ipa": "ˈtɛnsɔːflɔː",
            "expected": "tensorflow",
            "category": "Framework"
        },
        {
            "ipa": "ˈriːækt",
            "expected": "react",
            "category": "Library"
        },
        {
            "ipa": "ˈvjuː",
            "expected": "vue",
            "category": "Framework"
        },
        # 測試特殊音素
        {
            "ipa": "θɪŋk",
            "expected": "think",
            "category": "Common Word (θ, ŋ)"
        },
        {
            "ipa": "ʃɪp",
            "expected": "ship",
            "category": "Common Word (ʃ)"
        },
        {
            "ipa": "tʃiːp",
            "expected": "cheap",
            "category": "Common Word (tʃ)"
        },
        {
            "ipa": "dʒʌmp",
            "expected": "jump",
            "category": "Common Word (dʒ)"
        },
        {
            "ipa": "ðɪs",
            "expected": "this",
            "category": "Common Word (ð)"
        },
        # 測試元音
        {
            "ipa": "biːt",
            "expected": "beat",
            "category": "Long vowel (iː)"
        },
        {
            "ipa": "bɪt",
            "expected": "bit",
            "category": "Short vowel (ɪ)"
        },
        {
            "ipa": "boʊt",
            "expected": "boat",
            "category": "Diphthong (oʊ)"
        },
        {
            "ipa": "baɪt",
            "expected": "byte",
            "category": "Diphthong (aɪ)"
        },
        {
            "ipa": "haʊs",
            "expected": "house",
            "category": "Diphthong (aʊ)"
        },
        # 測試輔音群
        {
            "ipa": "strɔːŋ",
            "expected": "strong",
            "category": "Consonant cluster (str)"
        },
        {
            "ipa": "skuːl",
            "expected": "school",
            "category": "Consonant cluster (sk)"
        },
        # 複雜詞彙
        {
            "ipa": "ˈkjuːbərnɛtiːz",
            "expected": "kubernetes",
            "category": "Complex term"
        },
        {
            "ipa": "ˈdɒkər",
            "expected": "docker",
            "category": "Technical term"
        },
        {
            "ipa": "əˈpætʃi",
            "expected": "apache",
            "category": "Technical term"
        },
        # 更多測試案例
        {
            "ipa": "ɡɪt",
            "expected": "git",
            "category": "Version control"
        },
        {
            "ipa": "noʊd",
            "expected": "node",
            "category": "Runtime"
        },
        {
            "ipa": "ˈæŋɡjʊlər",
            "expected": "angular",
            "category": "Framework"
        },
    ]

    print("=" * 80)
    print("測試 IPA → 拼寫反查")
    print("=" * 80)

    passed = 0
    failed = 0
    total = len(test_cases)

    for i, test in enumerate(test_cases, 1):
        ipa = test["ipa"]
        expected = test["expected"]
        category = test["category"]

        print(f"\n{i}. {category}")
        print(f"   IPA: {ipa}")
        print(f"   Expected: {expected}")

        # 生成拼寫
        spellings = mapper.ipa_to_spellings(ipa, max_results=5)

        print(f"   Generated ({len(spellings)}):")
        for j, spelling in enumerate(spellings, 1):
            marker = " ✓" if spelling.lower() == expected.lower() else ""
            print(f"     {j}. {spelling}{marker}")

        # 檢查是否匹配
        if any(s.lower() == expected.lower() for s in spellings):
            passed += 1
            print(f"   Result: ✓ PASSED")
        else:
            failed += 1
            print(f"   Result: ✗ FAILED (expected '{expected}' not in top 5)")

    print("\n" + "=" * 80)
    print("測試結果統計")
    print("=" * 80)
    print(f"Total: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")

    # 驗收標準：至少通過 20 個測試案例
    if total >= 20 and passed >= 20:
        print(f"\n✓ 驗收標準達成：通過 {passed}/{total} 個測試案例（≥20）")
    else:
        print(f"\n✗ 驗收標準未達成：僅通過 {passed}/{total} 個測試案例（需要≥20）")

    print("=" * 80)

if __name__ == "__main__":
    test_ipa_to_spelling()

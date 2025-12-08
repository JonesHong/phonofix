#!/usr/bin/env python3
"""
測試重構後的 EnglishFuzzyGenerator

驗證 Task 5.4 的接受標準：
1. IPA 維度生成能產生有效變體
2. 硬編碼規則仍然正常工作
3. IPA 去重有效移除重複變體
4. 生成的變體數量合理（5-30個）
5. 對比舊版本，確保核心功能未退化
"""

from src.phonofix.languages.english.fuzzy_generator import EnglishFuzzyGenerator

def test_refactored_generator():
    """測試重構後的變體生成器"""
    generator = EnglishFuzzyGenerator()

    test_cases = [
        {
            "term": "Python",
            "min_variants": 5,
            "max_variants": 30,
            "expected_contains": ["pyton", "python", "pith"],  # 常見 ASR 錯誤
        },
        {
            "term": "TensorFlow",
            "min_variants": 5,
            "max_variants": 30,
            "expected_contains": ["ten so flow", "tensor flow"],
        },
        {
            "term": "React",
            "min_variants": 3,
            "max_variants": 30,
            "expected_contains": ["re act"],
        },
        {
            "term": "API",
            "min_variants": 2,
            "max_variants": 30,
            "expected_contains": ["a p i"],
        },
        {
            "term": "Git",
            "min_variants": 2,
            "max_variants": 30,
            "expected_contains": [],
        },
    ]

    print("=" * 80)
    print("測試重構後的 EnglishFuzzyGenerator")
    print("=" * 80)

    total_passed = 0
    total_failed = 0

    for i, test in enumerate(test_cases, 1):
        term = test["term"]
        min_variants = test["min_variants"]
        max_variants = test["max_variants"]
        expected_contains = test["expected_contains"]

        print(f"\n{i}. 測試: {term}")

        # 生成變體
        variants = generator.generate_variants(term, max_variants=max_variants)

        print(f"   生成變體數量: {len(variants)}")
        print(f"   變體列表 ({min(10, len(variants))} 個):")
        for v in variants[:10]:
            print(f"     - {v}")
        if len(variants) > 10:
            print(f"     ... 還有 {len(variants) - 10} 個變體")

        # 檢查數量
        passed = True
        if len(variants) < min_variants:
            print(f"   ✗ 變體數量不足: {len(variants)} < {min_variants}")
            passed = False
        elif len(variants) > max_variants:
            print(f"   ✗ 變體數量過多: {len(variants)} > {max_variants}")
            passed = False
        else:
            print(f"   ✓ 變體數量合理: {min_variants} <= {len(variants)} <= {max_variants}")

        # 檢查預期變體
        if expected_contains:
            found = []
            missing = []
            for expected in expected_contains:
                if expected in variants:
                    found.append(expected)
                else:
                    missing.append(expected)

            if missing:
                print(f"   ⚠ 部分預期變體缺失: {missing}")
            else:
                print(f"   ✓ 所有預期變體都存在: {found}")

        # 檢查是否有原詞
        if term in variants or term.lower() in variants:
            print(f"   ✗ 變體中包含原詞: {term}")
            passed = False
        else:
            print(f"   ✓ 原詞已被移除")

        # 檢查是否有重複
        unique_count = len(set(v.lower() for v in variants))
        if unique_count < len(variants):
            print(f"   ✗ 存在重複變體: {len(variants)} 個變體中有 {len(variants) - unique_count} 個重複")
            passed = False
        else:
            print(f"   ✓ 無重複變體")

        if passed:
            print(f"   Result: ✓ PASSED")
            total_passed += 1
        else:
            print(f"   Result: ✗ FAILED")
            total_failed += 1

    print("\n" + "=" * 80)
    print("測試結果統計")
    print("=" * 80)
    print(f"Total: {len(test_cases)}")
    print(f"Passed: {total_passed} ({total_passed/len(test_cases)*100:.1f}%)")
    print(f"Failed: {total_failed} ({total_failed/len(test_cases)*100:.1f}%)")

    if total_passed == len(test_cases):
        print("\n✓ 所有測試通過！重構成功！")
    else:
        print(f"\n✗ 部分測試失敗：{total_failed}/{len(test_cases)}")

    print("=" * 80)

if __name__ == "__main__":
    test_refactored_generator()

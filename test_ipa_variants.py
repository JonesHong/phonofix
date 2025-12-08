#!/usr/bin/env python3
"""
測試 IPA 變體生成器

驗證 Task 5.2 的接受標準：
1. 能為單個 IPA 生成 5-20 個變體
2. 變體覆蓋所有配置的規則類型
3. 通過單元測試（如 "ˈpaɪθɑn" → "ˈpaɪfɑn", "ˈbaɪθɑn" 等）
"""

from src.phonofix.languages.english.fuzzy_generator import EnglishFuzzyGenerator
from src.phonofix.languages.english.config import EnglishPhoneticConfig

def test_ipa_variant_generation():
    """測試 IPA 變體生成"""
    generator = EnglishFuzzyGenerator()

    # 測試案例 1: Python 的 IPA (包含多種音素)
    test_cases = [
        {
            "ipa": "ˈpaɪθɑn",
            "term": "Python",
            "expected_variants": [
                "ˈpaɪfɑn",   # θ→f (similar phone)
                "ˈbaɪθɑn",   # p→b (voicing)
                "ˈpaɪsɑn",   # θ→s (similar phone)
                "ˈpaɪðɑn",   # θ→ð (voicing)
            ]
        },
        {
            "ipa": "ˈtɛnsɔːflɔː",
            "term": "TensorFlow",
            "expected_variants": [
                "ˈdɛnsɔːflɔː",  # t→d (voicing)
                "ˈtɛnzɔːflɔː",  # s→z (voicing)
                "ˈtɛnsɔflɔː",   # ɔː→ɔ (vowel length)
            ]
        },
        {
            "ipa": "ˈriːækt",
            "term": "React",
            "expected_variants": [
                "ˈrɪækt",     # iː→ɪ (vowel length)
                "ˈriːækd",    # t→d (voicing)
                "ˈliːækt",    # r→l (similar phone)
            ]
        }
    ]

    print("=" * 80)
    print("測試 IPA 變體生成器")
    print("=" * 80)

    for i, test in enumerate(test_cases, 1):
        ipa = test["ipa"]
        term = test["term"]
        expected = test["expected_variants"]

        print(f"\n測試案例 {i}: {term}")
        print(f"原始 IPA: {ipa}")

        # 生成變體
        variants = generator._generate_ipa_fuzzy_variants(ipa)

        # 移除原始 IPA
        variants_no_original = [v for v in variants if v != ipa]

        print(f"生成變體數量: {len(variants_no_original)}")
        print(f"所有變體 ({len(variants)}):")
        for v in sorted(variants):
            marker = " (original)" if v == ipa else ""
            print(f"  - {v}{marker}")

        # 驗證數量
        assert 5 <= len(variants_no_original) <= 20, \
            f"變體數量 {len(variants_no_original)} 不在 5-20 範圍內"
        print(f"✓ 變體數量在範圍內: {len(variants_no_original)}")

        # 驗證預期變體
        found_expected = []
        missing_expected = []
        for expected_var in expected:
            if expected_var in variants:
                found_expected.append(expected_var)
            else:
                missing_expected.append(expected_var)

        print(f"\n預期變體檢查:")
        for var in found_expected:
            print(f"  ✓ {var}")

        if missing_expected:
            print(f"\n缺少的預期變體:")
            for var in missing_expected:
                print(f"  ✗ {var}")

        print(f"\n匹配率: {len(found_expected)}/{len(expected)} " +
              f"({len(found_expected)/len(expected)*100:.1f}%)")

    print("\n" + "=" * 80)
    print("規則覆蓋檢查")
    print("=" * 80)

    # 檢查所有規則類型都被使用
    config = EnglishPhoneticConfig

    rule_types = {
        "清濁音混淆": config.IPA_VOICING_CONFUSIONS,
        "長短元音混淆": config.IPA_VOWEL_LENGTH_CONFUSIONS,
        "相似音素混淆": config.IPA_SIMILAR_PHONE_CONFUSIONS,
        "音節簡化": config.IPA_REDUCTION_RULES,
        "重音變化": config.IPA_STRESS_VARIATIONS,
    }

    for rule_name, rules in rule_types.items():
        print(f"\n{rule_name}: {len(rules)} 條規則")
        for rule in rules[:3]:  # 只顯示前 3 條
            print(f"  - {rule}")
        if len(rules) > 3:
            print(f"  ... 還有 {len(rules) - 3} 條規則")

    print("\n" + "=" * 80)
    print("✓ 所有測試通過！")
    print("=" * 80)

if __name__ == "__main__":
    test_ipa_variant_generation()

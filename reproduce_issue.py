import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(os.getcwd()) / "src"))

from phonofix.languages.chinese.fuzzy_generator import ChineseFuzzyGenerator
from phonofix.languages.chinese.utils import ChinesePhoneticUtils


def test_pinyin_issues():
    generator = ChineseFuzzyGenerator()
    utils = ChinesePhoneticUtils()

    term = "台北車站"
    print(f"Original Term: {term}")

    # 1. Check pinyin transformation
    pinyin = utils.get_pinyin_string(term)
    print(f"Pinyin (get_pinyin_string): '{pinyin}'")

    # 3. Check fuzzy variants generation (High Level API)
    print("\n[High Level API Test]")
    variants_objects = generator.generate_variants(term, max_variants=20)
    variant_texts = [v.text for v in variants_objects]

    print(f"Generated Variants ({len(variant_texts)}):")
    for v in variant_texts:
        print(f"  - {v}")

    # Check if we have internal variation (like che -> ce)
    # expected: "台北測站", "太北車站" etc.
    if any("測" in v for v in variant_texts):
        print("PASS: Variant with '測' (internal variation) FOUND.")
    else:
        print("FAIL: Variant with '測' NOT found.")

    if any("太" in v for v in variant_texts):
        print("PASS: Variant with '太' (first char variation) FOUND.")
    else:
        print("FAIL: Variant with '太' NOT found.")

    # Check for homophone issue
    found_homophone_variant = False
    for v in variant_texts:
        # Check if v is a homophone of term but different characters
        # e.g. "臺北車站" or "太北車站"
        if v != term and utils.get_pinyin_string(v) == pinyin:
            found_homophone_variant = True
            print(f"PASS: Found homophone variant: {v}")
            break

    if not found_homophone_variant:
        print("FAIL: No full homophone variants found.")


if __name__ == "__main__":
    try:
        test_pinyin_issues()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()

"""
English Speech Recognition Correction Examples

This file demonstrates all core features of EnglishEngine:
1. Basic Usage - Engine.create_corrector() factory method
2. Phonetic Matching - IPA-based fuzzy matching via espeak-ng
3. Split Word Matching - Handling ASR word boundary errors
4. Acronym Expansion - Handling letter-by-letter pronunciation
5. Context Keywords - Context-aware replacement
6. Weight System - Controlling replacement priority
7. exclude_when - Preventing unwanted replacements
8. Framework Names - Common tech terms correction
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from phonofix import EnglishEngine

# Global Engine (singleton pattern, avoids repeated initialization)
engine = EnglishEngine()


# =============================================================================
# Example 1: Basic Usage - Auto-generate phonetic variants
# =============================================================================
def example_1_basic_usage():
    """
    Simplest usage: provide a list of terms, system matches via IPA phonetics
    """
    print("=" * 60)
    print("Example 1: Basic Usage - Phonetic Matching")
    print("=" * 60)

    # Provide correct terms, system will match phonetically similar errors
    corrector = engine.create_corrector(
        [
            "Python",      # Matches: Pyton, pie thon, etc.
            "TensorFlow",  # Matches: Ten so floor, tensor flow, etc.
            "JavaScript",  # Matches: java script, Java Script, etc.
            "React",       # Matches: re act, Re Act, etc.
            "Django",      # Matches: Jango, jango, etc.
        ]
    )

    test_cases = [
        ("I use Python for data science", "No correction needed"),
        ("I use Pyton for machine learning", "Phonetic match: Pyton→Python"),
        ("Learning Ten so floor for AI", "ASR error: Ten so floor→TensorFlow"),
        ("Building apps with java script", "Split word: java script→JavaScript"),
        ("Jango is a great web framework", "Phonetic match: Jango→Django"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print(f"Input:  {text}")
        print(f"Output: {result}")
        print(f"Note:   {explanation}")
        print()


# =============================================================================
# Example 2: Manual Aliases
# =============================================================================
def example_2_manual_aliases():
    """
    Manually provide aliases for specific error patterns
    Useful for: known ASR mistakes, abbreviations, common typos
    """
    print("=" * 60)
    print("Example 2: Manual Aliases")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "TensorFlow": ["Ten so floor", "tensor flow", "Tensor flow"],
            "PyTorch": ["pie torch", "Pie Torch", "py torch"],
            "Kubernetes": ["cooper netties", "cube netties", "K eight S"],
        }
    )

    test_cases = [
        ("Learning Ten so floor", "Manual alias: Ten so floor→TensorFlow"),
        ("Using pie torch for deep learning", "Manual alias: pie torch→PyTorch"),
        ("Deploy on cooper netties", "Manual alias: cooper netties→Kubernetes"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print(f"Input:  {text}")
        print(f"Output: {result}")
        print(f"Note:   {explanation}")
        print()


# =============================================================================
# Example 3: Split Word Matching (Common ASR Error)
# =============================================================================
def example_3_split_words():
    """
    Handle split word errors - common in ASR output:
    - "JavaScript" → "java script" or "Java Script"
    - "TypeScript" → "type script" or "Type Script"
    """
    print("=" * 60)
    print("Example 3: Split Word Matching")
    print("=" * 60)

    corrector = engine.create_corrector(
        [
            "JavaScript",
            "TypeScript",
            "PostgreSQL",
            "MongoDB",
            "GraphQL",
        ]
    )

    test_cases = [
        ("I love java script", "Split: java script→JavaScript"),
        ("Using type script for frontend", "Split: type script→TypeScript"),
        ("post gres q l is my database", "Split: post gres q l→PostgreSQL"),
        ("mongo d b for NoSQL", "Split: mongo d b→MongoDB"),
        ("graph q l for API", "Split: graph q l→GraphQL"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print(f"Input:  {text}")
        print(f"Output: {result}")
        print(f"Note:   {explanation}")
        print()


# =============================================================================
# Example 4: Acronym Matching
# =============================================================================
def example_4_acronyms():
    """
    Handle acronyms that may be spoken letter-by-letter:
    - "AWS" → "A W S" or "a w s"
    - "API" → "A P I" or "a p i"
    """
    print("=" * 60)
    print("Example 4: Acronym Matching")
    print("=" * 60)

    corrector = engine.create_corrector(
        [
            "AWS",
            "GCP",
            "API",
            "SDK",
            "CLI",
            "GPU",
            "CPU",
        ]
    )

    test_cases = [
        ("Deploy on A W S", "Acronym: A W S→AWS"),
        ("Using G C P for cloud", "Acronym: G C P→GCP"),
        ("Call the A P I endpoint", "Acronym: A P I→API"),
        ("Install the S D K", "Acronym: S D K→SDK"),
        ("Run from C L I", "Acronym: C L I→CLI"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print(f"Input:  {text}")
        print(f"Output: {result}")
        print(f"Note:   {explanation}")
        print()


# =============================================================================
# Example 5: Context Keywords
# =============================================================================
def example_5_context_keywords():
    """
    Use keywords for context-aware replacement:
    - keywords are "required conditions": must match at least one
    - Useful for ambiguous abbreviations
    """
    print("=" * 60)
    print("Example 5: Context Keywords")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "API": {
                "aliases": ["a p i", "A P I"],
                "keywords": ["call", "endpoint", "request", "REST", "GraphQL"],
                "weight": 0.3,
            },
            "GPU": {
                "aliases": ["g p u", "G P U"],
                "keywords": ["CUDA", "compute", "graphics", "rendering", "training"],
                "weight": 0.3,
            },
            "EKG": {
                "aliases": ["1 kg", "1kg", "one kg"],
                "keywords": ["heart", "medical", "device", "monitor", "patient"],
                "weight": 0.3,
            },
        }
    )

    test_cases = [
        ("Call the a p i endpoint", "Keywords(call+endpoint) → API"),
        ("Use g p u for CUDA compute", "Keywords(CUDA+compute) → GPU"),
        ("The medical 1 kg device", "Keywords(medical+device) → EKG"),
        ("I bought 1 kg of apples", "No keywords → no replacement"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print(f"Input:  {text}")
        print(f"Output: {result}")
        print(f"Note:   {explanation}")
        print()


# =============================================================================
# Example 6: exclude_when
# =============================================================================
def example_6_exclude_when():
    """
    Use exclude_when to prevent specific replacements:
    - exclude_when are "veto conditions": match any = no replacement
    - exclude_when takes priority over keywords
    """
    print("=" * 60)
    print("Example 6: exclude_when")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "EKG": {
                "aliases": ["1 kg", "1kg"],
                "keywords": ["medical", "device", "heart", "monitor"],
                "exclude_when": ["weight", "heavy", "kilogram", "kg of"],
            }
        }
    )

    test_cases = [
        ("The medical 1 kg device", "Keywords(medical) → EKG"),
        ("This 1 kg weight", "exclude_when(weight) → no change"),
        ("Bought 1 kg of sugar", "exclude_when(kg of) → no change"),
        ("The 1 kg device is heavy", "Keywords(device) + exclude_when(heavy) → no change"),
    ]

    for text, explanation in test_cases:
        result = corrector.correct(text)
        print(f"Input:  {text}")
        print(f"Output: {result}")
        print(f"Note:   {explanation}")
        print()


# =============================================================================
# Example 7: Weight System
# =============================================================================
def example_7_weight_system():
    """
    Use weights to control replacement priority:
    - Default weight is 0.15
    - Higher weight = higher priority for phonetic matches
    """
    print("=" * 60)
    print("Example 7: Weight System")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "TensorFlow": {"aliases": [], "weight": 0.5},  # High weight
            "TensorBoard": {"aliases": [], "weight": 0.1},  # Low weight
        }
    )

    result = corrector.correct("I use Ten so floor for training")
    print(f"Input:  I use Ten so floor for training")
    print(f"Output: {result}")
    print(f"Note:   Higher weight TensorFlow matched")
    print()


# =============================================================================
# Example 8: Framework and Library Names
# =============================================================================
def example_8_frameworks():
    """
    Complete example with tech stack terms:
    - Programming languages
    - Frameworks and libraries
    - Cloud services
    """
    print("=" * 60)
    print("Example 8: Framework and Library Names")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            # Programming Languages
            "Python": ["Pyton", "Pyson", "pie thon"],
            "JavaScript": ["java script", "Java Script"],
            "TypeScript": ["type script", "Type Script"],
            
            # ML/AI Frameworks
            "TensorFlow": ["Ten so floor", "tensor flow"],
            "PyTorch": ["pie torch", "Pie Torch"],
            "Scikit-learn": ["sigh kit learn", "sky kit learn"],
            
            # Web Frameworks
            "Django": ["Jango", "jango"],
            "FastAPI": ["fast a p i", "Fast A P I"],
            "Vue.js": ["view js", "View JS", "vue j s"],
            "Node.js": ["node js", "Node JS", "no JS"],
            
            # Databases
            "PostgreSQL": ["post gres", "postgres q l"],
            "MongoDB": ["mongo d b", "Mongo DB"],
            "Redis": ["read is", "red is"],
        }
    )

    test_cases = [
        "I use Pyton and Ten so floor for AI",
        "Frontend with java script and view js",
        "Backend using Jango and fast a p i",
        "Database is post gres and read is",
        "Full stack with node js and mongo d b",
    ]

    print("Correction Results:")
    for text in test_cases:
        result = corrector.correct(text)
        print(f"  Input:  {text}")
        print(f"  Output: {result}")
        print()


# =============================================================================
# Example 9: Full Test Suite
# =============================================================================
def example_9_full_test():
    """
    Complete test cases covering all features
    """
    print("=" * 60)
    print("Example 9: Full Test Suite")
    print("=" * 60)

    corrector = engine.create_corrector(
        {
            "Python": ["Pyton"],
            "TensorFlow": ["Ten so floor"],
            "JavaScript": ["java script"],
            "EKG": {
                "aliases": ["1 kg", "1kg"],
                "keywords": ["medical", "device", "heart"],
                "exclude_when": ["weight", "heavy", "kilogram"],
            },
        }
    )

    test_cases = [
        # Basic corrections
        ("I use Pyton", "I use Python"),
        ("Learning Ten so floor", "Learning TensorFlow"),
        ("Using java script", "Using JavaScript"),
        
        # Already correct
        ("I use Python", "I use Python"),
        
        # Context-dependent (EKG)
        ("The medical 1 kg device", "The medical EKG device"),
        ("This 1 kg weight", "This 1 kg weight"),  # exclude_when
        ("Bought 1kg of sugar", "Bought 1kg of sugar"),  # no keywords
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
    
    print(f"\nResult: {passed} passed, {failed} failed")


# =============================================================================
# Main
# =============================================================================
if __name__ == "__main__":
    print("\n" + "🚀" * 20)
    print("  English Speech Recognition Correction Examples")
    print("🚀" * 20 + "\n")

    examples = [
        ("Basic Usage", example_1_basic_usage),
        ("Manual Aliases", example_2_manual_aliases),
        ("Split Words", example_3_split_words),
        ("Acronyms", example_4_acronyms),
        ("Context Keywords", example_5_context_keywords),
        ("exclude_when", example_6_exclude_when),
        ("Weight System", example_7_weight_system),
        ("Frameworks", example_8_frameworks),
        ("Full Test", example_9_full_test),
    ]

    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"❌ Example '{name}' failed: {e}")
            import traceback
            traceback.print_exc()
        print()

    print("=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)

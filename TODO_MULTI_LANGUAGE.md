# Multi-Language Expansion Plan

## Phase 1: Core Architecture & Interfaces
- [x] Define `PhoneticSystem` abstract base class (core/phonetic_interface.py)
- [x] Define `Tokenizer` abstract base class (core/tokenizer_interface.py)
- [x] Create `LanguageRouter` for splitting text segments (router/language_router.py)

## Phase 2: Chinese Implementation (Porting)
- [x] Implement `ChineseTokenizer` (Character-based)
- [x] Implement `ChinesePhoneticSystem` (Wrapper around existing pinyin logic)
- [x] Create `ChineseCorrector` using the new architecture

## Phase 3: English Implementation (Term-Based)
- [x] Implement `EnglishTokenizer` (Word-based)
- [x] Implement `EnglishPhoneticSystem` (IPA/Phonetic based)
    - [x] **Goal**: Match user terms like "EKG" to input "1kg" via phonetic similarity.
    - [x] **Tool**: `eng_to_ipa` or similar library.
- [x] Create `EnglishCorrector`

## Phase 4: Unified Corrector & Integration
- [x] Create `UnifiedCorrector` (The main entry point)
- [x] Update `examples/mixed_language_correction.py` to demonstrate "EKG" -> "1kg" and "TensorFlow" -> "ten so floor".
- [x] Update `requirements.txt`

## Phase 5: Documentation
- [ ] Update README.md

# Japanese Language Expansion TODO List

## Phase 1: Setup & Dependencies
- [ ] **Update `pyproject.toml`**: Add `ja` optional dependencies (`cutlet`, `fugashi`, `unidic-lite`).
- [ ] **Install Dependencies**: Run `uv sync` or `pip install -e .[ja]` to install the new packages.
- [ ] **Create Directory Structure**: Create `src/phonofix/languages/japanese/` and empty `__init__.py`.

## Phase 2: Core Implementation (Japanese Module)
- [ ] **Implement `utils.py`**:
    - [ ] Create `_get_cutlet()` for lazy loading.
    - [ ] Implement `is_japanese_char()` helper for script detection.
- [ ] **Implement `config.py`**:
    - [ ] Define `JapanesePhoneticConfig` class (e.g., `use_foreign_spelling`, `system` type).
- [ ] **Implement `phonetic_impl.py`**:
    - [ ] Create `JapanesePhoneticSystem` class inheriting from `PhoneticSystem`.
    - [ ] Implement `to_phonetic(text)` using `cutlet`.
    - [ ] Handle edge cases (spaces, punctuation).
- [ ] **Implement `tokenizer.py`**:
    - [ ] Create `JapaneseTokenizer` class inheriting from `Tokenizer`.
    - [ ] Implement `tokenize(text)` using `cutlet` or `fugashi`.
    - [ ] Implement `get_token_indices(text)`.
- [ ] **Implement `corrector.py`**:
    - [ ] Create `JapaneseCorrector` class inheriting from `BaseCorrector` (or similar).
    - [ ] Integrate `JapaneseTokenizer` and `JapanesePhoneticSystem`.
- [ ] **Export Modules**: Update `src/phonofix/languages/japanese/__init__.py` to expose classes.

## Phase 3: Integration with Unified Engine
- [ ] **Update `LanguageRouter`**:
    - [ ] Add logic to detect Japanese text segments (Hiragana/Katakana/Kanji).
    - [ ] Ensure it plays nicely with Chinese detection (Kanji overlap).
- [ ] **Update `UnifiedEngine`**:
    - [ ] Register `JapaneseCorrector` in the engine factory.
    - [ ] Allow `create_corrector` to handle Japanese dictionaries.

## Phase 4: Testing & Validation
- [ ] **Create Test File**: `tests/test_japanese_corrector.py`.
- [ ] **Implement Basic Tests**: Verify phonetic conversion and tokenization.
- [ ] **Implement Correction Tests**: Test with sample medical terms (e.g., "アスピリン" -> "Aspirin").
- [ ] **TPS Integration Test**:
    - [ ] Create a helper script or test fixture that uses TPS to translate test cases for verification.
    - [ ] Verify that the developer can understand the test output via TPS.

## Phase 5: Documentation & Cleanup
- [ ] **Update README**: Add Japanese support section.
- [ ] **Verify Code Style**: Ensure all comments are in Traditional Chinese (zh-TW) and Google-style docstrings are used.

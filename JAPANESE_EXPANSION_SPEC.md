# Japanese Language Expansion Specification

## 1. Overview
This document outlines the specification for adding Japanese language support to the `phonofix` library. The goal is to enable phonetic correction for Japanese text (Kanji, Hiragana, Katakana) by converting it to a phonetic representation (Romaji) and performing fuzzy matching against a dictionary of proper nouns.

## 2. Technical Stack

### 2.1 Phonetic Conversion & Tokenization
We will use **Cutlet** as the primary library for Japanese processing.

*   **Library**: `cutlet`
*   **Backend**: `fugashi` (MeCab wrapper, fast C++ implementation)
*   **Dictionary**: `unidic-lite` (Modern Japanese dictionary)
*   **License**: MIT (Compatible with `phonofix`)
*   **Why**:
    *   **Accuracy**: Handles context-sensitive readings (e.g., particle "は" as "wa").
    *   **Ease of Use**: Converts mixed Japanese text directly to Romaji (Hepburn).
    *   **Performance**: Fast execution via `fugashi`.
    *   **Windows Support**: Provides binary wheels.
    *   **Reliability**: Built on top of **MeCab**, the industry-standard engine for Japanese NLP. While `SudachiPy` is also a popular enterprise choice, it requires additional layers to convert its Katakana output to Romaji. `Cutlet` provides this out-of-the-box with high accuracy.

### 2.2 Fallback (Pure Python)
If a pure Python environment is strictly required (no C extensions), we can fallback to `janome` + `romkan`, but `cutlet` is preferred for performance and accuracy.

## 3. Architecture Changes

We will add a new language module at `src/phonofix/languages/japanese/`.

```text
src/phonofix/languages/japanese/
├── __init__.py          # Exports
├── config.py            # Japanese-specific configuration
├── corrector.py         # JapaneseCorrector implementation
├── phonetic_impl.py     # Wrapper around Cutlet
├── tokenizer.py         # Wrapper around Cutlet/Fugashi for tokenization
└── utils.py             # Helper functions (e.g., script detection)
```

### 3.1 `phonetic_impl.py`
*   **Class**: `JapanesePhoneticImpl`
*   **Responsibility**: Convert Japanese text to Romaji.
*   **Method**: `get_phonetic(text: str) -> str`
*   **Example**:
    *   Input: "東京都"
    *   Output: "tokyo" (or "toukyou" depending on config)

### 3.2 `tokenizer.py`
*   **Class**: `JapaneseTokenizer`
*   **Responsibility**: Split text into words.
*   **Method**: `tokenize(text: str) -> List[str]`
*   **Implementation**: Use `cutlet.Cutlet().slug(text)` or underlying `fugashi` tagger to get tokens.

### 3.3 `corrector.py`
*   **Class**: `JapaneseCorrector`
*   **Inherits**: `BaseCorrector`
*   **Responsibility**: Orchestrate tokenization, phonetic conversion, and fuzzy matching.

## 4. Translation Proxy System (TPS) Integration

As the developer does not read Japanese, we will use the TPS API to translate original Japanese text into Traditional Chinese during development and debugging.

### 4.1 Usage Workflow
When displaying Japanese text in the terminal or logs, the system should:
1.  **Display Original**: Show the Japanese text.
2.  **Call TPS**: Send the text to the local TPS endpoint.
3.  **Display Translation**: Show the translated Chinese text below the original.

### 4.2 API Details
*   **Endpoint**: `POST http://localhost:8000/api/v1/translate`
*   **Headers**: `Content-Type: application/json`
*   **Payload**:
    ```json
    {
      "text": "こんにちは",
      "target_lang": "zh-tw",
      "source_lang": "ja",
      "preferred_provider": "auto",
      "enable_refinement": true
    }
    ```

### 4.3 Helper Function (Draft)
```python
import requests

def print_with_translation(text: str, lang: str = "ja"):
    print(f"Original: {text}")
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/translate",
            json={
                "text": text, 
                "target_lang": "zh-tw",
                "source_lang": "ja",
                "preferred_provider": "auto",
                "enable_refinement": True
            }
        )
        if response.status_code == 200:
            data = response.json()
            print(f"Translation: {data['data']['text']}")
        else:
            print(f"Translation Error: {response.status_code}")
    except Exception as e:
        print(f"Translation Failed: {e}")
```

## 5. Implementation Plan

### Step 1: Add Dependencies
Update `pyproject.toml` to include Japanese support extras.
```toml
[project.optional-dependencies]
ja = ["cutlet>=0.3.0", "fugashi>=1.3.0", "unidic-lite>=1.0.0"]
```

### Step 2: Create Module Structure
Create the `src/phonofix/languages/japanese/` directory and files.

### Step 3: Implement Phonetic Logic
Implement `JapanesePhoneticImpl` using `cutlet`.
*   Configure `cutlet` to use Hepburn romanization.
*   Ensure spaces are handled correctly for word boundaries.

### Step 4: Implement Tokenizer
Implement `JapaneseTokenizer`.
*   Ensure it correctly identifies proper nouns (which are the targets for correction).

### Step 5: Integrate into Unified Engine
*   Update `LanguageRouter` to detect Japanese (Script detection: Hiragana/Katakana/Kanji).
*   Register `JapaneseCorrector` in `UnifiedEngine`.

### Step 6: Testing
*   Create `tests/test_japanese_corrector.py`.
*   Add test cases for common medical terms or general proper nouns.
*   **Use TPS** to verify the meaning of test cases.

## 6. Example Scenarios

| Original (Input) | Phonetic (Romaji) | Target (Dictionary) | Correction |
| :--- | :--- | :--- | :--- |
| アスピリン | asupirin | Aspirin | Aspirin |
| ロキソニン | rokisonin | Loxonin | Loxonin |
| 胃カメラ | ikamera | Gastrocamera | 胃カメラ |

## 8. Project Consistency & Coding Standards

To ensure the Japanese expansion integrates seamlessly with the existing codebase, the following standards must be observed.

### 8.1 File Structure & Naming
Follow the pattern established in `src/phonofix/languages/chinese/`:

*   **Module Directory**: `src/phonofix/languages/japanese/`
*   **Files**:
    *   `__init__.py`: Expose public classes (`JapaneseCorrector`, `JapaneseEngine`, etc.).
    *   `config.py`: Configuration classes (e.g., `JapanesePhoneticConfig`).
    *   `corrector.py`: Main logic, class `JapaneseCorrector`.
    *   `phonetic_impl.py`: Implementation of `PhoneticSystem` interface, class `JapanesePhoneticSystem`.
    *   `tokenizer.py`: Implementation of `Tokenizer` interface, class `JapaneseTokenizer`.
    *   `utils.py`: Helper functions, lazy loading of `cutlet`/`fugashi`.

### 8.2 Class Design & Inheritance
*   **Corrector**: Must inherit from a base corrector (check `src/phonofix/correction/unified_corrector.py` or similar if applicable, otherwise follow `ChineseCorrector` pattern but adapted for Japanese).
*   **Phonetic System**: Must inherit from `phonofix.core.phonetic_interface.PhoneticSystem`.
    *   Method: `to_phonetic(self, text: str) -> str`
*   **Tokenizer**: Must inherit from `phonofix.core.tokenizer_interface.Tokenizer`.
    *   Method: `tokenize(self, text: str) -> List[str]`
    *   Method: `get_token_indices(self, text: str) -> List[Tuple[int, int]]`

### 8.3 Lazy Loading & Dependency Management
*   **Lazy Import**: Like `pypinyin` in the Chinese module, `cutlet` and `fugashi` must be lazy-loaded. Do not import them at the top level of the module to avoid crashing users who haven't installed the `[ja]` extras.
*   **Wrapper Functions**: Create wrapper functions in `utils.py` (e.g., `_get_cutlet()`) that handle the import and raise a friendly `ImportError` if dependencies are missing.

### 8.4 Documentation & Comments
*   **Docstrings**: Use Google-style docstrings for all classes and methods.
*   **Language**: Comments and docstrings should be in **Traditional Chinese (zh-TW)** to match the existing codebase (as seen in `chinese/corrector.py`).
*   **Type Hinting**: Use Python type hints (`typing` module) extensively.

### 8.5 Logging
*   Use `phonofix.utils.logger.get_logger` for logging.
*   Use `TimingContext` for performance-critical sections if needed.

### 8.6 Configuration
*   Define default configuration in `config.py`.
*   Allow users to override settings (e.g., `use_foreign_spelling` in Cutlet).

### 8.7 Testing
*   Test files should be placed in `tests/`.
*   Naming: `test_japanese_corrector.py`.
*   Use `pytest` fixtures where appropriate.


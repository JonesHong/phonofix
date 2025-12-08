# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Phonofix** - Multi-language phonetic similarity-based proper noun substitution engine.

This tool **does not maintain any dictionaries**; it only provides a substitution engine. Users provide their own proper noun dictionaries, and the tool automatically generates phonetic variants and performs intelligent substitution.

**Core Philosophy**:
- Tool provides only the substitution engine, no default dictionaries
- Users maintain domain-specific proper noun dictionaries
- Tool handles automatic phonetic variant generation and intelligent substitution
- **Not a full-text spell checker** - focuses on "phonetic similarity substitution for proper nouns"

**Supported Languages**:
- **Chinese**: Pinyin fuzzy phonetic matching (Taiwan Mandarin characteristics)
- **English**: IPA (International Phonetic Alphabet) phonetic similarity matching
- **Japanese**: Romaji (Hepburn) phonetic similarity matching
- **Mixed text**: Automatic language segment detection and routing

**Use Cases**:
- **ASR Post-Processing**: Correct proper noun errors from speech-to-text (including mixed Chinese-English)
- **LLM Output Post-Processing**: Correct homophone errors when LLMs choose wrong characters for rare proper nouns
- **Proper Noun Standardization**: Technical terms, brand names, person/place names
- **Regional Vocabulary Conversion**: Mainland China ↔ Taiwan terms
- **Abbreviation Expansion**: Colloquial abbreviations → formal full names

## Development Commands

### Setup
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e ".[all]"

# Install dev dependencies
uv sync --dev
```

### Run Examples
```bash
# Chinese examples
uv run python examples/chinese_examples.py

# English examples (requires espeak-ng)
uv run python examples/english_examples.py

# Mixed language examples
uv run python examples/mixed_language_examples.py

# Streaming examples
uv run python examples/realtime_streaming_examples.py

# Japanese examples (requires cutlet)
uv run python examples/japanese_examples.py
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_chinese_corrector.py

# Run specific test
uv run pytest tests/test_chinese_corrector.py::test_basic_correction
```

### Code Quality
```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy src/phonofix
```

### English Support Setup
English support requires espeak-ng. Use the provided installation scripts:

```bash
# Windows PowerShell (run as Administrator)
.\scripts\setup_espeak.ps1

# Windows CMD (run as Administrator)
scripts\setup_espeak_windows.bat

# macOS/Linux
chmod +x scripts/setup_espeak.sh
./scripts/setup_espeak.sh
```

## Architecture

### Module Structure

The project uses a **src layout** with clear separation of concerns:

```
src/phonofix/
├── __init__.py                    # Main entry point, exports public API
│
├── engine/                        # Engine layer (singleton pattern, entry point)
│   ├── base.py                    # CorrectorEngine abstract class
│   ├── unified_engine.py          # UnifiedEngine - mixed language support
│   ├── chinese_engine.py          # ChineseEngine - Chinese only
│   ├── english_engine.py          # EnglishEngine - English only
│   └── japanese_engine.py         # JapaneseEngine - Japanese only
│
├── backend/                       # Phonetic backend (external library wrappers)
│   ├── base.py                    # PhoneticBackend abstract class
│   ├── chinese_backend.py         # Chinese Pinyin backend (pypinyin wrapper)
│   ├── english_backend.py         # English IPA backend (phonemizer wrapper)
│   └── japanese_backend.py        # Japanese Romaji backend (cutlet wrapper)
│
├── correction/                    # Corrector layer
│   ├── protocol.py                # CorrectorProtocol definition
│   ├── unified_corrector.py       # Mixed language corrector
│   └── streaming_corrector.py     # Streaming corrector (ASR/LLM)
│
├── languages/                     # Language-specific implementations
│   ├── chinese/
│   │   ├── config.py              # Pinyin config (initials/finals/fuzzy sounds)
│   │   ├── corrector.py           # Chinese corrector
│   │   ├── fuzzy_generator.py     # Fuzzy phonetic variant generator
│   │   ├── number_variants.py     # Number variant handling
│   │   ├── phonetic_impl.py       # ChinesePhoneticSystem implementation
│   │   ├── tokenizer.py           # Chinese tokenizer
│   │   └── utils.py               # Helper functions
│   │
│   ├── english/
│   │   ├── config.py              # IPA config
│   │   ├── corrector.py           # English corrector
│   │   ├── fuzzy_generator.py     # Syllable split variant generator
│   │   ├── phonetic_impl.py       # EnglishPhoneticSystem implementation
│   │   └── tokenizer.py           # English tokenizer
│   │
│   └── japanese/
│       ├── config.py              # Romaji config
│       ├── corrector.py           # Japanese corrector
│       ├── fuzzy_generator.py     # Japanese fuzzy variant generator
│       ├── phonetic_impl.py       # JapanesePhoneticSystem implementation
│       ├── tokenizer.py           # Japanese tokenizer
│       └── utils.py               # Helper functions (lazy loading)
│
├── core/                          # Language abstraction layer
│   ├── phonetic_interface.py      # PhoneticSystem abstract interface
│   └── tokenizer_interface.py     # Tokenizer abstract interface
│
├── router/
│   └── language_router.py         # Language segment detection and routing
│
└── utils/
    ├── lazy_imports.py            # Lazy import management (optional dependencies)
    └── logger.py                  # Logging utilities
```

### Key Components

**1. Engine Layer (src/phonofix/engine/)**

The Engine layer provides the main entry point for users. Engines use a **singleton pattern** for expensive resources (phonetic backends).

- `CorrectorEngine` (base.py): Abstract base class for all engines
  - Manages shared phonetic systems, tokenizers, and fuzzy generators
  - Provides factory method to create lightweight Corrector instances
  - Handles logging and timing

- `UnifiedEngine`: Mixed language support (Chinese + English + Japanese)
- `ChineseEngine`: Chinese-only support
- `EnglishEngine`: English-only support
- `JapaneseEngine`: Japanese-only support

**Lifecycle**:
- Engine should be created once at application startup (~2s initialization for espeak-ng)
- Create multiple lightweight Corrector instances as needed (<10ms per instance)
- Corrector instances share the same backend through Engine singleton

**2. Backend Layer (src/phonofix/backend/)**

Backend layer wraps external phonetic libraries and provides caching.

- `PhoneticBackend` (base.py): Abstract base class
  - `to_phonetic(text)`: Convert text to phonetic representation
  - `is_initialized()`: Check if backend is initialized
  - `get_cache_stats()`: Get cache statistics

- `ChinesePhoneticBackend`: Wraps `pypinyin` for Pinyin conversion
- `EnglishPhoneticBackend`: Wraps `phonemizer`/`espeak-ng` for IPA conversion
- `JapanesePhoneticBackend`: Wraps `cutlet` for Romaji conversion

**All backends use singleton pattern** with lazy initialization and LRU caching.

**3. Core Abstraction Layer (src/phonofix/core/)**

Defines language-agnostic interfaces:

- `PhoneticSystem` (phonetic_interface.py):
  - `to_phonetic(text)`: Convert text to phonetic representation (Pinyin/IPA/Romaji)
  - `are_fuzzy_similar(phonetic1, phonetic2)`: Check if two phonetics are fuzzy similar
  - `get_tolerance(length)`: Get tolerance rate based on word length

- `Tokenizer` (tokenizer_interface.py):
  - `tokenize(text)`: Split text into tokens
  - `get_token_indices(text)`: Get token positions
  - Handles character-level (Chinese/Japanese) vs word-level (English) tokenization

**4. Language-Specific Implementations (src/phonofix/languages/)**

Each language module implements the core interfaces:

**Chinese Module**:
- Taiwan Mandarin fuzzy phonetic rules
- Retroflex consonants (z/zh, c/ch, s/sh)
- n/l confusion, r/l confusion, f/h confusion
- Final vowel confusion (in/ing, en/eng, ue/ie, etc.)
- Tolerance: 2-char 0.20 → 4+ chars 0.40

**English Module**:
- **IPA (International Phonetic Alphabet) phoneme-based fuzzy variant generation**
- **Core workflow**: Term → IPA → Fuzzy IPA → Spellings
- **IPA phoneme confusion rules**:
  - Voicing confusions: p/b, t/d, k/g, f/v, s/z, θ/ð, ʃ/ʒ
  - Similar phone confusions: θ/f, θ/s, l/r, v/w, ð/z
  - Vowel length confusions: iː/ɪ, uː/ʊ, ɔː/ɒ, ɑː/ʌ, ɜː/ə
  - Reduction rules: ɪŋ→ɪn, ər→ə
- **IPA → Spelling reverse lookup** using phoneme-to-grapheme rules
- **Automatic phonetic deduplication** via IPA phonetic keys
- **New word generalization**: Can generate variants for words not in dictionary (e.g., "Ollama", "Anthropic")
- **Legacy ASR pattern support**:
  - Syllable split variants ("TensorFlow" → "Ten so floor")
  - Acronym handling ("API" → "a p i")
  - Number-letter confusions ("EKG" → "1kg")
- Tolerance: 4-letter 0.35 → long words 0.45

**Japanese Module**:
- Romaji (Hepburn) phonetic matching
- Context-aware reading (e.g., particle "は" → "wa")
- Handles Hiragana, Katakana, and Kanji
- Uses cutlet for accurate phonetic conversion

**5. Correction Layer (src/phonofix/correction/)**

- `UnifiedCorrector`: Main entry point for mixed-language correction
  - Automatic language segment detection
  - Routes segments to appropriate language correctors
  - Core algorithm is language-agnostic:
    - Sliding window matching
    - Context keyword weighting (closer = higher bonus)
    - Dynamic tolerance rate adjustment
    - Protected terms list to avoid false corrections

- `StreamingCorrector`: For real-time ASR streaming
  - Accumulated mode for continuous ASR updates
  - Automatic paragraph detection and cache reset

- `ChunkStreamingCorrector`: For LLM streaming output
  - Incremental input with real-time output
  - Preserves overlap region to prevent word truncation

### Critical Architecture Decisions

**Singleton Pattern for Backends**:
- Expensive resources (espeak-ng initialization) are shared
- Multiple Corrector instances share the same backend
- Fast Corrector creation (<10ms) after initial Engine setup

**Language Abstraction Layer**:
- `PhoneticSystem` interface unifies different phonetic systems
- `Tokenizer` interface handles character-level vs word-level tokenization
- `LanguageRouter` handles mixed-language text segmentation
- Core algorithm (sliding window, context weighting) is completely language-agnostic

**IPA-Based Fuzzy Variant Generation (English Module)**:
- **Three-Stage Workflow**: Term → IPA → Fuzzy IPA → Spellings
- **IPA Phoneme Confusion Rules**: Apply linguistic confusion patterns (voicing, similar phones, vowel length, reduction)
- **IPA → Spelling Reverse Lookup**: Convert fuzzy IPA variants back to real spellings using phoneme-to-grapheme rules
- **Key Advantages**:
  - **New Word Generalization**: Can generate variants for words not in dictionary (e.g., "Ollama", "LangChain", "Anthropic")
  - **Linguistically Sound**: Based on real phonetic confusion patterns, not arbitrary string transformations
  - **Automatic Deduplication**: IPA phonetic keys ensure no phonetically duplicate variants
- **Hybrid Approach**: Combines IPA generation (primary) with legacy ASR patterns (supplementary)
- **Performance**: ~5-30 variants per word after IPA deduplication, <2s generation time

**Phonetic Deduplication**:
- Automatically filters duplicate phonetic aliases (Set-like behavior)
- Prevents dictionary bloat and duplicate matching
- Chinese: Usually 5-20 variants after Pinyin deduplication
- English: 5-30 variants after IPA deduplication (with new word generalization capability)

**Normalization Strategy**:
- Internal normalization always converts to standard term (forward conversion)
- All aliases convert to user-specified correct term
- If you don't want conversion, simply don't add to dictionary

**Mixed Language Processing**:
- Automatic detection of language segments (Chinese/English/Japanese)
- Segments routed to appropriate language system
- Prevents cross-language false matches

**Lazy Loading**:
- Optional dependencies (cutlet, phonemizer) are lazy-loaded
- Prevents import errors for users who haven't installed certain language support
- Wrapper functions in utils.py handle lazy imports with friendly error messages

## Dictionary Design Patterns

### Three Dictionary Types

1. **Regional Terms** (`weight: 0.0`)
   - Bidirectional mapping: Taiwan ↔ Mainland China terms
   - 100% conversion, no context judgment needed
   - Examples: 土豆 ↔ 馬鈴薯, 視頻 ↔ 影片

2. **ASR Errors/Typos** (`weight > 0`)
   - Unidirectional correction (error → correct)
   - Requires context judgment and phonetic fuzzy matching
   - Examples: 流奶 → 牛奶, 花揮 → 發揮

3. **Abbreviation Expansion** (`weight: 0.0 or > 0`)
   - Colloquial abbreviation → formal full name
   - Often requires context keywords (e.g., "永豆" could be "永和豆漿" or "勇者鬥惡龍")

### Recommended Organization

Organize dictionaries by type in separate files:

```python
from dictionaries.asr_errors import ASR_ERRORS
from dictionaries.region_cn_to_tw import REGION_CN_TO_TW
from dictionaries.abbreviations import ABBREVIATIONS

# Combine for your use case
engine = ChineseEngine()
corrector = engine.create_corrector({
    **ASR_ERRORS,
    **ABBREVIATIONS,
})
```

## API Usage Patterns

### Recommended: Unified Engine (Mixed Language)

```python
from phonofix import UnifiedEngine

# Define mixed language proper nouns
terms = [
    "台北車站",      # Chinese word
    "TensorFlow",   # English proper noun
    "Python",
    "アスピリン",    # Japanese proper noun
]

# Initialize engine (one-time cost, ~2s)
engine = UnifiedEngine()

# Create corrector (fast, <10ms)
corrector = engine.create_corrector(terms)

# Automatic mixed-language processing
text = "我在北車用Pyton寫Ten so floor的code"
result = corrector.correct(text)
# Output: "我在台北車站用Python寫TensorFlow的code"
```

### Language-Specific Engines

```python
from phonofix import ChineseEngine, EnglishEngine, JapaneseEngine

# Chinese only
chinese_engine = ChineseEngine()
chinese_corrector = chinese_engine.create_corrector(["台北車站", "牛奶"])

# English only
english_engine = EnglishEngine()
english_corrector = english_engine.create_corrector({
    "TensorFlow": ["Ten so floor"],
    "Python": ["Pyton"]
})

# Japanese only
japanese_engine = JapaneseEngine()
japanese_corrector = japanese_engine.create_corrector({
    "アスピリン": ["asupirin"],
    "ロキソニン": ["rokisonin"]
})
```

### Advanced: Context Keywords and Weights

```python
from phonofix import ChineseEngine

engine = ChineseEngine()
corrector = engine.create_corrector({
    "永和豆漿": {
        "aliases": ["永豆", "勇豆"],
        "keywords": ["吃", "喝", "買", "宵夜"],
        "weight": 0.3
    },
    "勇者鬥惡龍": {
        "aliases": ["勇鬥", "永鬥"],
        "keywords": ["玩", "遊戲", "攻略"],
        "weight": 0.2
    }
})

result = corrector.correct("我去買勇鬥當宵夜")
# Output: "我去買永和豆漿當宵夜"
# Matched "買" and "宵夜" keywords
```

### Streaming Processing

```python
from phonofix import ChineseEngine, StreamingCorrector, ChunkStreamingCorrector

engine = ChineseEngine()
corrector = engine.create_corrector(["台北車站", "牛奶"])

# For real-time ASR (accumulated mode)
streamer = StreamingCorrector(corrector, overlap_size=8)
for asr_output in asr_stream:
    result = streamer.feed(asr_output)
    print(f"Confirmed: {result.confirmed}")
    print(f"Pending: {result.pending}")

# For LLM streaming (chunk mode)
chunk_streamer = ChunkStreamingCorrector(corrector, overlap_size=6)
for llm_chunk in llm_stream:
    result = chunk_streamer.feed_chunk(llm_chunk)
    if result.confirmed:
        print(result.confirmed, end="", flush=True)
```

## Important Implementation Notes

### Language Detection & Routing

**Mixed Language Processing Flow**:
1. Language segment detection (Chinese/English/Japanese/mixed)
2. Segments routed to appropriate PhoneticSystem
3. Results merged while preserving original formatting

**Language Router Strategies**:
- **Rule-based**: Simple regex patterns (fast but imprecise)
- **Script-based**: Unicode character ranges (used by default)

### Phonetic Matching Algorithm

**Chinese Pinyin Similarity**:
1. Special syllable matching (e.g., fa ↔ hua)
2. Final vowel fuzzy matching (in/ing, en/eng, etc.)
3. Levenshtein edit distance calculation
4. Strict initial consonant check for 2-character words

**English IPA-Based Fuzzy Variant Generation**:

**Variant Generation Workflow** (for building fuzzy alias dictionary):
1. **Term → IPA**: Convert English word to IPA using phonemizer/espeak-ng
   - Example: "Python" → "ˈpaɪθɑn"
2. **IPA → Fuzzy IPA**: Apply phoneme confusion rules to generate IPA variants
   - Voicing: p/b, t/d, k/g, f/v, s/z, θ/ð, ʃ/ʒ
   - Similar phones: θ/f, θ/s, l/r, v/w, ð/z
   - Vowel length: iː/ɪ, uː/ʊ, ɔː/ɒ, ɑː/ʌ, ɜː/ə
   - Reduction: ɪŋ→ɪn, ər→ə
   - Example: "ˈpaɪθɑn" → ["ˈbaɪθɑn", "ˈpaɪðɑn", "ˈpaɪfɑn", "ˈpaɪsɑn", ...]
3. **Fuzzy IPA → Spellings**: Reverse-lookup using phoneme-to-grapheme rules
   - Example: "ˈbaɪθɑn" → "bython", "ˈpaɪfɑn" → "pifon"
4. **IPA Deduplication**: Remove variants with identical IPA phonetic keys
5. **Result**: 5-30 phonetically distinct spelling variants

**Matching Workflow** (during text correction):
1. Text to IPA conversion (via phonemizer/espeak-ng)
2. IPA edit distance calculation between candidate and fuzzy aliases
3. Tolerance adjusted by phonetic length

**Key Advantages**:
- **New Word Generalization**: Works for words not in any dictionary
- **Linguistically Accurate**: Based on real phonetic confusion patterns
- **Automatic Deduplication**: No phonetically duplicate variants

**Japanese Romaji Similarity**:
1. Text to Romaji conversion (via cutlet)
2. Context-aware reading generation
3. Romaji edit distance calculation

**Dynamic Tolerance Rates**:
- Chinese 2 chars: 0.20 (very strict)
- Chinese 3 chars: 0.30
- Chinese 4+ chars: 0.40 (more lenient)
- English short: 0.35
- English long: 0.45

### Context Keyword Weighting

**Distance-based Weighting**:
- Keywords closer to target = higher bonus
- Formula: `bonus = base_bonus * (1 / (1 + distance))`
- Prevents distant keywords from over-influencing

### Protected Terms

Protected terms prevent specific words from being corrected:

```python
corrector = engine.create_corrector(
    terms={"台北車站": ["北車"]},
    protected_terms=["北側", "南側"]  # Won't be corrected
)

result = corrector.correct("我在北側等你")
# Won't be corrected to "我在台北車站側等你"
```

## File References

- **README.md**: Complete usage guide and examples (multi-language support)
- **README.zh-TW.md**: Traditional Chinese version
- **JAPANESE_EXPANSION_SPEC.md**: Japanese support architecture and implementation plan
- **TODO_JAPANESE_EXPANSION.md**: Japanese expansion task list
- **pyproject.toml**: Project configuration and dependencies
- **examples/**: Example scripts for different use cases
- **tests/**: Unit tests for all language modules
- **references/API_Documentation.md**: API reference documentation

## Common Pitfalls

1. **Use UnifiedEngine for Mixed Language**: For mixed Chinese-English-Japanese text, use `UnifiedEngine` to avoid language mismatches
2. **Tokenization Differences**: Chinese uses character-level sliding window vs English uses word-level tokens - ensure correct Tokenizer
3. **Language Router is Critical**: For mixed language scenarios, language routing is essential, otherwise performance degrades
4. **Don't Limit Variants**: Use all deduplicated phonetic variants to avoid missing valid candidates
5. **Weight Settings**: Regional terms `weight: 0.0`, general substitution `weight > 0` requires context judgment
6. **Phonetic Deduplication is Automatic**: Duplicate phonetic aliases (Chinese Pinyin/English IPA) are automatically filtered
7. **Normalization is Fixed**: All aliases convert to standard term, if you don't want conversion, don't add to dictionary
8. **Not a Full-Text Spell Checker**: Focuses on proper noun phonetic similarity substitution, not general spelling or grammar
9. **Backend Initialization**: First Engine initialization takes ~2s (espeak-ng loading), subsequent Corrector creation is fast (<10ms)
10. **Lazy Loading**: Import errors for optional dependencies (cutlet, phonemizer) mean those dependencies aren't installed - use `pip install "phonofix[ja]"` or `pip install "phonofix[en]"`

## Development Roadmap

### Completed
- ✅ Chinese support with Pinyin fuzzy matching
- ✅ English support with IPA phonetic matching
- ✅ Mixed language support with automatic routing
- ✅ Singleton pattern for backend optimization
- ✅ Streaming support for ASR/LLM
- ✅ Japanese support with Romaji phonetic matching

### Planned
- Korean support: Hangul phonetic and final consonant confusion rules
- Better language router: ML-based language detection
- Performance optimization: Parallelization for large texts
- Web API: REST API for cloud deployment

### Key Challenges
- **Tokenization Differences**: Character-level vs word-level needs careful handling
- **Fuzzy Rules**: Requires language expert input for each language
- **Word Frequency**: English homophones may need additional corpus
- **Code-Switching**: Mixed language scenarios need robust language routing

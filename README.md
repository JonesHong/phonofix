**English** | [繁體中文](README.zh-TW.md)

# Phonetic Substitution Engine

A multi-language phonetic similarity-based proper noun substitution tool. Supports ASR/LLM post-processing, regional vocabulary conversion, abbreviation expansion, and various other use cases.
Specially optimized for **Code-Switching** (mixed Chinese-English) scenarios.

## 💡 Core Philosophy

**This package does not maintain any proper noun dictionaries; instead, it provides a substitution engine based on phonetic vector space.**

The core mechanism of this package is to uniformly map text from different languages into a **phonetic vector space** (composed of Pinyin and IPA phonetic symbols).

Whether it's spelling errors from ASR (Automatic Speech Recognition), LLM (Large Language Models), or other scenarios—typically caused by rare proper nouns leading to incorrect character selection—this tool converts them to the **Pinyin/IPA dimension**.

The system then compares these converted phonetic features with **user-provided proper nouns** (plus system-generated fuzzy phonetic variants) to calculate probability and precisely replace spelling errors.

> ⚠️ **Note**: This is not a full-text spell checker, but focuses on "phonetic similarity substitution for proper nouns."

Users must provide their own proper noun dictionary. This tool will:
1. **Automatically generate phonetic variants**:
   - **Chinese**: Automatically generate Taiwanese accent/fuzzy phonetic variants (e.g., "北車" → "台北車站")
   - **English**: Calculate phonetic similarity based on IPA (International Phonetic Alphabet) (e.g., "Ten so floor" → "TensorFlow")
2. **Intelligent vocabulary substitution**: Automatically identify language segments and replace phonetically similar words with your specified standard proper nouns

**Use Cases**:
- **ASR Post-Processing**: Correct proper noun errors from speech-to-text (including mixed Chinese-English)
- **LLM Output Post-Processing**: Correct homophone/near-homophone errors when LLMs choose wrong characters for rare proper nouns
- **Proper Noun Standardization**: Restore colloquial/misspelled terms to their formal names
- **Regional Vocabulary Conversion**: Mainland China terms ↔ Taiwan terms

## 📚 Features

### 1. Multi-Language Support
- **Unified Corrector**: Single entry point, automatically handles mixed Chinese-English-Japanese text
- **English Phonetic Substitution**: 
    - Uses IPA (International Phonetic Alphabet) for phonetic similarity matching
    - Supports phonetic restoration of acronyms
- **Chinese Phonetic Substitution**:
    - Uses Pinyin for fuzzy phonetic matching
    - Supports Taiwanese Mandarin-specific pronunciation confusion patterns
- **Japanese Phonetic Substitution**:
    - Uses Romaji (Hepburn) for phonetic similarity matching
    - Supports context-aware reading generation (e.g., particle "ha" -> "wa")

### 2. Automatic Phonetic Variant Generation
- **Chinese**: Automatically generates Taiwanese accent/fuzzy phonetic variants
  - Retroflex consonants (z/zh, c/ch, s/sh)
  - n/l confusion (Taiwanese Mandarin)
  - r/l confusion, f/h confusion
  - Final vowel confusion (in/ing, en/eng, ue/ie, etc.)
- **English**: Automatically generates common ASR/LLM error variants
  - Syllable split variants ("TensorFlow" → "Ten so floor")
  - Acronym expansion variants ("AWS" → "A W S")

### 3. Intelligent Substitution Engine
- Sliding window matching algorithm
- Context keyword weighting mechanism
- Dynamic tolerance rate adjustment

### 4. Streaming Support (ASR/LLM Streaming)
- **Accumulated Mode** (`StreamingCorrector`): For Realtime ASR
  - Supports continuous updates of accumulated text
  - Automatically detects new paragraphs and resets cache
- **Chunk Mode** (`ChunkStreamingCorrector`): For LLM Streaming
  - Incremental input, real-time output of confirmed corrections
  - Preserves overlap region to prevent word truncation

## 📦 Installation

### Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is the next-generation Python package manager, fast and feature-complete.

```bash
# Install uv (Windows PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
# Default installation (includes both Chinese and English support)
uv add phonofix

# Chinese support only
uv add "phonofix[ch]"

# English support only (requires espeak-ng installation, see below)
uv add "phonofix[en]"

# Full installation (same as default)
uv add "phonofix[all]"
```

### English Support (espeak-ng Installation)

English phonetic features depend on the [espeak-ng](https://github.com/espeak-ng/espeak-ng) system package.

**Using Built-in Installation Scripts (Recommended)**:

This project provides automated installation scripts that will download, install, and configure environment variables automatically:

```bash
# Windows PowerShell (recommended to run as Administrator)
.\scripts\setup_espeak.ps1

# Windows CMD (recommended to run as Administrator)
scripts\setup_espeak_windows.bat

# macOS / Linux
chmod +x scripts/setup_espeak.sh
./scripts/setup_espeak.sh
```

The scripts will automatically:
1. Check/install espeak-ng
2. Set the `PHONEMIZER_ESPEAK_LIBRARY` environment variable
3. Verify that phonemizer works correctly

**Manual Installation**:

```bash
# Windows: Download installer from GitHub
# https://github.com/espeak-ng/espeak-ng/releases

# macOS
brew install espeak-ng

# Debian/Ubuntu
sudo apt install espeak-ng

# Arch Linux
sudo pacman -S espeak-ng
```

### Japanese Support (Optional)

Japanese support requires `cutlet`, `fugashi`, and `unidic-lite`.

```bash
pip install "phonofix[ja]"
```

### Development Environment Setup

```bash
# Install dependencies after cloning
uv sync

# Install dev dependencies
uv sync --dev

# Run examples
uv run python examples/chinese_examples.py

# Run tests
uv run pytest
```

## 🧪 Development

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Code formatting
uv run ruff format .

# Code linting
uv run ruff check .

# Type checking
uv run mypy src/phonofix
```

## 🚀 Quick Start

### 1. Mixed Language Substitution (Unified Corrector)

```python
from phonofix import UnifiedEngine

# Define your proper noun dictionary
terms = [
    "台北車站",      # Chinese word
    "TensorFlow",   # English proper noun
    "Python"
]

# Initialize engine (singleton pattern, recommended to initialize only once globally)
engine = UnifiedEngine()

# Create corrector
corrector = engine.create_corrector(terms)

# ASR output post-processing
asr_text = "我在北車用Pyton寫Ten so floor的code"
result = corrector.correct(asr_text)
print(result)
# Output: "我在台北車站用Python寫TensorFlow的code"

# LLM output post-processing (LLM may choose wrong homophones for rare words)
llm_text = "我在北車用派森寫code"  # LLM transliterated Python as "派森"
result = corrector.correct(llm_text)
print(result)
# Output: "我在台北車站用Python寫code"
```

### 2. Japanese Support

Japanese support uses Romaji (Hepburn) for phonetic matching.

```python
from phonofix import UnifiedEngine

engine = UnifiedEngine()
corrector = engine.create_corrector({
    "アスピリン": ["asupirin"],  # Aspirin
    "ロキソニン": ["rokisonin"], # Loxonin
    "胃カメラ": ["ikamera"]      # Gastrocamera
})

text = "頭が痛いのでasupirinを飲みました"
result = corrector.correct(text)
print(result)
# Output: "頭が痛いのでアスピリンを飲みました"
```

### 3. Chinese Only (Chinese Engine)

**Important Note**: This tool does not provide a default dictionary. You need to create your own proper noun list based on your business scenario.

#### Recommended Usage - Auto-generate Aliases

Using `ChineseEngine`, **you only need to provide your proper noun list**, and the tool will automatically generate all possible fuzzy phonetic variants with Pinyin deduplication:

#### Simplest Format - Keyword List Only

```python
from phonofix import ChineseEngine

# Step 1: Provide your proper noun list (this is the dictionary you need to maintain)
my_terms = ["台北車站", "牛奶", "發揮"]

# Step 2: Initialize engine and create corrector
# The tool will automatically generate all possible fuzzy phonetic variants
# For example: "台北車站" → automatically generates "北車", "臺北車站", etc.
engine = ChineseEngine()
corrector = engine.create_corrector(my_terms)

# Step 3: Automatically convert phonetically similar words to correct proper nouns
result = corrector.correct("我在北車買了流奶,他花揮了才能")
# Result: '我在台北車站買了牛奶,他發揮了才能'
# Explanation: "北車" → "台北車站", "流奶" → "牛奶", "花揮" → "發揮"
```

#### Full Format - Aliases + Keywords + Weights

When the same alias may correspond to multiple proper nouns, use context keywords and weights to improve accuracy:

```python
# Your proper noun dictionary (maintain based on your business scenario)
my_business_terms = {
    "永和豆漿": {
        "aliases": ["永豆", "勇豆"],  # Manually provide common aliases or mispronunciations
        "keywords": ["吃", "喝", "買", "宵夜"],  # Context keywords help with judgment
        "weight": 0.3  # Matching weight
    },
    "勇者鬥惡龍": {
        "aliases": ["勇鬥", "永鬥"],  # Homophones with different meanings
        "keywords": ["玩", "遊戲", "攻略"],
        "weight": 0.2
    }
}

engine = ChineseEngine()
corrector = engine.create_corrector(my_business_terms)

result = corrector.correct("我去買勇鬥當宵夜")
# Result: '我去買永和豆漿當宵夜'
# Explanation: Matched "買" and "宵夜" keywords, determined to be "永和豆漿" instead of "勇者鬥惡龍"
```

**Advantages**:
- ✅ Automatically generates fuzzy phonetic variants, no manual maintenance required
- ✅ Automatically filters Pinyin-duplicate aliases (similar to Set behavior)
- ✅ Supports multiple input formats, flexible usage
- ✅ Reduces configuration effort, focus on core vocabulary

### Advanced Features

#### Context Keywords

```python
from phonofix import ChineseEngine

# Use context keywords to improve accuracy
engine = ChineseEngine()
corrector = engine.create_corrector({
    "永和豆漿": {
        "aliases": ["永豆"],
        "keywords": ["吃", "喝", "買", "宵夜", "早餐"]
    },
    "勇者鬥惡龍": {
        "aliases": ["勇鬥"],
        "keywords": ["玩", "遊戲", "電動", "攻略"]
    }
})

result = corrector.correct("我去買勇鬥當宵夜")  # Matched "買" → 永和豆漿
result = corrector.correct("這款永豆的攻略很難找")  # Matched "攻略" → 勇者鬥惡龍
```

#### Weight System

```python
# Use weights to increase priority
engine = ChineseEngine()
corrector = engine.create_corrector({
    "恩典": {
        "aliases": ["安點"],
        "weight": 0.3  # High weight, priority matching
    },
    "上帝": {
        "aliases": ["上帝"],
        "weight": 0.1  # Low weight
    }
})
```

#### Protected Terms

```python
# Set protected terms list to prevent specific words from being corrected
engine = ChineseEngine()
corrector = engine.create_corrector(
    terms={
        "台北車站": ["北車"]
    },
    protected_terms=["北側", "南側"]  # These words will not be corrected
)

result = corrector.correct("我在北側等你")  # Will not be corrected to "台北車站側"
```

### 4. English Only (English Engine)

```python
from phonofix import EnglishEngine

engine = EnglishEngine()
corrector = engine.create_corrector({
    "TensorFlow": ["Ten so floor"],
    "Python": ["Pyton"]
})

result = corrector.correct("I use Pyton to write Ten so floor code")
# Output: "I use Python to write TensorFlow code"
```

### 5. Streaming Processing (ASR/LLM Streaming)

#### Realtime ASR Streaming

For real-time subtitle scenarios in speech recognition, passing accumulated complete recognition results each time:

```python
from phonofix import ChineseEngine, StreamingCorrector

engine = ChineseEngine()
corrector = engine.create_corrector(["台北車站", "牛奶"])

# Create streaming processor
streamer = StreamingCorrector(corrector, overlap_size=8)

# Simulate ASR accumulated input
asr_outputs = [
    "我在胎北",
    "我在胎北車站",
    "我在胎北車站買了流",
    "我在胎北車站買了流奶",
]

for text in asr_outputs:
    result = streamer.feed(text)
    print(f"Confirmed: {result.confirmed} | Pending: {result.pending}")

# Get complete result at the end
final = streamer.finalize()
print(f"Final: {final}")
# Final: 我在台北車站買了牛奶
```

#### LLM Streaming Output

For LLM streaming output, passing new chunks each time:

```python
from phonofix import ChineseEngine, ChunkStreamingCorrector

engine = ChineseEngine()
corrector = engine.create_corrector(["聖靈", "聖經", "恩典"])

# Create chunk mode streaming processor
streamer = ChunkStreamingCorrector(corrector, overlap_size=6)

# Simulate LLM streaming output
llm_chunks = ["聖林", "借著默氏", "寫了這本", "生經，", "是安點。"]

for chunk in llm_chunks:
    result = streamer.feed_chunk(chunk)
    if result.confirmed:
        print(result.confirmed, end="", flush=True)  # Real-time output

# Output remaining part at the end
remaining = streamer.finalize()
print(remaining)
# Output: 聖靈借著默氏寫了這本聖經，是恩典。
```

#### WebSocket Real-World Application

```python
from phonofix import ChineseEngine, StreamingCorrector
import json

engine = ChineseEngine()
corrector = engine.create_corrector(my_terms)

async def handle_asr_websocket(websocket):
    streamer = StreamingCorrector(corrector, overlap_size=10)
    
    async for message in websocket:
        data = json.loads(message)
        
        if data["type"] == "partial":
            result = streamer.feed(data["text"])
            await websocket.send(json.dumps({
                "confirmed": result.confirmed,
                "pending": result.pending,
            }))
            
        elif data["type"] == "final":
            final = streamer.finalize()
            await websocket.send(json.dumps({"final": final}))
            streamer.reset()  # Reset, ready for next segment
```

## 📁 Project Structure

```
phonofix/
├── src/
│   └── phonofix/                      # Main package (src layout)
│       ├── __init__.py                # Main entry, exports UnifiedEngine, ChineseEngine, etc.
│       │
│       ├── engine/                    # Engine layer (singleton pattern entry)
│       │   ├── base.py                # BaseEngine abstract class
│       │   ├── unified_engine.py      # UnifiedEngine - mixed language
│       │   ├── chinese_engine.py      # ChineseEngine - Chinese only
│       │   └── english_engine.py      # EnglishEngine - English only
│       │
│       ├── backend/                   # Phonetic backend (phonemizer/pypinyin wrapper)
│       │   ├── base.py                # PhoneticBackend abstract class
│       │   ├── chinese_backend.py     # Chinese Pinyin backend
│       │   └── english_backend.py     # English IPA backend
│       │
│       ├── correction/                # Corrector layer
│       │   ├── protocol.py            # CorrectorProtocol definition
│       │   ├── unified_corrector.py   # Mixed language corrector
│       │   └── streaming_corrector.py # Streaming corrector (ASR/LLM)
│       │
│       ├── languages/                 # Language-specific implementations
│       │   ├── chinese/               # Chinese module
│       │   │   ├── config.py          # Pinyin config (initials/finals/fuzzy sounds)
│       │   │   ├── corrector.py       # Chinese corrector
│       │   │   ├── fuzzy_generator.py # Fuzzy phonetic variant generator
│       │   │   ├── number_variants.py # Number variant handling
│       │   │   └── tokenizer.py       # Chinese tokenizer
│       │   │
│       │   └── english/               # English module
│       │       ├── config.py          # IPA config
│       │       ├── corrector.py       # English corrector
│       │       ├── fuzzy_generator.py # Syllable split variant generator
│       │       └── tokenizer.py       # English tokenizer
│       │
│       ├── router/                    # Language router
│       │   └── language_router.py     # Auto-detect Chinese/English segments
│       │
│       └── utils/                     # Utility modules
│           ├── lazy_imports.py        # Lazy imports (optional dependency management)
│           └── logger.py              # Logging utilities
│
├── scripts/                           # Installation scripts
│   ├── setup_espeak.ps1               # Windows PowerShell espeak-ng installer
│   ├── setup_espeak.sh                # macOS/Linux espeak-ng installer
│   └── setup_espeak_windows.bat       # Windows CMD espeak-ng installer
│
├── examples/                          # Usage examples
│   ├── chinese_examples.py            # Chinese correction examples
│   ├── english_examples.py            # English correction examples
│   ├── mixed_language_examples.py     # Mixed language examples
│   ├── streaming_demo.py              # Streaming processing examples
│   └── timing_demo.py                 # Performance timing examples
│
├── tests/                             # Unit tests
│   ├── test_chinese_corrector.py
│   ├── test_english_corrector.py
│   └── test_unified_corrector.py
│
├── pyproject.toml                     # Project configuration (phonofix)
├── requirements.txt                   # Dependency list
└── README.md
```

## 🎯 Use Cases

The following examples demonstrate how to create your own proper noun dictionary for different business scenarios:

### 1. ASR Post-Processing

**Problem**: Speech recognition often mishears proper nouns as phonetically similar common words

```python
# Your proper noun dictionary
terms = ["牛奶", "發揮", "然後", "TensorFlow", "Kubernetes"]

engine = UnifiedEngine()
corrector = engine.create_corrector(terms)

# ASR output: proper nouns misheard
asr_output = "我買了流奶，蘭後用Ten so floor訓練模型"
result = corrector.correct(asr_output)
# Result: "我買了牛奶，然後用TensorFlow訓練模型"
```

### 2. LLM Output Post-Processing

**Problem**: LLMs may choose phonetically similar common characters for rare proper nouns

```python
# Your proper noun dictionary
terms = ["耶穌", "恩典", "PyTorch", "NumPy"]

engine = UnifiedEngine()
corrector = engine.create_corrector(terms)

# LLM output: rare proper nouns replaced with homophone common characters
llm_output = "耶穌的恩點很大，我用排炬和南派做機器學習"
result = corrector.correct(llm_output)
# Result: "耶穌的恩典很大，我用PyTorch和NumPy做機器學習"
```

### 3. Regional Vocabulary Conversion

**Your Dictionary**: Maintain regional mapping table (e.g., Mainland China ↔ Taiwan terms)

```python
# Your regional vocabulary dictionary
region_terms = {
    "馬鈴薯": {"aliases": ["土豆"], "weight": 0.0},
    "影片": {"aliases": ["視頻"], "weight": 0.0}
}

engine = ChineseEngine()
corrector = engine.create_corrector(region_terms)

result = corrector.correct("我用土豆做了視頻")
# Result: "我用馬鈴薯做了影片"
```

### 4. Abbreviation Expansion

**Your Dictionary**: Maintain common abbreviations and full names mapping

```python
# Your abbreviation dictionary
abbreviation_terms = {
    "台北車站": {"aliases": ["北車"], "weight": 0.0}
}

engine = ChineseEngine()
corrector = engine.create_corrector(abbreviation_terms)

result = corrector.correct("我在北車等你")
# Result: "我在台北車站等你"
```

### 5. Professional Terminology Standardization

**Your Dictionary**: Maintain professional terminology for your business domain

```python
# Your medical terminology dictionary
medical_terms = {
    "阿斯匹靈": {"aliases": ["阿斯匹林", "二四批林"], "weight": 0.2}
}

engine = ChineseEngine()
corrector = engine.create_corrector(medical_terms)

result = corrector.correct("醫生開了二四批林給我")
# Result: "醫生開了阿斯匹靈給我"
```

## 📖 Complete Examples

Please refer to the `examples/` directory, which contains multiple usage examples:

| File | Description |
|------|-------------|
| `chinese_examples.py` | Chinese phonetic substitution examples |
| `english_examples.py` | English phonetic substitution examples |
| `mixed_language_examples.py` | Mixed Chinese-English substitution examples |
| `streaming_demo.py` | Basic streaming processing examples |
| `realtime_streaming_demo.py` | ASR/LLM real-time streaming examples |
| `timing_demo.py` | Performance timing examples |

```bash
# Run Chinese examples
uv run python examples/chinese_examples.py

# Run English examples (requires espeak-ng)
uv run python examples/english_examples.py

# Run streaming examples
uv run python examples/realtime_streaming_demo.py
```

## 🔧 Technical Details

### Phonetic Matching Mechanism

#### Chinese: Pinyin Fuzzy Sound Rules

**Initial Consonant Fuzzy Groups**
| Group | Phonemes | Description |
|-------|----------|-------------|
| Retroflex | z ⇄ zh, c ⇄ ch, s ⇄ sh | Common in Taiwanese Mandarin |
| n/l confusion | n ⇄ l | Taiwanese Mandarin characteristic |
| r/l confusion | r ⇄ l | Common ASR error |
| f/h confusion | f ⇄ h | Dialect influence |

**Final Vowel Fuzzy Mapping**
- `in` ⇄ `ing`, `en` ⇄ `eng`, `an` ⇄ `ang`
- `ian` ⇄ `iang`, `uan` ⇄ `uang`, `uan` ⇄ `an`
- `ong` ⇄ `eng`, `uo` ⇄ `o`, `ue` ⇄ `ie`

**Special Syllable Mappings**
- `fa` ⇄ `hua` (發/花)
- `xue` ⇄ `xie` (學/鞋)
- `ran` ⇄ `lan`, `yan` (然/蘭/嚴)
- For more, please refer to `src/phonofix/languages/chinese/config.py`

#### English: IPA Phonetic Matching

Uses **IPA (International Phonetic Alphabet)** phoneme-based fuzzy variant generation system for accurate phonetic similarity matching.

**Core Architecture**:
1. **Term → IPA**: Convert English words to IPA using [phonemizer](https://github.com/bootphon/phonemizer) (espeak-ng backend)
2. **IPA → Fuzzy IPA**: Apply phoneme confusion rules to generate phonetic variants
3. **Fuzzy IPA → Spellings**: Reverse-lookup to generate real spelling variants

**IPA Phoneme Confusion Rules**:

| Confusion Type | Rule | Example |
|----------------|------|---------|
| **Voicing** | p/b, t/d, k/g, f/v, s/z, θ/ð, ʃ/ʒ | "Python" [ˈpaɪθɑn] → [ˈbaɪθɑn] → "Bython" |
| **Similar Phones** | θ/f, θ/s, l/r, v/w, ð/z | "think" [θɪŋk] → [fɪŋk] → "fink" |
| **Vowel Length** | iː/ɪ, uː/ʊ, ɔː/ɒ, ɑː/ʌ | "beat" [biːt] → [bɪt] → "bit" |
| **Reduction** | ɪŋ→ɪn, ər→ə | "working" [ˈwɜːkɪŋ] → [ˈwɜːkɪn] |

**Key Advantages**:
- ✅ **New Word Generalization**: Can generate variants for words not in dictionary (e.g., "Ollama", "Anthropic", "LangChain")
- ✅ **Phonetically Accurate**: Based on real IPA phoneme system, linguistically sound
- ✅ **Automatic Deduplication**: Removes phonetically identical variants via IPA phonetic key

**Common ASR/LLM Error Types**:

| Error Type | Example | Description |
|------------|---------|-------------|
| **IPA Phoneme Confusion** | "Python" → "Pithon", "Bython" | θ/f confusion, p/b voicing |
| **Syllable Splitting** | "TensorFlow" → "Ten so floor" | Speech recognition split error |
| **Acronym Expansion** | "API" → "A P I" | Letter-by-letter pronunciation |
| **New Word Variants** | "Ollama" → "Olama", "Olema" | IPA-based generalization |

**Example: IPA Variant Generation**
```python
from phonofix import EnglishEngine

engine = EnglishEngine()

# Term → IPA → Fuzzy IPA → Spellings workflow
corrector = engine.create_corrector({
    "Python": [],  # System auto-generates variants via IPA
    "Ollama": [],  # Works even for new words not in dictionary
})

# IPA generates variants like:
# "Python" [ˈpaɪθɑn] → "pithon", "bython", "piton", "pythom", etc.
# "Ollama" [əˈlɑːmə] → "olama", "olema", "ollama", etc.

text = "I use Pithon and Olama for AI development"
result = corrector.correct(text)
print(result)
# Output: "I use Python and Ollama for AI development"
```

### Keywords and exclude_when Mechanism

When the same alias may correspond to multiple proper nouns, use `keywords` and `exclude_when` for precise judgment:

```
Substitution Logic:
┌─────────────────────────────────────────────────────────┐
│  Input text contains alias (e.g., "1kg")                │
│                    ↓                                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Step 1: Check exclude_when (exclusion conditions)│    │
│  │   - If text contains any exclusion word → No sub ❌│   │
│  │   - e.g.: "1kg水很重" contains "水" → No sub to EKG│   │
│  └─────────────────────────────────────────────────┘    │
│                    ↓ (No exclusion match)                │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Step 2: Check keywords (required conditions)     │    │
│  │   - If keywords set and none match → No sub ❌    │    │
│  │   - If keywords set and matched → Substitute ✅   │    │
│  │   - If no keywords set → Substitute ✅            │    │
│  │   - e.g.: "1kg設備" contains "設備" → Sub to EKG  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

**Important Rule: exclude_when Takes Priority Over Keywords**

Even if keywords match, no substitution occurs if exclude_when matches:

```python
"EKG": {
    "aliases": ["1kg"],
    "keywords": ["設備", "醫療"],      # Must contain one to substitute
    "exclude_when": ["重", "公斤"],    # Contains any = no substitution
}

# Examples:
"這個設備有 1kg重"  # keywords(設備) ✓ + exclude_when(重) ✓ → No substitution
"這個 1kg設備"      # keywords(設備) ✓ + exclude_when ✗ → Substitute to EKG
"買了 1kg的東西"    # keywords ✗ → No substitution
```

### Substitution Algorithm Flow

```
Input Text
    │
    ▼
┌─────────────────────────────────────┐
│ 1. Build Protection Mask             │
│    Mark positions of protected_terms │
│    These positions skip substitution │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 2. Language Block Detection          │
│    (UnifiedCorrector)                │
│    Chinese block → ChineseCorrector  │
│    English block → EnglishCorrector  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 3. Sliding Window Scan               │
│    Traverse all possible word length │
│    combinations                      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 4. Phonetic Similarity Calculation   │
│    Chinese: Pinyin (special→final→   │
│             edit distance)           │
│    English: IPA edit distance        │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 5. Keywords/exclude_when Filtering   │
│    - exclude_when matched → Skip     │
│    - No keywords matched → Skip      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 6. Calculate Final Score             │
│    Score = error_rate - weight -     │
│            context_bonus             │
│    (Lower score is better)           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 7. Conflict Resolution               │
│    Sort by score, select best        │
│    non-overlapping candidates        │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 8. Text Replacement                  │
│    Replace from back to front to     │
│    avoid index shifting              │
└─────────────────────────────────────┘
    │
    ▼
Output Result
```

### Dynamic Tolerance Rate

| Word Length | Tolerance | Description |
|-------------|-----------|-------------|
| 2 chars/letters | 0.20 | Must be very accurate |
| 3 chars/letters | 0.30 | Moderately strict |
| 4+ chars/letters | 0.40 | Higher tolerance |
| English mixed | 0.45 | Higher tolerance |

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📄 License

MIT License

## 👨‍💻 Author

JonesHong

## 🙏 Acknowledgments

Thanks to the following projects:
- [pypinyin](https://github.com/mozillazg/python-pinyin)
- [python-Levenshtein](https://github.com/maxbachmann/Levenshtein)
- [Pinyin2Hanzi](https://github.com/letiantian/Pinyin2Hanzi)
- [hanziconv](https://github.com/berniey/hanziconv)

[<kbd><strong>English</strong></kbd>](README.md) [<kbd>繁體中文</kbd>](README.zh-TW.md)

# Phonofix (Multilingual Phonetic Substitution Engine)

Phonofix is a proper-noun substitution tool built around **phonetic similarity**. It is useful for ASR/LLM post-processing, proper-noun standardization, and homophone/near-homophone correction.

Project structure and the full API/symbol snapshot: [snapshot.md](snapshot.md)

---

## Table of Contents

- [Supported Languages](#supported-languages)
- [Core Concepts](#core-concepts)
- [Quick Start (Latest API)](#quick-start-latest-api)
- [Observability & Failure Policy](#observability--failure-policy)
- [Substitution Algorithm Flow (Overview)](#substitution-algorithm-flow-overview)
- [Installation](#installation)
- [Development & Validation](#development--validation)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Supported Languages

| Language | Phonetic Key | Engine | Extras |
|---|---|---|---|
| Chinese | Pinyin | `ChineseEngine` | `phonofix[ch]` |
| English | IPA | `EnglishEngine` | `phonofix[en]` |
| Japanese | Romaji | `JapaneseEngine` | `phonofix[ja]` |

> Note: More languages will be added over time. Since the author is not fluent in all languages, some language modules are developed with AI assistance and may contain mistakes. If you find issues in real usage, please report them via GitHub Issues:
> - https://github.com/JonesHong/phonofix/issues

## Core Concepts

- You provide a **proper-noun dictionary** (canonical + aliases/config).
- The system maps both the dictionary and the input text into a **phonetic key** space.
- Matches are applied back to the original string, outputting the **canonical spelling**.

> Note: This is not a full-text spell checker; it focuses on the proper nouns you care about.

## Quick Start (Latest API)

### Chinese

```python
from phonofix import ChineseEngine

engine = ChineseEngine()
corrector = engine.create_corrector({"台北車站": ["北車", "胎北車站"]})

print(corrector.correct("我在北車等你"))
# Output: 我在台北車站等你
```

### English (requires espeak-ng)

```python
from phonofix import EnglishEngine

engine = EnglishEngine()
corrector = engine.create_corrector({"TensorFlow": ["Ten so floor"], "Python": ["Pyton"]})

print(corrector.correct("I use Pyton to write Ten so floor code"))
# Output: I use Python to write TensorFlow code
```

### Japanese

```python
from phonofix import JapaneseEngine

engine = JapaneseEngine()
corrector = engine.create_corrector({"会議": ["kaigi"], "ロボット": ["robotto"]})

print(corrector.correct("明日のkaigiに参加します"))
# Output: 明日の会議に参加します
print(corrector.correct("新しいrobottoのkaihatsu"))  # Example: can also correct other terms
# Output: 新しいロボットのkaihatsu
```

### Mixed Language (manual chaining)

This project does not perform automatic language detection. For mixed inputs, manually chain correctors:

```python
from phonofix import ChineseEngine, EnglishEngine

ch = ChineseEngine().create_corrector({"台北車站": ["北車"]})
en = EnglishEngine().create_corrector({"Python": ["Pyton"]})

text = "我在北車用Pyton寫code"
text = en.correct(text, full_context=text)
text = ch.correct(text, full_context=text)
print(text)
# Output: 我在台北車站用Python寫code
```

## Observability & Failure Policy

Principle: degrade is allowed, but silent degrade is not.

- `on_event`: preferred SDK surface for collecting replacements, errors, and degrade signals
- `silent=True`: only disables logger output; events can still be used for observability
- `fail_policy`:
  - `"degrade"` (default): on fuzzy exception, fall back to exact-only and emit events
  - `"raise"`: on fuzzy exception, raise immediately (good for CI/offline evaluation)
- `mode`:
  - `"production"` is equivalent to `fail_policy="degrade"`
  - `"evaluation"` is equivalent to `fail_policy="raise"`
- `trace_id`: correlation ID for events produced by a single `correct()` call (caller-provided)

## Substitution Algorithm Flow (Overview)

Reference implementation: `PipelineCorrectorBase.correct()` (see [snapshot.md](snapshot.md) for the full symbol list).

> This project does not do automatic language detection. For mixed-language inputs, manually chain correctors (see the example above).

```text
Input text
    │
    ▼
┌─────────────────────────────────────┐
│ 1. Build a protection mask          │
│    Mark spans covered by            │
│    protected_terms                  │
│    Protected spans are excluded     │
│    from substitution               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 2. Generate candidate drafts        │
│    2.1 exact: Aho-Corasick matches  │
│    2.2 fuzzy: sliding windows +     │
│         phonetic similarity         │
│         - can degrade to exact-only │
│           via fail_policy           │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 3. Filter by keywords/exclude_when  │
│    - exclude_when matched → skip    │
│    - keywords not satisfied → skip  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 4. Calculate final score            │
│    Score = error_ratio - weight -   │
│            context_bonus            │
│    (lower is better)                │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 5. Conflict resolution              │
│    Sort by score, keep the best     │
│    non-overlapping candidates       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 6. Apply replacements               │
│    Rebuild the output string in     │
│    ascending start order to avoid   │
│    index shifting                   │
│    and ensure consistent output     │
└─────────────────────────────────────┘
    │
    ▼
Output
```

## Installation

### Requirements

- Python `>=3.10`

### Using uv (recommended)

```bash
uv add phonofix
```

You can also use extras to make dependency intent explicit (actual versions are defined in `pyproject.toml`):

```bash
uv add "phonofix[ch]"
uv add "phonofix[en]"
uv add "phonofix[ja]"
```

### English Support (espeak-ng)

English phonetic features depend on the system package `espeak-ng`.

Recommended: use the setup scripts under `scripts/` (they help install and configure environment variables):

- Windows PowerShell: `.\scripts\setup_espeak.ps1`
- Windows CMD: `scripts\setup_espeak_windows.bat`
- macOS / Linux: `./scripts/setup_espeak.sh`

Manual installation:
- macOS: `brew install espeak-ng`
- Linux: `apt install espeak-ng`

## Development & Validation

- Run tests: `pytest -q`
- Run examples:
  - Chinese: `python examples/chinese_examples.py`
  - English: `python examples/english_examples.py`
  - Japanese: `python examples/japanese_examples.py`
- Generate project snapshot: `python tools/snapshot.py` (outputs `snapshot.md`)

## License

MIT License

## Acknowledgments

- [pypinyin](https://github.com/mozillazg/python-pinyin)
- [python-Levenshtein](https://github.com/maxbachmann/Levenshtein)
- [Pinyin2Hanzi](https://github.com/letiantian/Pinyin2Hanzi)
- [hanziconv](https://github.com/berniey/hanziconv)
- [phonemizer](https://github.com/bootphon/phonemizer)
- [espeak-ng](https://github.com/espeak-ng/espeak-ng)
- [cutlet](https://github.com/polm/cutlet)
- [fugashi](https://github.com/polm/fugashi)

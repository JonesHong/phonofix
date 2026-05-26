# phonofix v0.4.0 — Schema Reference

## 1. Confusion Rule Schema (`schemas/confusion-rule.schema.json`)

### Purpose

The confusion rule file tells `PhoneticMatcher` which phonemes are acoustically or
orthographically similar enough to be treated as "equivalent" during fuzzy matching.
It drives Tier 1–3 of the phonetic match pipeline and determines whether a candidate
term is within acceptable phonetic distance from the ASR output.

### File Format

```json
{
  "version": 1,
  "language": "zh",
  "rules": [
    {
      "from": "ㄢ",
      "to": ["ㄤ"],
      "weight": 1.0
    },
    {
      "from": "ㄗ",
      "to": ["ㄓ", "ㄘ"],
      "weight": 0.8,
      "context": "\\d"
    }
  ]
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer | yes | Must be `1` |
| `language` | string | yes | One of `zh`, `ja`, `en`, `ko` |
| `rules` | array | yes | One or more rule objects (see below) |

**Rule object fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `from` | string | yes | — | Source phoneme/token that may be misrecognised |
| `to` | array of string | yes | — | Phonemes commonly confused with `from` |
| `weight` | float [0, 1] | no | `1.0` | Confusion likelihood; used in edit-distance cost function |
| `context` | string (regex) | no | — | Rule applies only when surrounding text matches this regex |

### Caller Customisation

A caller can ship their own confusion rules to tune phonofix for domain-specific vocabulary
(e.g. game character names with unusual phoneme patterns):

```python
import phonofix

matcher = phonofix.load(
    "my-dict.yaml",
    confusion_rules="my-rules/zh-confusion.json",  # override default
)
```

Validation against `confusion-rule.schema.json` runs at `load()` time.
Invalid files raise `phonofix.SchemaError` with field-level diagnostics.

To stack rules (merge caller overrides on top of built-in defaults):

```python
matcher = phonofix.load(
    "my-dict.yaml",
    confusion_rules=["builtin:zh", "my-rules/zh-confusion.json"],  # ordered merge
)
```

Later entries in the list override earlier entries for the same `from` phoneme.

---

## 2. Tolerance YAML (`schemas/tolerance.example.yaml`)

### Purpose

The tolerance config defines **per-language, per-term-length thresholds** for how much
phonetic edit distance is acceptable before a candidate is rejected.
Different term lengths need different ratios: a 2-character term with one phoneme error
is a 50% miss, while a 10-character term with one error is only 10%.

### File Format

```yaml
version: 1
language: zh
tolerance:
  - {min_len: 2, max_len: 3, ratio: 0.50}
  - {min_len: 4, max_len: 6, ratio: 0.33}
  - {min_len: 7, max_len: 999, ratio: 0.25}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer | yes | Must be `1` |
| `language` | string | yes | One of `zh`, `ja`, `en`, `ko` |
| `tolerance` | array | yes | Ordered list of length bands (first match wins) |

**Tolerance band fields:**

| Field | Type | Description |
|-------|------|-------------|
| `min_len` | integer | Inclusive lower bound of term length (tokens/chars) |
| `max_len` | integer | Inclusive upper bound; use `999` for unbounded |
| `ratio` | float [0, 1] | `max_edit_distance / term_length`; lower = stricter |

### Matching Logic

```
for band in tolerance:
    if band.min_len <= len(term) <= band.max_len:
        max_allowed = floor(len(term) * band.ratio)
        accept = (phonetic_edit_distance <= max_allowed)
        break
```

Tolerance files are loaded per-language and cached. To override for a specific
`PhoneticMatcher` instance:

```python
matcher = phonofix.load(
    "my-dict.yaml",
    tolerance="my-configs/zh-tolerance.yaml",
)
```

---

## 3. Per-Language Must (§四.1)

Each language implementation requires these 5 components. They are **not** part of
universal infrastructure — every language must define them independently:

1. **G2P initialisation** — Initialise the language-specific grapheme-to-phoneme library
   (e.g. `pypinyin` for Chinese, `cutlet + fugashi + unidic-lite` for Japanese,
   `phonemizer/espeak-ng` for English, `ko-pron + python-mecab-ko` for Korean).

2. **Phoneme normalisation** — Convert raw G2P output into a unified IPA-like `Phoneme` tuple
   that the language-agnostic `PhoneticMatcher` can compare across candidates.

3. **Confusion rules** — A `confusion-rule.schema.json`-conforming file listing acoustically
   similar phoneme pairs. Ground truth must come from real ASR error samples (50+ sentences),
   not from phonology textbooks alone.

4. **Tolerance parameters** — A `tolerance.example.yaml`-conforming file mapping term
   length bands to edit-distance ratio thresholds, tuned to the language's typical word
   length distribution.

5. **Tokenizer step strategy** — Define the tokenisation unit:
   - Character-level: Chinese (Han), Japanese (hiragana/katakana/kanji), Korean (jamo blocks)
   - Word-level: English (whitespace/punctuation split)
   The tokenizer determines how the sliding window advances and how `min_len`/`max_len`
   in tolerance bands are measured.

---

## 4. Universal Infrastructure (§四.2)

The following components are implemented **once** and shared across all languages.
Adding a new language does NOT require rewriting any of these:

| Component | Description |
|-----------|-------------|
| **Sliding window matching** | Advances over the tokenised stream, tries each window length from `max_term_len` down to `min_term_len` |
| **Context keyword distance weighting** | Scores candidates higher when `keywords` from the dictionary entry appear within a configurable token radius |
| **Edit distance calculation** | Levenshtein on `Phoneme` tuples; cost function uses `weight` from confusion rules (lower weight = cheaper substitution) |
| **AC engine** | Aho-Corasick automaton (`utils/aho_corasick.py` — self-hosted, replaces `pyahocorasick`); rebuilt on hot-reload |
| **Phoneme LRU cache** | Per-backend in-process cache keyed on raw text; avoids repeated G2P inference for repeated terms |
| **Dictionary schema validator** | Validates `dict-v2.yaml` at `add_terms()` entry point; rejects ambiguous definitions before they enter the AC index |
| **Active vs protect arbitration** | When `mode=replace` and `mode=protect` candidates overlap, the protect mask wins unconditionally |

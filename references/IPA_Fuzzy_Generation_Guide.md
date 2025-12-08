# English IPA-Based Fuzzy Variant Generation System

## Overview

The English module uses an **IPA (International Phonetic Alphabet) phoneme-based fuzzy variant generation system** to automatically generate spelling variants for proper nouns. This system enables **new word generalization** - the ability to generate variants for words not present in any dictionary.

## Core Architecture

### Three-Stage Workflow

```
Term → IPA → Fuzzy IPA → Spellings
```

1. **Term → IPA**: Convert English word to IPA using phonemizer/espeak-ng
2. **IPA → Fuzzy IPA**: Apply phoneme confusion rules to generate phonetic variants
3. **Fuzzy IPA → Spellings**: Reverse-lookup to generate real spelling variants

### Example Flow

```python
# Input: "Python"

# Stage 1: Term → IPA
"Python" → "ˈpaɪθɑn"

# Stage 2: IPA → Fuzzy IPA (apply confusion rules)
"ˈpaɪθɑn" → [
    "ˈpaɪθɑn",   # original
    "ˈbaɪθɑn",   # p→b (voicing)
    "ˈpaɪðɑn",   # θ→ð (voicing)
    "ˈpaɪfɑn",   # θ→f (similar phone)
    "ˈpaɪsɑn",   # θ→s (similar phone)
    "ˈpaɪθʌn",   # ɑ→ʌ (vowel)
    # ... more variants
]

# Stage 3: Fuzzy IPA → Spellings (reverse lookup)
"ˈbaɪθɑn" → "bython"
"ˈpaɪfɑn" → "pifon", "pifan"
"ˈpaɪsɑn" → "pison", "pisan"
# ... more spellings

# Final Output (after deduplication):
["bython", "pifon", "pifan", "pisan", "pison", "pythom", ...]
```

## IPA Phoneme Confusion Rules

### 1. Voicing Confusions

Pairs of consonants that differ only in voicing (vocal cord vibration):

| Unvoiced | Voiced | Example |
|----------|--------|---------|
| p | b | "Python" [paɪθɑn] → "Bython" [baɪθɑn] |
| t | d | "tent" [tɛnt] → "dent" [dɛnt] |
| k | g | "coat" [koʊt] → "goat" [ɡoʊt] |
| f | v | "fast" [fæst] → "vast" [væst] |
| s | z | "bus" [bʌs] → "buzz" [bʌz] |
| θ | ð | "think" [θɪŋk] → "this" [ðɪs] |
| ʃ | ʒ | "resh" [rɛʃ] → "rouge" [ruːʒ] |

**Configuration**: `EnglishPhoneticConfig.IPA_VOICING_CONFUSIONS`

### 2. Similar Phone Confusions

Phonetically similar consonants often confused by non-native speakers:

| Phone 1 | Phone 2 | Example |
|---------|---------|---------|
| θ | f | "think" [θɪŋk] → "fink" [fɪŋk] |
| θ | s | "think" [θɪŋk] → "sink" [sɪŋk] |
| l | r | "light" [laɪt] → "right" [raɪt] (Asian speakers) |
| v | w | "vest" [vɛst] → "west" [wɛst] |
| ð | z | "the" [ðə] → "ze" [zə] |

**Configuration**: `EnglishPhoneticConfig.IPA_SIMILAR_PHONE_CONFUSIONS`

### 3. Vowel Length Confusions

Long and short vowel pairs:

| Long | Short | Example |
|------|-------|---------|
| iː | ɪ | "beat" [biːt] → "bit" [bɪt] |
| uː | ʊ | "pool" [puːl] → "pull" [pʊl] |
| ɔː | ɒ | "caught" [kɔːt] → "cot" [kɒt] |
| ɑː | ʌ | "cart" [kɑːrt] → "cut" [kʌt] |
| ɜː | ə | "bird" [bɜːrd] → "about" [əˈbaʊt] |

**Configuration**: `EnglishPhoneticConfig.IPA_VOWEL_LENGTH_CONFUSIONS`

### 4. Reduction Rules

Common phonetic reductions in casual speech:

| Full | Reduced | Example |
|------|---------|---------|
| ɪŋ | ɪn | "working" [ˈwɜːkɪŋ] → [ˈwɜːkɪn] |
| ər | ə | "butter" [ˈbʌtər] → [ˈbʌtə] |

**Configuration**: `EnglishPhoneticConfig.IPA_REDUCTION_RULES`

## IPA → Spelling Reverse Lookup

### Phoneme-to-Grapheme Rules

The `IPAToSpellingMapper` class converts IPA phonemes back to English spelling using common grapheme patterns:

```python
PHONEME_TO_GRAPHEME = {
    # Consonants
    'θ': ['th'],
    'ð': ['th'],
    'ʃ': ['sh', 'ti', 'ci'],
    'ʒ': ['s', 'si', 'zi'],
    'tʃ': ['ch', 'tch'],
    'dʒ': ['j', 'g', 'dge'],
    'ŋ': ['ng', 'n'],

    # Vowels
    'iː': ['ee', 'ea', 'e', 'ie'],
    'ɪ': ['i', 'y'],
    'eɪ': ['ay', 'ai', 'a_e', 'ey'],
    'ɛ': ['e', 'ea'],
    'æ': ['a'],
    # ... more mappings
}
```

### Example: IPA → Spelling

```python
# IPA: "ˈpaɪfɑn" (fuzzy variant of "Python")
# Breakdown:
#   ˈ = primary stress (ignored in spelling)
#   p = 'p'
#   aɪ = 'ai', 'ay', 'i_e', 'igh'
#   f = 'f', 'ph'
#   ɑ = 'o', 'a'
#   n = 'n'

# Possible spellings:
#   "pifon", "pifan", "paifon", "paifan", "piphon", "piphan"
```

## Key Advantages

### 1. New Word Generalization

The IPA system can generate variants for words **not present in any dictionary**:

```python
from phonofix import EnglishEngine

engine = EnglishEngine()

# These words don't exist in CMU Dict or any hardcoded patterns
corrector = engine.create_corrector({
    "Ollama": [],      # New AI tool (2024)
    "LangChain": [],   # AI framework (2022)
    "Anthropic": [],   # Company name (2021)
    "Claude": [],      # AI assistant (2023)
})

# System auto-generates variants via IPA:
# "Ollama" → [olama, olema, ollema, olamma, ...]
# "LangChain" → [langchain, lang chain, lankchain, ...]

text = "I use Olama and Langchane for AI"
result = corrector.correct(text)
# Output: "I use Ollama and LangChain for AI"
```

### 2. Linguistically Accurate

All variants are based on **real phonetic confusion patterns** documented in linguistics literature:

- Voicing confusion: Universal phonetic phenomenon
- θ/f confusion: Common among non-native speakers
- l/r confusion: Well-documented for East Asian language speakers
- Vowel length: Common in languages without phonemic vowel length

### 3. Automatic Deduplication

IPA phonetic keys ensure no phonetically identical variants:

```python
# Without IPA deduplication (naive approach):
variants = ["pithon", "pythun", "pithon"]  # duplicate!

# With IPA deduplication:
# "pithon" → IPA: "ˈpɪθɑn"
# "pythun" → IPA: "ˈpaɪθʌn"
# "pithon" → IPA: "ˈpɪθɑn" (duplicate IPA, removed!)
variants = ["pithon", "pythun"]  # unique
```

## Hybrid Approach: IPA + Legacy Patterns

The system combines IPA generation (primary) with legacy ASR patterns (supplementary):

```python
def generate_variants(term):
    variants = {}

    # Method 1: IPA Generation (Primary)
    base_ipa = phonetic.to_phonetic(term)
    ipa_variants = generate_ipa_fuzzy_variants(base_ipa)
    for ipa_var in ipa_variants:
        spellings = ipa_to_spellings(ipa_var)
        variants.update(spellings)

    # Method 2: Legacy ASR Patterns (Supplementary)
    pattern_variants = apply_asr_patterns(term)
    variants.update(pattern_variants)

    # Deduplicate by IPA
    return deduplicate_by_ipa(variants)
```

**Legacy ASR Patterns Include**:
- Syllable splitting: "TensorFlow" → "ten so floor"
- Acronym handling: "API" → "a p i"
- Number-letter confusions: "EKG" → "1kg"
- Hardcoded common mistakes from config

## Performance Characteristics

- **Variant Count**: 5-30 variants per word (after IPA deduplication)
- **Generation Time**: <2 seconds per word
- **Batch Performance**: <1 second average per word (with caching)
- **Memory**: Minimal overhead (only stores IPA mappings)

## Configuration

All IPA confusion rules are defined in `src/phonofix/languages/english/config.py`:

```python
class EnglishPhoneticConfig:
    # Voicing confusions (8 pairs)
    IPA_VOICING_CONFUSIONS = [
        ('p', 'b'), ('t', 'd'), ('k', 'ɡ'),
        ('f', 'v'), ('s', 'z'), ('θ', 'ð'), ('ʃ', 'ʒ')
    ]

    # Similar phone confusions (5 pairs)
    IPA_SIMILAR_PHONE_CONFUSIONS = [
        ('θ', 'f'), ('θ', 's'), ('l', 'r'), ('v', 'w'), ('ð', 'z')
    ]

    # Vowel length confusions (5 pairs)
    IPA_VOWEL_LENGTH_CONFUSIONS = [
        ('iː', 'ɪ'), ('uː', 'ʊ'), ('ɔː', 'ɒ'),
        ('ɑː', 'ʌ'), ('ɜː', 'ə')
    ]

    # Reduction rules (2 rules)
    IPA_REDUCTION_RULES = [
        ('ɪŋ', 'ɪn'), ('ər', 'ə')
    ]
```

## Testing

Comprehensive test suite in `tests/test_english_fuzzy_ipa.py`:

1. **IPA Fuzzy Variant Generation**: Validates phoneme confusion rules
2. **New Word Generalization**: Tests with unseen words (Ollama, LangChain, etc.)
3. **IPA Deduplication**: Ensures no phonetically duplicate variants
4. **IPA → Spelling Mapping**: Validates reverse lookup accuracy
5. **End-to-End Workflow**: Tests complete Term → IPA → Fuzzy IPA → Spellings
6. **Performance Benchmarks**: Ensures <2s generation time
7. **Edge Cases**: Empty strings, single letters, numbers, special characters

## Future Enhancements

### Planned Improvements

1. **Enhanced IPA → Spelling Rules**:
   - Expand phoneme-to-grapheme mappings
   - Add position-dependent rules (initial/medial/final)
   - Context-sensitive spelling generation

2. **Stress Pattern Variations**:
   - Primary stress movement (ˈ)
   - Secondary stress variations (ˌ)
   - Unstressed syllable reduction

3. **Syllable Structure Rules**:
   - Valid onset/coda constraints
   - Phonotactic rules for English
   - Syllable boundary awareness

4. **Statistical Ranking**:
   - Rank variants by likelihood
   - Use corpus frequency for spelling selection
   - Prioritize common confusion patterns

5. **Performance Optimization**:
   - Cache IPA conversions
   - Parallelize variant generation
   - Optimize deduplication algorithm

## References

1. **Phonemizer Library**: https://github.com/bootphon/phonemizer
2. **eSpeak-ng**: https://github.com/espeak-ng/espeak-ng
3. **IPA Chart**: https://www.internationalphoneticassociation.org/content/ipa-chart
4. **English Phonology**: https://en.wikipedia.org/wiki/English_phonology
5. **CMU Pronouncing Dictionary**: http://www.speech.cs.cmu.edu/cgi-bin/cmudict

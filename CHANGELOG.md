# Changelog

All notable changes to Phonofix will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-12-09

### 💥 Breaking Changes

- **ChineseCorrector**: Renamed `asr_text` parameter to `text` for interface consistency
  - Users using keyword argument `asr_text=` need to update to `text=`
  - Positional argument users are not affected (~90% of users)
  - Migration guide available: [MIGRATION_0.2_TO_0.3.md](MIGRATION_0.2_TO_0.3.md)

### ✨ Features

- **BaseCorrector ABC**: Added `BaseCorrector(ABC)` in `core/corrector_interface.py`
  - All correctors now inherit from unified base class
  - Enforces consistent method signatures across languages: `correct(text, full_context, silent)`
  - Provides compile-time interface checking (replaces Protocol-only approach)
  - Improves IDE support and type checking

- **Unified Interface**: Standardized corrector interface across all languages
  - ChineseCorrector, EnglishCorrector, JapaneseCorrector all use consistent signatures
  - New `full_context` parameter for context-aware corrections (optional)
  - Better type safety with ABC-based inheritance

### 🔧 Internal Improvements

- **Architecture Consistency**: All core components now use ABC pattern
  - PhoneticSystem, Tokenizer, BaseFuzzyGenerator, **BaseCorrector**, CorrectorEngine
  - Improved maintainability and code organization

- **UnifiedCorrector**: Updated type annotations to support both `BaseCorrector` and `CorrectorProtocol`
  - Maintains backward compatibility
  - Better type inference for mixed language scenarios

### 📝 Documentation

- Updated `CLAUDE.md` with BaseCorrector architecture
- Added "Unified Corrector Interface" section to Critical Architecture Decisions
- Created comprehensive migration guide: `MIGRATION_0.2_TO_0.3.md`
- Updated module structure diagram with `corrector_interface.py`

### 🧪 Testing

- All 8/8 Chinese corrector tests pass
- Type annotation verification successful
- No functional regressions detected

---

## [0.2.0] - 2025-10-XX

### ✨ Features

- **Japanese Support**: Added full Japanese language support with Romaji phonetic matching
  - New `JapaneseEngine` and `JapaneseCorrector`
  - Context-aware reading generation (e.g., particle "は" → "wa")
  - Handles Hiragana, Katakana, and Kanji
  - Uses cutlet for accurate phonetic conversion

- **Cross-Lingual Vocabulary Mapping**: Pre-matching for terms spanning multiple languages
  - Solves issues where mixed-language terms get split by router
  - Example: "PCN的引流袋" → "PCN引流袋" (prevents splitting)
  - Set via `corrector.set_cross_lingual_mappings()`

- **Competitive Correction for English Segments**: Improved handling of short alphanumeric codes
  - Multiple correctors compete for best match
  - Better handling of ASR errors like "1kg" → "EKG"
  - Priority order: Japanese (Romaji) → Chinese → English

### 🐛 Bug Fixes

- Fixed language routing for Japanese Romaji segments
- Improved detection of short alphanumeric codes in mixed text

### 📝 Documentation

- Added Japanese examples: `examples/japanese_examples.py`
- Updated architecture documentation with Japanese module
- Added Japanese expansion specifications

---

## [0.1.0] - 2025-XX-XX

### ✨ Features

- **Initial Release**: Multi-language phonetic similarity-based proper noun substitution
- **Chinese Support**: Pinyin fuzzy matching with Taiwan Mandarin characteristics
- **English Support**: IPA phonetic similarity matching with espeak-ng integration
- **Mixed Language Support**: Automatic language detection and routing
- **Streaming Support**: Real-time ASR and LLM output processing
- **Fuzzy Phonetic Generation**: Automatic variant generation based on linguistic rules

### 🏗️ Architecture

- Modular language-agnostic design
- Singleton pattern for expensive phonetic backends
- ABC-based interfaces for PhoneticSystem and Tokenizer
- Lightweight corrector instances with shared backends

---

## Version History Summary

| Version | Date | Key Changes |
|---------|------|-------------|
| 0.3.0 | 2025-12-09 | BaseCorrector ABC, interface unification, breaking changes |
| 0.2.0 | 2025-10-XX | Japanese support, cross-lingual mapping, competitive correction |
| 0.1.0 | 2025-XX-XX | Initial release with Chinese and English support |

---

**Note**: Dates marked as "XX-XX" are placeholder and should be updated with actual release dates.

# Changelog

This project follows Semantic Versioning (SemVer).

> Note: Before `1.0.0` (i.e., in `0.x`), the API may include breaking changes. For the stable public surface, follow the official entry points documented in `README.md`.

## [0.3.1] - 2025-12-16

### Changed

- Refreshed the README header section: added the project logo and badges (PyPI/Python versions/License/Snapshot/Changelog) and normalized links to the latest repository.
- Added `assets/images/logo.png` for documentation use.

## [0.3.0] - 2025-12-16

### Breaking Changes

- Minimum Python version is now `>=3.10` (see `pyproject.toml`).
- The stable public API is engine-first: `ChineseEngine` / `EnglishEngine` / `JapaneseEngine`. Legacy `UnifiedEngine` / `UnifiedCorrector` / streaming entry points are no longer treated as stable public API (migrate using the latest examples in `README.md`).
- `import phonofix` is now lightweight via PEP 562 lazy imports, avoiding importing/initializing heavy dependencies at import time (e.g., `phonemizer` / `pypinyin` / `cutlet` / `fugashi`).

### Added

- Japanese support: `JapaneseEngine`, a romaji phonetic system, tokenization, and fuzzy variant generation.
- Observability & failure policy: `on_event` callback support, `trace_id`, and unified `mode` / `fail_policy` behavior (e.g., degrade vs. raise when fuzzy fails).
- Backend & cache stats: unified `get_cache_stats()` schema across Chinese/English/Japanese; English backend supports observable `initialize_lazy()` background initialization.
- Tooling & docs: `tools/snapshot.py` to generate project snapshots (`snapshot.zh-TW.md` / `snapshot.md`).

### Changed

- Modularized the per-language corrector pipeline into `candidates` / `filters` / `indexing` / `scoring` / `replacements` modules for maintainability.
- Made Japanese exact-match more conservative to avoid short romaji aliases matching inside longer tokens (e.g., `ai` inside `kaihatsu`).

### Fixed

- `initialize_lazy()` background initialization failures are now observable via backend stats, with test coverage to prevent silent failures.

# Changelog

This project follows Semantic Versioning (SemVer).

> Note: Before `1.0.0` (i.e., in `0.x`), the API may include breaking changes. For the stable public surface, follow the official entry points documented in `README.md`.

## [0.4.0] - 2026-05-26

### Added

- **Tier 1-3 fuzzy hash path** for 4 languages (zh/ja/en/ko). Per-language adapters: zh canonical_key + ja normalized_cache + en Double Metaphone (jellyfish) + ko jamo decompose with `KOREAN_CONFUSION_MAP_JAMO`.
- **Tier 5 fallback** to legacy `fuzzy_buckets` for "rule-outside substitution" cases. Default `enable_tier5_fallback=True` gives 100% v0.3.x parity; set `False` for ~3× speed (literal-hit case stays fast either way).
- **`pyahocorasick` C extension** replaces self-impl AC engine. Real-data measured: normal query 7-9× faster, delete-1 ~5×, memory 100×+ smaller.
- **AC delete-1 expansion** (Tier 3) for 1-char-deletion fuzzy via `core/ac_expansion.py`.
- **Korean support (experimental)**: `KoreanPhonemizer` + 17 syllable / 10 jamo confusion rules (8 paper-cited + Zeroth real-data 7 補). `KOREAN_STATUS="experimental"` flag, 61.9% measured coverage on Zeroth-20 (below 70% target — caller should retest with own dataset).
- **macOS auto-detect `espeak-ng`** library path (brew install — no env var needed).
- **DictRuntime atomic snapshot** + `add_terms` / `remove_terms` hot reload (< 1ms on 10K terms).
- **StreamBuffer** `feed` / `flush` with crossing-hit retract + duplicate suppression.
- **AsyncEventQueue** + `trace_id` contextvar for `on_event` async dispatch.
- **5 CLI subcommands**: `phonofix lint / build / correct / bench / migrate`.
- **Bench suite** + GitHub Actions perf regression gate (`.github/workflows/perf.yml`).
- New OSS hygiene: `LICENSE` / `SECURITY.md` / `CONTRIBUTING.md` / `RELEASE.md`.

### Changed

- Speed: zh small dict literal-hit ~48× (2.5K → ~120K ops/s); full fuzzy with Tier 5 ON ~2-3× v0.3.x (LLM exact-hit hot path very fast).
- `phonofix.ChineseEngine` / `JapaneseEngine` / `EnglishEngine` remain backward-compatible (走 v0.3.x path; thin-compat layer + `DeprecationWarning` planned for v0.5.0 with ≥ 3-month grace).
- Dict yaml schema v2 introduced (`mode: protect | replace`); v1 still loaded via `phonofix migrate dict-v1.yaml --out v2.yaml`.

### Fixed

- Canonical auto-protect mask integrated into new `PhoneticMatcher` (carried from v0.3.2 P0).
- Tier 1 overlap priority: longest-span exact > Tier 1 > Tier 3 delete-1 (Codex audit B.1).
- `add_terms` / `remove_terms` now invalidates Tier 5 legacy corrector cache (reviewer P1).
- zh Tier 1 pinyin offset drift on ASCII/punctuation input (`errors="default"` preserves 1:1 char alignment — Codex audit B.3).
- Tier 5 event payload schema unified (nullable `start/end/term/canonical/original_alias` for caller dispatch — Codex audit A.4).

### Dependencies

- Added `pyahocorasick>=2.1.0`, `jellyfish>=1.2.1` to core.
- New optional extras: `[ko]` with `ko-pron + python-mecab-ko`.

### Tests

- 554 in-scope tests passed (+18 adversarial tests via independent reviewer agent + Codex audit).

## [0.3.2] - 2026-05-25

### Fixed

- Canonical literals are now preserved against alias-substring replacement. When a dictionary alias was a substring of its canonical (e.g. alias `北車` of canonical `台北車站`), input containing the canonical literal was being destroyed (`台北車站` → `台台北車站站`). Canonicals are now auto-added to the protection mask. Affects all three languages — the bug lived in the language-neutral pipeline (#1).
- Chinese and English `resolve_conflicts` now use a `(score, -length)` sort key to prefer longer matches on score ties, matching the existing Japanese behavior. Prevents short aliases from winning over longer aliases that fully cover the same span.

### Tests

- Added `tests/test_canonical_substring_preservation.py` — 7 regression tests covering ch/ja canonical-literal preservation, alias-still-replaceable, mixed input, and phonetic-alias cases.
- Adjusted two `tests/test_performance_guards.py` fuzzy-bucket tests whose inputs were dictionary canonicals; they now explicitly clear `protected_terms` to exercise the fuzzy path (the new auto-protect short-circuits earlier — same final output, faster).

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

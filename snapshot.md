# Snapshot

- Root: `phonofix/`
- Generated: `2025-12-15 22:48:48`
- Max tree depth: `12`
- Include private symbols: `True`
- Use .gitignore: `True`

## Project File Tree
```text
phonofix/
├── src/
│   └── phonofix/
│       ├── backend/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── chinese_backend.py
│       │   ├── english_backend.py
│       │   ├── japanese_backend.py
│       │   └── stats.py
│       ├── core/
│       │   ├── protocols/
│       │   │   ├── __init__.py
│       │   │   ├── corrector.py
│       │   │   ├── fuzzy.py
│       │   │   └── pipeline.py
│       │   ├── engine_interface.py
│       │   ├── events.py
│       │   ├── phonetic_interface.py
│       │   ├── pipeline_corrector.py
│       │   ├── term_config.py
│       │   └── tokenizer_interface.py
│       ├── languages/
│       │   ├── chinese/
│       │   │   ├── __init__.py
│       │   │   ├── candidates.py
│       │   │   ├── config.py
│       │   │   ├── corrector.py
│       │   │   ├── engine.py
│       │   │   ├── filters.py
│       │   │   ├── fuzzy_generator.py
│       │   │   ├── indexing.py
│       │   │   ├── number_variants.py
│       │   │   ├── phonetic_impl.py
│       │   │   ├── replacements.py
│       │   │   ├── scoring.py
│       │   │   ├── tokenizer.py
│       │   │   ├── types.py
│       │   │   └── utils.py
│       │   ├── english/
│       │   │   ├── __init__.py
│       │   │   ├── candidates.py
│       │   │   ├── config.py
│       │   │   ├── corrector.py
│       │   │   ├── engine.py
│       │   │   ├── filters.py
│       │   │   ├── fuzzy_generator.py
│       │   │   ├── indexing.py
│       │   │   ├── phonetic_impl.py
│       │   │   ├── replacements.py
│       │   │   ├── scoring.py
│       │   │   ├── tokenizer.py
│       │   │   └── types.py
│       │   └── japanese/
│       │       ├── __init__.py
│       │       ├── candidates.py
│       │       ├── config.py
│       │       ├── corrector.py
│       │       ├── engine.py
│       │       ├── filters.py
│       │       ├── fuzzy_generator.py
│       │       ├── indexing.py
│       │       ├── phonetic_impl.py
│       │       ├── replacements.py
│       │       ├── scoring.py
│       │       ├── tokenizer.py
│       │       ├── types.py
│       │       └── utils.py
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── aho_corasick.py
│       │   └── logger.py
│       └── __init__.py
├── tools/
│   ├── __init__.py
│   ├── benchmark_phonetic.py
│   └── translation_client.py
├── .gitignore
├── CLAUDE.md
├── pyproject.toml
├── README.md
├── README.zh-TW.md
├── requirements.txt
├── snapshot.md
└── uv.lock
```

## Functions / Classes (AST)
### `src/phonofix/__init__.py`
- **function** `__getattr__(name: ...) -> ...` — Lazy-load top-level public symbols (PEP 562).
- **function** `__dir__() -> ...` — Expose lazy-loaded symbols to IDE/dir().

### `src/phonofix/backend/base.py`
- **class** `PhoneticBackend(ABC)` — Phonetic backend abstract base class (ABC).
- **method** `PhoneticBackend.to_phonetic(self, text: ...) -> ...` — Convert text to a phonetic representation.
- **method** `PhoneticBackend.is_initialized(self) -> ...` — Check whether the backend is initialized.
- **method** `PhoneticBackend.initialize(self) -> ...` — Initialize the backend.
- **method** `PhoneticBackend.get_cache_stats(self) -> ...` — Get cache statistics.
- **method** `PhoneticBackend.clear_cache(self) -> ...` — Clear the cache.

### `src/phonofix/backend/chinese_backend.py`
- **function** `_get_pypinyin()` — Lazy-load the `pypinyin` module.
- **function** `_cached_get_pinyin_string(text: ...) -> ...` — Cached pinyin-string computation.
- **function** `_cached_get_pinyin_syllables(text: ...) -> ...` — Cached pinyin syllable list (no tones, lowercase).
- **function** `_cached_get_initials(text: ...) -> ...` — Cached initials list computation.
- **function** `_cached_get_finals(text: ...) -> ...` — Cached finals list computation.
- **class** `ChinesePhoneticBackend(PhoneticBackend)` — Chinese phonetic backend (singleton).
- **method** `ChinesePhoneticBackend.__init__(self)` — Initialize the backend.
- **method** `ChinesePhoneticBackend.initialize(self) -> ...` — Initialize the backend.
- **method** `ChinesePhoneticBackend.is_initialized(self) -> ...` — Check whether it is initialized.
- **method** `ChinesePhoneticBackend.to_phonetic(self, text: ...) -> ...` — Convert Chinese text to pinyin.
- **method** `ChinesePhoneticBackend.get_initials(self, text: ...) -> ...` — Get the initials list for the text.
- **method** `ChinesePhoneticBackend.get_pinyin_syllables(self, text: ...) -> ...` — Get the pinyin syllable list for the text (no tones).
- **method** `ChinesePhoneticBackend.get_finals(self, text: ...) -> ...` — Get the finals list for the text.
- **method** `ChinesePhoneticBackend.get_cache_stats(self) -> ...` — Get pinyin cache statistics.
- **method** `ChinesePhoneticBackend.clear_cache(self) -> ...` — Clear all pinyin caches.
- **function** `get_chinese_backend() -> ...` — Get the `ChinesePhoneticBackend` singleton.

### `src/phonofix/backend/english_backend.py`
- **function** `_setup_espeak_library()` — Auto-set the `PHONEMIZER_ESPEAK_LIBRARY` environment variable (Windows only).
- **function** `_get_phonemize()` — Lazy-load the `phonemizer` module.
- **function** `_record_hits(count: ...=...) -> ...` — Accumulate cache hit count (thread-safe).
- **function** `_record_misses(count: ...=...) -> ...` — Accumulate cache miss count (thread-safe).
- **function** `_cached_ipa_convert(text: ...) -> ...` — Cached IPA conversion (single string).
- **function** `_normalize_english_text_for_ipa(text: ...) -> ...` — Light normalization before English IPA conversion (for token/canonical alignment).
- **function** `_batch_ipa_convert(texts: ...) -> ...` — Batch IPA conversion (performance optimization).
- **class** `EnglishPhoneticBackend(PhoneticBackend)` — English phonetic backend (singleton).
- **method** `EnglishPhoneticBackend.__init__(self)` — Initialize the backend.
- **method** `EnglishPhoneticBackend.initialize(self) -> ...` — Initialize `espeak-ng`.
- **method** `EnglishPhoneticBackend.initialize_lazy(self) -> ...` — Initialize `espeak-ng` in a background thread and return immediately (non-blocking).
- **function** `EnglishPhoneticBackend.initialize_lazy._background_init()` — Background initialization task.
- **method** `EnglishPhoneticBackend.is_initialized(self) -> ...` — Check whether it is initialized.
- **method** `EnglishPhoneticBackend.to_phonetic(self, text: ...) -> ...` — Convert text to IPA.
- **method** `EnglishPhoneticBackend.to_phonetic_batch(self, texts: ...) -> ...` — Batch convert text to IPA (performance optimization).
- **method** `EnglishPhoneticBackend.get_cache_stats(self) -> ...` — Get IPA cache statistics.
- **method** `EnglishPhoneticBackend.clear_cache(self) -> ...` — Clear the IPA cache.
- **function** `get_english_backend() -> ...` — Get the `EnglishPhoneticBackend` singleton.
- **function** `is_phonemizer_available() -> ...` — Check whether `phonemizer` is available.

### `src/phonofix/backend/japanese_backend.py`
- **function** `_strip_macrons(text: ...) -> ...` — Remove romaji macrons.
- **function** `_get_cutlet() -> ...` — Get a `cutlet` instance (lazy loading).
- **function** `_get_fugashi() -> ...` — Get `fugashi.Tagger` (lazy loading).
- **function** `_cached_romaji(text: ...) -> ...` — Cache: Japanese text -> romaji.
- **function** `_cached_tokens(text: ...) -> ...` — Cache: Japanese tokenization results (surface tokens).
- **class** `JapanesePhoneticBackend(PhoneticBackend)` — Japanese phonetic backend (singleton).
- **method** `JapanesePhoneticBackend.__init__(self) -> ...` — Create the backend instance (use `get_japanese_backend()` to get the singleton).
- **method** `JapanesePhoneticBackend.initialize(self) -> ...` — Initialize the backend (thread-safe).
- **method** `JapanesePhoneticBackend.is_initialized(self) -> ...` — Return whether the backend has finished initialization.
- **method** `JapanesePhoneticBackend.to_phonetic(self, text: ...) -> ...` — Convert Japanese text to romaji (phonetic key).
- **method** `JapanesePhoneticBackend.tokenize(self, text: ...) -> ...` — Tokenize Japanese text into a list of surface tokens.
- **method** `JapanesePhoneticBackend.get_cutlet(self) -> ...` — Get the `cutlet` instance (ensures initialized before returning).
- **method** `JapanesePhoneticBackend.get_tagger(self) -> ...` — Get `fugashi.Tagger` (ensures initialized before returning).
- **method** `JapanesePhoneticBackend.get_cache_stats(self) -> ...` — Return cache stats in the unified format (romaji/tokens).
- **method** `JapanesePhoneticBackend.clear_cache(self) -> ...` — Clear the romaji/tokens `lru_cache` (mainly for tests or performance observation).
- **function** `get_japanese_backend() -> ...` — Get the `JapanesePhoneticBackend` singleton (thread-safe).

### `src/phonofix/backend/stats.py`
- **class** `CacheStats(TypedDict)` — Statistics for a single cache.
- **class** `LazyInitError(TypedDict)` — Error information when lazy init fails (for observability/debugging).
- **class** `LazyInitStats(TypedDict)` — Observable status for lazy initialization.
- **class** `BackendStats(TypedDict)` — Backend stats overview (unified return schema).

### `src/phonofix/core/engine_interface.py`
- **class** `CorrectorEngine(ABC)` — Correction engine abstract base class (ABC).
- **method** `CorrectorEngine._init_logger(self, verbose: ...=..., on_timing: ...=...) -> ...` — Initialize the engine logger and (optional) timing callback.
- **method** `CorrectorEngine._log_timing(self, operation: ...) -> ...` — Create a timing context (`TimingContext`).
- **method** `CorrectorEngine.create_corrector(self, term_dict: ..., **kwargs) -> ...` — Create a language corrector from `term_dict`.
- **method** `CorrectorEngine.is_initialized(self) -> ...` — Return whether the engine is initialized (including the underlying backend).
- **method** `CorrectorEngine.get_backend_stats(self) -> ...` — Return backend cache/stats (advanced: performance observability, debugging).

### `src/phonofix/core/events.py`
- **class** `CorrectionEvent(TypedDict)` — Correction event schema (`TypedDict`, `total=False`).

### `src/phonofix/core/phonetic_interface.py`
- **class** `PhoneticSystem(ABC)` — Language phonetic system abstract interface (ABC).
- **method** `PhoneticSystem.to_phonetic(self, text: ...) -> ...` — Convert text to a phonetic representation (e.g., pinyin, IPA, romaji).
- **method** `PhoneticSystem.are_fuzzy_similar(self, phonetic1: ..., phonetic2: ...) -> ...` — Determine whether two phonetic strings are fuzzily similar.
- **method** `PhoneticSystem.get_tolerance(self, length: ...) -> ...` — Get the tolerance threshold based on length.

### `src/phonofix/core/pipeline_corrector.py`
- **class** `PipelineCorrectorBase(ABC)` — Corrector pipeline base
- **method** `PipelineCorrectorBase._build_protection_mask(self, text: ...) -> ...` — Build the protection mask.
- **method** `PipelineCorrectorBase._generate_exact_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — Generate candidate drafts for exact matches.
- **method** `PipelineCorrectorBase._generate_fuzzy_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — Generate candidate drafts for fuzzy matches.
- **method** `PipelineCorrectorBase._score_candidate_drafts(self, drafts: ...) -> ...` — Score candidate drafts and return comparable candidates.
- **method** `PipelineCorrectorBase._resolve_conflicts(self, candidates: ...) -> ...` — Resolve candidate conflicts and return the final candidates to apply.
- **method** `PipelineCorrectorBase._apply_replacements(self, text: ..., candidates: ..., silent: ...=..., *, trace_id: ...=...) -> ...` — Apply candidates to the text and return the result.
- **method** `PipelineCorrectorBase._emit_pipeline_event(self, event: ..., *, silent: ...) -> ...` — Emit pipeline events (e.g., `fuzzy_error` / `degraded`).
- **method** `PipelineCorrectorBase.correct(self, text: ..., full_context: ...=..., silent: ...=..., *, mode: ...=..., fail_policy: ...=..., trace_id: ...=...) -> ...` — Run the generic correction pipeline.

### `src/phonofix/core/protocols/corrector.py`
- **class** `CorrectorProtocol(Protocol)` — Corrector protocol.
- **method** `CorrectorProtocol.correct(self, text: ..., full_context: ...=..., silent: ...=..., *, mode: ...=..., fail_policy: ...=..., trace_id: ...=...) -> ...` — Correct text (optional full context / silent mode).
- **class** `ContextAwareCorrectorProtocol(CorrectorProtocol, Protocol)` — Context-aware corrector protocol.

### `src/phonofix/core/protocols/fuzzy.py`
- **class** `FuzzyGeneratorProtocol(Protocol)` — Fuzzy variant generator interface (Protocol).
- **method** `FuzzyGeneratorProtocol.generate_variants(self, term: ..., max_variants: ...=...) -> ...` — Generate fuzzy variants for the input term.

### `src/phonofix/core/protocols/pipeline.py`
- **class** `ProtectionMaskBuilderProtocol(Protocol)` — Generate a protection mask.
- **method** `ProtectionMaskBuilderProtocol.build(self, text: ...) -> ...` — Build the protection mask.
- **class** `ExactDraftGeneratorProtocol(Protocol)` — Exact-match draft generator.
- **method** `ExactDraftGeneratorProtocol.generate(self, text: ..., context: ..., protected_indices: ...) -> ...` — Generate exact-match candidate drafts.
- **class** `FuzzyDraftGeneratorProtocol(Protocol)` — Fuzzy-match draft generator.
- **method** `FuzzyDraftGeneratorProtocol.generate(self, text: ..., context: ..., protected_indices: ...) -> ...` — Generate fuzzy-match candidate drafts.
- **class** `DraftScorerProtocol(Protocol)` — Candidate draft scorer.
- **method** `DraftScorerProtocol.score(self, drafts: ...) -> ...` — Score drafts and return candidates.
- **class** `ConflictResolverProtocol(Protocol)` — Candidate conflict resolver.
- **method** `ConflictResolverProtocol.resolve(self, candidates: ...) -> ...` — Resolve candidate conflicts and return the final list to apply.
- **class** `ReplacementApplierProtocol(Protocol)` — Replacement applier.
- **method** `ReplacementApplierProtocol.apply(self, text: ..., candidates: ..., *, silent: ..., trace_id: ...) -> ...` — Apply candidate replacements.

### `src/phonofix/core/term_config.py`
- **class** `NormalizedTermConfig(TypedDict)` — Normalized term config (`TypedDict`, `total=False`).
- **function** `normalize_term_dict(term_dict: ..., *, default_weight: ...=..., default_max_variants: ...=...) -> ...` — Normalize user `term_dict` into `canonical -> NormalizedTermConfig`.

### `src/phonofix/core/tokenizer_interface.py`
- **class** `Tokenizer(ABC)` — Tokenizer abstract interface (ABC).
- **method** `Tokenizer.tokenize(self, text: ...) -> ...` — Split text into a token list (Chinese: characters, English: words).
- **method** `Tokenizer.get_token_indices(self, text: ...) -> ...` — Get the start/end indices of each token in the original text.

### `src/phonofix/languages/chinese/__init__.py`
- **function** `__getattr__(name: ...) -> ...` — Lazy-load main symbols in the language module (PEP 562).
- **function** `__dir__() -> ...` — Expose lazy-loaded symbols to IDE/dir().

### `src/phonofix/languages/chinese/candidates.py`
- **function** `generate_exact_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., exact_matcher: ..., exact_items_by_alias: ..., protected_terms: ...) -> ...` — Generate exact-match candidate drafts.
- **function** `process_fuzzy_match_draft(*, context: ..., start_idx: ..., original_segment: ..., item: ..., engine: ..., config: ..., utils: ..., segment_initials: ...=..., segment_syllables: ...=...) -> ...` — Process a fuzzy match.
- **function** `generate_fuzzy_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., fuzzy_buckets: ..., config: ..., engine: ..., utils: ..., protected_terms: ...) -> ...` — Search all possible fuzzy correction candidates (no scoring; drafts only).
- **function** `score_candidate_drafts(*, drafts: ..., use_canonical: ...) -> ...` — Unified scoring stage.

### `src/phonofix/languages/chinese/config.py`
- **class** `ChinesePhoneticConfig` — Pinyin config class — centralizes all pinyin fuzzy rules.
- **method** `ChinesePhoneticConfig.build_group_to_initials_map(cls)` — Build a reverse lookup table: fuzzy group -> initials list.

### `src/phonofix/languages/chinese/corrector.py`
- **class** `ChineseCorrector(PipelineCorrectorBase)` — Chinese corrector.
- **method** `ChineseCorrector._from_engine(cls, engine: ..., term_mapping: ..., protected_terms: ...=..., on_event: ...=...) -> ...` — Internal factory method called by `ChineseEngine`.
- **method** `ChineseCorrector._emit_replacement(self, candidate: ..., *, silent: ..., trace_id: ...) -> ...` — Emit a `replacement` event (and log when not in silent mode).
- **method** `ChineseCorrector._emit_pipeline_event(self, event: ..., *, silent: ...) -> ...` — Emit pipeline events (e.g., `fuzzy_error` / `degraded`).
- **method** `ChineseCorrector._build_protection_mask(self, text: ...) -> ...` — Build a `protected_terms` mask (avoid replacing protected spans).
- **method** `ChineseCorrector._generate_exact_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — Generate exact-match candidate drafts (delegates to the `candidates` module).
- **method** `ChineseCorrector._generate_fuzzy_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — Generate fuzzy-match candidate drafts (delegates to `candidates`, with bucket pruning).
- **method** `ChineseCorrector._score_candidate_drafts(self, drafts: ...) -> ...` — Score candidate drafts (delegates to the `candidates` module).
- **method** `ChineseCorrector._resolve_conflicts(self, candidates: ...) -> ...` — Resolve candidate conflicts (delegates to the `replacements` module).
- **method** `ChineseCorrector._apply_replacements(self, text: ..., candidates: ..., silent: ...=..., *, trace_id: ...=...) -> ...` — Apply replacements and emit events/logs (delegates to `replacements`).

### `src/phonofix/languages/chinese/engine.py`
- **class** `ChineseEngine(CorrectorEngine)` — Chinese correction engine.
- **method** `ChineseEngine.__init__(self, phonetic_config: ...=..., *, enable_surface_variants: ...=..., enable_representative_variants: ...=..., verbose: ...=..., on_timing: ...=...)` — Initialize `ChineseEngine`.
- **method** `ChineseEngine.phonetic(self) -> ...` — Get the Chinese phonetic system (pinyin conversion & similarity).
- **method** `ChineseEngine.tokenizer(self) -> ...` — Get the Chinese tokenizer (for sliding windows and token indices).
- **method** `ChineseEngine.fuzzy_generator(self) -> ...` — Get the Chinese fuzzy variant generator (homophones/near-homophones, etc.).
- **method** `ChineseEngine.utils(self) -> ...` — Get Chinese phonetic utilities (initial/final extraction, fuzzy checks, etc.).
- **method** `ChineseEngine.config(self) -> ...` — Get the Chinese phonetic config.
- **method** `ChineseEngine.backend(self) -> ...` — Get the Chinese phonetic backend (advanced: cache stats/clearing).
- **method** `ChineseEngine.is_initialized(self) -> ...` — Check whether the engine is initialized.
- **method** `ChineseEngine.get_backend_stats(self) -> ...` — Get backend cache statistics.
- **method** `ChineseEngine.create_corrector(self, term_dict: ..., protected_terms: ...=..., on_event: ...=..., **kwargs) -> ...` — Create `ChineseCorrector` from `term_dict`.
- **method** `ChineseEngine._normalize_term_value(self, term: ..., value: ...) -> ...` — Normalize a `term_dict` value into the internal config dict.
- **method** `ChineseEngine._filter_aliases_by_pinyin(self, aliases: ...) -> ...` — Deduplicate aliases by pinyin (keep the first spelling).

### `src/phonofix/languages/chinese/filters.py`
- **function** `check_context_bonus(*, full_text: ..., start_idx: ..., end_idx: ..., keywords: ..., window_size: ...=...) -> ...` — Check context keyword bonus.
- **function** `build_protection_mask(*, text: ..., protected_terms: ..., protected_matcher: ...) -> ...` — Build a protection mask and mark spans that should not be corrected (protected terms).
- **function** `is_segment_protected(*, start_idx: ..., word_len: ..., protected_indices: ...) -> ...` — Check whether a span contains protected indices.
- **function** `is_span_protected(*, start: ..., end: ..., protected_indices: ...) -> ...` — Check whether a span hits the protection mask.
- **function** `is_valid_segment(*, segment: ...) -> ...` — Check whether a span contains valid characters (Chinese/English/digits).
- **function** `should_exclude_by_context(*, full_text: ..., exclude_when: ...) -> ...` — Check whether to exclude a correction based on context.
- **function** `has_required_keyword(*, full_text: ..., keywords: ...) -> ...` — Check whether required keywords are satisfied.

### `src/phonofix/languages/chinese/fuzzy_generator.py`
- **function** `_get_pinyin2hanzi()` — Lazy-load the `Pinyin2Hanzi` module.
- **function** `_get_hanziconv()` — Lazy-load the `hanziconv` module.
- **class** `ChineseFuzzyGenerator(FuzzyGeneratorProtocol)` — Chinese fuzzy variant generator.
- **method** `ChineseFuzzyGenerator.__init__(self, config=..., backend: ...=..., *, enable_representative_variants: ...=..., max_phonetic_states: ...=...)` — Initialize the Chinese fuzzy variant generator.
- **method** `ChineseFuzzyGenerator._pinyin_string(self, text: ...) -> ...` — Get the pinyin string for the text (delegates to backend cache).
- **method** `ChineseFuzzyGenerator.dag_params(self)` — Lazy-initialize DAG parameters.
- **method** `ChineseFuzzyGenerator._pinyin_to_chars(self, pinyin_str, max_chars=...)` — Convert pinyin to possible Hanzi (homophone reverse lookup).
- **method** `ChineseFuzzyGenerator._get_char_variations(self, char)` — Get all fuzzy-phonetic variants for a single Hanzi character.
- **method** `ChineseFuzzyGenerator._generate_char_combinations(self, char_options_list, *, max_results: ...)` — Generate permutations of all character variants.
- **method** `ChineseFuzzyGenerator._add_sticky_phrase_aliases(self, term, aliases)` — Add phrase aliases for liaison/colloquial pronunciations.
- **method** `ChineseFuzzyGenerator.generate_variants(self, term: ..., max_variants: ...=...)` — Generate a list of fuzzy variants for the input term.
- **method** `ChineseFuzzyGenerator.filter_homophones(self, term_list)` — Filter homophones.

### `src/phonofix/languages/chinese/indexing.py`
- **function** `parse_term_data(data: ...) -> ...` — Parse the term data structure and extract aliases, keywords, exclude-when rules, and weights.
- **function** `create_index_item(*, engine: ..., utils: ..., term: ..., canonical: ..., keywords: ..., exclude_when: ..., weight: ...) -> ...` — Build an index item and precompute pinyin/initial features.
- **function** `build_search_index(*, engine: ..., utils: ..., term_mapping: ...) -> ...` — Build the search index.
- **function** `build_exact_matcher(search_index: ...) -> ...` — Build an exact-match index for surface aliases (Aho-Corasick).
- **function** `build_fuzzy_buckets(*, search_index: ..., config: ...) -> ...` — Build a bucket index for cheap pruning.

### `src/phonofix/languages/chinese/number_variants.py`
- **function** `generate_number_variants(number_str: ...) -> ...` — Generate all possible pronunciation variants for a numeric string.
- **function** `get_variant_count(length: ...) -> ...` — Calculate the maximum number of variants for an N-digit number.

### `src/phonofix/languages/chinese/phonetic_impl.py`
- **class** `ChinesePhoneticSystem(PhoneticSystem)` — Chinese phonetic system.
- **method** `ChinesePhoneticSystem.__init__(self, backend: ...=...)` — Initialize the Chinese phonetic system.
- **method** `ChinesePhoneticSystem.to_phonetic(self, text: ...) -> ...` — Convert Chinese text to a pinyin string.
- **method** `ChinesePhoneticSystem.are_fuzzy_similar(self, phonetic1: ..., phonetic2: ...) -> ...` — Determine whether two pinyin strings are fuzzily similar.
- **method** `ChinesePhoneticSystem.get_tolerance(self, length: ...) -> ...` — Get the tolerance threshold based on pinyin length.

### `src/phonofix/languages/chinese/replacements.py`
- **function** `resolve_conflicts(*, candidates: ...) -> ...` — Resolve candidate conflicts.
- **function** `apply_replacements(*, text: ..., final_candidates: ..., emit_replacement: ..., silent: ...=..., trace_id: ...=...) -> ...` — Apply corrections and emit events/logs.

### `src/phonofix/languages/chinese/scoring.py`
- **function** `get_dynamic_threshold(*, word_len: ..., is_mixed: ...=...) -> ...` — Dynamically calculate tolerance based on term length.
- **function** `calculate_pinyin_similarity(*, engine: ..., config: ..., utils: ..., segment: ..., target_pinyin_str: ..., segment_syllables: ...=..., target_syllables: ...=...) -> ...` — Calculate pinyin similarity.
- **function** `check_initials_match(*, engine: ..., config: ..., utils: ..., segment: ..., item: ..., segment_initials: ...=...) -> ...` — Check whether initials match.
- **function** `calculate_final_score(*, error_ratio: ..., item: ..., has_context: ..., context_distance: ...=...) -> ...` — Calculate final score (lower is better).

### `src/phonofix/languages/chinese/tokenizer.py`
- **class** `ChineseTokenizer(Tokenizer)` — Chinese tokenizer.
- **method** `ChineseTokenizer.tokenize(self, text: ...) -> ...` — Split Chinese text into a list of characters.
- **method** `ChineseTokenizer.get_token_indices(self, text: ...) -> ...` — Get the start/end indices of each character in the original text.

### `src/phonofix/languages/chinese/types.py`
- **class** `ChineseIndexItem(TypedDict)` — Unified data structure for a single index item (term or alias).
- **class** `ChineseCandidateDraft(TypedDict)` — Candidate draft.
- **class** `ChineseCandidate(TypedDict)` — Final candidate.

### `src/phonofix/languages/chinese/utils.py`
- **class** `ChinesePhoneticUtils` — Chinese phonetic utility class.
- **method** `ChinesePhoneticUtils.__init__(self, config=..., backend: ...=...)` — Initialize Chinese phonetic utilities.
- **method** `ChinesePhoneticUtils.contains_english(text)` — Check whether a string contains ASCII letters.
- **method** `ChinesePhoneticUtils.get_pinyin_string(self, text: ...) -> ...` — Get the pinyin string for the text (no tones, lowercase; delegates to backend cache).
- **method** `ChinesePhoneticUtils.extract_initial_final(pinyin_str)` — Extract initials and finals from pinyin.
- **method** `ChinesePhoneticUtils.is_fuzzy_initial_match(self, init1_list, init2_list)` — Determine whether two initials lists match fuzzily.
- **method** `ChinesePhoneticUtils.check_finals_fuzzy_match(self, pinyin1, pinyin2)` — Check whether finals match fuzzily (also considering initial compatibility).
- **method** `ChinesePhoneticUtils.check_special_syllable_match(self, pinyin1, pinyin2, bidirectional=...)` — Check special-syllable mappings (whole-syllable fuzzy matching).
- **method** `ChinesePhoneticUtils.generate_fuzzy_pinyin_variants(self, pinyin_str, bidirectional=...)` — Generate all fuzzy pinyin variants.
- **method** `ChinesePhoneticUtils.are_fuzzy_similar(self, pinyin1, pinyin2)` — Determine whether two pinyin strings can be treated as fuzzily similar.

### `src/phonofix/languages/english/__init__.py`
- **function** `__getattr__(name: ...) -> ...` — Lazy-load main symbols in the language module (PEP 562).
- **function** `__dir__() -> ...` — Expose lazy-loaded symbols to IDE/dir().

### `src/phonofix/languages/english/candidates.py`
- **function** `generate_exact_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., tokenizer: ..., exact_matcher: ..., exact_items_by_alias: ..., protected_terms: ...) -> ...` — Exact-match draft generation (Aho-Corasick surface alias).
- **function** `generate_fuzzy_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., tokenizer: ..., backend: ..., phonetic: ..., fuzzy_buckets: ..., protected_terms: ...) -> ...` — Search all possible fuzzy correction candidates (no scoring; drafts only).
- **function** `score_candidate_drafts(*, drafts: ...) -> ...` — Unified scoring stage.

### `src/phonofix/languages/english/config.py`
- **class** `EnglishPhoneticConfig` — English phonetic config class — centralizes English fuzzy rules.

### `src/phonofix/languages/english/corrector.py`
- **class** `EnglishCorrector(PipelineCorrectorBase)` — English corrector.
- **method** `EnglishCorrector._from_engine(cls, engine: ..., term_mapping: ..., protected_terms: ...=..., on_event: ...=...) -> ...` — Create a lightweight corrector instance from the engine (internal).
- **method** `EnglishCorrector._emit_replacement(self, candidate: ..., *, silent: ..., trace_id: ...) -> ...` — Emit a `replacement` event (and log when not in silent mode).
- **method** `EnglishCorrector._emit_pipeline_event(self, event: ..., *, silent: ...) -> ...` — Emit pipeline events (e.g., `fuzzy_error` / `degraded`).
- **method** `EnglishCorrector._build_protection_mask(self, text: ...) -> ...` — Build a `protected_terms` mask (avoid replacing protected spans).
- **method** `EnglishCorrector._generate_exact_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — Generate exact-match candidate drafts (delegates to the `candidates` module).
- **method** `EnglishCorrector._generate_fuzzy_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — Generate fuzzy-match candidate drafts (delegates to `candidates`, with bucket pruning).
- **method** `EnglishCorrector._score_candidate_drafts(self, drafts: ...) -> ...` — Score candidate drafts (delegates to the `candidates` module).
- **method** `EnglishCorrector._resolve_conflicts(self, candidates: ...) -> ...` — Resolve candidate conflicts (delegates to the `replacements` module).
- **method** `EnglishCorrector._apply_replacements(self, text: ..., candidates: ..., silent: ...=..., *, trace_id: ...=...) -> ...` — Apply replacements and emit events/logs (delegates to `replacements`).

### `src/phonofix/languages/english/engine.py`
- **class** `EnglishEngine(CorrectorEngine)` — English correction engine.
- **method** `EnglishEngine.__init__(self, phonetic_config: ...=..., *, enable_surface_variants: ...=..., enable_representative_variants: ...=..., verbose: ...=..., on_timing: ...=...)` — Initialize `EnglishEngine`.
- **method** `EnglishEngine.phonetic(self) -> ...` — Get the English phonetic system (IPA conversion & similarity).
- **method** `EnglishEngine.tokenizer(self) -> ...` — Get the English tokenizer (for sliding windows and boundary checks).
- **method** `EnglishEngine.fuzzy_generator(self) -> ...` — Get the English fuzzy variant generator (for auto-variants expansion).
- **method** `EnglishEngine.config(self) -> ...` — Get the English phonetic config.
- **method** `EnglishEngine.backend(self) -> ...` — Get the English phonetic backend (advanced: cache/batch IPA, etc.).
- **method** `EnglishEngine.is_initialized(self) -> ...` — Check whether the engine and backend are initialized.
- **method** `EnglishEngine.get_backend_stats(self) -> ...` — Get backend cache stats (hits/misses/size).
- **method** `EnglishEngine.create_corrector(self, term_dict: ..., protected_terms: ...=..., on_event: ...=..., **kwargs) -> ...` — Create `EnglishCorrector` from `term_dict`.
- **method** `EnglishEngine._normalize_term_value(self, term: ..., value: ...) -> ...` — Normalize a `term_dict` value into the internal config dict.
- **method** `EnglishEngine._filter_aliases_by_phonetic(self, aliases: ...) -> ...` — Deduplicate aliases by IPA (keep the first spelling).

### `src/phonofix/languages/english/filters.py`
- **function** `should_exclude_by_context(*, exclude_when: ..., context: ...) -> ...` — Check whether to exclude a correction based on context.
- **function** `has_required_keyword(*, keywords: ..., context: ...) -> ...` — Check whether required keywords are satisfied.
- **function** `check_context_bonus(*, full_text: ..., start_idx: ..., end_idx: ..., keywords: ..., window_size: ...=...) -> ...` — Check context keyword bonus.
- **function** `build_protection_mask(*, text: ..., protected_terms: ..., protected_matcher: ...) -> ...` — Build a protection mask and mark spans that should not be corrected (protected terms).
- **function** `is_span_protected(*, start: ..., end: ..., protected_indices: ...) -> ...` — Check whether a span hits the protection mask.
- **function** `token_boundaries(*, tokenizer: ..., text: ...) -> ...` — Get token boundary spans to prevent substring false positives in exact matching.

### `src/phonofix/languages/english/fuzzy_generator.py`
- **class** `_Candidate` — Internal candidate data structure (for deduping and sorting variants).
- **class** `EnglishFuzzyGenerator(FuzzyGeneratorProtocol)` — English fuzzy variant generator (surface-only, optional).
- **method** `EnglishFuzzyGenerator.__init__(self, config: ...=..., backend: ...=..., *, enable_representative_variants: ...=...) -> ...` — Initialize the English fuzzy variant generator.
- **method** `EnglishFuzzyGenerator.generate_variants(self, term: ..., max_variants: ...=...) -> ...` — Generate English fuzzy variants for the input term (surface variants).
- **method** `EnglishFuzzyGenerator._try_get_backend(self) -> ...` — Try to get the English backend (returns `None` on failure).
- **method** `EnglishFuzzyGenerator._generate_safe_surface_variants(self, term: ...) -> ...` — Generate low-risk, generalizable surface variants.
- **method** `EnglishFuzzyGenerator._generate_representative_spelling_variants(self, term: ...) -> ...` — Generate more aggressive representative spelling variants (disabled by default).
- **function** `generate_english_variants(term: ..., max_variants: ...=...) -> ...` — Convenience function: quickly get English fuzzy variants.

### `src/phonofix/languages/english/indexing.py`
- **function** `first_ipa_symbol(ipa: ...) -> ...` — Get the first effective phoneme symbol in an IPA string.
- **function** `first_phoneme_group(ipa: ..., *, config: ...=...) -> ...` — Get the first-phoneme group for IPA.
- **function** `build_search_index(*, engine: ..., tokenizer: ..., term_mapping: ...) -> ...` — Build the search index.
- **function** `build_exact_matcher(search_index: ...) -> ...` — Build an exact-match index for surface aliases (Aho-Corasick).
- **function** `build_fuzzy_buckets(*, search_index: ..., config: ...=...) -> ...` — Build a bucket index for cheap pruning.

### `src/phonofix/languages/english/phonetic_impl.py`
- **class** `EnglishPhoneticSystem(PhoneticSystem)` — English phonetic system (IPA distance / fuzzy match).
- **method** `EnglishPhoneticSystem.__init__(self, backend: ...=...) -> ...` — Initialize the English phonetic system.
- **method** `EnglishPhoneticSystem.to_phonetic(self, text: ...) -> ...` — Convert text to IPA (with normalization for distance calculation).
- **method** `EnglishPhoneticSystem.are_fuzzy_similar(self, phonetic1: ..., phonetic2: ...) -> ...` — Determine whether two IPA strings are fuzzily similar (within tolerance).
- **method** `EnglishPhoneticSystem.calculate_similarity_score(self, phonetic1: ..., phonetic2: ...) -> ...` — Calculate IPA similarity score.
- **method** `EnglishPhoneticSystem._normalize_ipa_for_distance(self, ipa: ...) -> ...` — Normalize IPA into a form suitable for distance calculation.
- **method** `EnglishPhoneticSystem._map_to_phoneme_groups(self, ipa: ...) -> ...` — Map IPA symbols to phoneme-group codes to reduce distance sensitivity.
- **method** `EnglishPhoneticSystem._consonant_skeleton(self, ipa: ...) -> ...` — Extract a consonant skeleton string from IPA.
- **method** `EnglishPhoneticSystem._are_first_phonemes_similar(self, phonetic1: ..., phonetic2: ...) -> ...` — Check first-phoneme compatibility (extra conservative gate).
- **method** `EnglishPhoneticSystem.get_tolerance(self, length: ...) -> ...` — Choose tolerance by IPA length (shorter is stricter).

### `src/phonofix/languages/english/replacements.py`
- **function** `resolve_conflicts(*, candidates: ...) -> ...` — Resolve candidate conflicts.
- **function** `apply_replacements(*, text: ..., candidates: ..., emit_replacement: ..., logger: ..., silent: ...=..., trace_id: ...=...) -> ...` — Apply corrections and log.

### `src/phonofix/languages/english/scoring.py`
- **function** `calculate_final_score(*, error_ratio: ..., item: ..., has_context: ..., context_distance: ...=...) -> ...` — Calculate final score (lower is better).

### `src/phonofix/languages/english/tokenizer.py`
- **class** `EnglishTokenizer(Tokenizer)` — English tokenizer.
- **method** `EnglishTokenizer.tokenize(self, text: ...) -> ...` — Split English text into a list of words.
- **method** `EnglishTokenizer.get_token_indices(self, text: ...) -> ...` — Get the start/end indices of each word in the original text.

### `src/phonofix/languages/english/types.py`
- **class** `EnglishIndexItem(TypedDict)` — Single index item (term or alias).
- **class** `EnglishCandidateDraft(TypedDict)` — Candidate draft.
- **class** `EnglishCandidate(TypedDict)` — Final candidate.

### `src/phonofix/languages/japanese/__init__.py`
- **function** `__getattr__(name: ...) -> ...` — Lazy-load main symbols in the language module (PEP 562).
- **function** `__dir__() -> ...` — Expose lazy-loaded symbols to IDE/dir().

### `src/phonofix/languages/japanese/candidates.py`
- **function** `_is_ascii_alnum(ch: ...) -> ...`
- **function** `_is_ascii_word(s: ...) -> ...` — Determine whether a string is an ASCII word (romaji/digits).
- **function** `generate_exact_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., exact_matcher: ..., exact_items_by_alias: ..., protected_terms: ...) -> ...` — Exact-match draft generation (Aho-Corasick surface alias).
- **function** `generate_fuzzy_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., tokenizer: ..., phonetic: ..., fuzzy_buckets: ..., protected_terms: ...) -> ...` — Search all possible fuzzy correction candidates (no scoring; drafts only).
- **function** `score_candidate_drafts(*, drafts: ...) -> ...` — Convert drafts into final candidates and do basic deduping.

### `src/phonofix/languages/japanese/config.py`
- **class** `JapanesePhoneticConfig` — Japanese phonetic config.

### `src/phonofix/languages/japanese/corrector.py`
- **class** `JapaneseCorrector(PipelineCorrectorBase)` — Japanese corrector.
- **method** `JapaneseCorrector._from_engine(cls, engine: ..., term_mapping: ..., protected_terms: ...=..., on_event: ...=...) -> ...` — Create a lightweight corrector instance from the engine (internal).
- **method** `JapaneseCorrector._emit_replacement(self, candidate: ..., *, silent: ..., trace_id: ...) -> ...` — Emit a `replacement` event (and log when not in silent mode).
- **method** `JapaneseCorrector._emit_pipeline_event(self, event: ..., *, silent: ...) -> ...` — Emit pipeline events (e.g., `fuzzy_error` / `degraded`).
- **method** `JapaneseCorrector._build_protection_mask(self, text: ...) -> ...` — Build a `protected_terms` mask (avoid replacing protected spans).
- **method** `JapaneseCorrector._generate_exact_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — Generate exact-match candidate drafts (delegates to the `candidates` module).
- **method** `JapaneseCorrector._generate_fuzzy_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — Generate fuzzy-match candidate drafts (delegates to `candidates`, with bucket pruning).
- **method** `JapaneseCorrector._score_candidate_drafts(self, drafts: ...) -> ...` — Score candidate drafts (delegates to the `candidates` module).
- **method** `JapaneseCorrector._resolve_conflicts(self, candidates: ...) -> ...` — Resolve candidate conflicts (delegates to the `replacements` module).
- **method** `JapaneseCorrector._apply_replacements(self, text: ..., candidates: ..., silent: ...=..., *, trace_id: ...=...) -> ...` — Apply replacements and emit events/logs (delegates to `replacements`).

### `src/phonofix/languages/japanese/engine.py`
- **class** `JapaneseEngine(CorrectorEngine)` — Japanese correction engine.
- **method** `JapaneseEngine.__init__(self, phonetic_config: ...=..., *, enable_surface_variants: ...=..., enable_representative_variants: ...=..., verbose: ...=..., on_timing: ...=...)` — Initialize `JapaneseEngine`.
- **method** `JapaneseEngine.phonetic(self) -> ...` — Get the Japanese phonetic system (romaji conversion & similarity).
- **method** `JapaneseEngine.tokenizer(self) -> ...` — Get the Japanese tokenizer (via backend tokenization).
- **method** `JapaneseEngine.fuzzy_generator(self) -> ...` — Get the Japanese fuzzy variant generator (surface variants).
- **method** `JapaneseEngine.config(self) -> ...` — Get the Japanese phonetic config.
- **method** `JapaneseEngine.is_initialized(self) -> ...` — Check whether the engine and backend are initialized.
- **method** `JapaneseEngine.get_backend_stats(self) -> ...` — Get backend cache stats (romaji/tokens).
- **method** `JapaneseEngine.create_corrector(self, term_dict: ..., protected_terms: ...=..., on_event: ...=..., **kwargs) -> ...` — Create `JapaneseCorrector` from `term_dict`.
- **method** `JapaneseEngine._normalize_term_value(self, term: ..., value: ...) -> ...` — Normalize a `term_dict` value into the internal config dict.
- **method** `JapaneseEngine._filter_aliases_by_phonetic(self, aliases: ..., *, canonical: ...) -> ...` — Deduplicate aliases by phonetic key (romaji).

### `src/phonofix/languages/japanese/filters.py`
- **function** `should_exclude_by_context(*, exclude_when: ..., context: ...) -> ...` — Check whether to exclude a correction based on context.
- **function** `has_required_keyword(*, keywords: ..., context: ...) -> ...` — Check whether required keywords are satisfied.
- **function** `check_context_bonus(*, full_text: ..., start_idx: ..., end_idx: ..., keywords: ..., window_size: ...=...) -> ...` — Check context keyword bonus.
- **function** `build_protection_mask(*, text: ..., protected_terms: ..., protected_matcher: ...) -> ...` — Build a protection mask and mark spans that should not be corrected (protected terms).
- **function** `is_span_protected(*, start: ..., end: ..., protected_indices: ...) -> ...` — Check whether a span hits the protection mask.

### `src/phonofix/languages/japanese/fuzzy_generator.py`
- **class** `_Candidate` — Internal candidate data structure (for deduping and sorting variants).
- **function** `_kata_to_hira(text: ...) -> ...` — Convert katakana to hiragana (kana only; other chars unchanged).
- **function** `_hira_to_kata(text: ...) -> ...` — Convert hiragana to katakana (kana only; other chars unchanged).
- **function** `_has_japanese_script(text: ...) -> ...` — Roughly detect whether text contains Japanese scripts (kana or common Kanji ranges).
- **function** `_normalize_romaji(romaji: ..., config: ...) -> ...` — Normalize romaji to produce a stable phonetic key.
- **function** `_romaji_variants(base: ..., config: ..., *, max_states: ...) -> ...` — Do limited expansion in the romaji space (avoid combinatorial explosion).
- **class** `JapaneseFuzzyGenerator(FuzzyGeneratorProtocol)` — Japanese fuzzy variant generator (surface-only, optional).
- **method** `JapaneseFuzzyGenerator.__init__(self, config: ...=..., backend: ...=..., *, enable_representative_variants: ...=..., max_phonetic_states: ...=...) -> ...` — Initialize the Japanese fuzzy variant generator.
- **method** `JapaneseFuzzyGenerator.generate_variants(self, term: ..., max_variants: ...=...) -> ...` — Generate Japanese fuzzy variants for the input term (surface variants).
- **method** `JapaneseFuzzyGenerator._to_hiragana_reading(self, text: ...) -> ...` — Convert Japanese text to a hiragana reading string.
- **method** `JapaneseFuzzyGenerator._to_romaji(self, text: ...) -> ...` — Convert Japanese text (kana/kanji) to romaji.
- **method** `JapaneseFuzzyGenerator._phonetic_key(self, text: ...) -> ...` — Get the candidate's phonetic key (normalized romaji).
- **method** `JapaneseFuzzyGenerator._romaji_rule_variants(self, romaji: ...) -> ...` — Generate a small set of rule-based romaji variants (Hepburn/Kunrei, long vowels, sokuon, nasal).
- **method** `JapaneseFuzzyGenerator._kana_confusion_variants(self, hira: ...) -> ...` — Generate kana-level confusion variants (more expensive, optional).
- **function** `JapaneseFuzzyGenerator._kana_confusion_variants.options(ch: ...) -> ...` — Get replacement options for a single kana (including the original).

### `src/phonofix/languages/japanese/indexing.py`
- **function** `first_romaji_group(romaji: ...) -> ...` — Get the first-sound group for romaji.
- **function** `build_search_index(*, phonetic: ..., tokenizer: ..., term_mapping: ...) -> ...` — Build the search index.
- **function** `build_exact_matcher(search_index: ...) -> ...` — Build an exact-match index for surface aliases (Aho-Corasick).
- **function** `build_fuzzy_buckets(*, search_index: ...) -> ...` — Build a bucket index for cheap pruning.

### `src/phonofix/languages/japanese/phonetic_impl.py`
- **class** `JapanesePhoneticSystem(PhoneticSystem)` — Japanese phonetic system.
- **method** `JapanesePhoneticSystem.__init__(self, backend: ...=...) -> ...` — Initialize the Japanese phonetic system.
- **method** `JapanesePhoneticSystem.to_phonetic(self, text: ...) -> ...` — Convert Japanese text to romaji.
- **method** `JapanesePhoneticSystem.calculate_similarity_score(self, phonetic1: ..., phonetic2: ...) -> ...` — Calculate romaji similarity score.
- **method** `JapanesePhoneticSystem._normalize_phonetic(self, phonetic: ...) -> ...` — Normalize romaji for fuzzy matching.
- **method** `JapanesePhoneticSystem.are_fuzzy_similar(self, phonetic1: ..., phonetic2: ...) -> ...` — Determine whether two romaji strings are fuzzily similar.
- **method** `JapanesePhoneticSystem.get_tolerance(self, length: ...) -> ...` — Choose tolerance based on text length.

### `src/phonofix/languages/japanese/replacements.py`
- **function** `resolve_conflicts(*, candidates: ..., logger: ...=...) -> ...` — Resolve candidate conflicts (lower score wins).
- **function** `apply_replacements(*, text: ..., candidates: ..., emit_replacement: ..., logger: ..., silent: ...=..., trace_id: ...=...) -> ...` — Apply corrections and log (rebuild string to avoid index shifting).

### `src/phonofix/languages/japanese/scoring.py`
- **function** `calculate_final_score(*, error_ratio: ..., item: ..., has_context: ..., context_distance: ...=...) -> ...` — Calculate final score (lower is better).

### `src/phonofix/languages/japanese/tokenizer.py`
- **class** `JapaneseTokenizer(Tokenizer)` — Japanese tokenizer.
- **method** `JapaneseTokenizer.__init__(self, backend: ...=...) -> ...` — Initialize the Japanese tokenizer.
- **method** `JapaneseTokenizer.tokenize(self, text: ...) -> ...` — Split Japanese text into a list of words.
- **method** `JapaneseTokenizer.get_token_indices(self, text: ...) -> ...` — Get the start/end indices of each word in the original text.

### `src/phonofix/languages/japanese/types.py`
- **class** `JapaneseIndexItem(TypedDict)` — Single index item (term or alias).
- **class** `JapaneseCandidateDraft(TypedDict)` — Candidate draft.
- **class** `JapaneseCandidate(TypedDict)` — Final candidate.

### `src/phonofix/languages/japanese/utils.py`
- **function** `is_japanese_char(char: ...) -> ...` — Determine whether a character is Japanese (hiragana/katakana).

### `src/phonofix/utils/aho_corasick.py`
- **class** `_Node(Generic[...])` — Aho-Corasick trie node (internal).
- **class** `AhoCorasick(Generic[...])` — Aho-Corasick multi-pattern string matcher.
- **method** `AhoCorasick.__init__(self) -> ...` — Create the matcher. After calling `add()`, call `build()` before matching (or let `iter_matches` auto-build).
- **method** `AhoCorasick.add(self, word: ..., value: ...) -> ...` — Add a pattern.
- **method** `AhoCorasick.build(self) -> ...` — Build fail links (convert the trie into a linearly scannable automaton).
- **method** `AhoCorasick.iter_matches(self, text: ...) -> ...` — Iterate and yield matches.

### `src/phonofix/utils/logger.py`
- **function** `get_logger(name: ...=...) -> ...` — Get the project logger.
- **function** `setup_logger(level: ...=..., format_string: ...=..., handler: ...=...) -> ...` — Configure the project logger.
- **class** `TimingContext` — Timing context manager.
- **method** `TimingContext.__init__(self, operation: ..., logger: ...=..., level: ...=..., callback: ...=...)` — Initialize the timing context.
- **method** `TimingContext.__enter__(self) -> ...` — Enter the timing block and record the start time.
- **method** `TimingContext.__exit__(self, exc_type, exc_val, exc_tb) -> ...` — Exit the timing block, compute elapsed time, and optionally write to logger/callback.
- **function** `log_timing(operation: ...=..., logger: ...=..., level: ...=...)` — Timing decorator.
- **function** `log_timing.decorator(func: ...) -> ...` — Wrap any function with timing logic.
- **function** `log_timing.decorator.wrapper(*args, **kwargs) -> ...` — Actual wrapper: time before/after the call via `TimingContext`.
- **function** `enable_debug_logging() -> ...` — Enable debug logging.
- **function** `enable_timing_logging() -> ...` — Enable timing logging.

### `tools/benchmark_phonetic.py`
- **function** `benchmark_g2p(convert_func: ..., words: ..., name: ..., iterations: ...=...) -> ...` — Benchmark per-word G2P function performance.
- **function** `benchmark_g2p_batch(convert_batch_func: ..., words: ..., name: ..., iterations: ...=...) -> ...` — Benchmark batch G2P function performance (convert multiple strings at once).
- **function** `main() -> ...`
- **function** `main.to_ipa(word: ...) -> ...`
- **function** `main.to_ipa_batch(words: ...) -> ...`
- **function** `main.old_convert(text: ...) -> ...`

### `tools/translation_client.py`
- **function** `translate_text(text, target_lang=...)` — Call the local translation API.

## Dependencies
### phonofix
- Path: `.`
- Source: `pyproject.toml`

#### devDependencies
```json
{
    "mypy": ">=1.0.0",
    "pytest": ">=7.0.0",
    "pytest-cov": ">=4.0.0",
    "ruff": ">=0.1.0"
}
```

#### dependencies
```json
{
    "cutlet": ">=0.3.0",
    "fugashi": ">=1.3.0",
    "hanziconv": ">=0.3.2",
    "phonemizer": ">=3.3.0",
    "pinyin2hanzi": ">=0.1.1",
    "pypinyin": ">=0.44.0",
    "python-levenshtein": ">=0.12.2",
    "unidic-lite": ">=1.0.0"
}
```

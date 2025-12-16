# Snapshot

- Root: `phonofix/`
- Generated: `2025-12-15 22:48:48`
- Max tree depth: `12`
- Include private symbols: `True`
- Use .gitignore: `True`

## 專案目錄結構
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

## 函式/類別清單（AST）
### `src/phonofix/__init__.py`
- **function** `__getattr__(name: ...) -> ...` — 延遲載入頂層公開符號（PEP 562）。
- **function** `__dir__() -> ...` — 讓 IDE/dir() 能看到延遲載入的符號清單。

### `src/phonofix/backend/base.py`
- **class** `PhoneticBackend(ABC)` — 語音後端抽象基類 (Abstract Base Class)
- **method** `PhoneticBackend.to_phonetic(self, text: ...) -> ...` — 將文字轉換為語音表示
- **method** `PhoneticBackend.is_initialized(self) -> ...` — 檢查後端是否已初始化
- **method** `PhoneticBackend.initialize(self) -> ...` — 初始化後端
- **method** `PhoneticBackend.get_cache_stats(self) -> ...` — 取得快取統計資訊
- **method** `PhoneticBackend.clear_cache(self) -> ...` — 清除快取

### `src/phonofix/backend/chinese_backend.py`
- **function** `_get_pypinyin()` — 延遲載入 pypinyin 模組
- **function** `_cached_get_pinyin_string(text: ...) -> ...` — 快取版拼音字串計算
- **function** `_cached_get_pinyin_syllables(text: ...) -> ...` — 快取版拼音音節列表（無聲調，小寫）
- **function** `_cached_get_initials(text: ...) -> ...` — 快取版聲母列表計算
- **function** `_cached_get_finals(text: ...) -> ...` — 快取版韻母列表計算
- **class** `ChinesePhoneticBackend(PhoneticBackend)` — 中文語音後端 (單例)
- **method** `ChinesePhoneticBackend.__init__(self)` — 初始化後端
- **method** `ChinesePhoneticBackend.initialize(self) -> ...` — 初始化後端
- **method** `ChinesePhoneticBackend.is_initialized(self) -> ...` — 檢查是否已初始化
- **method** `ChinesePhoneticBackend.to_phonetic(self, text: ...) -> ...` — 將中文文字轉換為拼音
- **method** `ChinesePhoneticBackend.get_initials(self, text: ...) -> ...` — 取得文字的聲母列表
- **method** `ChinesePhoneticBackend.get_pinyin_syllables(self, text: ...) -> ...` — 取得文字的拼音音節列表（無聲調）
- **method** `ChinesePhoneticBackend.get_finals(self, text: ...) -> ...` — 取得文字的韻母列表
- **method** `ChinesePhoneticBackend.get_cache_stats(self) -> ...` — 取得拼音快取統計
- **method** `ChinesePhoneticBackend.clear_cache(self) -> ...` — 清除所有拼音快取
- **function** `get_chinese_backend() -> ...` — 取得 ChinesePhoneticBackend 單例

### `src/phonofix/backend/english_backend.py`
- **function** `_setup_espeak_library()` — 自動設定 PHONEMIZER_ESPEAK_LIBRARY 環境變數 (僅 Windows)
- **function** `_get_phonemize()` — 延遲載入 phonemizer 模組
- **function** `_record_hits(count: ...=...) -> ...` — 累計快取命中次數（thread-safe）。
- **function** `_record_misses(count: ...=...) -> ...` — 累計快取未命中次數（thread-safe）。
- **function** `_cached_ipa_convert(text: ...) -> ...` — 快取版 IPA 轉換 (單一文字)
- **function** `_normalize_english_text_for_ipa(text: ...) -> ...` — 英文 IPA 轉換前的輕量正規化（用於 token/canonical 對齊）
- **function** `_batch_ipa_convert(texts: ...) -> ...` — 批次 IPA 轉換 (效能優化)
- **class** `EnglishPhoneticBackend(PhoneticBackend)` — 英文語音後端 (單例)
- **method** `EnglishPhoneticBackend.__init__(self)` — 初始化後端
- **method** `EnglishPhoneticBackend.initialize(self) -> ...` — 初始化 espeak-ng
- **method** `EnglishPhoneticBackend.initialize_lazy(self) -> ...` — 在背景執行緒初始化 espeak-ng，立即返回不阻塞
- **function** `EnglishPhoneticBackend.initialize_lazy._background_init()` — 背景初始化工作。
- **method** `EnglishPhoneticBackend.is_initialized(self) -> ...` — 檢查是否已初始化
- **method** `EnglishPhoneticBackend.to_phonetic(self, text: ...) -> ...` — 將文字轉換為 IPA
- **method** `EnglishPhoneticBackend.to_phonetic_batch(self, texts: ...) -> ...` — 批次將文字轉換為 IPA (效能優化)
- **method** `EnglishPhoneticBackend.get_cache_stats(self) -> ...` — 取得 IPA 快取統計
- **method** `EnglishPhoneticBackend.clear_cache(self) -> ...` — 清除 IPA 快取
- **function** `get_english_backend() -> ...` — 取得 EnglishPhoneticBackend 單例
- **function** `is_phonemizer_available() -> ...` — 檢查 phonemizer 是否可用

### `src/phonofix/backend/japanese_backend.py`
- **function** `_strip_macrons(text: ...) -> ...` — 移除羅馬字長音符號（macrons）。
- **function** `_get_cutlet() -> ...` — 取得 Cutlet 實例（Lazy Loading）。
- **function** `_get_fugashi() -> ...` — 取得 fugashi.Tagger（Lazy Loading）。
- **function** `_cached_romaji(text: ...) -> ...` — 快取：日文文本 -> romaji（羅馬拼音）
- **function** `_cached_tokens(text: ...) -> ...` — 快取：日文文本分詞結果（surface tokens）。
- **class** `JapanesePhoneticBackend(PhoneticBackend)` — 日文語音後端（單例）。
- **method** `JapanesePhoneticBackend.__init__(self) -> ...` — 建立後端實例（請透過 `get_japanese_backend()` 取得單例）。
- **method** `JapanesePhoneticBackend.initialize(self) -> ...` — 初始化 backend（執行緒安全）。
- **method** `JapanesePhoneticBackend.is_initialized(self) -> ...` — 回傳 backend 是否已完成初始化。
- **method** `JapanesePhoneticBackend.to_phonetic(self, text: ...) -> ...` — 將日文文本轉為 romaji（phonetic key）。
- **method** `JapanesePhoneticBackend.tokenize(self, text: ...) -> ...` — 將日文文本分詞為 surface token 列表。
- **method** `JapanesePhoneticBackend.get_cutlet(self) -> ...` — 取得 cutlet 實例（確保初始化後回傳）。
- **method** `JapanesePhoneticBackend.get_tagger(self) -> ...` — 取得 fugashi.Tagger（確保初始化後回傳）。
- **method** `JapanesePhoneticBackend.get_cache_stats(self) -> ...` — 回傳統一格式的快取統計（romaji/tokens）。
- **method** `JapanesePhoneticBackend.clear_cache(self) -> ...` — 清除 romaji/tokens 的 lru_cache（主要用於測試或效能觀測）。
- **function** `get_japanese_backend() -> ...` — 取得 `JapanesePhoneticBackend` 單例（執行緒安全）。

### `src/phonofix/backend/stats.py`
- **class** `CacheStats(TypedDict)` — 單一快取的統計資訊。
- **class** `LazyInitError(TypedDict)` — lazy init 失敗時的錯誤資訊（供觀測/除錯）。
- **class** `LazyInitStats(TypedDict)` — lazy initialization 的可觀測狀態。
- **class** `BackendStats(TypedDict)` — backend 統計總覽（統一回傳格式）。

### `src/phonofix/core/engine_interface.py`
- **class** `CorrectorEngine(ABC)` — 修正引擎抽象基類 (Abstract Base Class)
- **method** `CorrectorEngine._init_logger(self, verbose: ...=..., on_timing: ...=...) -> ...` — 初始化 Engine 的 logger 與（可選的）計時回呼。
- **method** `CorrectorEngine._log_timing(self, operation: ...) -> ...` — 建立計時上下文（TimingContext）。
- **method** `CorrectorEngine.create_corrector(self, term_dict: ..., **kwargs) -> ...` — 依據 term_dict 建立語言 corrector。
- **method** `CorrectorEngine.is_initialized(self) -> ...` — 回傳 Engine 是否已完成初始化（包含底層 backend 的初始化狀態）。
- **method** `CorrectorEngine.get_backend_stats(self) -> ...` — 回傳 backend 的快取/統計資訊（進階用途：效能觀測、debug）。

### `src/phonofix/core/events.py`
- **class** `CorrectionEvent(TypedDict)` — 修正事件資料結構（TypedDict, total=False）。

### `src/phonofix/core/phonetic_interface.py`
- **class** `PhoneticSystem(ABC)` — 語言發音系統抽象介面 (Abstract Base Class)
- **method** `PhoneticSystem.to_phonetic(self, text: ...) -> ...` — 將文本轉換為發音表示 (如拼音、IPA、羅馬拼音)
- **method** `PhoneticSystem.are_fuzzy_similar(self, phonetic1: ..., phonetic2: ...) -> ...` — 判斷兩個發音字串是否模糊相似
- **method** `PhoneticSystem.get_tolerance(self, length: ...) -> ...` — 根據長度取得容錯率閾值

### `src/phonofix/core/pipeline_corrector.py`
- **class** `PipelineCorrectorBase(ABC)` — Corrector pipeline base
- **method** `PipelineCorrectorBase._build_protection_mask(self, text: ...) -> ...` — 建立保護遮罩。
- **method** `PipelineCorrectorBase._generate_exact_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — 產生精準命中（exact-match）的候選草稿。
- **method** `PipelineCorrectorBase._generate_fuzzy_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — 產生模糊命中（fuzzy-match）的候選草稿。
- **method** `PipelineCorrectorBase._score_candidate_drafts(self, drafts: ...) -> ...` — 對候選草稿進行計分，回傳可比較的 candidates。
- **method** `PipelineCorrectorBase._resolve_conflicts(self, candidates: ...) -> ...` — 解決候選衝突，回傳最後要套用的 candidates。
- **method** `PipelineCorrectorBase._apply_replacements(self, text: ..., candidates: ..., silent: ...=..., *, trace_id: ...=...) -> ...` — 將 candidates 套用到 text 上並回傳結果。
- **method** `PipelineCorrectorBase._emit_pipeline_event(self, event: ..., *, silent: ...) -> ...` — 發送 pipeline 事件（例如 fuzzy_error / degraded）。
- **method** `PipelineCorrectorBase.correct(self, text: ..., full_context: ...=..., silent: ...=..., *, mode: ...=..., fail_policy: ...=..., trace_id: ...=...) -> ...` — 執行通用修正管線。

### `src/phonofix/core/protocols/corrector.py`
- **class** `CorrectorProtocol(Protocol)` — 修正器協議 (Corrector Protocol)
- **method** `CorrectorProtocol.correct(self, text: ..., full_context: ...=..., silent: ...=..., *, mode: ...=..., fail_policy: ...=..., trace_id: ...=...) -> ...` — 修正文本（可選完整上下文/靜默模式）
- **class** `ContextAwareCorrectorProtocol(CorrectorProtocol, Protocol)` — 上下文感知修正器協議

### `src/phonofix/core/protocols/fuzzy.py`
- **class** `FuzzyGeneratorProtocol(Protocol)` — 模糊變體生成器介面（Protocol）。
- **method** `FuzzyGeneratorProtocol.generate_variants(self, term: ..., max_variants: ...=...) -> ...` — 為輸入詞彙生成模糊變體

### `src/phonofix/core/protocols/pipeline.py`
- **class** `ProtectionMaskBuilderProtocol(Protocol)` — 產生保護遮罩（Protection Mask）。
- **method** `ProtectionMaskBuilderProtocol.build(self, text: ...) -> ...` — 建立保護遮罩。
- **class** `ExactDraftGeneratorProtocol(Protocol)` — 精準比對候選（exact-match）生成器。
- **method** `ExactDraftGeneratorProtocol.generate(self, text: ..., context: ..., protected_indices: ...) -> ...` — 產生 exact-match 候選草稿。
- **class** `FuzzyDraftGeneratorProtocol(Protocol)` — 模糊比對候選（fuzzy-match）生成器。
- **method** `FuzzyDraftGeneratorProtocol.generate(self, text: ..., context: ..., protected_indices: ...) -> ...` — 產生 fuzzy-match 候選草稿。
- **class** `DraftScorerProtocol(Protocol)` — 候選草稿計分器。
- **method** `DraftScorerProtocol.score(self, drafts: ...) -> ...` — 對 drafts 計分並回傳 candidates。
- **class** `ConflictResolverProtocol(Protocol)` — 候選衝突解決器。
- **method** `ConflictResolverProtocol.resolve(self, candidates: ...) -> ...` — 解決候選衝突，回傳最後要套用的候選列表。
- **class** `ReplacementApplierProtocol(Protocol)` — 替換套用器。
- **method** `ReplacementApplierProtocol.apply(self, text: ..., candidates: ..., *, silent: ..., trace_id: ...) -> ...` — 套用候選替換。

### `src/phonofix/core/term_config.py`
- **class** `NormalizedTermConfig(TypedDict)` — 正規化後的 term config（TypedDict, total=False）。
- **function** `normalize_term_dict(term_dict: ..., *, default_weight: ...=..., default_max_variants: ...=...) -> ...` — 將使用者輸入的 term_dict 統一成 canonical -> NormalizedTermConfig

### `src/phonofix/core/tokenizer_interface.py`
- **class** `Tokenizer(ABC)` — 語言分詞器抽象介面 (Abstract Base Class)
- **method** `Tokenizer.tokenize(self, text: ...) -> ...` — 將文本分割為 Token 列表 (中文為字，英文為詞)
- **method** `Tokenizer.get_token_indices(self, text: ...) -> ...` — 取得每個 Token 在原始文本中的起始與結束索引

### `src/phonofix/languages/chinese/__init__.py`
- **function** `__getattr__(name: ...) -> ...` — 延遲載入語言模組內的主要符號（PEP 562）。
- **function** `__dir__() -> ...` — 讓 IDE/dir() 能看到延遲載入的符號清單。

### `src/phonofix/languages/chinese/candidates.py`
- **function** `generate_exact_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., exact_matcher: ..., exact_items_by_alias: ..., protected_terms: ...) -> ...` — 產生 exact-match 候選草稿。
- **function** `process_fuzzy_match_draft(*, context: ..., start_idx: ..., original_segment: ..., item: ..., engine: ..., config: ..., utils: ..., segment_initials: ...=..., segment_syllables: ...=...) -> ...` — 處理模糊匹配
- **function** `generate_fuzzy_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., fuzzy_buckets: ..., config: ..., engine: ..., utils: ..., protected_terms: ...) -> ...` — 搜尋所有可能的模糊修正候選（不計分，只產生候選資訊）
- **function** `score_candidate_drafts(*, drafts: ..., use_canonical: ...) -> ...` — 統一計分階段

### `src/phonofix/languages/chinese/config.py`
- **class** `ChinesePhoneticConfig` — 拼音配置類別 - 集中管理所有拼音模糊音規則
- **method** `ChinesePhoneticConfig.build_group_to_initials_map(cls)` — 建立反向查找表: 模糊音群組 -> 聲母列表

### `src/phonofix/languages/chinese/corrector.py`
- **class** `ChineseCorrector(PipelineCorrectorBase)` — 中文修正器
- **method** `ChineseCorrector._from_engine(cls, engine: ..., term_mapping: ..., protected_terms: ...=..., on_event: ...=...) -> ...` — 由 ChineseEngine 調用的內部工廠方法
- **method** `ChineseCorrector._emit_replacement(self, candidate: ..., *, silent: ..., trace_id: ...) -> ...` — 發送 replacement 事件（並在非 silent 模式輸出日誌）。
- **method** `ChineseCorrector._emit_pipeline_event(self, event: ..., *, silent: ...) -> ...` — 發送 pipeline 事件（例如 fuzzy_error / degraded）。
- **method** `ChineseCorrector._build_protection_mask(self, text: ...) -> ...` — 建立 protected_terms 的保護遮罩（避免替換到受保護區段）。
- **method** `ChineseCorrector._generate_exact_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — 產生 exact-match 候選草稿（委派給 candidates 模組）。
- **method** `ChineseCorrector._generate_fuzzy_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — 產生 fuzzy-match 候選草稿（委派給 candidates 模組，含分桶剪枝）。
- **method** `ChineseCorrector._score_candidate_drafts(self, drafts: ...) -> ...` — 對候選草稿計分（委派給 candidates 模組）。
- **method** `ChineseCorrector._resolve_conflicts(self, candidates: ...) -> ...` — 解決候選衝突（委派給 replacements 模組）。
- **method** `ChineseCorrector._apply_replacements(self, text: ..., candidates: ..., silent: ...=..., *, trace_id: ...=...) -> ...` — 套用候選替換並輸出事件/日誌（委派給 replacements 模組）。

### `src/phonofix/languages/chinese/engine.py`
- **class** `ChineseEngine(CorrectorEngine)` — 中文修正引擎。
- **method** `ChineseEngine.__init__(self, phonetic_config: ...=..., *, enable_surface_variants: ...=..., enable_representative_variants: ...=..., verbose: ...=..., on_timing: ...=...)` — 初始化 ChineseEngine。
- **method** `ChineseEngine.phonetic(self) -> ...` — 取得中文發音系統（拼音轉換與相似度）。
- **method** `ChineseEngine.tokenizer(self) -> ...` — 取得中文分詞器（用於滑動視窗與 token indices）。
- **method** `ChineseEngine.fuzzy_generator(self) -> ...` — 取得中文模糊變體生成器（同音/近音等變體）。
- **method** `ChineseEngine.utils(self) -> ...` — 取得中文語音工具（聲母/韻母/模糊音判斷等）。
- **method** `ChineseEngine.config(self) -> ...` — 取得中文語音設定（phonetic config）。
- **method** `ChineseEngine.backend(self) -> ...` — 取得中文語音 backend（進階用途：快取統計/清除等）。
- **method** `ChineseEngine.is_initialized(self) -> ...` — 檢查 Engine 是否已完成初始化。
- **method** `ChineseEngine.get_backend_stats(self) -> ...` — 取得 backend 快取統計資訊。
- **method** `ChineseEngine.create_corrector(self, term_dict: ..., protected_terms: ...=..., on_event: ...=..., **kwargs) -> ...` — 依據 term_dict 建立 ChineseCorrector。
- **method** `ChineseEngine._normalize_term_value(self, term: ..., value: ...) -> ...` — 將 term_dict 的 value 正規化為 internal config dict。
- **method** `ChineseEngine._filter_aliases_by_pinyin(self, aliases: ...) -> ...` — 依拼音去重 aliases（保留第一個出現的拼寫）。

### `src/phonofix/languages/chinese/filters.py`
- **function** `check_context_bonus(*, full_text: ..., start_idx: ..., end_idx: ..., keywords: ..., window_size: ...=...) -> ...` — 檢查上下文關鍵字加分
- **function** `build_protection_mask(*, text: ..., protected_terms: ..., protected_matcher: ...) -> ...` — 建立保護遮罩，標記不應被修正的區域 (受保護的詞彙)
- **function** `is_segment_protected(*, start_idx: ..., word_len: ..., protected_indices: ...) -> ...` — 檢查特定片段是否包含受保護的索引
- **function** `is_span_protected(*, start: ..., end: ..., protected_indices: ...) -> ...` — 檢查 span 是否命中保護遮罩。
- **function** `is_valid_segment(*, segment: ...) -> ...` — 檢查片段是否包含有效字符 (中文、英文、數字)
- **function** `should_exclude_by_context(*, full_text: ..., exclude_when: ...) -> ...` — 檢查是否應根據上下文排除修正
- **function** `has_required_keyword(*, full_text: ..., keywords: ...) -> ...` — 檢查是否滿足關鍵字必要條件

### `src/phonofix/languages/chinese/fuzzy_generator.py`
- **function** `_get_pinyin2hanzi()` — 延遲載入 Pinyin2Hanzi 模組
- **function** `_get_hanziconv()` — 延遲載入 hanziconv 模組
- **class** `ChineseFuzzyGenerator(FuzzyGeneratorProtocol)` — 中文模糊變體生成器
- **method** `ChineseFuzzyGenerator.__init__(self, config=..., backend: ...=..., *, enable_representative_variants: ...=..., max_phonetic_states: ...=...)` — 初始化中文模糊變體生成器。
- **method** `ChineseFuzzyGenerator._pinyin_string(self, text: ...) -> ...` — 取得文本的拼音字串（委派給 backend 快取）。
- **method** `ChineseFuzzyGenerator.dag_params(self)` — 延遲初始化 DAG 參數
- **method** `ChineseFuzzyGenerator._pinyin_to_chars(self, pinyin_str, max_chars=...)` — 將拼音轉換為可能的漢字 (同音字反查)
- **method** `ChineseFuzzyGenerator._get_char_variations(self, char)` — 取得單個漢字的所有模糊音變體
- **method** `ChineseFuzzyGenerator._generate_char_combinations(self, char_options_list, *, max_results: ...)` — 生成所有字符變體的排列組合
- **method** `ChineseFuzzyGenerator._add_sticky_phrase_aliases(self, term, aliases)` — 添加黏音/懶音短語別名
- **method** `ChineseFuzzyGenerator.generate_variants(self, term: ..., max_variants: ...=...)` — 為輸入詞彙生成模糊變體列表
- **method** `ChineseFuzzyGenerator.filter_homophones(self, term_list)` — 過濾同音詞

### `src/phonofix/languages/chinese/indexing.py`
- **function** `parse_term_data(data: ...) -> ...` — 解析專有名詞資料結構，提取別名、關鍵字、上下文排除條件與權重
- **function** `create_index_item(*, engine: ..., utils: ..., term: ..., canonical: ..., keywords: ..., exclude_when: ..., weight: ...) -> ...` — 建立單個索引項目，預先計算拼音與聲母特徵
- **function** `build_search_index(*, engine: ..., utils: ..., term_mapping: ...) -> ...` — 建立搜尋索引
- **function** `build_exact_matcher(search_index: ...) -> ...` — 建立 surface alias 的 exact-match 索引（Aho-Corasick）。
- **function** `build_fuzzy_buckets(*, search_index: ..., config: ...) -> ...` — 建立便宜 pruning 用的分桶索引

### `src/phonofix/languages/chinese/number_variants.py`
- **function** `generate_number_variants(number_str: ...) -> ...` — 為數字字串生成所有可能的發音變體組合
- **function** `get_variant_count(length: ...) -> ...` — 計算 N 位數字最多可能產生的變體數量

### `src/phonofix/languages/chinese/phonetic_impl.py`
- **class** `ChinesePhoneticSystem(PhoneticSystem)` — 中文發音系統
- **method** `ChinesePhoneticSystem.__init__(self, backend: ...=...)` — 初始化中文發音系統。
- **method** `ChinesePhoneticSystem.to_phonetic(self, text: ...) -> ...` — 將中文文本轉換為拼音字串
- **method** `ChinesePhoneticSystem.are_fuzzy_similar(self, phonetic1: ..., phonetic2: ...) -> ...` — 判斷兩個拼音字串是否模糊相似
- **method** `ChinesePhoneticSystem.get_tolerance(self, length: ...) -> ...` — 根據拼音字串長度取得容錯率閾值

### `src/phonofix/languages/chinese/replacements.py`
- **function** `resolve_conflicts(*, candidates: ...) -> ...` — 解決候選衝突
- **function** `apply_replacements(*, text: ..., final_candidates: ..., emit_replacement: ..., silent: ...=..., trace_id: ...=...) -> ...` — 應用修正並輸出事件/日誌

### `src/phonofix/languages/chinese/scoring.py`
- **function** `get_dynamic_threshold(*, word_len: ..., is_mixed: ...=...) -> ...` — 根據詞長動態計算容錯率閾值
- **function** `calculate_pinyin_similarity(*, engine: ..., config: ..., utils: ..., segment: ..., target_pinyin_str: ..., segment_syllables: ...=..., target_syllables: ...=...) -> ...` — 計算拼音相似度
- **function** `check_initials_match(*, engine: ..., config: ..., utils: ..., segment: ..., item: ..., segment_initials: ...=...) -> ...` — 檢查聲母是否匹配
- **function** `calculate_final_score(*, error_ratio: ..., item: ..., has_context: ..., context_distance: ...=...) -> ...` — 計算最終分數 (越低越好)

### `src/phonofix/languages/chinese/tokenizer.py`
- **class** `ChineseTokenizer(Tokenizer)` — 中文分詞器
- **method** `ChineseTokenizer.tokenize(self, text: ...) -> ...` — 將中文文本分割為字符列表
- **method** `ChineseTokenizer.get_token_indices(self, text: ...) -> ...` — 取得每個字符在原始文本中的起始與結束索引

### `src/phonofix/languages/chinese/types.py`
- **class** `ChineseIndexItem(TypedDict)` — 單一索引項目（term 或 alias）的統一資料結構。
- **class** `ChineseCandidateDraft(TypedDict)` — 候選草稿（draft）。
- **class** `ChineseCandidate(TypedDict)` — 最終候選（candidate）。

### `src/phonofix/languages/chinese/utils.py`
- **class** `ChinesePhoneticUtils` — 中文語音工具類別
- **method** `ChinesePhoneticUtils.__init__(self, config=..., backend: ...=...)` — 初始化中文語音工具。
- **method** `ChinesePhoneticUtils.contains_english(text)` — 判斷字串中是否包含英文字母。
- **method** `ChinesePhoneticUtils.get_pinyin_string(self, text: ...) -> ...` — 取得文本的拼音字串（無聲調、小寫，委派給 backend 快取）。
- **method** `ChinesePhoneticUtils.extract_initial_final(pinyin_str)` — 提取拼音的聲母與韻母
- **method** `ChinesePhoneticUtils.is_fuzzy_initial_match(self, init1_list, init2_list)` — 判斷兩個聲母列表是否模糊匹配
- **method** `ChinesePhoneticUtils.check_finals_fuzzy_match(self, pinyin1, pinyin2)` — 檢查兩個拼音是否韻母模糊匹配 (同時考慮聲母是否相容)
- **method** `ChinesePhoneticUtils.check_special_syllable_match(self, pinyin1, pinyin2, bidirectional=...)` — 檢查特殊音節映射 (整音節模糊匹配)
- **method** `ChinesePhoneticUtils.generate_fuzzy_pinyin_variants(self, pinyin_str, bidirectional=...)` — 生成拼音的所有模糊變體
- **method** `ChinesePhoneticUtils.are_fuzzy_similar(self, pinyin1, pinyin2)` — 判斷兩個拼音是否可視為模糊相似。

### `src/phonofix/languages/english/__init__.py`
- **function** `__getattr__(name: ...) -> ...` — 延遲載入語言模組內的主要符號（PEP 562）。
- **function** `__dir__() -> ...` — 讓 IDE/dir() 能看到延遲載入的符號清單。

### `src/phonofix/languages/english/candidates.py`
- **function** `generate_exact_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., tokenizer: ..., exact_matcher: ..., exact_items_by_alias: ..., protected_terms: ...) -> ...` — exact-match 候選生成（Aho-Corasick surface alias）
- **function** `generate_fuzzy_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., tokenizer: ..., backend: ..., phonetic: ..., fuzzy_buckets: ..., protected_terms: ...) -> ...` — 搜尋所有可能的模糊修正候選（不計分，只產生候選資訊）
- **function** `score_candidate_drafts(*, drafts: ...) -> ...` — 統一計分階段

### `src/phonofix/languages/english/config.py`
- **class** `EnglishPhoneticConfig` — 英文語音配置類別 - 集中管理英文模糊音規則

### `src/phonofix/languages/english/corrector.py`
- **class** `EnglishCorrector(PipelineCorrectorBase)` — 英文修正器
- **method** `EnglishCorrector._from_engine(cls, engine: ..., term_mapping: ..., protected_terms: ...=..., on_event: ...=...) -> ...` — 從 Engine 建立輕量 Corrector 實例 (內部方法)
- **method** `EnglishCorrector._emit_replacement(self, candidate: ..., *, silent: ..., trace_id: ...) -> ...` — 發送 replacement 事件（並在非 silent 模式輸出日誌）。
- **method** `EnglishCorrector._emit_pipeline_event(self, event: ..., *, silent: ...) -> ...` — 發送 pipeline 事件（例如 fuzzy_error / degraded）。
- **method** `EnglishCorrector._build_protection_mask(self, text: ...) -> ...` — 建立 protected_terms 的保護遮罩（避免替換到受保護區段）。
- **method** `EnglishCorrector._generate_exact_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — 產生 exact-match 候選草稿（委派給 candidates 模組）。
- **method** `EnglishCorrector._generate_fuzzy_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — 產生 fuzzy-match 候選草稿（委派給 candidates 模組，含分桶剪枝）。
- **method** `EnglishCorrector._score_candidate_drafts(self, drafts: ...) -> ...` — 對候選草稿計分（委派給 candidates 模組）。
- **method** `EnglishCorrector._resolve_conflicts(self, candidates: ...) -> ...` — 解決候選衝突（委派給 replacements 模組）。
- **method** `EnglishCorrector._apply_replacements(self, text: ..., candidates: ..., silent: ...=..., *, trace_id: ...=...) -> ...` — 套用候選替換並輸出事件/日誌（委派給 replacements 模組）。

### `src/phonofix/languages/english/engine.py`
- **class** `EnglishEngine(CorrectorEngine)` — 英文修正引擎。
- **method** `EnglishEngine.__init__(self, phonetic_config: ...=..., *, enable_surface_variants: ...=..., enable_representative_variants: ...=..., verbose: ...=..., on_timing: ...=...)` — 初始化 EnglishEngine。
- **method** `EnglishEngine.phonetic(self) -> ...` — 取得英文發音系統（IPA 轉換與相似度）。
- **method** `EnglishEngine.tokenizer(self) -> ...` — 取得英文分詞器（用於滑動視窗與邊界判斷）。
- **method** `EnglishEngine.fuzzy_generator(self) -> ...` — 取得英文模糊變體生成器（用於 auto-variants 擴充）。
- **method** `EnglishEngine.config(self) -> ...` — 取得英文語音設定（phonetic config）。
- **method** `EnglishEngine.backend(self) -> ...` — 取得英文語音 backend（進階用途：快取/批次 IPA 等）。
- **method** `EnglishEngine.is_initialized(self) -> ...` — 檢查 Engine 與 backend 是否已完成初始化。
- **method** `EnglishEngine.get_backend_stats(self) -> ...` — 取得 backend 快取統計（hits/misses/size）。
- **method** `EnglishEngine.create_corrector(self, term_dict: ..., protected_terms: ...=..., on_event: ...=..., **kwargs) -> ...` — 依據 term_dict 建立 EnglishCorrector。
- **method** `EnglishEngine._normalize_term_value(self, term: ..., value: ...) -> ...` — 將 term_dict 的 value 正規化為 internal config dict。
- **method** `EnglishEngine._filter_aliases_by_phonetic(self, aliases: ...) -> ...` — 依 IPA 去重 aliases（保留第一個出現的拼寫）。

### `src/phonofix/languages/english/filters.py`
- **function** `should_exclude_by_context(*, exclude_when: ..., context: ...) -> ...` — 檢查是否應根據上下文排除修正
- **function** `has_required_keyword(*, keywords: ..., context: ...) -> ...` — 檢查是否滿足關鍵字必要條件
- **function** `check_context_bonus(*, full_text: ..., start_idx: ..., end_idx: ..., keywords: ..., window_size: ...=...) -> ...` — 檢查上下文關鍵字加分
- **function** `build_protection_mask(*, text: ..., protected_terms: ..., protected_matcher: ...) -> ...` — 建立保護遮罩，標記不應被修正的區域 (受保護的詞彙)
- **function** `is_span_protected(*, start: ..., end: ..., protected_indices: ...) -> ...` — 檢查 span 是否命中保護遮罩。
- **function** `token_boundaries(*, tokenizer: ..., text: ...) -> ...` — 取得 token 邊界集合，供 exact 匹配避免子字串誤擊

### `src/phonofix/languages/english/fuzzy_generator.py`
- **class** `_Candidate` — 內部候選資料結構（用於 variants 去重與排序）。
- **class** `EnglishFuzzyGenerator(FuzzyGeneratorProtocol)` — 英文模糊變體生成器（surface-only，可選）
- **method** `EnglishFuzzyGenerator.__init__(self, config: ...=..., backend: ...=..., *, enable_representative_variants: ...=...) -> ...` — 初始化英文模糊變體生成器。
- **method** `EnglishFuzzyGenerator.generate_variants(self, term: ..., max_variants: ...=...) -> ...` — 為輸入詞彙生成英文模糊變體（surface variants）。
- **method** `EnglishFuzzyGenerator._try_get_backend(self) -> ...` — 嘗試取得英文 backend（失敗時回傳 None）。
- **method** `EnglishFuzzyGenerator._generate_safe_surface_variants(self, term: ...) -> ...` — 產生低風險、可泛化的 surface variants。
- **method** `EnglishFuzzyGenerator._generate_representative_spelling_variants(self, term: ...) -> ...` — 產生較激進的 representative spelling variants（預設關閉）。
- **function** `generate_english_variants(term: ..., max_variants: ...=...) -> ...` — 便利函數：快速取得英文模糊變體。

### `src/phonofix/languages/english/indexing.py`
- **function** `first_ipa_symbol(ipa: ...) -> ...` — 取得 IPA 字串的第一個「有效音素字元」。
- **function** `first_phoneme_group(ipa: ..., *, config: ...=...) -> ...` — 取得 IPA 的「首音素群組」
- **function** `build_search_index(*, engine: ..., tokenizer: ..., term_mapping: ...) -> ...` — 建立搜尋索引
- **function** `build_exact_matcher(search_index: ...) -> ...` — 建立 surface alias 的 exact-match 索引（Aho-Corasick）
- **function** `build_fuzzy_buckets(*, search_index: ..., config: ...=...) -> ...` — 建立便宜 pruning 用的分桶索引

### `src/phonofix/languages/english/phonetic_impl.py`
- **class** `EnglishPhoneticSystem(PhoneticSystem)` — 英文發音系統（IPA distance / fuzzy match）
- **method** `EnglishPhoneticSystem.__init__(self, backend: ...=...) -> ...` — 初始化英文發音系統。
- **method** `EnglishPhoneticSystem.to_phonetic(self, text: ...) -> ...` — 將文字轉換為 IPA（並做距離計算用的正規化）。
- **method** `EnglishPhoneticSystem.are_fuzzy_similar(self, phonetic1: ..., phonetic2: ...) -> ...` — 判斷兩個 IPA 是否可視為模糊相似（符合容錯閾值）。
- **method** `EnglishPhoneticSystem.calculate_similarity_score(self, phonetic1: ..., phonetic2: ...) -> ...` — 計算 IPA 相似度分數
- **method** `EnglishPhoneticSystem._normalize_ipa_for_distance(self, ipa: ...) -> ...` — 將 IPA 正規化成適合距離計算的形式。
- **method** `EnglishPhoneticSystem._map_to_phoneme_groups(self, ipa: ...) -> ...` — 將 IPA 字元映射到「音素群組代碼」以降低距離敏感度。
- **method** `EnglishPhoneticSystem._consonant_skeleton(self, ipa: ...) -> ...` — 從 IPA 中抽出「子音骨架」字串。
- **method** `EnglishPhoneticSystem._are_first_phonemes_similar(self, phonetic1: ..., phonetic2: ...) -> ...` — 檢查首音是否相容（作為額外保守門檻）。
- **method** `EnglishPhoneticSystem.get_tolerance(self, length: ...) -> ...` — 根據 IPA 長度選擇容錯閾值（越短越嚴格）。

### `src/phonofix/languages/english/replacements.py`
- **function** `resolve_conflicts(*, candidates: ...) -> ...` — 解決候選衝突
- **function** `apply_replacements(*, text: ..., candidates: ..., emit_replacement: ..., logger: ..., silent: ...=..., trace_id: ...=...) -> ...` — 應用修正並輸出日誌

### `src/phonofix/languages/english/scoring.py`
- **function** `calculate_final_score(*, error_ratio: ..., item: ..., has_context: ..., context_distance: ...=...) -> ...` — 計算最終分數 (越低越好)

### `src/phonofix/languages/english/tokenizer.py`
- **class** `EnglishTokenizer(Tokenizer)` — 英文分詞器
- **method** `EnglishTokenizer.tokenize(self, text: ...) -> ...` — 將英文文本分割為單字列表
- **method** `EnglishTokenizer.get_token_indices(self, text: ...) -> ...` — 取得每個單字在原始文本中的起始與結束索引

### `src/phonofix/languages/english/types.py`
- **class** `EnglishIndexItem(TypedDict)` — 單一索引項目（term 或 alias）
- **class** `EnglishCandidateDraft(TypedDict)` — 候選草稿（draft）。
- **class** `EnglishCandidate(TypedDict)` — 最終候選（candidate）。

### `src/phonofix/languages/japanese/__init__.py`
- **function** `__getattr__(name: ...) -> ...` — 延遲載入語言模組內的主要符號（PEP 562）。
- **function** `__dir__() -> ...` — 讓 IDE/dir() 能看到延遲載入的符號清單。

### `src/phonofix/languages/japanese/candidates.py`
- **function** `_is_ascii_alnum(ch: ...) -> ...`
- **function** `_is_ascii_word(s: ...) -> ...` — 判斷字串是否屬於 ASCII「單詞」類型（羅馬字/數字）。
- **function** `generate_exact_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., exact_matcher: ..., exact_items_by_alias: ..., protected_terms: ...) -> ...` — exact-match 候選生成（Aho-Corasick surface alias）
- **function** `generate_fuzzy_candidate_drafts(*, text: ..., context: ..., protected_indices: ..., tokenizer: ..., phonetic: ..., fuzzy_buckets: ..., protected_terms: ...) -> ...` — 搜尋所有可能的模糊修正候選（不計分，只產生候選資訊）
- **function** `score_candidate_drafts(*, drafts: ...) -> ...` — 將候選草稿（draft）轉成最終候選（candidate），並做基本去重。

### `src/phonofix/languages/japanese/config.py`
- **class** `JapanesePhoneticConfig` — 日文發音配置

### `src/phonofix/languages/japanese/corrector.py`
- **class** `JapaneseCorrector(PipelineCorrectorBase)` — 日文修正器
- **method** `JapaneseCorrector._from_engine(cls, engine: ..., term_mapping: ..., protected_terms: ...=..., on_event: ...=...) -> ...` — 從 Engine 建立輕量 Corrector 實例 (內部方法)
- **method** `JapaneseCorrector._emit_replacement(self, candidate: ..., *, silent: ..., trace_id: ...) -> ...` — 發送 replacement 事件（並在非 silent 模式輸出日誌）。
- **method** `JapaneseCorrector._emit_pipeline_event(self, event: ..., *, silent: ...) -> ...` — 發送 pipeline 事件（例如 fuzzy_error / degraded）。
- **method** `JapaneseCorrector._build_protection_mask(self, text: ...) -> ...` — 建立 protected_terms 的保護遮罩（避免替換到受保護區段）。
- **method** `JapaneseCorrector._generate_exact_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — 產生 exact-match 候選草稿（委派給 candidates 模組）。
- **method** `JapaneseCorrector._generate_fuzzy_candidate_drafts(self, text: ..., context: ..., protected_indices: ...) -> ...` — 產生 fuzzy-match 候選草稿（委派給 candidates 模組，含分桶剪枝）。
- **method** `JapaneseCorrector._score_candidate_drafts(self, drafts: ...) -> ...` — 對候選草稿計分（委派給 candidates 模組）。
- **method** `JapaneseCorrector._resolve_conflicts(self, candidates: ...) -> ...` — 解決候選衝突（委派給 replacements 模組）。
- **method** `JapaneseCorrector._apply_replacements(self, text: ..., candidates: ..., silent: ...=..., *, trace_id: ...=...) -> ...` — 套用候選替換並輸出事件/日誌（委派給 replacements 模組）。

### `src/phonofix/languages/japanese/engine.py`
- **class** `JapaneseEngine(CorrectorEngine)` — 日文修正引擎。
- **method** `JapaneseEngine.__init__(self, phonetic_config: ...=..., *, enable_surface_variants: ...=..., enable_representative_variants: ...=..., verbose: ...=..., on_timing: ...=...)` — 初始化 JapaneseEngine。
- **method** `JapaneseEngine.phonetic(self) -> ...` — 取得日文發音系統（romaji 轉換與相似度）。
- **method** `JapaneseEngine.tokenizer(self) -> ...` — 取得日文分詞器（透過 backend tokenize）。
- **method** `JapaneseEngine.fuzzy_generator(self) -> ...` — 取得日文模糊變體生成器（surface variants）。
- **method** `JapaneseEngine.config(self) -> ...` — 取得日文語音設定（phonetic config）。
- **method** `JapaneseEngine.is_initialized(self) -> ...` — 檢查 Engine 與 backend 是否已完成初始化。
- **method** `JapaneseEngine.get_backend_stats(self) -> ...` — 取得 backend 快取統計（romaji/tokens）。
- **method** `JapaneseEngine.create_corrector(self, term_dict: ..., protected_terms: ...=..., on_event: ...=..., **kwargs) -> ...` — 依據 term_dict 建立 JapaneseCorrector。
- **method** `JapaneseEngine._normalize_term_value(self, term: ..., value: ...) -> ...` — 將 term_dict 的 value 正規化為 internal config dict。
- **method** `JapaneseEngine._filter_aliases_by_phonetic(self, aliases: ..., *, canonical: ...) -> ...` — 依 phonetic key（romaji）去重 aliases。

### `src/phonofix/languages/japanese/filters.py`
- **function** `should_exclude_by_context(*, exclude_when: ..., context: ...) -> ...` — 檢查是否應根據上下文排除修正
- **function** `has_required_keyword(*, keywords: ..., context: ...) -> ...` — 檢查是否滿足關鍵字必要條件
- **function** `check_context_bonus(*, full_text: ..., start_idx: ..., end_idx: ..., keywords: ..., window_size: ...=...) -> ...` — 檢查上下文關鍵字加分
- **function** `build_protection_mask(*, text: ..., protected_terms: ..., protected_matcher: ...) -> ...` — 建立保護遮罩，標記不應被修正的區域 (受保護的詞彙)
- **function** `is_span_protected(*, start: ..., end: ..., protected_indices: ...) -> ...` — 檢查 span 是否命中保護遮罩。

### `src/phonofix/languages/japanese/fuzzy_generator.py`
- **class** `_Candidate` — 內部候選資料結構（用於 variants 去重與排序）。
- **function** `_kata_to_hira(text: ...) -> ...` — 將片假名轉為平假名（僅轉換假名字元，其他字元保持不變）。
- **function** `_hira_to_kata(text: ...) -> ...` — 將平假名轉為片假名（僅轉換假名字元，其他字元保持不變）。
- **function** `_has_japanese_script(text: ...) -> ...` — 粗略判斷文字是否包含日文書寫系統（假名或常用漢字區段）。
- **function** `_normalize_romaji(romaji: ..., config: ...) -> ...` — 正規化 romaji，產生穩定的 phonetic key。
- **function** `_romaji_variants(base: ..., config: ..., *, max_states: ...) -> ...` — 以 romaji 維度做有限展開（避免爆炸）
- **class** `JapaneseFuzzyGenerator(FuzzyGeneratorProtocol)` — 日文模糊變體生成器（surface-only，可選）
- **method** `JapaneseFuzzyGenerator.__init__(self, config: ...=..., backend: ...=..., *, enable_representative_variants: ...=..., max_phonetic_states: ...=...) -> ...` — 初始化日文模糊變體生成器。
- **method** `JapaneseFuzzyGenerator.generate_variants(self, term: ..., max_variants: ...=...) -> ...` — 為輸入詞彙生成日文模糊變體（surface variants）。
- **method** `JapaneseFuzzyGenerator._to_hiragana_reading(self, text: ...) -> ...` — 將日文文本轉為平假名讀音字串。
- **method** `JapaneseFuzzyGenerator._to_romaji(self, text: ...) -> ...` — 將（假名/漢字）日文文本轉為 romaji。
- **method** `JapaneseFuzzyGenerator._phonetic_key(self, text: ...) -> ...` — 取得候選文字的 phonetic key（正規化 romaji）。
- **method** `JapaneseFuzzyGenerator._romaji_rule_variants(self, romaji: ...) -> ...` — 針對 romaji 產生少量規則變體（hepburn/kunrei、長音、促音、鼻音）。
- **method** `JapaneseFuzzyGenerator._kana_confusion_variants(self, hira: ...) -> ...` — 產生假名層級的混淆變體（較昂貴，可選）。
- **function** `JapaneseFuzzyGenerator._kana_confusion_variants.options(ch: ...) -> ...` — 取得單一假名的可替代選項集合（含原字）。

### `src/phonofix/languages/japanese/indexing.py`
- **function** `first_romaji_group(romaji: ...) -> ...` — 取得 Romaji 的「首音群組」
- **function** `build_search_index(*, phonetic: ..., tokenizer: ..., term_mapping: ...) -> ...` — 建立搜尋索引
- **function** `build_exact_matcher(search_index: ...) -> ...` — 建立 surface alias 的 exact-match 索引（Aho-Corasick）。
- **function** `build_fuzzy_buckets(*, search_index: ...) -> ...` — 建立便宜 pruning 用的分桶索引

### `src/phonofix/languages/japanese/phonetic_impl.py`
- **class** `JapanesePhoneticSystem(PhoneticSystem)` — 日文發音系統
- **method** `JapanesePhoneticSystem.__init__(self, backend: ...=...) -> ...` — 初始化日文發音系統。
- **method** `JapanesePhoneticSystem.to_phonetic(self, text: ...) -> ...` — 將日文文本轉換為羅馬拼音
- **method** `JapanesePhoneticSystem.calculate_similarity_score(self, phonetic1: ..., phonetic2: ...) -> ...` — 計算羅馬拼音相似度分數
- **method** `JapanesePhoneticSystem._normalize_phonetic(self, phonetic: ...) -> ...` — 正規化羅馬拼音以進行模糊比對
- **method** `JapanesePhoneticSystem.are_fuzzy_similar(self, phonetic1: ..., phonetic2: ...) -> ...` — 判斷兩個羅馬拼音是否模糊相似
- **method** `JapanesePhoneticSystem.get_tolerance(self, length: ...) -> ...` — 根據文本長度決定容錯率

### `src/phonofix/languages/japanese/replacements.py`
- **function** `resolve_conflicts(*, candidates: ..., logger: ...=...) -> ...` — 解決候選衝突（越低分越優先）
- **function** `apply_replacements(*, text: ..., candidates: ..., emit_replacement: ..., logger: ..., silent: ...=..., trace_id: ...=...) -> ...` — 應用修正並輸出日誌（重建字串避免索引偏移）

### `src/phonofix/languages/japanese/scoring.py`
- **function** `calculate_final_score(*, error_ratio: ..., item: ..., has_context: ..., context_distance: ...=...) -> ...` — 計算最終分數 (越低越好)

### `src/phonofix/languages/japanese/tokenizer.py`
- **class** `JapaneseTokenizer(Tokenizer)` — 日文分詞器
- **method** `JapaneseTokenizer.__init__(self, backend: ...=...) -> ...` — 初始化日文分詞器。
- **method** `JapaneseTokenizer.tokenize(self, text: ...) -> ...` — 將日文文本分割為單詞列表
- **method** `JapaneseTokenizer.get_token_indices(self, text: ...) -> ...` — 取得每個單詞在原始文本中的起始與結束索引

### `src/phonofix/languages/japanese/types.py`
- **class** `JapaneseIndexItem(TypedDict)` — 單一索引項目（term 或 alias）
- **class** `JapaneseCandidateDraft(TypedDict)` — 候選草稿（draft）。
- **class** `JapaneseCandidate(TypedDict)` — 最終候選（candidate）。

### `src/phonofix/languages/japanese/utils.py`
- **function** `is_japanese_char(char: ...) -> ...` — 判斷字元是否為日文 (平假名、片假名)

### `src/phonofix/utils/aho_corasick.py`
- **class** `_Node(Generic[...])` — Aho-Corasick trie 節點（內部使用）。
- **class** `AhoCorasick(Generic[...])` — Aho-Corasick 多模式字串匹配器。
- **method** `AhoCorasick.__init__(self) -> ...` — 建立 matcher。呼叫 `add()` 後需 `build()` 才能開始匹配（或讓 iter_matches 自動 build）。
- **method** `AhoCorasick.add(self, word: ..., value: ...) -> ...` — 加入一個 pattern。
- **method** `AhoCorasick.build(self) -> ...` — 建立 fail links（將 trie 轉為可線性掃描的 automaton）。
- **method** `AhoCorasick.iter_matches(self, text: ...) -> ...` — 逐一輸出 matches

### `src/phonofix/utils/logger.py`
- **function** `get_logger(name: ...=...) -> ...` — 取得專案 Logger
- **function** `setup_logger(level: ...=..., format_string: ...=..., handler: ...=...) -> ...` — 設定專案 Logger
- **class** `TimingContext` — 計時上下文管理器
- **method** `TimingContext.__init__(self, operation: ..., logger: ...=..., level: ...=..., callback: ...=...)` — 初始化計時上下文
- **method** `TimingContext.__enter__(self) -> ...` — 進入計時區塊，記錄起始時間。
- **method** `TimingContext.__exit__(self, exc_type, exc_val, exc_tb) -> ...` — 離開計時區塊，計算 elapsed 並視需要寫入 logger / callback。
- **function** `log_timing(operation: ...=..., logger: ...=..., level: ...=...)` — 計時裝飾器
- **function** `log_timing.decorator(func: ...) -> ...` — 將任意函式包上一層計時邏輯。
- **function** `log_timing.decorator.wrapper(*args, **kwargs) -> ...` — 實際 wrapper：在呼叫前後用 TimingContext 計時。
- **function** `enable_debug_logging() -> ...` — 啟用 debug 日誌
- **function** `enable_timing_logging() -> ...` — 啟用計時日誌

### `tools/benchmark_phonetic.py`
- **function** `benchmark_g2p(convert_func: ..., words: ..., name: ..., iterations: ...=...) -> ...` — 測試逐字 G2P 函式的效能。
- **function** `benchmark_g2p_batch(convert_batch_func: ..., words: ..., name: ..., iterations: ...=...) -> ...` — 測試批次 G2P 函式的效能（一次轉換多個字串）。
- **function** `main() -> ...`
- **function** `main.to_ipa(word: ...) -> ...`
- **function** `main.to_ipa_batch(words: ...) -> ...`
- **function** `main.old_convert(text: ...) -> ...`

### `tools/translation_client.py`
- **function** `translate_text(text, target_lang=...)` — Call the local translation API.

## 依賴清單
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

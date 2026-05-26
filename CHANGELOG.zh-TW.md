# Changelog（變更紀錄）

本專案採用語意化版本（SemVer）。

> 說明：在 `1.0.0` 之前（`0.x`），API 仍可能包含破壞性變更；若你依賴的是「穩定對外 API」，請以 `README.zh-TW.md` 內標註的官方入口為準。

## [0.4.0] - 2026-05-26

### 新增（Added）

- **Tier 1-3 fuzzy hash 路徑** 4 語（中/日/英/韓）。Per-language adapter：中文 canonical_key + 日文 normalized_cache + 英文 Double Metaphone (jellyfish) + 韓文 jamo decompose + `KOREAN_CONFUSION_MAP_JAMO`。
- **Tier 5 fallback** 回退到 legacy `fuzzy_buckets`，cover「規則外 substitution」。Default `enable_tier5_fallback=True` 給 100% v0.3.x 等效；設 `False` 換 ~3× 速度。
- **`pyahocorasick` C extension** 取代自製 AC engine。實測：normal query 7-9× / delete-1 ~5× / memory 100×+ 小。
- **AC delete-1 expansion** (Tier 3) 1-char-deletion fuzzy。
- **韓文支援（experimental）**: `KoreanPhonemizer` + 17 syllable / 10 jamo 規則（8 paper-cited + Zeroth 實測 7 補）。`KOREAN_STATUS="experimental"` flag，Zeroth-20 句覆蓋 61.9%（< 70% target，caller 須用自己 dataset 重測）。
- **macOS 自動偵測 `espeak-ng`**（brew 裝完不用 export env var）。
- **DictRuntime atomic snapshot** + `add_terms` / `remove_terms` 熱重載（10K 字 < 1ms）。
- **StreamBuffer** `feed` / `flush`（跨界 hit retract + duplicate suppression）。
- **AsyncEventQueue** + `trace_id` contextvar `on_event` async。
- **5 個 CLI 子指令**: `phonofix lint / build / correct / bench / migrate`。
- **Bench suite** + GitHub Actions perf regression gate。
- 新 OSS 檔: `LICENSE` / `SECURITY.md` / `CONTRIBUTING.md` / `RELEASE.md`。

### 變更（Changed）

- 速度：zh 小字典 literal-hit ~48×（2.5K → ~120K ops/s）；完整 fuzzy + Tier 5 ON ~2-3× v0.3.x。
- `ChineseEngine / JapaneseEngine / EnglishEngine` 保留 backward compat（走 v0.3.x path；thin-compat layer + `DeprecationWarning` 預定 v0.5.0，≥ 3 個月 grace）。
- Dict yaml schema v2（`mode: protect | replace`）；v1 用 `phonofix migrate` CLI 轉換。

### 修復（Fixed）

- canonical auto-protect mask 整合進新 `PhoneticMatcher`。
- Tier 1 overlap priority: 最長 span exact > Tier 1 > Tier 3 delete-1（Codex audit B.1）。
- `add_terms` / `remove_terms` 後 Tier 5 legacy corrector cache invalidate（reviewer P1）。
- zh Tier 1 pinyin offset 漂移修（ASCII/標點 input — Codex audit B.3）。
- Tier 5 event payload schema 統一（nullable span 欄位 — Codex audit A.4）。

### 依賴（Dependencies）

- 核心新增 `pyahocorasick>=2.1.0`, `jellyfish>=1.2.1`。
- 新 optional extras: `[ko]` 含 `ko-pron + python-mecab-ko`。

### 測試（Tests）

- 554 個 in-scope 測試全綠（+18 個 adversarial — 獨立 reviewer agent + Codex 雙獨立 audit）。

## [0.3.2] - 2026-05-25

### 修復（Fixed）

- 修正「alias 是 canonical 子字串」場景下 canonical 字面被破壞的 bug。原本當字典 alias 是 canonical 的子字串（如 alias `北車` 是 canonical `台北車站` 子字串），input 中含 canonical 字面會被內部 alias match 二次替換（`台北車站` → `台台北車站站`）。修法：在 corrector 初始化時自動把 canonical 加入 protection mask。影響三語，bug 位於語言無關核心層（#1）。
- 中文與英文的 `resolve_conflicts` 同步加上 `(score, -length)` tie-break，與日文行為一致。防止短 alias 在同分競爭時吃掉完整覆蓋的長 alias。

### 測試（Tests）

- 新增 `tests/test_canonical_substring_preservation.py` — 7 個防回歸 test，涵蓋中/日的：canonical 字面保護 / alias 仍可替換 / 混合 input / 同音 alias 案例。
- `tests/test_performance_guards.py` 兩個 fuzzy 分桶測試修整：它們的 input 是字典 canonical 字面，現在 auto-protect 會在更早階段 short-circuit（功能正確、更快），測試需顯式清掉 `protected_terms` 才能驗證原本的 fuzzy 分桶假設。

## [0.3.1] - 2025-12-16

### 調整（Changed）

- README 首頁區塊更新：新增專案 Logo 與 badges（PyPI/Python versions/License/Snapshot/Changelog），並統一連結到最新 repo。
- 新增 `assets/images/logo.png`（文件使用）。

## [0.3.0] - 2025-12-16

### 重大變更（Breaking）

- Python 最低版本提升至 `>=3.10`（見 `pyproject.toml`）。
- 官方公開 API 以 `ChineseEngine` / `EnglishEngine` / `JapaneseEngine` 為主；舊版 `UnifiedEngine` / `UnifiedCorrector` / streaming 相關入口不再作為穩定 API（請依 `README.zh-TW.md` 的最新範例遷移）。
- `import phonofix` 改為 PEP 562 延遲載入：避免在 import 階段就載入/初始化重依賴（如 `phonemizer` / `pypinyin` / `cutlet` / `fugashi`）。

### 新增（Added）

- 日文支援：`JapaneseEngine`、romaji phonetic system、分詞與模糊變體生成器。
- 可觀測性與故障策略：支援 `on_event` 事件回呼、`trace_id`，並統一 `mode` / `fail_policy`（例如 fuzzy 失敗時降級或直接拋錯）。
- Backend 與快取統計：中英日 backend 統一 `get_cache_stats()` 回傳結構；英文 backend 支援 `initialize_lazy()` 並可觀測背景初始化狀態。
- 工具與文件：新增 `tools/snapshot.py` 產生專案快照（`snapshot.zh-TW.md` / `snapshot.md`）。

### 調整（Changed）

- 三語 corrector/pipeline 拆分模組（`candidates` / `filters` / `indexing` / `scoring` / `replacements`），降低單檔肥大並提升可維護性。
- 日文 exact-match 更保守：避免短 romaji alias 命中在更長 token 內（例如 `ai` 命中 `kaihatsu`）。

### 修正（Fixed）

- `initialize_lazy()` 背景初始化失敗不再可能「默默」發生：失敗狀態與錯誤可由 backend stats 觀測，並有測試覆蓋。

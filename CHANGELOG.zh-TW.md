# Changelog（變更紀錄）

本專案採用語意化版本（SemVer）。

> 說明：在 `1.0.0` 之前（`0.x`），API 仍可能包含破壞性變更；若你依賴的是「穩定對外 API」，請以 `README.zh-TW.md` 內標註的官方入口為準。

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

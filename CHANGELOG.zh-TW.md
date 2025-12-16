# Changelog（變更紀錄）

本專案採用語意化版本（SemVer）。

> 說明：在 `1.0.0` 之前（`0.x`），API 仍可能包含破壞性變更；若你依賴的是「穩定對外 API」，請以 `README.zh-TW.md` 內標註的官方入口為準。

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


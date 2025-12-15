# 新語言擴充清單（一步一步）

這份清單是「可以照著打勾」的實作流程，目標是降低漏做與回歸的風險。

## A. 命名與入口

- 決定 `{language}` 目錄名（例如 `korean`）與 Engine `_engine_name`
- 在 `src/phonofix/__init__.py`（或語言 `__init__.py` 的 lazy import）加入 Engine 匯出
- 在 `pyproject.toml` 新增 optional dependency group（例如 `ko = [...]`）

## B. Backend（依賴與快取的單一真實來源）

- 延遲載入第三方庫（import 只在第一次使用時發生）
- `initialize()` / `is_initialized()`：必要時先 warm up
- 將 phonetic 與 tokenizer 需要的昂貴物件集中共用（例如 tagger/model）
- LRU 或等價快取並提供 `get_cache_stats()` / `clear_cache()`
- 未安裝依賴時丟出可讀的 `{LANG}_INSTALL_HINT`

## C. Engine（組裝與 normalize）

- 初始化 backend（呼叫 backend.initialize）
- 建立 phonetic system / tokenizer / fuzzy generator
- `create_corrector()`：
  - normalize term dict
  - 生成 variants（可選）
  - 以 phonetic key 去重（避免詞典膨脹）
  - 建立 corrector（用 `_from_engine`）

## D. Corrector（薄 orchestrator + pipeline steps）

- corrector 必須繼承 `PipelineCorrectorBase`
- 不自行實作 correct()（除非只是呼叫 super，但原則上不需要）
- 索引初始化放在 `_from_engine`：
  - `search_index`
  - `exact matcher`
  - `fuzzy buckets`
- 事件輸出：
  - replacement
  - pipeline events（fuzzy_error / degraded）

## E. 拆分模組（避免單檔肥大）

- 完成 `types.py / indexing.py / filters.py / scoring.py / candidates.py / replacements.py`
- 確保各模組註解包含：
  - 模組責任
  - 設計原則（效能/可測性/可維護性）
  - 重要欄位/策略說明（例如 buckets、pruning、token boundaries）

## F. 測試與守門

- 功能測試：至少能做 2–3 個代表案例
- 依賴穩定性測試：
  - monkeypatch fuzzy draft 生成丟例外
  - 仍需 exact-match 成功
  - 檢查事件中包含 fuzzy_error / degraded（依 fail_policy）
  - 參考：`tests/test_dependency_stability.py`
- 效能守門（不做時間閾值）：
  - 記錄關鍵呼叫次數（例如 similarity 呼叫次數）
  - 或記錄被處理的 item 數，確保分桶 pruning 沒退化
  - 參考：`tests/test_performance_guards.py`
- backend 單例/初始化測試：多引擎共享同 backend，不重複 init

## G. 範例與文件

- 新增 `examples/{language}_examples.py`（至少 basic/keywords/exclude_when/weight）
- 更新 `README.md`（或 `README.zh-TW.md`）的語言支援與安裝方式

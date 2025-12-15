# 建議檔案樹（以現有中/英/日為準）

這份清單是「你新增語言時應該落在哪些位置」，以及每個檔案應負責什麼。

## 1) Backend（負責依賴、初始化、快取、單例）

- `src/phonofix/backend/{language}_backend.py`
  - 單例：`get_{language}_backend()`
  - 延遲載入第三方庫（第一次使用才 import）
  - 初始化（需要時）：`initialize()` / `is_initialized()`
  - 快取：LRU 或等價機制，並提供 `get_cache_stats()` / `clear_cache()`
  - 目的：把外部依賴風險與效能熱點集中在單一真實來源，避免散落在 corrector/utils。
- `src/phonofix/backend/__init__.py`
  - 匯出 `get_{language}_backend` 與 `{Language}PhoneticBackend`

## 2) Language package（語言實作）

- `src/phonofix/languages/{language}/__init__.py`
  - 定義 `{LANG}_INSTALL_HINT` 與 `INSTALL_HINT`
  - 提供 lazy import（讓 `from phonofix import {Language}Engine` 可工作）
- `src/phonofix/languages/{language}/config.py`
  - 放規則表、分桶群組表、模糊規則、預設參數（避免散落在其他檔案）
- `src/phonofix/languages/{language}/phonetic_impl.py`
  - `PhoneticSystem` 實作（將文本/片段轉成 phonetic domain）
  - similarity 計算通常也在這裡（或至少提供 `calculate_similarity_score`）
- `src/phonofix/languages/{language}/tokenizer.py`
  - `Tokenizer` 實作：`tokenize()` + `get_token_indices()`
  - 必須能把 token span 映射回原文字串（corrector 會用）
- `src/phonofix/languages/{language}/fuzzy_generator.py`
  - `FuzzyGeneratorProtocol` 實作（surface variants）
  - 生成階段就以 phonetic key 去重，控制膨脹（參考中文/英文/日文）
- `src/phonofix/languages/{language}/engine.py`
  - `CorrectorEngine` 實作：持有 backend/phonetic/tokenizer/fuzzy_generator
  - `create_corrector()`：normalize term dict、生成 variants（可選）、過濾/去重、建立 corrector
- `src/phonofix/languages/{language}/corrector.py`
  - 薄 orchestrator：索引初始化 + 事件 emission + pipeline steps 委派
  - 不應再寫一套 correct()；必須使用 `PipelineCorrectorBase.correct()`

## 3) Corrector 拆分模組（避免 corrector.py 肥大）

放在 `src/phonofix/languages/{language}/` 內：
- `types.py`：draft/candidate/index item 的型別形狀（TypedDict）
- `indexing.py`：build_search_index / build_exact_matcher / build_fuzzy_buckets
- `filters.py`：protected mask、exclude_when/keywords、token boundary（若需要）、context bonus
- `scoring.py`：final score policy（把 error_ratio 轉成排序分數）
- `candidates.py`：exact/fuzzy drafts 生成 + 統一計分（score_candidate_drafts）
- `replacements.py`：conflict resolution + apply replacements（字串重建或反向套用）

## 4) Tests（至少要有的四種）

放在 `tests/`：
- 功能測試：確保基本修正可用
- 依賴穩定性：fuzzy 流程故障時，exact-match 仍可工作（degrade 事件）
- 效能守門：分桶 pruning 有效（以呼叫次數/遍歷數驗證）
- 並發/單例：backend 單例與初始化行為

## 5) Examples（讓使用者與你們自己能快速驗收）

放在 `examples/{language}_examples.py`：
- basic usage
- keywords / exclude_when
- weight
- long article（可選，但建議保留）


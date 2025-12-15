# 新語言擴充模板（只含註解/註釋）

這份模板的目標是讓你們未來要擴充語言時，可以「照著讀、照著做」，並且自然對齊目前專案已落地的架構（中文/英文/日文）。

重要原則（直說、避免踩雷）：
- 不把模板放在 `src/`：避免被打包進 wheel、被 IDE 誤判為可用語言模組、甚至被誤 import 造成混淆。
- 以「一致的層次」擴充：`Backend → Engine → Corrector`，並且 `Corrector` 一律使用 core 的 `PipelineCorrectorBase.correct()`。
- 以「效能守門」當設計需求：不要用 wall-clock 閾值做測試，改用「關鍵呼叫次數上限」與「分桶 pruning 行為」做回歸保護。

本模板只提供文件與註釋，不包含可執行程式碼；你在真正實作時，應以現有三語言為 reference，將對應檔案落在 `src/phonofix/`。

## 你要做的事情（總覽）

1. 決定語言代號與命名（例如 `korean` / `ko`），並確定 Engine `_engine_name` 與套件路徑一致。
2. 新增 backend：管理外部依賴的延遲載入、初始化、快取、執行緒安全的單例。
3. 新增 engine：持有 backend、phonetic system、tokenizer、fuzzy generator，並提供 `create_corrector()` 工廠方法。
4. 新增 language 模組：`config.py`、`phonetic_impl.py`、`tokenizer.py`、`fuzzy_generator.py`、`corrector.py`、`__init__.py`。
5. 讓 corrector 使用「拆分模組」：`types/indexing/filters/scoring/candidates/replacements`，避免肥大檔案。
6. 補上 tests 與 examples：至少包含功能、依賴退化、效能守門、以及範例腳本。

## 不要省略的關鍵設計（用來避免未來維護地獄）

### 1) 依賴與延遲載入（backend 必須是單一真實來源）

你們是複合式封裝多庫的專案，新的語言依賴應直接寫在 `pyproject.toml`（用 optional-dependencies group），並且：
- backend 必須負責延遲載入第三方庫，並在未安裝時丟出「可讀的 INSTALL_HINT」。
- engine 應在初始化時呼叫 backend.initialize()（若有昂貴 init），並提供 `get_backend_stats()`。

### 2) Corrector 一律走 core pipeline（不要再在各語言重寫 correct()）

`PipelineCorrectorBase.correct()` 已統一處理：
- `mode` / `fail_policy`（fuzzy 失敗時 degrade 的事件與行為）
- `trace_id`
- timing context（可觀測性）

各語言 corrector 應只提供 pipeline steps（保護遮罩、候選生成、計分、衝突解決、套用替換、事件 emission）。

### 3) 效能守門（分桶 + 關鍵呼叫上限）

對於「滑動視窗 + 模糊比對」類演算法，最常見的回歸是：
- 退化成每個窗口對所有 items 計算 similarity（呼叫數爆炸）

因此模板要求你在設計上就要有：
- 分桶索引（至少要有 `window length` + `首音/首群組` 的維度）
- 測試以「呼叫次數」驗證 pruning 有效（不要用時間閾值）

## 文件索引

- `templates/language_template/FILE_TREE.md`：建議的檔案樹與每個檔案的責任
- `templates/language_template/CHECKLIST.md`：一步一步實作清單（含測試與驗收）
- `templates/language_template/OBSERVABILITY_AND_GUARDS.md`：事件/降級/效能守門的規格
- `templates/language_template/PACKAGING_AND_DEPS.md`：pyproject optional dependencies 與 INSTALL_HINT 規格


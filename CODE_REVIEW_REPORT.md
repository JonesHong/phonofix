# Phonofix 代碼評估報告（現況風險 / 可改進項 / 缺漏）

日期：2025-12-14  
基準版本：`65e89d4`（含目前工作樹改動；未提交）  
範圍：`src/phonofix/**`、`tests/**`、`pyproject.toml`、`.gitignore`、`README*.md`  

## 0. 概覽（直說）

- 架構：三語言統一 Backend → Engine → Corrector，保護詞 / 事件 / 降級策略已對齊。
- 可靠度：`python -m pytest -q` → **70 passed**；`ruff check .` → **All checks passed**。
- 可重現性：`uv.lock` 已 `git add`（尚未提交），`.gitignore` 已移除忽略規則，README 已補 `uv sync --locked`。
- 可觀測性：`fail_policy="degrade"/"raise"` + `mode="production"/"evaluation"`；`silent` 只關掉 logger，不關掉事件；新增事件型別 `fuzzy_error/degraded/warning`，帶 `trace_id`（每次 correct 內傳遞，不會被併發覆蓋）。
- 效能：Aho-Corasick build 改用 `deque`；`protected_terms` 以 Aho 索引；新增效能守門/變體上限等測試。

## 1. 仍需注意的風險（按優先序）

### R1（可重現性）`uv.lock` 未提交
- 狀態：已 `git add uv.lock`，但尚未 commit。
- 風險：發佈/CI 若不用 lock 安裝，版本可重現性不保。
- 建議：提交 `uv.lock`，並在 CI/文件固定使用 `uv sync --locked`。

### R2（數據精度）Backend hits/misses 未加鎖
- 影響：高併發下統計可能偏差；功能不受影響，但若用於自動化決策/監控會不準。
- 建議：若要使用這些統計，改為 thread-safe counter 或加鎖；若暫不需要，文件標註「近似值」。

### R3（資源邊界）超大保護詞集
- 影響：雖已 Aho 索引，protected_terms 很大時仍可能增加記憶體/建索引時間。
- 建議：在 README/配置註明建議上限或提供分批/懶載入策略。

### R4（釋出節奏）大量改動未提交
- 影響：變更涵蓋核心/測試/文件，若不一次性檢視提交，後續 merge 容易混亂。
- 建議：完成檢視後打包提交並更新版本號/變更日誌。

## 2. 已完成的改進（相對於舊版）

- `uv.lock` 納入追蹤流程；README 補 `uv sync --locked`。
- `protected_terms` 跨語言一致，採 Aho 索引，重疊保護行為一致並有測試。
- 降級策略/可觀測性：`fail_policy`/`mode` + `fuzzy_error/degraded/warning` 事件；`silent` 只抑制 logger；事件帶 `trace_id`。
- trace_id 併發安全：改 per-call 傳遞，避免多執行緒覆蓋。
- Aho build 用 `deque`，降低大量 alias 時的 build 退化風險。
- 測試增補：效能守門、依賴降級、併發、安全事件、變體上限、保護詞重疊等（總計 70 項通過）。

## 3. 建議的短期行動

1) 提交 `uv.lock` 並在 CI/發佈流程固定用 `uv sync --locked`。  
2) 決定 backend 統計是否需精確；若是，改 thread-safe 計數並補測試；若否，文件標註近似。  
3) 文件補充 protected_terms 規模建議（避免一次塞過大詞集）。  
4) 統一檢視目前改動並提交（附版本號與變更日誌）。  

## 4. 驗證摘要

- 測試：`python -m pytest -q` → **70 passed**  
- Lint：`ruff check .` → **All checks passed**

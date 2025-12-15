# 可觀測性與效能守門規格（擴充語言必讀）

本文件描述「你新增語言時要維持的一致性」，避免每個語言各自發展後失控。

## 1) 事件（on_event）規格

### replacement 事件（必須）
- 目的：讓使用者能觀測每一次替換的原因與細節
- 建議欄位：
  - `type = "replacement"`
  - `engine`：語言代號（例如 `english`）
  - `trace_id`：一次 correct 呼叫的追蹤 ID
  - `start/end`：替換 span
  - `original/replacement`
  - `canonical/alias`
  - `score`
  - `has_context`（若你的語言有 keywords/context bonus）

### fuzzy_error / degraded 事件（由 core pipeline 觸發）
- fuzzy draft 產生失敗時，必須：
  - emit `fuzzy_error`（帶 exception_type/message）
  - fail_policy=degrade 時再 emit `degraded`（fallback=exact_only）

## 2) fail_policy 與 mode

新增語言時不要自行發明新的行為；請維持現有語意：
- `fail_policy="raise"`：fuzzy 失敗就 raise，但仍要 emit `fuzzy_error`
- `fail_policy="degrade"`：fuzzy 失敗降級為 exact-only（emit `fuzzy_error` + `degraded`）
- `mode="evaluation"`：等同 fail_policy=raise
- `mode="production"`：等同 fail_policy=degrade

## 3) 效能守門測試（不要用時間）

禁止用 wall-clock 做閾值測試，原因是 CI/使用者環境波動會造成 flaky。

建議做法：
- 以呼叫次數上限守門：例如「similarity 計算呼叫 <= N」
- 以遍歷數量守門：例如「只會遍歷同群組 items」

你要守的核心回歸風險：
- fuzzy 掃描退化成「每個 window 對所有 items 做 similarity」

可參考現有測試（作為風格與粒度的 reference）：
- `tests/test_dependency_stability.py`：fuzzy 失敗時仍能 exact-only，並驗證事件
- `tests/test_performance_guards.py`：以呼叫次數/分桶行為守門，避免 O(windows * items) 回歸

## 4) 分桶策略（最低標準）

語言若採滑動視窗 fuzzy 掃描，最低要求：
- bucket 維度 1：窗口長度（token_count 或字元長度）
- bucket 維度 2：首音/首群組（phonetic domain 的第一個可用特徵）

並在 candidates 生成階段使用：
- 先算「窗口首音群組」再取對應 bucket items
- 盡早 pruning（protected mask、空 phonetic、長度差上限等）

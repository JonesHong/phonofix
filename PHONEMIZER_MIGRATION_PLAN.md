# 使用 phonemizer + espeak-ng 替代 eng-to-ipa 的完整計畫

## 目標

- 將目前專案中依賴的 `eng-to-ipa` 替換為 **`phonemizer` 搭配 `espeak-ng`**，作為英文文字 → 音標（phoneme/IPA）映射的主要引擎。
- 在不破壞既有功能的前提下，提供：
  - 更穩定且完整的英文 G2P（grapheme-to-phoneme）能力。
  - 能處理 OOV（未登錄詞、專有名詞、新字）的能力。
  - 良好的效能與可維護性。
- 使用 **`git worktree`** 建立獨立工作樹進行開發與測試，在確認穩定後再合併回主分支。

---

## 一、技術選型說明

### 1. 現狀：`eng-to-ipa`

- 優點：
  - 純 Python，安裝簡單。
  - 直接輸出 IPA，易於人類閱讀。
- 缺點（本次替換主因）：
  - **小眾、維護停滯**，後續風險較高。
  - 主要基於 CMU 字典，對於 OOV（例如人名、新創詞）表現不佳，可能回傳 `*` 或無發音。
  - 社群與生態系相對薄弱。

### 2. 新方案：`phonemizer` + `espeak-ng`

- `phonemizer`：
  - Python 套件，提供統一接口，底層可切換多種 G2P 後端（`espeak`, `festival`, `segments` 等）。
  - 在 TTS/ASR 社群使用廣泛，維護與社群活動度較佳。
- `espeak-ng`：
  - C/C++ 實作的多語言語音合成引擎，支援英文與多種語言的 G2P。
  - **優點**：
    - 速度極快，適合在線處理。
    - 規則豐富，對 OOV 與非標準拼寫有一定容錯能力。
  - **缺點**：
    - Windows 環境需要安裝系統層級的可執行檔，並設定 PATH，部署成本較高。

### 3. 輸出格式與音標空間

- `phonemizer` 使用 `espeak`/`espeak-ng` 後端時，可輸出：
  - IPA（預設或經由選項調整）。
  - 可再透過自定義處理轉換為內部 phoneme id 空間。
- 對本專案的意義：
  - 雖然不強制一定要 IPA，但使用 IPA 有利於：
    - 與中文音標（拼音、注音）之間做距離設計。
    - 方便 Debug 與人工檢查。

---

## 二、開發流程（使用 git worktree）

以下以主分支名稱為 `main` 為例，若實際專案為其他名稱（例如 `master`），請調整指令。

### 1. 建立專用工作樹與功能分支

在專案根目錄（包含 `.git` 的上層）執行：

```bash
# 1. 建立新 worktree 目錄（例如 phonemizer-migration）
git worktree add ../multi_language_corrector-phonemizer main

# 2. 進入新工作樹目錄
cd ../multi_language_corrector-phonemizer

# 3. 建立並切換到新功能分支
git checkout -b feature/phonemizer-migration
```

> 說明：
> - 這樣可以在 `c:/work/multi_language_corrector` 與 `c:/work/multi_language_corrector-phonemizer` 兩個實體目錄中，分別進行穩定維護與實驗開發。
> - 測試通過後，再將 `feature/phonemizer-migration` 分支合併回 `main`。

### 2. 開發與提交流程建議

1. 在 worktree 分支上逐步完成以下技術任務（見下一節）。
2. 每完成一個邏輯步驟（例如「新增 `phonemizer` 依賴」或「實作英文 phonetic adapter」）就進行一次小範圍 commit：
   - 有助於日後追蹤與 rollback。
3. 在 `feature/phonemizer-migration` 上執行完整的單元測試：
   - `pytest`
4. 確認所有測試通過、並在 README/文件更新完成後，發起 PR 或直接在 `main` 上進行 fast-forward 合併。

---

## 三、技術實作步驟

### 步驟 1：新增依賴與環境設定

1. **在 `pyproject.toml` 中新增 `phonemizer` 依賴**：

   - `dependencies` 區段：
     - 移除：`"eng-to-ipa>=0.0.2"`
     - 新增：`"phonemizer>=3.2.1"`（實際版本以 PyPI 當下穩定版為準）。

2. **文件說明 Windows 上安裝 `espeak-ng` 的方式**：

   - 在 `README.md` 或新增 `docs/PHONEMIZER_SETUP.md`：
     - 提供：
       - 下載連結（官方或可信來源）。
       - 安裝步驟。
       - 如何將 `espeak-ng` 的 `bin` 路徑加入環境變數 `PATH`。
       - 簡單驗證指令，例如：
         - 在命令列執行：`espeak-ng "hello"` 應能發聲或輸出文字。

3. **可選：加上環境檢查工具**

   - 在專案中提供一個小工具腳本（例如 `debug_test.py` 或新的 `tools/check_espeak.py`）：
     - 嘗試呼叫 `phonemizer` 進行簡單 G2P。
     - 若失敗，印出清楚的錯誤訊息與安裝提示。

### 步驟 2：設計英文 phonetic adapter 介面

1. 在 `multi_language_corrector/english/phonetic_impl.py`（若尚未有，則新增）中定義**統一介面**：

   - 例如：

     ```python
     from typing import List

     def text_to_phonemes(text: str) -> List[str]:
         """將英文文字轉換成內部使用的 phoneme/音標序列。"""
         ...
     ```

   - 未來可以在此處切換底層實作（`phonemizer`、`g2p-en`、或其他實驗性引擎），而不影響上層邏輯。

2. 明確定義**內部 phonetic 空間**：

   - 選項 A：直接使用 IPA 字元序列（由 `phonemizer` + `espeak` 提供）。
   - 選項 B：建立一個映射表 `ipa_symbol -> internal_id`，輸出為 `List[int]` 或 `List[str]` 的離散代碼。
   - 在現階段建議：
     - 先以 `List[str]`（IPA 符號序列）為主，讓系統能快速接入並驗證效果。
     - 未來若須優化效能或記憶體再引入 `id` 映射層。

### 步驟 3：以 `phonemizer` + `espeak-ng` 實作 G2P

1. 基本用法草案（僅作計畫說明）：

   ```python
   from phonemizer import phonemize

   def text_to_phonemes(text: str) -> list[str]:
       # language: 'en-us' 或 'en'，backend: 'espeak' 或 'espeak-mbrola'
       ipa = phonemize(
           text,
           language='en-us',
           backend='espeak',
           strip=True,        # 去除多餘空白
           preserve_punctuation=False,
           with_stress=True,  # 視需求保留/移除重音
       )
       # 依實際輸出格式拆分
       # 例如："həˈloʊ" 或 "h ə ˈ l oʊ"，需要視 backend 和 options 調整
       return ipa.split()  # 或自訂切分規則
   ```

2. 規則設計：

   - 針對 `phonemizer` 不同選項與 `espeak-ng` 實際輸出格式，需：
     - 決定是否保留重音記號（如 `ˈ`）。
     - 決定是否保留音節界線（如 `.`）。
     - 決定如何處理標點符號與數字。
   - 建議：
     - 初期保留重音與音節資訊，但在計算距離時可設定權重較低。

3. OOV 處理驗證：

   - 選定一組測試樣例，例如：
     - 常見詞：`"hello", "world"`
     - 專有名詞：`"ChatGPT", "OpenAI", "Taipower"`
     - 混合：`"LLaMA3", "iPhone", "YouTube"`
   - 驗證：
     - `phonemizer` 是否能為所有樣例給出合理 phoneme。
     - 與 `eng-to-ipa` 的差異（例如不再出現 `*`）。

### 步驟 4：把英文 phonetic adapter 接入現有 correction 流程

1. 搜尋目前專案中使用英文音標的地方：

   - 例如：
     - `multi_language_corrector/languages/english/phonetic_impl.py`
     - `multi_language_corrector/languages/english/utils.py`
     - 或任何使用 `eng-to-ipa` 的模組。

2. 將底層 G2P 呼叫改為呼叫 `text_to_phonemes`：

   - 這樣可以讓上層 correction engine 與底層實作解耦，未來可切換實作。

3. 確認：

   - 多語言 router（`multi_language_corrector/router/language_router.py`）無需變更或僅需微調。
   - 中文端邏輯不受影響。

### 步驟 5：測試與驗證

1. 單元測試：

   - `tests/test_english_corrector.py`：
     - 新增 / 更新測試：
       - 檢查英文輸入能產生非空 phoneme 序列。
       - 對於特定單字，比較與過去預期結果是否在「音近」範圍內（不必逐字完全相同，但需合理）。

2. 整合測試 / 範例腳本：

   - 更新 `examples/mixed_language_examples.py` 或新增 `examples/english_phonemizer_demo.py`：
     - 顯示：
       - 原文 → phoneme 序列。
       - 在 correction 場景下，示範「音近替換」。

3. 效能驗證：

   - 撰寫簡單 benchmark（可放在 `debug_test.py` 或 `tools/benchmark_phonetic.py`）：
     - 給一組大量英文詞彙，測量：
       - `eng-to-ipa` 舊版本耗時。
       - `phonemizer` 新版本耗時。
     - 目標：新方案效能不顯著慢於舊方案，或在可接受範圍內。

---

## 四、部署與回滾策略

### 1. 部署策略

1. 在 `feature/phonemizer-migration` 分支上完成：
   - 依賴更新。
   - 英文 phonetic adapter 實作。
   - 測試與範例更新。
   - Windows 上 `espeak-ng` 安裝文件。
2. CI（若有）通過所有測試。
3. 在 PR 或 code review 通過後，將 `feature/phonemizer-migration` 合併到 `main`。

### 2. 回滾策略

1. 若在實際使用中出現嚴重問題：
   - 可以透過 git revert 回到 `eng-to-ipa` 版本。
   - 因為透過 `git worktree` + 分支開發，原始 `main` 分支在開發期間不受污染，回滾成本低。
2. 在實作時保留舊版 adapter（暫時不刪除）：
   - 例如保留一個 `eng_to_ipa_adapter.py`，方便對照與比對輸出差異。

---

## 五、後續優化與擴充方向

1. **多語言統一 phonetic 空間**：
   - 未來可考慮使用 IPA 為跨語言共同層，將中文（拼音/注音）與英文的音素映射到同一套 `phoneme_id` 空間，讓跨語言音近替換更精準。

2. **替代後端開關**：
   - 預留配置選項允許切換 G2P backend：
     - `phonemizer+espeak`（預設）。
     - 其他實驗方案（例如 `g2p-en`、`deep-phonemizer`）。

3. **錯誤收集與日誌**：
   - 在實際服務中記錄：
     - 哪些輸入在 G2P 上效果比較差或產生異常。
     - 方便後續優化規則或補充自定字典。

---

## 六、小結

- 本計畫透過 `phonemizer` + `espeak-ng` 替代 `eng-to-ipa`，主要目的是：
  - 強化英文 G2P 能力（支援 OOV、速度快）。
  - 選擇社群較大、維護較佳的技術棧。
- 透過 `git worktree` 與獨立分支進行開發與測試，可以：
  - 將風險隔離在專用工作樹中。
  - 在所有測試與文件更新完備後，再安全地合併回主分支。
- 後續可在此基礎上，逐步優化跨語言 phonetic 空間與多語言音近替換策略。
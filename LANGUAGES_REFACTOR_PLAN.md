# Phonofix 多語言重構規劃（精簡架構 / 介面一致化）

目標：把 `src/phonofix/languages/*` 整理成可持續擴充的「語言模組」，並且：
- 官方支援：使用者可以直接 import/使用各語言的公開 API（不只 Engine）。
- 介面一致：類別與方法命名一致（流程邏輯可因語言不同）。
- 易擴充：未來語言會越來越多，新增語言時只需新增一個語言資料夾。
- 先求有：本計畫先不做第三方 plugin/entry-points，等內部整理穩定後再加。
- 精簡模組：移除目前覺得多餘的「組合/串流」修正層，先把單一語言能力做穩。

> 前提：目前是測試版，不考慮向後相容；重構完成後以「最新 API」為準（允許 breaking changes）。

補充（本計畫納入的「一致性護欄」，避免重構中途被非架構問題卡住）：
- `pyproject.toml` 的 version / extras 名稱、`src/phonofix/__init__.py` 的 `__version__` 與 install 範例需一致（目前已不一致）。
- `CorrectorEngine` 的 type hints 不能引用不存在的模組（舊版曾指向 `phonofix.correction.base`，但該檔不存在）。

---

## 零、專案目的（核心概念 / 不變量：以中文為基準）

本計畫以「中文（Chinese）」作為 **reference implementation**（最完整、先開發、你最熟悉），先把中文的資料結構/流程/行為鎖成基準規格；英文、日文後續重構必須對齊中文的基準（若因語言特性需要例外，必須在計畫書中明文列出例外點與驗收方式）。

### 目的
- 使用者提供「專有名詞字典」（canonical term mapping）
- 系統把 **拼寫（surface form）統一轉到「發音表示（phonetic representation）」維度**，建立可比對的群體（canonical + fuzzy variants）
- 當文本進來時，同樣轉到發音維度，比對命中後，再把原文片段替換成正確拼寫（canonical surface）

### 中文基準流程（reference）
以下用中文術語對齊你目前 `ChineseEngine/ChineseCorrector` 的設計語言，作為全語言共同模板：
1) **詞典輸入 → 正規化（canonical config）**
   - 支援 list/dict/full-config 三種輸入
   - key 永遠是 canonical（正確拼寫），value 描述 aliases/keywords/exclude_when/weight 等
2) **auto-fuzzy 擴充（以中文 config.py 規則為準的思路）**
   - 根據 `config.py` 定義的容易混淆規則（聲母/韻母/整音節/黏著詞等），在「發音維度」生成 variants
   - **不論使用者提供哪種輸入形狀、是否已提供 aliases，都必做 auto-fuzzy**
3) **建立可比對群體（canonical 必須納入）**
   - 每個 canonical 的比對群體至少包含 `{canonical} ∪ aliases ∪ fuzzy_variants`
   - canonical 必須被納入群體（不論是直接納入 targets、或以等價方式納入索引），避免「只修錯字不修正確詞」或大小寫/繁簡等情境出現行為落差
4) **文本進來 → 同維度轉換 → 比對 → 替換**
   - 文本與候選都要轉到同一個 phonetic domain（中文=拼音字串）
   - 比對發生在 phonetic domain（Levenshtein/容錯率/模糊規則）
   - 命中後回到 surface domain 做替換（用 tokenizer indices / window indices 保證替換位置正確）

### 基本流程（語言無關，對齊中文模板）
1) **輸入正規化**：把使用者輸入（list / dict / full config）統一成 `NormalizedTermConfig`
2) **auto-fuzzy 擴充**：依各語言 `config.py` 的混淆規則，產生 variants，並與使用者提供 aliases 合併（所有語言、所有輸入形狀都必做）
3) **建索引（phonetic domain）**：
   - 把每個 alias/variant 轉成該語言的發音表示（中文=拼音、英文=IPA、日文=羅馬拼音）
   - 建立搜尋索引（包含 phonetic、token/長度、keywords/exclude_when/weight 等）
4) **文本修正（phonetic matching → surface replace）**：
   - 將輸入文本分割（token/window），轉成 phonetic
   - 在 phonetic 空間比對（允許模糊規則），找到候選後回到 surface 位置做替換

### 不變量（重構時必須維持）
- 比對在 phonetic domain 完成；替換輸出必回到 canonical surface
- `FuzzyGenerator.generate_variants(term)` 只負責「term → variants」，不依賴整份詞典
- `Engine.create_corrector(...)` 需對所有輸入形狀都做 auto-fuzzy merge（再交給 corrector 建索引）
- `Tokenizer.get_token_indices()` 必須能把「比對單元」映射回原文位置，確保替換不亂位
- 每個 canonical 的比對群體必須包含 canonical 本身（對齊中文既有策略 `targets = set(aliases) | {canonical}`）

### 現況對照（以中文基準檢查：目前不一致/缺漏，需在 Phase 0～6 解決）
- auto-fuzzy 尚未做到「所有語言/所有輸入形狀必做」：中文/英文/日文策略不同，需統一成中文基準
- fuzzy generator 契約不一致：
  - 中文 fuzzy generator 仍混用 `str|list` 輸入且會把 canonical 放入回傳列表（需統一成 variants-only + 單一輸入型別）
  - 英文/日文 fuzzy generator 介面已較接近，但必須對齊「variants-only」與上限策略
- canonical 是否納入比對群體不一致：
  - 中文既有做法會把 canonical 納入 targets；英文/日文目前偏向只索引 aliases，需對齊中文基準（或提出等價替代法並寫入驗收）
- 日文 fuzzy generator 已存在但未被 JapaneseEngine 使用：需納入 auto-fuzzy（對齊中文模板第 2 步）
- 中文 corrector 仍有單語言 streaming API：你決定先移除，以維持「語言模組一致性」

---

## 一、先定義「會被承諾」的 Public API

### 1) 對外入口（以最新為準）
- `phonofix.EnglishEngine / ChineseEngine / JapaneseEngine`（官方使用方式）
- Protocols（統一放在 `phonofix.core.protocols`）
  - `CorrectorProtocol`
  - `ContextAwareCorrectorProtocol`
  - `FuzzyGeneratorProtocol`（本次新增，統一 fuzzy）

### 2) 也要讓使用者能直接用 languages（你的需求）
每個語言 package 對外 export 一致的元件集合：
- `<Lang>Engine`
- `<Lang>Corrector`
- `<Lang>FuzzyGenerator`
- `<Lang>Tokenizer`
- `<Lang>PhoneticSystem`
- `<Lang>PhoneticConfig`

---

## 二、目標資料夾結構（建議落地版）

### 語言模組統一 layout（未來新增語言照抄）
```
src/phonofix/languages/<lang>/
  __init__.py            # 統一 export
  engine.py              # <Lang>Engine（語言自己的 engine）
  corrector.py           # <Lang>Corrector
  fuzzy_generator.py     # <Lang>FuzzyGenerator（統一介面）
  tokenizer.py           # <Lang>Tokenizer（已是 ABC 介面）
  phonetic_impl.py       # <Lang>PhoneticSystem（已是 ABC 介面）
  config.py              # <Lang>PhoneticConfig
  utils.py               # lazy import / helper（避免循環依賴）
```

### Engine 抽象基類（共用層）
```
src/phonofix/core/
  engine_interface.py    # CorrectorEngine (ABC)
```

> 本計畫會移除 `src/phonofix/engine/unified_engine.py`，並把各語言 engine 移到 `languages/<lang>/engine.py`。
>
> 另外因為 `engine/` 僅剩抽象基類，已將 `CorrectorEngine` 併入 `core/`（`src/phonofix/core/engine_interface.py`）。

### Protocols（集中管理）
```
src/phonofix/core/protocols/
  __init__.py
  corrector.py           # CorrectorProtocol / ContextAwareCorrectorProtocol
  fuzzy.py               # FuzzyGeneratorProtocol
```

> 放在 `core/` 的原因：它們是跨模組共用的「契約層」，跟 `core/phonetic_interface.py`、`core/tokenizer_interface.py` 的定位一致；避免散落在 `correction/` 之類的特定功能資料夾造成誤解。

---

## 三、核心介面（契約）統一策略

你目前的 repo 已經混用 ABC（Tokenizer/PhoneticSystem/Backend/Engine）與 Protocol（Corrector）。
本次先聚焦「內部一致化」，建議：
- **對外最小契約**：Corrector 仍維持 `Protocol`（已完成）
- **內部可控抽象**：Backend、Tokenizer、PhoneticSystem、CorrectorEngine 維持 ABC

### 建議新增：FuzzyGeneratorProtocol（最小、可擴充）
統一 fuzzy generator 的「單詞輸入」行為（避免中文現在的 list/dict 混合模式污染共同介面）：
- `generate_variants(term: str, max_variants: int = 30) -> list[str]`

補充（本次明確定義行為）：
- `generate_variants(...)` **只回傳 aliases/variants**（不包含原始 `term` 本身），Engine 會自行決定 canonical 是否也加入搜尋目標。
- 所有語言、所有 `create_corrector()` 的輸入形狀都要做 **auto-fuzzy 擴充**：即使使用者已提供 `aliases`，也會再 merge fuzzy 生成的 variants（並去重、套用上限）。

批次需求：
- 放到 Engine 層做 loop，或另開 `generate_variants_many(...)`（但不要混在同一個 method 裡）

---

## 四、重構順序清單（每步要改什麼 + 驗收）

### Phase 0 — 先修護欄與一致性（避免一開始就踩雷）
**目標**
- 先修掉「會讓後續重構無法順利進行」的斷鏈與不一致（不是架構改動，但會阻塞）。

**要更新的檔案**
- 更新：`src/phonofix/core/engine_interface.py`
  - 移除/修正對不存在的 `phonofix.correction.base` 的 type hint 依賴（回傳型別先改用現行的 `CorrectorProtocol` 或 forward-ref；Phase 1 再統一搬到 `phonofix.core.protocols`）。
- 更新：`src/phonofix/__init__.py`
  - `__version__` 與 `pyproject.toml` 一致。
  - install 範例的 extras 名稱與 `pyproject.toml` 一致（目前 `ch/en/ja` 與 `chinese/english` 混用）。
  - 對外 re-export 要包含 `JapaneseEngine`（本計畫已承諾）。

**驗收**
- `python -c "import phonofix; print(phonofix.__version__)"` 可用且與 `pyproject.toml` 一致
- `pytest -q` 全綠（此 Phase 只修斷鏈/一致性，行為不應改變）

---

### Phase 1 — 協議（Protocols）收斂到 `core/`（先把「放哪裡」定下來）
**目標**
- 移除 `src/phonofix/correction/protocol.py` 的定位歧義：Protocol 不是「修正功能」，而是跨模組契約。
- 後續所有型別/契約都只從 `phonofix.core.protocols` 匯入。

**要更新/新增的檔案**
- 新增：
  - `src/phonofix/core/protocols/__init__.py`
  - `src/phonofix/core/protocols/corrector.py`（搬移 `CorrectorProtocol`、`ContextAwareCorrectorProtocol`）
  - `src/phonofix/core/protocols/fuzzy.py`（新增 `FuzzyGeneratorProtocol`）
- 刪除：
  - `src/phonofix/correction/protocol.py`
- 更新所有引用點（import path 全改）：
  - `src/phonofix/languages/*/corrector.py`
  - `src/phonofix/__init__.py`
  - 以及任何使用到 CorrectorProtocol 的地方

**驗收**
- `pytest -q` 全綠（此時 `correction/` 還沒移除，但 protocol 來源已統一）

---

### Phase 2 — 建立重構護欄（先鎖行為，避免改到最後不敢合）
**目標**
- 讓後續每一步都能用測試確認「輸入/輸出契約沒壞」。
- 先鎖定中文的行為作為基準（golden behavior），英文/日文必須對齊（除非在本計畫明確列出例外）。

**要更新/新增的檔案**
- 新增：`tests/test_language_contracts.py`
  - 驗證每個語言的：
    - `FuzzyGenerator.generate_variants()` 回傳 `list[str]`
    - `Corrector.correct()` 回傳 `str`
    - `Tokenizer.tokenize()` / `get_token_indices()` 基本一致性
  - 驗證「不論輸入形狀都會 auto-fuzzy」：
    - `engine.create_corrector(["Term"])` 與 `engine.create_corrector({"Term": []})` 都會有 auto-fuzzy 擴充（以中文基準的語意：canonical 群體必含 canonical + merge variants）
  - 驗證 canonical 必須納入比對群體（對齊中文）：
    - 給定 `{ "台北車站": [] }`，corrector 的索引/比對群體至少包含 canonical 自身（以可觀測行為驗收，例如 canonical 大小寫/繁簡等不會導致「完全不處理」）
- 更新：`tests/test_engine.py`
  - 補齊 `JapaneseEngine` 的初始化/建立 corrector/修正能力測試（目前 coverage 不完整）

**驗收**
- `pytest -q` 全綠

---

### Phase 3 — 統一「詞典輸入格式」與 normalization（Engine 層先統一）
**目標**
- 所有 Engine 的 `create_corrector()` 接受同一種 input 形狀並轉成統一的 normalized config。
- 不先改 corrector 演算法，只把資料入口統一起來，並為後續「必做 auto-fuzzy」提供一致的資料結構。
- 以中文既有資料語意為準：輸入 dict 的 key 是 canonical；canonical 是否納入群體不應由 fuzzy generator 決定，而是由 Engine/corrector 的 targets 規則決定。

**要更新/新增的檔案**
- 新增：`src/phonofix/core/term_config.py`
  - 定義 `TermDictInput`、`NormalizedTermConfig`（建議用 `TypedDict`）
  - 定義 normalization helper：`normalize_term_dict(...) -> dict[str, NormalizedTermConfig]`
  - `NormalizedTermConfig` 最小欄位建議固定為：
    - `aliases: list[str]`（使用者提供的 aliases；不含 canonical）
    - `keywords: list[str]`
    - `exclude_when: list[str]`
    - `weight: float`
    - `max_variants: int`（單詞 fuzzy 生成上限，預設 30）
  - 強制規則（對齊中文 baseline）：
    - `aliases` 不包含 canonical；canonical 永遠由 key 表達
    - 後續建立 targets 時必須做 `targets = set(aliases) | {canonical}`
- 更新：`src/phonofix/core/engine_interface.py`
  - `create_corrector()` docstring/typing 對齊 `TermDictInput`
- 更新：
  - `src/phonofix/languages/english/engine.py`
  - `src/phonofix/languages/chinese/engine.py`
  - `src/phonofix/languages/japanese/engine.py`
  - 讓它們都使用 `normalize_term_dict`，避免各自手寫 normalize 邏輯發散

**驗收**
- `tests/test_engine.py` 全綠
- 每個 Engine 都能接受：
  - `["台北車站"]`
  - `{"台北車站": ["北車"]}`
  - `{"台北車站": {"aliases": ["北車"], "keywords": [], "exclude_when": [], "weight": 0.0}}`

---

### Phase 4 — 統一 fuzzy generator 介面（先做 “term -> list[str]”）
**目標**
- 三語言 fuzzy generator method signature 統一：
  - `generate_variants(term: str, max_variants: int = 30) -> list[str]`
- `generate_variants(...)` 行為統一：回傳 variants（不包含原始 term），並以 `max_variants` 控制上限。
- 把中文 fuzzy generator 的「list 輸入回 dict」行為移出（改由 Engine loop 或 helper 處理）。
- **所有語言、所有輸入形狀都必做 auto-fuzzy**：Engine 需在 `create_corrector()` 階段把 fuzzy variants 與使用者 aliases merge 後再建立 corrector。

**要更新/新增的檔案**
- 更新：
  - `src/phonofix/languages/chinese/fuzzy_generator.py`
    - `generate_variants(term: str, max_variants: int = 30) -> list[str]`
    - 移除 `term: list[str] -> dict` 的混合行為（需要批次就另開 helper，例如 `generate_variants_many`，但不納入 Protocol）
  - `src/phonofix/languages/english/fuzzy_generator.py`（參數/回傳一致）
  - `src/phonofix/languages/japanese/fuzzy_generator.py`（參數/回傳一致）
- 更新：
  - `src/phonofix/languages/chinese/engine.py`
  - `src/phonofix/languages/english/engine.py`
  - `src/phonofix/languages/japanese/engine.py`
  - 確保 auto-fuzzy 擴充只依賴 `generate_variants(term: str, ...)`，且不論輸入形狀都會執行（再 merge 使用者 aliases）

**驗收**
- 新增/更新 `tests/test_language_contracts.py`：三語言 fuzzy 都通過型別/行為測試
- Engine auto-fuzzy 邏輯仍可運作

---

### Phase 5 — 統一 corrector 的「最小對外介面」與參數（只做表面一致）
**目標**
- 更新 `CorrectorProtocol` 使其對外介面一致（仍可只傳 `text` 呼叫）
- 但讓三語言 corrector 的實際 signature 盡量一致（對使用者更直覺，也利於未來做組合層）：
  - `correct(text: str, full_context: str | None = None, silent: bool = False) -> str`

**要更新/新增的檔案**
- 更新：
  - `src/phonofix/languages/chinese/corrector.py`
    - `correct(asr_text, silent=False)` 調整為可接受 `full_context=None`（可忽略不用）
  - `src/phonofix/languages/english/corrector.py`（已接近）
  - `src/phonofix/languages/japanese/corrector.py`（已接近）
- 更新：`src/phonofix/core/protocols/corrector.py`
  - 讓 `CorrectorProtocol` 明確包含 `full_context`/`silent`（皆有預設值）
  - `ContextAwareCorrectorProtocol` 視需要保留或刪除（若 `CorrectorProtocol` 已涵蓋就不再需要）

**驗收**
- `tests/test_*_corrector.py` 全綠
- 各語言 corrector 均符合 `CorrectorProtocol`

---

### Phase 6 — 刪除組合/串流修正層，精簡 `phonofix` API
**目標**
- 移除目前覺得多餘的模組：
  - `src/phonofix/engine/unified_engine.py`
  - `src/phonofix/correction/unified_corrector.py`
  - `src/phonofix/correction/streaming_corrector.py`
- 移除中文 corrector 內建的 streaming API（避免單一語言殘留特殊介面造成不一致）：
  - `ChineseCorrector.correct_streaming(...)`
- `src/phonofix/correction/` 不再作為對外 API（可整包刪除或留空，依你希望的整潔度）
- `CorrectorEngine` 抽象基類收斂到 `core/`（`src/phonofix/core/engine_interface.py`）

**要更新/新增的檔案**
- 刪除：
  - `src/phonofix/engine/unified_engine.py`
  - `src/phonofix/correction/unified_corrector.py`
  - `src/phonofix/correction/streaming_corrector.py`
  - `src/phonofix/correction/__init__.py`（若整包移除）
- 更新（移除對上述模組的 export/import）：
  - `src/phonofix/__init__.py`
  - （已調整）`CorrectorEngine` 併入 `src/phonofix/core/engine_interface.py`，`engine/` 目錄不再需要保留
- 更新測試（移除或改寫）：
  - `tests/test_unified_corrector.py`（刪除）
  - `tests/test_engine.py`（移除 UnifiedEngine 相關測試）
  - `tests/test_chinese_corrector.py`（若有使用 `correct_streaming`，則移除/改寫）
- 更新文件：
  - `README.md`
  - `README.zh-TW.md`

**驗收**
- `from phonofix import EnglishEngine` / `ChineseEngine` / `JapaneseEngine` 可用
- `pytest -q` 全綠

---

### Phase 7 — 把各語言 Engine 移到 `languages/<lang>/engine.py`
**目標**
- 你想要的結構：語言越多，就新增一個語言資料夾即可。
- 以 `phonofix.languages.<lang>.engine.<Lang>Engine` 作為單一來源。

**要更新/新增的檔案（依實際差異逐一修）**
- 新增（或移動後形成的新檔案）：
  - `src/phonofix/languages/english/engine.py`
  - `src/phonofix/languages/chinese/engine.py`
  - `src/phonofix/languages/japanese/engine.py`
- 刪除（舊位置的語言 engine）：
  - `src/phonofix/engine/english_engine.py`
  - `src/phonofix/engine/chinese_engine.py`
  - `src/phonofix/engine/japanese_engine.py`
- 更新 exports：
  - `src/phonofix/languages/*/__init__.py`（三語言 export 統一）
  - `src/phonofix/__init__.py`（官方入口改指向 languages）
  - `tests/test_engine.py`（import path 更新）

**驗收**
- `CorrectorEngine` 位於 `src/phonofix/core/engine_interface.py`
- `pytest -q` 全綠

---

### Phase 8 — 全域整理（未使用 import / 死代碼 / 未接上的 fuzzy）
**目標**
- 清掉目前各檔案「import 但沒用」的內容，避免越擴越髒。
- 清掉已不再使用的模組/符號（尤其是移除 Unified/Streaming 後殘留的 export、測試、README 範例）。
- 確認每個語言的 fuzzy generator「不是寫了放著」：要嘛被語言 engine 實際用於 auto-alias，要嘛明確標示為 advanced API 並在文件中說明使用方式。

**目前 repo 已觀測到的具體項目（重構前基準，用來驗收 Phase 8 是否有清乾淨）**
- **auto-fuzzy 必做的落地檢查**
  - 三語言 Engine 對所有輸入形狀都會執行 fuzzy 擴充（即使已有 aliases 也會 merge fuzzy variants）
  - `languages/<lang>/__init__.py` 對外 export 一致（包含 `<Lang>FuzzyGenerator`）
- **可能是多餘的便利函數（repo 內未引用，需決定保留/刪除/納入 public API）**
  - `src/phonofix/languages/english/fuzzy_generator.py`：`generate_english_variants(...)` 目前只在本檔內出現，未被其他模組引用。
- **刪除 Unified/Streaming 後會變成死模組（可直接一併刪除或移除引用）**
  - `src/phonofix/router/language_router.py`：目前只被 `src/phonofix/engine/unified_engine.py`、`src/phonofix/correction/unified_corrector.py` 引用；若 Phase 6 刪除 Unified，這個 router 將變成未使用。
- **已由 ruff 偵測到的未使用 import / 未使用變數（F401/F841，25 個，皆可 auto-fix）**
  - `src/phonofix/correction/unified_corrector.py`：`re` 未使用（但此檔在 Phase 6 會刪除）
  - `src/phonofix/router/language_router.py`：`re` 未使用（若 router 也刪除則不必修）
  - `src/phonofix/languages/chinese/corrector.py`：`List`、`Union`、`ChinesePhoneticConfig`、`ChinesePhoneticUtils` 未使用
  - `src/phonofix/languages/english/corrector.py`：`re`、`Union`、`Set`、`EnglishPhoneticSystem`、`EnglishTokenizer` 未使用
  - `src/phonofix/languages/japanese/corrector.py`：`Tuple`、`CorrectorProtocol`、`JapanesePhoneticSystem`、`JapaneseTokenizer`、`JapanesePhoneticConfig` 未使用
  - `src/phonofix/languages/english/fuzzy_generator.py`：`itertools.product` 未使用
  - `src/phonofix/languages/japanese/utils.py`：`importlib`、`logging` 未使用
  - `src/phonofix/utils/logger.py`：`contextlib.contextmanager` 未使用
  - `src/phonofix/backend/english_backend.py`：區域變數 `e` 指派後未使用
  - `src/phonofix/languages/english/phonetic_impl.py`：`re`、`List`、`Optional` 未使用；區域變數 `e` 指派後未使用

**要更新/新增的檔案**
- 更新：`src/phonofix/languages/*/*.py`
  - 移除未使用 imports（典型：`typing`、`logging`、`TYPE_CHECKING`、不再存在的 Unified/Streaming 相關引用）
  - 移除未使用的 helper/function（若已被重構淘汰）
- 更新：`src/phonofix/__init__.py`
  - 移除未使用/已移除模組的 re-export
- 更新：`README.md`、`README.zh-TW.md`
  - 移除已刪功能的範例（Unified/Streaming）
  - 補上每語言的官方用法（Engine + create_corrector + correct）
- 更新：`tests/*`
  - 刪除或改寫已移除功能的測試
- （可選）新增：`docs/ARCHITECTURE.md`
  - 簡短描述 core/languages/backend 的邊界，避免未來又把職責放錯層

**工具與驗收**
- 跑 `ruff check --fix`（移除未使用 import、整理 lint）
- 跑 `pytest -q`
- 額外檢查（人工）：搜尋 `UnifiedEngine` / `UnifiedCorrector` / `StreamingCorrector` 應該只剩歷史文件或完全不存在
- 額外檢查（人工）：搜尋 `FuzzyGenerator` 介面，確認每語言：
  - `languages/<lang>/engine.py` 有明確策略（auto alias 是否使用 fuzzy）
  - `languages/<lang>/__init__.py` export 一致且沒有漏掉/寫錯

## 五、風險點（提前規避）
- **循環依賴**：`languages/*` 不要反向 import `phonofix.engine.*`；共用層才 import languages。（本次已移除 `phonofix.engine`）
- **可選依賴**：日文/中文/英文的外部依賴要延遲載入（中文已做得不錯），避免 `import phonofix` 就因缺依賴爆炸。
- **auto-fuzzy 成本**：本計畫要求所有語言/輸入形狀都要 auto-fuzzy，需用 `max_variants`、去重與必要的過濾策略避免詞典膨脹與建構時間失控。
- **breaking change 成本**：不做向後相容代表要一次把 repo 內所有引用點與 README/測試一起改乾淨。

---

## 六、建議執行方式（最省力的切分）
- 每個 Phase 一個 PR（或至少一個可回滾的 commit 區塊）
- Phase 0～5 先做完（先定契約與介面），再做 Phase 6～8（刪模組/搬家/全域整理），避免先大搬檔案導致修復成本爆炸。

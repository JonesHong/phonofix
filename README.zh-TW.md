[<kbd>English</kbd>](README.md) [<kbd><strong>繁體中文</strong></kbd>](README.zh-TW.md)

# Phonofix（多語言語音相似替換引擎）

Phonofix 是一個「以語音相似度為核心」的專有名詞替換工具，適合用在 ASR/LLM 後處理、專有名詞標準化、同音/近音錯寫修正等場景。

---

## 目錄

- [Phonofix（多語言語音相似替換引擎）](#phonofix多語言語音相似替換引擎)
  - [目錄](#目錄)
  - [支援語言](#支援語言)
  - [核心概念](#核心概念)
  - [快速開始（最新 API）](#快速開始最新-api)
    - [中文](#中文)
    - [英文（需安裝 espeak-ng）](#英文需安裝-espeak-ng)
    - [日文](#日文)
    - [混合語言（手動串接）](#混合語言手動串接)
  - [可觀測性與故障策略](#可觀測性與故障策略)
  - [替換算法流程（概觀）](#替換算法流程概觀)
  - [安裝](#安裝)
    - [環境需求](#環境需求)
    - [使用 uv（推薦）](#使用-uv推薦)
    - [英文支援（espeak-ng）](#英文支援espeak-ng)
  - [開發/驗證](#開發驗證)
  - [授權](#授權)
  - [致謝](#致謝)

---

## 支援語言

| 語言 | 發音表示（Phonetic Key） | Engine 入口 | Extras |
|---|---|---|---|
| 中文 | 拼音 | `ChineseEngine` | `phonofix[ch]` |
| 英文 | IPA | `EnglishEngine` | `phonofix[en]` |
| 日文 | Romaji | `JapaneseEngine` | `phonofix[ja]` |

> 註記：後續會陸續新增更多語言支援。因作者不熟悉部分語言，相關功能會使用 AI 協助開發，難免可能出錯；若你在實務使用時發現問題，歡迎透過 GitHub Issue 回報與討論：
> - https://github.com/JonesHong/phonofix/issues

專案檔案結構與完整 API/符號快照請見：[snapshot.zh-TW.md](snapshot.zh-TW.md)。

## 核心概念

- 你提供「專有名詞字典」（canonical + aliases/設定）
- 系統把文本與詞典都轉到「發音表示（phonetic key）」維度做比對
- 命中後回到原文字串維度做替換（輸出 canonical 拼寫）

> 注意：這不是全文拼字檢查器；它專注在「你關心的專有名詞」。

## 快速開始（最新 API）

### 中文

```python
from phonofix import ChineseEngine

engine = ChineseEngine()
corrector = engine.create_corrector({"台北車站": ["北車", "胎北車站"]})

print(corrector.correct("我在北車等你"))
# 輸出: 我在台北車站等你
```

### 英文（需安裝 espeak-ng）

```python
from phonofix import EnglishEngine

engine = EnglishEngine()
corrector = engine.create_corrector({"TensorFlow": ["Ten so floor"], "Python": ["Pyton"]})

print(corrector.correct("I use Pyton to write Ten so floor code"))
# Output: I use Python to write TensorFlow code
```

### 日文

```python
from phonofix import JapaneseEngine

engine = JapaneseEngine()
corrector = engine.create_corrector({"会議": ["kaigi"], "ロボット": ["robotto"]})

print(corrector.correct("明日のkaigiに参加します"))
# 出力: 明日の会議に参加します
print(corrector.correct("新しいrobottoのkaihatsu"))  # 例：也可同時處理其他詞
# 出力: 新しいロボットのkaihatsu
```

### 混合語言（手動串接）

本專案不做自動語言偵測；混合輸入請以「手動串接」方式處理：

```python
from phonofix import ChineseEngine, EnglishEngine

ch = ChineseEngine().create_corrector({"台北車站": ["北車"]})
en = EnglishEngine().create_corrector({"Python": ["Pyton"]})

text = "我在北車用Pyton寫code"
text = en.correct(text, full_context=text)
text = ch.correct(text, full_context=text)
print(text)
# 輸出: 我在台北車站用Python寫code
```

## 可觀測性與故障策略

原則：允許降級，但不允許默默降級。

- `on_event`：建議作為 SDK 面向的觀測介面（收集 replacement / fuzzy_error / degraded 等）
- `silent=True`：只關閉 logger 輸出；事件仍可用於觀測
- `fail_policy`：
  - `"degrade"`（預設）：fuzzy 發生例外時降級為 exact-only，並發出事件
  - `"raise"`：fuzzy 發生例外時直接拋出（適合 CI/離線評估）
- `mode`：
  - `"production"` 等同 `fail_policy="degrade"`
  - `"evaluation"` 等同 `fail_policy="raise"`
- `trace_id`：同一次 `correct()` 的事件關聯 ID（可由呼叫端傳入）

## 替換算法流程（概觀）


對應實作：`PipelineCorrectorBase.correct()`（完整符號請見 [snapshot.zh-TW.md](snapshot.zh-TW.md)）。

> 本專案不做自動語言偵測：混合語言請「手動串接」多個 corrector（詳見上方範例）。

```text
輸入文本
    │
    ▼
┌─────────────────────────────────────┐
│ 1. 建立保護遮罩                         │
│    標記 protected_terms 的範圍          │
│    受保護範圍不參與替換                  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 2. 產生候選草稿（Drafts）                │
│    2.1 exact：Aho-Corasick 命中         │
│    2.2 fuzzy：滑動視窗 + 語音相似度      │
│        - fail_policy 可降級為 exact     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 3. Keywords/exclude_when 過濾           │
│    - exclude_when 命中 → 跳過           │
│    - keywords 不滿足 → 跳過             │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 4. 計算最終分數                         │
│    Score = error_ratio - weight -      │
│            context_bonus               │
│    （分數越低越好）                      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 5. 去衝突（Conflict Resolution）        │
│    依分數排序，選擇不重疊的最佳候選       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 6. 套用替換                             │
│    以 start 升序「重建字串」套用         │
│    避免索引偏移，確保輸出一致             │
└─────────────────────────────────────┘
    │
    ▼
輸出結果
```

## 安裝

### 環境需求

- Python `>=3.10`

### 使用 uv（推薦）

```bash
uv add phonofix
```

你也可以用 extras 讓依賴意圖更清楚（實際依賴版本以 `pyproject.toml` 為準）：

```bash
uv add "phonofix[ch]"
uv add "phonofix[en]"
uv add "phonofix[ja]"
```

### 英文支援（espeak-ng）

英文語音功能依賴系統套件 `espeak-ng`。

建議直接使用本專案提供的安裝腳本（會協助安裝/設定環境變數）：

- Windows PowerShell：`.\scripts\setup_espeak.ps1`
- Windows CMD：`scripts\setup_espeak_windows.bat`
- macOS / Linux：`./scripts/setup_espeak.sh`

若你想自行安裝：
- macOS：`brew install espeak-ng`
- Linux：`apt install espeak-ng`

## 開發/驗證

- 執行測試：`pytest -q`
- 跑範例：
  - 中文：`python examples/chinese_examples.py`
  - 英文：`python examples/english_examples.py`
  - 日文：`python examples/japanese_examples.py`
- 產生專案快照：`python tools/snapshot.py`（輸出到 `snapshot.zh-TW.md`）

## 授權

MIT License

## 致謝

- [pypinyin](https://github.com/mozillazg/python-pinyin)
- [python-Levenshtein](https://github.com/maxbachmann/Levenshtein)
- [Pinyin2Hanzi](https://github.com/letiantian/Pinyin2Hanzi)
- [hanziconv](https://github.com/berniey/hanziconv)
- [phonemizer](https://github.com/bootphon/phonemizer)
- [espeak-ng](https://github.com/espeak-ng/espeak-ng)
- [cutlet](https://github.com/polm/cutlet)
- [fugashi](https://github.com/polm/fugashi)

# CLAUDE.md

Guidance for Claude Code working in this repository.

## Project

**Phonofix** — 多語言語音相似替換引擎（PyPI: `phonofix`）。把字典與輸入文本都映射到**語音鍵**空間比對，命中後以 canonical 拼寫寫回原字串。

**不維護任何字典** — 工具只提供替換引擎，字典由使用者依業務領域維護。**不是全文糾錯工具**，只處理「使用者指定的專有名詞」，不碰語法或一般拼寫錯誤。

適用場景：ASR 後處理、LLM 輸出後處理、TTS 前處理（用同音字繞過 acoustic model 的中文多音字誤讀，範例字典 `scenarios/zh/tts_polyphone.yaml`）、專有名詞標準化、地域詞轉換、縮寫擴展。

## 開發命令

```bash
uv run pytest tests/ -q          # 測試
uv run ruff check .              # lint（開 PR 前必綠）
python examples/chinese_examples.py    # 範例：chinese / english / japanese
python tools/snapshot.py         # 重生 snapshot.md（AST 快照）
```

## 硬規則

- **DCO 強制**：每個 commit 必須有 `Signed-off-by` → 用 `git commit -s`
- **`SPEC.md` 已凍結**：PR 不得變動 spec，要改先開 issue 討論
- 開 PR 前 `ruff check` + `pytest` 都要全綠
- 目前在 `main` 開發。`CONTRIBUTING.md` 寫的「從 `v0.4-dev` 開分支」已過時——該分支在 v0.4.0 合併進 main 後已刪除

## 架構要點（非顯而易見處）

入口是 **Engine → Corrector** 兩段式，不是單一 corrector 類別：

```python
from phonofix import ChineseEngine        # 或 EnglishEngine / JapaneseEngine
corrector = ChineseEngine().create_corrector({"台北車站": ["北車", "胎北車站"]})
corrector.correct("我在北車等你")          # → 我在台北車站等你
```

| 語言 | 語音鍵 | Engine | extras |
|---|---|---|---|
| 中文 | 拼音 | `ChineseEngine` | `phonofix[ch]` |
| 英文 | IPA | `EnglishEngine` | `phonofix[en]` |
| 日文 | 羅馬音 | `JapaneseEngine` | `phonofix[ja]` |

- `src/phonofix/languages/<lang>/` — 各語言的 candidates / config / corrector / engine / filters / fuzzy_generator / indexing / scoring / tokenizer
- `src/phonofix/backend/` — 語音後端（pypinyin / espeak-ng / mecab 等的封裝）
- `src/phonofix/core/protocols/` — corrector / fuzzy / pipeline 的 Protocol 定義
- 完整檔案樹與 AST 級別的類別/函式清單：**`snapshot.md`**（別在這裡重複；它由 `tools/snapshot.py` 自動生成）

## Gotcha

1. **沒有自動語言偵測**。混合語言要**手動串接** corrector，並把原文傳給 `full_context`：
   ```python
   text = en.correct(text, full_context=text)
   text = ch.correct(text, full_context=text)
   ```
   （早期版本的 `UnifiedCorrector` / `LanguageRouter` 自動路由**已移除**，別再引用。）
2. **英文需要系統套件 `espeak-ng`**：`brew install espeak-ng`，或跑 `scripts/setup_espeak.sh`（Windows 用 `scripts/setup_espeak.ps1`）。缺了英文語音功能會壞
3. **Python >= 3.10**（用到 match / walrus / 新式 annotations）
4. 字典權重：地域慣用詞這種 100% 轉換用 `weight: 0.0`；需要上下文判斷的替換用 `weight > 0`
5. 別限制變體數量——用音標去重後的全部變體，砍掉會漏掉有效候選

## 導航

| 要找什麼 | 看哪 |
|---|---|
| 檔案樹 / 類別 / 函式簽章 | `snapshot.md`（自動生成）|
| v0.4 架構規格（凍結） | `SPEC.md` |
| 版本變更 | `CHANGELOG.md` |
| 從舊版 API 遷移 | `MIGRATION.md` |
| PR 流程 / DCO / code style | `CONTRIBUTING.md` |
| 使用方式與完整範例 | `README.md` / `README.zh-TW.md` |
| 各語言深入設計 | `docs/`（PHASE2-COMPAT-DESIGN、PHASE4-THREADING、PHASE5-*、KO-INSTALL-MATRIX、SCHEMAS）|

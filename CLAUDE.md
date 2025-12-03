# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Phonetic Substitution Engine** - 多語言語音相似替換引擎

基於語音相似度的多語言詞彙替換引擎。本工具**不維護任何字典**，僅提供替換引擎。使用者提供專有名詞字典後，工具會自動生成語音變體並進行智能替換。

**核心理念**:
- 工具只提供替換引擎，不維護任何預設字典
- 使用者維護符合業務領域的專有名詞字典
- 工具負責自動生成語音變體與智能替換
- **不是全文糾錯工具**，專注於「專有名詞的語音相似替換」

**支援語言**:
- **中文**：拼音模糊音匹配（台灣國語特徵）
- **英文**：IPA 語音相似度匹配
- **混合文本**：自動語言片段識別與分段處理

**適用場景**:
- **ASR 語音識別後處理**：修正語音轉文字產生的專有名詞錯誤（含中英混合）
- **LLM 輸出後處理**：修正大型語言模型因專有名詞罕見而選錯的同音字
- **專有名詞標準化**：技術術語、品牌名稱、人名地名的統一
- **地域詞彙轉換**：中國 ↔ 台灣慣用詞
- **縮寫擴展**：口語簡稱 → 正式全稱

## Development Commands

### Setup
```bash
# Install dependencies
pip install pypinyin Levenshtein Pinyin2Hanzi hanziconv
# Or use requirements.txt
pip install -r requirements.txt
```

### Run Examples
```bash
# Auto-correct examples (6 examples, recommended)
python auto_correct_examples.py

# Legacy examples
python examples/examples.py
```

### Testing
```bash
# Basic functionality test
python -c "from chinese_text_corrector import ChineseTextCorrector; print('Import successful')"
```

## Architecture

### Module Structure

```
multi_language_corrector/
├── core/                      # 語言抽象層
│   ├── phonetic_interface.py # PhoneticSystem 抽象介面
│   └── tokenizer_interface.py # Tokenizer 抽象介面
├── languages/                 # 語言特定實現
│   ├── chinese/
│   │   ├── phonetic_config.py  # 中文拼音模糊音配置
│   │   ├── phonetic_utils.py   # 中文拼音工具函數
│   │   ├── phonetic_impl.py    # ChinesePhoneticSystem
│   │   ├── tokenizer.py        # 字元級 tokenizer
│   │   └── generator.py        # 中文模糊音詞典生成器
│   └── english/
│       ├── phonetic_impl.py    # EnglishPhoneticSystem (IPA)
│       ├── tokenizer.py        # 單字級 tokenizer
│       └── generator.py        # 英文模糊音詞典生成器
├── router/
│   └── language_router.py     # 語言片段識別與路由
└── correction/
    └── unified_corrector.py   # UnifiedCorrector (統一入口)

# Legacy (向後兼容)
chinese_text_corrector/
└── corrector.py               # ChineseTextCorrector (alias)
```

### Key Components

**1. PhoneticSystem** (`core/phonetic_interface.py`)
- **抽象介面**定義語言發音系統
- 關鍵方法：
  - `to_phonetic(text)`: 將文本轉為音標表示（拼音/IPA/假名）
  - `are_fuzzy_similar(phonetic1, phonetic2)`: 判斷兩個音標是否模糊相似
  - `get_tolerance(word_length)`: 根據詞長取得容錯率
- **實現類別**：
  - `ChinesePhoneticSystem`: 中文拼音模糊音匹配
  - `EnglishPhoneticSystem`: 英文 IPA 語音相似度匹配

**2. Tokenizer** (`core/tokenizer_interface.py`)
- **抽象介面**處理語言特定的 token 切分
- 解決字元流 vs 單字流的差異：
  - 中文/日文：字元級滑動視窗
  - 英文/韓文：單字級 token 流（依空白/標點）
- 避免英文詞被錯誤切割導致誤判

**3. LanguageRouter** (`router/language_router.py`)
- 識別混合語言文本中的語言片段
- 將不同語言片段路由至對應的 PhoneticSystem
- 支援策略：rule-based、fastText、Whisper diarization
- 避免中文模組誤處理英文詞（或反之）

**4. UnifiedCorrector** (`correction/unified_corrector.py`)
- **主要入口類別**，統一處理多語言文本替換
- 自動識別語言片段並調用對應的語言系統
- **核心機制**（語言無關）:
  - 滑動視窗匹配算法（依賴 Tokenizer 介面）
  - 上下文關鍵字加權（距離越近加分越多）
  - 動態容錯率調整（依語言和詞長）
  - 豁免清單避免誤改

**5. ChinesePhoneticSystem** (`languages/chinese/phonetic_impl.py`)
- 台灣國語拼音模糊音規則：
  - n/l 不分、f/h 混淆、r/l 混淆、捲舌音混淆
  - 韻母模糊對應、特例音節映射
- 容錯率：2字詞 0.20 → 4+字詞 0.40
- 使用 `pypinyin` 進行漢字轉拼音

**6. EnglishPhoneticSystem** (`languages/english/phonetic_impl.py`)
- IPA (國際音標) 語音相似度計算
- 解決 ASR 專有名詞錯誤（如 "1kg" → "EKG"）
- 使用 `eng_to_ipa` 或 `epitran` 進行文字轉 IPA
- 容錯率：4字詞 0.35 → 長詞 0.45

### Critical Architecture Decisions

**語言抽象層設計**:
- `PhoneticSystem` 介面統一處理不同語言的發音系統
- `Tokenizer` 介面解決字元流 vs 單字流的差異
- `LanguageRouter` 處理混合語言文本的片段識別
- 核心算法（滑動視窗、上下文加權）完全語言無關

**拼音/音標去重機制**:
- 自動過濾重複音標的別名（類似 Set 行為）
- 避免字典膨脹和重複匹配
- 中文：拼音去重後通常只有 5-20 個變體
- 英文：IPA 去重後變體數量較少

**歸一化策略**:
- 內部固定歸一化為標準詞（正向轉換）
- 所有別名一律轉換為使用者指定的正確詞
- 若不想轉換，直接不加入字典即可

**混合語言處理**:
- 自動識別文本中的語言片段（中文/英文/混合）
- 分段交給對應的語言系統處理
- 避免跨語言誤匹配（中文模組處理英文詞）

## Dictionary Design Patterns

### Three Dictionary Types

參考 `docs/DICTIONARY_ORGANIZATION.md` 了解詳細分類建議：

1. **地域慣用詞** (`weight: 0.0`)
   - 雙向索引：台灣 ↔ 中國慣用詞
   - 100% 轉換，不需上下文判斷
   - 範例：土豆 ↔ 馬鈴薯、視頻 ↔ 影片

2. **ASR 錯誤/錯別字** (`weight > 0`)
   - 單向修正（錯誤 → 正確）
   - 需要上下文判斷和拼音模糊匹配
   - 範例：流奶 → 牛奶、花揮 → 發揮

3. **縮寫擴展** (`weight: 0.0 或 > 0`)
   - 口語簡稱 → 正式全稱
   - 常需上下文關鍵字判斷（如「永豆」可能是「永和豆漿」或「勇者鬥惡龍」）

### Recommended Organization

```python
# 建議分檔管理不同類型詞典
from dictionaries.asr_errors import ASR_ERRORS
from dictionaries.region_cn_to_tw import REGION_CN_TO_TW
from dictionaries.abbreviations import ABBREVIATIONS

# 場景組合
asr_corrector = ChineseTextCorrector.from_terms({
    **ASR_ERRORS,
    **ABBREVIATIONS,
})
```

## API Usage Patterns

### Recommended: Unified Corrector (多語言混合)

```python
from multi_language_corrector.correction.unified_corrector import UnifiedCorrector

# 定義混合語言專有名詞
terms = [
    "台北車站",      # 中文詞
    "TensorFlow",   # 英文專有名詞
    "EKG",          # 英文縮寫
    "Python"
]

corrector = UnifiedCorrector(terms)

# 自動處理混合語言文本
text = "我在北車用Pyton寫code，這個1kg設備很貴"
result = corrector.correct(text)
# "我在台北車站用Python寫code，這個EKG設備很貴"
```

### Legacy: Chinese-Only Corrector

```python
from chinese_text_corrector import ChineseTextCorrector

# 最簡格式 - 僅提供關鍵字列表
corrector = ChineseTextCorrector.from_terms(["台北車站", "牛奶", "發揮"])

# 完整格式 - 別名 + 關鍵字 + 權重
corrector = ChineseTextCorrector.from_terms({
    "永和豆漿": {
        "aliases": ["永豆", "勇豆"],
        "keywords": ["吃", "喝", "買", "宵夜"],
        "weight": 0.3
    }
})

result = corrector.correct("我在北車買了流奶,他花揮了才能")
# '我在台北車站買了牛奶,他發揮了才能'
```

## Important Implementation Notes

### Language Detection & Routing

**混合語言處理流程**:
1. 語言片段識別（中文/英文/混合）
2. 分段交給對應的 PhoneticSystem 處理
3. 合併結果並保持原文格式

**Language Router 策略**:
- **Rule-based**: 簡單正則表達式判斷（快速但不精確）
- **fastText**: 語言識別模型（平衡速度與準確度）
- **Whisper diarization**: ASR 自帶語言標記（最準確）

### Phonetic Matching Algorithm

**中文拼音相似度計算**:
1. 特例音節匹配（優先，如 fa ↔ hua）
2. 韻母模糊匹配（in/ing, en/eng 等）
3. Levenshtein 編輯距離計算
4. 短詞聲母嚴格檢查（2字詞必須聲母匹配）

**英文 IPA 相似度計算**:
1. 文字轉 IPA 音標（使用 eng_to_ipa/epitran）
2. IPA 編輯距離計算（Levenshtein）
3. 容錯率依音標長度調整

**容錯率動態調整**:
- 中文 2 字詞: 0.20（必須非常準確）
- 中文 3 字詞: 0.30
- 中文 4+ 字詞: 0.40（寬容度最高）
- 英文短詞: 0.35
- 英文長詞: 0.45

### Context Keyword Weighting

**距離加權機制** (參考 `docs/DISTANCE_WEIGHTING_FEATURE.md`):
- 關鍵字距離越近，加分越多
- 公式: `bonus = base_bonus * (1 / (1 + distance))`
- 避免遠距離關鍵字過度影響判斷

### Exclusion List

豁免清單避免特定詞被修正：
```python
corrector = ChineseTextCorrector.from_terms(
    ["台北車站"],
    exclusions=["北側", "車站"]  # 這些詞不會被修正
)
```

## File References

- **README.md**: 完整使用說明和範例（多語言支援）
- **auto_correct_examples.py**: 6 個完整範例展示不同使用方式
- **docs/MULTI_LANGUAGE_EXPANSION.md**: 多語言擴展架構分析與實作建議
- **docs/DICTIONARY_ORGANIZATION.md**: 詞典分類管理建議
- **docs/DISTANCE_WEIGHTING_FEATURE.md**: 距離加權機制說明
- **docs/CHANGELOG.md**: 版本更新記錄

## Common Pitfalls

1. **混合語言需使用 UnifiedCorrector**: 中英混合文本必須使用 `UnifiedCorrector`，避免語言誤匹配
2. **Tokenization 差異**: 中文字元級滑窗 vs 英文單字級 token，需正確選擇 Tokenizer
3. **Language Router 必要性**: 混合語言場景務必啟用語言路由，否則性能崩潰
4. **不要限制變體數量**: 使用所有音標去重後的變體，避免遺漏有效候選
5. **權重設定**: 地域詞 `weight: 0.0`，一般替換 `weight > 0` 需上下文判斷
6. **音標去重自動進行**: 自動過濾重複音標的別名（中文拼音/英文 IPA）
7. **歸一化固定為 True**: 所有別名一律轉換為標準詞，若不想轉換則不加入字典
8. **本工具不是全文糾錯**: 專注於專有名詞的語音相似替換，不處理語法或一般拼寫錯誤

## Development Roadmap

參考 `docs/MULTI_LANGUAGE_EXPANSION.md` 了解完整的多語言擴展計畫：

### Phase 1: 重構現有架構（1-2 週）
- [x] 定義 `PhoneticSystem` 抽象介面
- [x] 定義 `Tokenizer` 抽象介面
- [x] 實現 `LanguageRouter` 語言片段識別
- [x] 重構為 `UnifiedCorrector` 統一入口
- [x] 中文實現包裝為 `ChinesePhoneticSystem`
- [x] 英文實現為 `EnglishPhoneticSystem` (IPA-based)

### Phase 2: 擴展新語言支援（每種語言 3-5 天）
- [ ] 日文支援：假名/羅馬音轉換與模糊音規則
- [ ] 韓文支援：韓文拼音與收音混淆規則
- [ ] 其他語言：依需求優先級添加

### 關鍵挑戰
- **Tokenization 差異**: 字元流 vs 單字流需正確處理
- **模糊音規則**: 需要語言專家協助定義各語言規則
- **詞頻/語料依賴**: 英文同音詞判斷可能需要額外語料
- **Code-Switching**: 混合語言場景需要完善的語言路由機制

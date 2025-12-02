# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Chinese Text Corrector** - 中文文本校正工具包

通用的中文詞彙替換引擎，專注於提供校正引擎而非維護字典。使用者需自行提供專有名詞字典，工具會自動生成模糊音變體並進行智能文本校正。

**核心理念**:
- 工具只提供校正引擎，不維護任何預設字典
- 使用者維護符合業務領域的專有名詞字典
- 工具負責自動生成模糊音變體與智能替換

**適用場景**:
- ASR 語音識別後處理
- 地域詞彙轉換（中國 ↔ 台灣慣用詞）
- 縮寫擴展（口語簡稱 → 正式全稱）
- 錯別字修正

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
chinese_text_corrector/
├── core/                      # 核心拼音處理邏輯
│   ├── phonetic_config.py     # 拼音模糊音配置（聲母/韻母/特例音節）
│   └── phonetic_utils.py      # 拼音工具函數
├── dictionary/                # 詞典生成
│   └── generator.py           # 模糊音詞典生成器
└── correction/                # 文本校正
    └── corrector.py           # 主校正器（ChineseTextCorrector）
```

### Key Components

**1. PhoneticConfig** (`core/phonetic_config.py`)
- 定義所有拼音模糊音規則的配置類別
- 支援台灣國語特徵：n/l 不分、f/h 混淆、r/l 混淆、捲舌音混淆
- 包含聲母模糊群組、韻母模糊對應、特例音節映射
- 所有規則集中管理，便於維護和擴展

**2. PhoneticUtils** (`core/phonetic_utils.py`)
- 提供拼音處理的工具函數
- 關鍵方法：
  - `get_pinyin_string()`: 取得中文字串的拼音表示
  - `extract_initial_final()`: 拆解拼音為聲母和韻母
  - `are_fuzzy_similar()`: 判斷兩個拼音是否模糊相似

**3. FuzzyDictionaryGenerator** (`dictionary/generator.py`)
- 自動生成模糊音變體詞典
- 基於 PhoneticConfig 的規則產生所有可能的發音變體
- 支援聲母替換、韻母替換、特例音節對應

**4. ChineseTextCorrector** (`correction/corrector.py`)
- **主要入口類別**，提供文本校正功能
- **類方法工廠**: `from_terms()` - 自動生成別名的推薦使用方式
- **核心機制**:
  - 滑動視窗匹配算法
  - 上下文關鍵字加權（距離越近加分越多）
  - 拼音相似度計算（Levenshtein 距離）
  - 動態容錯率調整（2字詞 0.20 → 4+字詞 0.40）
  - 豁免清單避免誤改

### Critical Architecture Decisions

**拼音去重機制**:
- `from_terms()` 會自動過濾拼音重複的別名（類似 Set 行為）
- 使用 `_filter_aliases_by_pinyin()` 保留第一個出現的拼音
- 避免字典膨脹和重複匹配

**歸一化策略**:
- 內部固定 `use_canonical_normalization = True`
- 所有別名一律轉換為標準詞（正向）
- 若不想轉換，直接不加入字典即可

**變體數量**:
- 移除 `max_variants` 限制
- 拼音去重後通常只有 5-20 個變體
- 使用所有去重後的變體，避免遺漏有效候選

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

### Recommended: Auto-generate Aliases

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

### Advanced: Manual Alias Management

```python
from chinese_text_corrector import ChineseTextCorrector, FuzzyDictionaryGenerator

# 手動生成模糊音詞典
generator = FuzzyDictionaryGenerator()
fuzzy_dict = generator.generate_fuzzy_dictionary(["台北車站"])

# 手動建立校正器
corrector = ChineseTextCorrector({
    "台北車站": ["北車", "臺北車站"]
})
```

## Important Implementation Notes

### Phonetic Matching Algorithm

**拼音相似度計算流程**:
1. 特例音節匹配（優先，如 fa ↔ hua）
2. 韻母模糊匹配（in/ing, en/eng 等）
3. Levenshtein 編輯距離計算
4. 短詞聲母嚴格檢查（2字詞必須聲母匹配）

**容錯率動態調整**:
- 2 字詞: 0.20（必須非常準確）
- 3 字詞: 0.30
- 4+ 字詞: 0.40（寬容度最高）
- 英文混用: 0.45

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

- **README.md**: 完整使用說明和範例（中文）
- **auto_correct_examples.py**: 6 個完整範例展示不同使用方式
- **docs/DICTIONARY_ORGANIZATION.md**: 詞典分類管理建議
- **docs/DISTANCE_WEIGHTING_FEATURE.md**: 距離加權機制說明
- **docs/CHANGELOG.md**: 版本更新記錄

## Common Pitfalls

1. **不要限制變體數量**: 移除了 `max_variants` 參數，使用所有拼音去重後的變體
2. **權重設定**: 地域詞 `weight: 0.0`，ASR 錯誤 `weight > 0` 需上下文判斷
3. **拼音去重自動進行**: `from_terms()` 會自動過濾重複拼音的別名
4. **歸一化固定為 True**: 所有別名一律轉換為標準詞，若不想轉換則不加入字典

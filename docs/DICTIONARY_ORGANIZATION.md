# 詞典分類管理建議

## 概述

本文檔說明為什麼應該將詞典按類型分類管理，以及如何在不修改核心代碼的情況下實現靈活的詞典組織。

---

## 三種詞典類型

### 1. 替換字（地域慣用詞轉換）

**用途**: 不同地區的慣用詞互轉

**特性**:
- 來源詞是**正確的**，只是地域/習慣不同
- 需要**雙向索引**（台灣場景 vs 中國場景）
- 應該 **100% 轉換**（`weight: 0.0`）
- **不需要**拼音模糊匹配

**範例**:
```python
# 中國 → 台灣
"馬鈴薯": {"aliases": ["土豆"], "weight": 0.0}
"影片": {"aliases": ["視頻"], "weight": 0.0}
"鼠標": {"aliases": ["滑鼠"], "weight": 0.0}

# 台灣 → 中國（反過來）
"土豆": {"aliases": ["馬鈴薯"], "weight": 0.0}
"視頻": {"aliases": ["影片"], "weight": 0.0}
"滑鼠": {"aliases": ["鼠標"], "weight": 0.0}
```

### 2. 錯別字/ASR 錯誤修正

**用途**: 修正語音識別錯誤或錯別字

**特性**:
- 來源詞是**錯誤的**
- **單向修正**，永不反轉
- 需要**上下文判斷**（`weight > 0`）
- 需要**拼音模糊匹配**（台灣國語特徵：n/l, f/h, r/l 混淆）

**範例**:
```python
"牛奶": {"aliases": ["流奶"], "weight": 0.3}       # n/l 混淆
"然後": {"aliases": ["蘭後"], "weight": 0.3}       # n/l 混淆
"發揮": {"aliases": ["花揮"], "weight": 0.3}       # f/h 混淆
"阿斯匹靈": {"aliases": ["阿斯匹林"], "weight": 0.2}
```

### 3. 縮寫擴展

**用途**: 口語簡稱轉換為正式全稱

**特性**:
- 來源詞是**簡化的**但不算錯
- 可能**雙向**（口語用簡稱，書面用全稱）
- 需要**場景控制**（`use_canonical_normalization`）
- 常需要**上下文關鍵字**判斷

**範例**:
```python
"台北車站": {
    "aliases": ["北車"],
    "weight": 0.0
}

"永和豆漿": {
    "aliases": ["永豆", "勇豆"],
    "keywords": ["買", "吃", "喝", "宵夜"],
    "weight": 0.3
}

"勇者鬥惡龍": {
    "aliases": ["勇鬥", "永鬥"],
    "keywords": ["玩", "遊戲", "攻略"],
    "weight": 0.2
}
```

---

## 混在一起的問題

### 問題 1: 維護困難

```python
# ❌ 不好的做法：混合管理
"馬鈴薯": {
    "aliases": ["土豆", "馬齡薯", "馬零薯"],  # 地域詞 + 錯別字混在一起
    "weight": 0.3  # 這個權重給誰？
}
```

- "土豆"（地域詞）應該 `weight=0`，總是轉換
- "馬齡薯"（錯別字）應該 `weight>0`，需要上下文判斷
- **無法分別配置**

### 問題 2: 場景衝突

**場景 A：地域轉換**
- 只想轉換地域詞（土豆→馬鈴薯）
- 不想改動其他正確的詞

**場景 B：ASR 後處理**
- 想修正所有語音識別錯誤
- 不想做地域轉換（保持用戶原意）

**場景 C：正式文書**
- 只想擴展縮寫（北車→台北車站）
- 不改地域詞，不改其他內容

**混在一起 → 無法選擇性啟用**

### 問題 3: 未來擴展困難

- 想批量調整「所有地域詞的轉換方向」→ 做不到
- 想新增「專業術語標準化」→ 繼續混在一起
- 想單獨測試某種功能 → 無法隔離
- 多人協作時詞典越來越混亂

---

## 建議方案：漸進式拆分

### 階段 1: 詞典層面拆分（立即實施）

**核心思想**: 不修改代碼，只組織詞典檔案

#### 詞典檔案結構

```
chinese_corrector/
├── dictionaries/
│   ├── __init__.py
│   ├── asr_errors.py          # ASR 錯誤修正
│   ├── region_cn_to_tw.py     # 中國 → 台灣
│   ├── region_tw_to_cn.py     # 台灣 → 中國
│   ├── abbreviations.py       # 縮寫擴展
│   └── domain_medical.py      # 醫療領域術語（未來擴展）
```

#### 詞典內容範例

**`dictionaries/asr_errors.py`**:
```python
"""
ASR 錯誤修正詞典

用途：修正語音識別中的常見錯誤
特點：
- 台灣國語特徵（n/l, f/h, r/l 混淆）
- 需要上下文判斷 (weight > 0)
- 單向修正
"""

ASR_ERRORS = {
    # n/l 混淆
    "牛奶": {"aliases": ["流奶"], "weight": 0.3},
    "然後": {"aliases": ["蘭後"], "weight": 0.3},
    "能力": {"aliases": ["能立", "淩立"], "weight": 0.3},

    # f/h 混淆
    "發揮": {"aliases": ["花揮"], "weight": 0.3},
    "方法": {"aliases": ["航法"], "weight": 0.3},

    # 捲舌音混淆
    "日本": {"aliases": ["立本"], "weight": 0.3},
    "人": {"aliases": ["銀"], "weight": 0.4},

    # 其他常見錯誤
    "阿斯匹靈": {"aliases": ["阿斯匹林", "二四批林"], "weight": 0.2},
}
```

**`dictionaries/region_cn_to_tw.py`**:
```python
"""
地域詞轉換：中國 → 台灣

用途：將中國慣用詞轉換為台灣慣用詞
特點：
- 100% 轉換 (weight = 0)
- 不需要上下文判斷
- 精確匹配
"""

REGION_CN_TO_TW = {
    # 食物
    "馬鈴薯": {"aliases": ["土豆"], "weight": 0.0},
    "玉米": {"aliases": ["玉蜀黍"], "weight": 0.0},
    "番茄": {"aliases": ["西紅柿"], "weight": 0.0},

    # 科技/媒體
    "影片": {"aliases": ["視頻"], "weight": 0.0},
    "軟體": {"aliases": ["軟件"], "weight": 0.0},
    "網路": {"aliases": ["網絡"], "weight": 0.0},
    "鼠標": {"aliases": ["滑鼠"], "weight": 0.0},

    # 交通
    "出租車": {"aliases": ["計程車"], "weight": 0.0},
    "公交車": {"aliases": ["公車"], "weight": 0.0},
}
```

**`dictionaries/region_tw_to_cn.py`**:
```python
"""
地域詞轉換：台灣 → 中國

用途：將台灣慣用詞轉換為中國慣用詞
特點：
- 100% 轉換 (weight = 0)
- 與 region_cn_to_tw.py 方向相反
"""

REGION_TW_TO_CN = {
    # 食物
    "土豆": {"aliases": ["馬鈴薯"], "weight": 0.0},
    "玉蜀黍": {"aliases": ["玉米"], "weight": 0.0},
    "西紅柿": {"aliases": ["番茄"], "weight": 0.0},

    # 科技/媒體
    "視頻": {"aliases": ["影片"], "weight": 0.0},
    "軟件": {"aliases": ["軟體"], "weight": 0.0},
    "網絡": {"aliases": ["網路"], "weight": 0.0},
    "滑鼠": {"aliases": ["鼠標"], "weight": 0.0},

    # 交通
    "計程車": {"aliases": ["出租車"], "weight": 0.0},
    "公車": {"aliases": ["公交車"], "weight": 0.0},
}
```

**`dictionaries/abbreviations.py`**:
```python
"""
縮寫擴展詞典

用途：將口語簡稱擴展為正式全稱
特點：
- 常需要上下文關鍵字
- 可能有多個專有名詞共用同一簡稱
"""

ABBREVIATIONS = {
    # 地點/機構
    "台北車站": {
        "aliases": ["北車"],
        "weight": 0.0
    },

    # 餐飲品牌（需要上下文）
    "永和豆漿": {
        "aliases": ["永豆", "勇豆"],
        "keywords": ["買", "吃", "喝", "宵夜", "早餐"],
        "weight": 0.3
    },

    # 遊戲（需要上下文）
    "勇者鬥惡龍": {
        "aliases": ["勇鬥", "永鬥"],
        "keywords": ["玩", "遊戲", "電動", "攻略"],
        "weight": 0.2
    },
}
```

#### 使用方式

```python
from chinese_text_corrector import ChineseTextCorrector
from dictionaries.asr_errors import ASR_ERRORS
from dictionaries.region_cn_to_tw import REGION_CN_TO_TW
from dictionaries.region_tw_to_cn import REGION_TW_TO_CN
from dictionaries.abbreviations import ABBREVIATIONS

# 場景 1：ASR 後處理（台灣場景）
asr_corrector = ChineseTextCorrector.from_terms({
    **ASR_ERRORS,
    **ABBREVIATIONS,
})

text = "我在北車買了流奶,蘭後回家"
result = asr_corrector.correct(text)
# 結果: "我在台北車站買了牛奶,然後回家"


# 場景 2：地域轉換（中國 → 台灣）
region_corrector = ChineseTextCorrector.from_terms(REGION_CN_TO_TW)

text = "我用土豆做了視頻"
result = region_corrector.correct(text)
# 結果: "我用馬鈴薯做了影片"


# 場景 3：反向地域轉換（台灣 → 中國）
region_corrector_reverse = ChineseTextCorrector.from_terms(REGION_TW_TO_CN)

text = "我用馬鈴薯做了影片"
result = region_corrector_reverse.correct(text)
# 結果: "我用土豆做了視頻"


# 場景 4：全功能（ASR + 地域 + 縮寫）
full_corrector = ChineseTextCorrector.from_terms({
    **ASR_ERRORS,
    **REGION_CN_TO_TW,
    **ABBREVIATIONS,
})

text = "我在北車買了土豆和流奶,蘭後回家"
result = full_corrector.correct(text)
# 結果: "我在台北車站買了馬鈴薯和牛奶,然後回家"


# 場景 5：只擴展縮寫（正式文書場景）
formal_corrector = ChineseTextCorrector.from_terms(ABBREVIATIONS)

text = "請在北車站前等候"
result = formal_corrector.correct(text)
# 結果: "請在台北車站站前等候"
```

#### 優點

✅ **立即可用**：不需要修改核心代碼
✅ **詞典清晰**：每個檔案職責單一，易於維護
✅ **靈活組合**：使用 `**dict` 語法自由組合
✅ **容易測試**：可以單獨載入測試每種詞典
✅ **文檔完整**：每個檔案頂部說明用途和特點
✅ **團隊協作**：不同人負責不同類型詞典

### 階段 2: 增加類型標記（有需求時）

如果未來需要更細緻的控制，可以在核心代碼中增加類型系統：

```python
# 擴展 from_terms() 支援類型標記
corrector = ChineseTextCorrector.from_terms(
    {
        "馬鈴薯": {
            "aliases": ["土豆"],
            "type": "region",  # 新增類型標記
            "weight": 0.0
        },
        "牛奶": {
            "aliases": ["流奶"],
            "type": "asr_error",
            "weight": 0.3
        },
    },
    enabled_types=["region"]  # 選擇性啟用類型
)
```

**何時需要**：
- 詞典規模 > 1000 條
- 需要動態開關某些類型
- 需要統計不同類型的修正率

### 階段 3: 多引擎架構（成熟後）

如果系統變得非常複雜，可以考慮獨立的處理引擎：

```python
from chinese_text_corrector.pipeline import CorrectionPipeline
from chinese_text_corrector.engines import (
    ASRCorrector,
    RegionConverter,
    AbbreviationExpander
)

pipeline = CorrectionPipeline([
    ASRCorrector(ASR_ERRORS),
    RegionConverter(REGION_CN_TO_TW, direction="cn2tw"),
    AbbreviationExpander(ABBREVIATIONS),
])

result = pipeline.process(text)
```

**何時需要**：
- 不同類型需要完全不同的處理邏輯
- 需要精細控制處理順序和優先級
- 需要性能優化（並行處理）

---

## 實施建議

### 立即實施（階段 1）

1. **建立 `dictionaries/` 目錄**
2. **將現有詞典拆分到不同檔案**：
   - `asr_errors.py`
   - `region_cn_to_tw.py`
   - `region_tw_to_cn.py`
   - `abbreviations.py`
3. **每個檔案加上清晰的文檔說明**
4. **更新使用範例**

### 觀察評估（階段 2）

等待以下情況再實施：
- 詞典規模變大（> 1000 條）
- 出現類型管理痛點
- 需要動態控制功能

### 謹慎推進（階段 3）

只在以下情況考慮：
- 系統非常成熟穩定
- 有明確的性能/功能需求
- 團隊有充足資源

---

## 總結

**核心原則**：
- ✅ 詞典分類管理是必要的
- ✅ 從檔案組織開始，而非立即重構代碼
- ✅ 漸進式演進，避免過度設計
- ✅ 保持系統簡潔性和靈活性

**立即行動**：
把詞典按類型拆成不同檔案，使用時靈活組合。

**耐心等待**：
等真正遇到痛點再升級架構，不要過度設計。

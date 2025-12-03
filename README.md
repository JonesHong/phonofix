# Phonetic Substitution Engine (多語言語音相似替換引擎)

基於語音相似度的多語言專有名詞替換工具。支援 ASR/LLM 後處理、地域慣用詞轉換、縮寫擴展等多種應用場景。
特別針對 **中英混合 (Code-Switching)** 場景進行了優化。

## 💡 核心理念

**本工具專注於提供替換引擎，不維護任何預設字典。**

> ⚠️ **注意**：這不是全文糾錯工具，而是專注於「專有名詞的語音相似替換」。

使用者需自行提供專有名詞字典，本工具會：
1. **自動生成語音變體**：
   - **中文**：自動產生台式口音/模糊音變體（如「北車」→「台北車站」）
   - **英文**：基於 IPA (國際音標) 計算語音相似度（如 "Ten so floor" → "TensorFlow"）
2. **智能詞彙替換**：自動識別語言片段，將語音相似的詞彙替換為您指定的標準專有名詞

**適用場景**：
- **ASR 語音識別後處理**：修正語音轉文字產生的專有名詞錯誤（含中英夾雜）
- **LLM 輸出後處理**：修正大型語言模型因專有名詞罕見而選錯的同音字/近音字
- **專有名詞標準化**：將口語/誤寫的術語還原為正式名稱
- **地域詞彙轉換**：中國慣用詞 ↔ 台灣慣用詞

## 📚 功能特色

### 1. 多語言支援
- **Unified Corrector**: 統一入口，自動處理中英混合文本
- **英文語音替換**: 
    - 使用 IPA (International Phonetic Alphabet) 進行語音相似度比對
    - 支援 Acronyms (縮寫) 的語音還原
- **中文語音替換**:
    - 使用拼音進行模糊音比對
    - 支援台灣國語特有的發音混淆模式

### 2. 自動語音變體生成
- **中文**：自動產生台式口音/模糊音變體
  - 捲舌音 (z/zh, c/ch, s/sh)
  - n/l 不分 (台灣國語)
  - r/l 混淆、f/h 混淆
  - 韻母模糊 (in/ing, en/eng, ue/ie 等)
- **英文**：自動產生 ASR/LLM 常見錯誤變體
  - 音節分割變體 ("TensorFlow" → "Ten so floor")
  - 縮寫展開變體 ("AWS" → "A W S")

### 3. 智能替換引擎
- 滑動視窗匹配算法
- 上下文關鍵字加權機制
- 動態容錯率調整

## 📦 安裝

### 使用 uv (推薦)

```bash
# 安裝 uv (如果尚未安裝)
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安裝專案依賴
uv sync

# 安裝開發依賴
uv sync --dev

# 執行範例
uv run python examples/chinese_examples.py

# 執行測試
uv run pytest
```

### 使用 pip

```bash
# 安裝依賴
pip install -r requirements.txt
```

## 🧪 開發

```bash
# 執行測試
uv run pytest

# 執行測試並顯示覆蓋率
uv run pytest --cov

# 程式碼格式化
uv run ruff format .

# 程式碼檢查
uv run ruff check .

# 型別檢查
uv run mypy chinese_text_corrector multi_language_corrector
```

## 🚀 快速開始

### 1. 混合語言替換 (Unified Corrector)

```python
from multi_language_corrector.correction.unified_corrector import UnifiedCorrector

# 定義您的專有名詞字典
terms = [
    "台北車站",      # 中文詞
    "TensorFlow",   # 英文專有名詞
    "Python"
]

# 初始化替換器
corrector = UnifiedCorrector(terms)

# ASR 輸出後處理
asr_text = "我在北車用Pyton寫Ten so floor的code"
result = corrector.correct(asr_text)
print(result)
# 輸出: "我在台北車站用Python寫TensorFlow的code"

# LLM 輸出後處理 (LLM 可能因罕見詞而選錯同音字)
llm_text = "我在北車用派森寫code"  # LLM 把 Python 音譯成「派森」
result = corrector.correct(llm_text)
print(result)
# 輸出: "我在台北車站用Python寫code"
```

### 2. 中文專用 (Legacy Mode)
pip install pypinyin Levenshtein Pinyin2Hanzi hanziconv
```

## 🚀 快速開始

**重要提醒**：本工具不提供預設字典，您需要根據自己的業務場景建立專有名詞清單。

### 推薦使用方式 - 自動生成別名

使用 `ChineseTextCorrector.from_terms()` 類方法，**只需提供您的專有名詞清單**，工具會自動生成所有可能的模糊音變體並進行拼音去重：

#### 最簡格式 - 僅提供關鍵字列表

```python
from chinese_text_corrector import ChineseTextCorrector

# 步驟 1: 提供您的專有名詞清單（這是您需要維護的字典）
my_terms = ["台北車站", "牛奶", "發揮"]

# 步驟 2: 工具自動生成所有可能的模糊音變體
# 例如："台北車站" → 自動生成 "北車"、"臺北車站" 等變體
corrector = ChineseTextCorrector.from_terms(my_terms)

# 步驟 3: 自動將接近音的詞轉換為正確的專有名詞
result = corrector.correct("我在北車買了流奶,他花揮了才能")
# 結果: '我在台北車站買了牛奶,他發揮了才能'
# 說明: "北車" → "台北車站", "流奶" → "牛奶", "花揮" → "發揮"
```

#### 完整格式 - 別名 + 關鍵字 + 權重

當同一個別名可能對應多個專有名詞時，可使用上下文關鍵字和權重來提高準確度：

```python
# 您的專有名詞字典（根據您的業務場景維護）
my_business_terms = {
    "永和豆漿": {
        "aliases": ["永豆", "勇豆"],  # 手動提供常見別名或錯音
        "keywords": ["吃", "喝", "買", "宵夜"],  # 上下文關鍵字幫助判斷
        "weight": 0.3  # 匹配權重
    },
    "勇者鬥惡龍": {
        "aliases": ["勇鬥", "永鬥"],  # 同音但不同意義
        "keywords": ["玩", "遊戲", "攻略"],
        "weight": 0.2
    }
}

corrector = ChineseTextCorrector.from_terms(my_business_terms)

result = corrector.correct("我去買勇鬥當宵夜")
# 結果: '我去買永和豆漿當宵夜'
# 說明: 因為命中「買」和「宵夜」關鍵字，判斷為「永和豆漿」而非「勇者鬥惡龍」
```

**優點**:
- ✅ 自動生成模糊音變體，無需手動維護
- ✅ 自動過濾拼音重複的別名（類似 Set 行為）
- ✅ 支援多種輸入格式，使用靈活
- ✅ 減少配置工作量，專注於核心詞彙

### 進階使用 - 手動管理別名

如果需要完全控制別名，可以手動建立校正器：

```python
from multi_language_corrector.languages.chinese import ChineseCorrector, ChineseFuzzyGenerator

# 1. 生成模糊音詞典
generator = ChineseFuzzyGenerator()
fuzzy_dict = generator.generate_variants(["台北車站", "阿斯匹靈"])

# 2. 建立校正器
corrector = ChineseCorrector.from_terms({
    "台北車站": ["北車", "臺北車站"],
    "阿斯匹靈": ["阿斯匹林", "二四批林"]
})

# 3. 校正文本
result = corrector.correct("我在北車等你,醫生開了二四批林給我")
# '我在台北車站等你,醫生開了阿斯匹靈給我'
```

### 進階功能

#### 上下文關鍵字校正

```python
from multi_language_corrector.languages.chinese import ChineseCorrector

# 使用上下文關鍵字提高準確度
corrector = ChineseCorrector.from_terms({
    "永和豆漿": {
        "aliases": ["永豆"],
        "keywords": ["吃", "喝", "買", "宵夜", "早餐"]
    },
    "勇者鬥惡龍": {
        "aliases": ["勇鬥"],
        "keywords": ["玩", "遊戲", "電動", "攻略"]
    }
})

result = corrector.correct("我去買勇鬥當宵夜")  # 命中「買」→ 永和豆漿
result = corrector.correct("這款永豆的攻略很難找")  # 命中「攻略」→ 勇者鬥惡龍
```

#### 權重系統

```python
# 使用權重提高優先級
corrector = ChineseTextCorrector({
    "恩典": {
        "aliases": ["安點"],
        "weight": 0.3  # 高權重,優先匹配
    },
    "上帝": {
        "aliases": ["上帝"],
        "weight": 0.1  # 低權重
    }
})
```

#### 豁免清單

```python
# 設定豁免清單,避免特定詞被修正
corrector = ChineseTextCorrector(
    term_mapping={
        "台北車站": ["北車"]
    },
    exclusions=["北側", "南側"]  # 這些詞不會被修正
)

result = corrector.correct("我在北側等你")  # 不會修正為「台北車站側」
```

## 📁 專案結構

```
chinese_text_corrector/
├── __init__.py                    # 主入口
├── core/
│   ├── __init__.py
│   ├── phonetic_config.py         # 拼音配置 (聲母/韻母/特例音節)
│   └── phonetic_utils.py          # 拼音工具函數
├── dictionary/
│   ├── __init__.py
│   └── generator.py               # 模糊詞典生成器
└── correction/
    ├── __init__.py
    └── corrector.py               # 文本校正器
```

## 🎯 使用場景

以下範例展示不同業務場景下，如何建立您自己的專有名詞字典：

### 1. ASR 語音識別後處理

**問題**：語音識別常將專有名詞聽錯成發音相近的一般詞彙

```python
# 您的專有名詞字典
terms = ["牛奶", "發揮", "然後", "TensorFlow", "Kubernetes"]

corrector = UnifiedCorrector(terms)

# ASR 輸出：專有名詞被聽錯
asr_output = "我買了流奶，蘭後用Ten so floor訓練模型"
result = corrector.correct(asr_output)
# 結果: "我買了牛奶，然後用TensorFlow訓練模型"
```

### 2. LLM 輸出後處理

**問題**：LLM 可能因專有名詞罕見而選擇發音相近的常用字

```python
# 您的專有名詞字典
terms = ["耶穌", "恩典", "PyTorch", "NumPy"]

corrector = UnifiedCorrector(terms)

# LLM 輸出：罕見專有名詞被替換成同音常用字
llm_output = "耶穌的恩點很大，我用排炬和南派做機器學習"
result = corrector.correct(llm_output)
# 結果: "耶穌的恩典很大，我用PyTorch和NumPy做機器學習"
```

### 3. 地域慣用詞轉換

**您的字典**：維護地域對照表（例如：中國 ↔ 台灣慣用詞）

```python
# 您的地域詞彙字典
region_terms = {
    "馬鈴薯": {"aliases": ["土豆"], "weight": 0.0},
    "影片": {"aliases": ["視頻"], "weight": 0.0}
}

corrector = ChineseTextCorrector.from_terms(region_terms)

result = corrector.correct("我用土豆做了視頻")
# 結果: "我用馬鈴薯做了影片"
```

### 4. 縮寫擴展

**您的字典**：維護常用縮寫與全稱對照表

```python
# 您的縮寫字典
abbreviation_terms = {
    "台北車站": {"aliases": ["北車"], "weight": 0.0}
}

corrector = ChineseTextCorrector.from_terms(abbreviation_terms)

result = corrector.correct("我在北車等你")
# 結果: "我在台北車站等你"
```

### 5. 專業術語標準化

**您的字典**：維護業務領域的專業術語

```python
# 您的醫療術語字典
medical_terms = {
    "阿斯匹靈": {"aliases": ["阿斯匹林", "二四批林"], "weight": 0.2}
}

corrector = ChineseTextCorrector.from_terms(medical_terms)

result = corrector.correct("醫生開了二四批林給我")
# 結果: "醫生開了阿斯匹靈給我"
```

## 📖 完整範例

請參考 `auto_correct_examples.py` 檔案,包含 6 個完整範例:

1. 最簡格式 - 僅提供關鍵字列表
2. 提供部分別名 (拼音去重)
3. 完整格式 (別名 + 關鍵字 + 權重)
4. 混合格式 (多種配置方式)
5. 使用豁免清單
6. 綜合範例 (多種配置混用)

```bash
# 執行範例
python auto_correct_examples.py
```

## 🔧 技術細節

### 拼音模糊音規則

#### 聲母模糊群組
- `z_group`: z, zh (捲舌音)
- `c_group`: c, ch (捲舌音)
- `s_group`: s, sh (捲舌音)
- `n_l_group`: n, l (n/l 不分)
- `r_l_group`: r, l (r/l 混淆)
- `f_h_group`: f, h (f/h 混淆)

#### 韻母模糊對應
- `in` ⇄ `ing`
- `en` ⇄ `eng`
- `an` ⇄ `ang`
- `ian` ⇄ `iang`
- `uan` ⇄ `uang`
- `uan` ⇄ `an`
- `ong` ⇄ `eng`, `on`
- `uo` ⇄ `o`, `ou`
- `ue` ⇄ `ie`

#### 特例音節映射
- `fa` ⇄ `hua` (發/花)
- `xue` ⇄ `xie` (學/鞋)
- `ran` ⇄ `lan`, `yan` (然/蘭/嚴)
- 更多請參考 `phonetic_config.py`

### 替換算法流程

1. **建立保護遮罩**: 標記豁免詞位置
2. **滑動視窗掃描**: 遍歷所有可能的詞長
3. **語音相似度計算**:
   - 中文：拼音比對（特例音節 → 韻母模糊 → 編輯距離）
   - 英文：IPA 音標比對（Levenshtein 編輯距離）
4. **聲母/首音嚴格檢查**: 短詞必須首音匹配
5. **上下文加分**: 檢查關鍵字出現
6. **權重計分**: 最終分數 = 錯誤率 - 權重 - 上下文獎勵
7. **衝突解決**: 依分數排序,選擇最佳不重疊候選
8. **文字替換**: 從後向前替換,避免索引錯位

### 動態容錯率

- 2 字詞: 0.20 (必須非常準確)
- 3 字詞: 0.30
- 4+ 字詞: 0.40 (寬容度最高)
- 英文混用: 0.45 (容錯較高)

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request!

## 📄 授權

MIT License

## 👨‍💻 作者

Your Name

## 🙏 致謝

感謝以下專案:
- [pypinyin](https://github.com/mozillazg/python-pinyin)
- [python-Levenshtein](https://github.com/maxbachmann/Levenshtein)
- [Pinyin2Hanzi](https://github.com/letiantian/Pinyin2Hanzi)
- [hanziconv](https://github.com/berniey/hanziconv)

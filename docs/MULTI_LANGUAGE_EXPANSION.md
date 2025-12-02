# Multi-Language Expansion Analysis

## 🎯 核心問題分析

**需求本質**：將「拼音模糊匹配」的概念推廣到其他語言的「發音模糊匹配」，但必須承認不同語系在「分詞粒度」「容錯邏輯」「錯誤型態」上完全不同，不能期待單一套件直接沿用。

當前架構高度依賴中文拼音特性：
- 聲母/韻母分離
- 台灣國語特定模糊音規則（n/l 不分、捲舌音等）
- `pypinyin` 庫的中文拼音轉換

**現實限制**：
- 語音模糊規則無法跨語言通用（英語 Homophones 與中文聲母錯位完全不同）
- 容錯率需依語言調整，甚至同語言內也要依詞頻、詞形變化調節
- 真實 ASR 修正離不開語境、詞頻與語料庫特徵
- 多語混合文本需要 Language Routing 或至少 per-token 語種判斷

**核心理念仍不變**：只提供糾正器，不維護字典 → 使用者提供專有名詞字典，工具做模糊處理和文本校正，但我們需要額外的語言判斷與語料支援來達到實用水準。

---

## 💡 推薦方案：語言抽象層 + 插件式設計

### 架構重組

```
chinese_text_corrector/  →  multi_language_corrector/
├── core/
│   ├── phonetic_interface.py        # 抽象介面
│   ├── tokenizer_interface.py       # 語言特定 tokenization（字元流 vs 單字流）
│   ├── corrector_base.py            # 通用校正邏輯（語言無關、但依賴 token stream）
│   └── matcher.py                   # 滑動視窗、上下文加權（需感知 token 邊界）
├── router/
│   └── language_router.py           # 多語混合文本 routing（可插拔）
├── languages/                       # 語言特定實現
│   ├── chinese/
│   │   ├── tokenizer.py             # 字元級滑窗
│   │   ├── phonetic_impl.py         # 中文拼音實現
│   │   └── config.py                # 現有 PhoneticConfig
│   ├── english/
│   │   ├── tokenizer.py             # 單字級 token 流（依空白/標點）
│   │   ├── phonetic_impl.py         # 英文音素實現（IPA + Homophone 辨識）
│   │   └── lexicon.py               # 詞頻/語料提供者
│   ├── japanese/
│   │   └── phonetic_impl.py         # 日文假名/羅馬音實現
│   └── korean/
│       └── phonetic_impl.py         # 韓文拼音實現
└── correction/
    └── unified_corrector.py         # 統一入口（可根據語言路由 call 對應系統）
```

> ✅ **重點調整**：滑動視窗 matcher 雖然概念語言無關，但實作必須透過 `Tokenizer` 層處理字元流 vs 單字流，否則英文/韓文的詞邊界會被錯誤切割。Language Router 則讓同一句混合語言時可以分段交給不同 phonetic system 分別處理。

---

## 🔧 技術實現要點

### 1️⃣ 定義語言抽象介面

```python
# core/phonetic_interface.py
from abc import ABC, abstractmethod
from typing import List, Tuple

class PhoneticSystem(ABC):
    """語言發音系統抽象介面"""

    @abstractmethod
    def to_phonetic(self, text: str) -> str:
        """將文本轉為音標表示（如拼音、音素、假名）"""
        pass

    @abstractmethod
    def are_fuzzy_similar(self, phonetic1: str, phonetic2: str) -> bool:
        """判斷兩個音標是否模糊相似"""
        pass

    @abstractmethod
    def get_tolerance(self, word_length: int) -> float:
        """根據詞長取得容錯率"""
        pass
```

### 2️⃣ 中文實現範例

```python
# languages/chinese/phonetic_impl.py
from core.phonetic_interface import PhoneticSystem
from core.phonetic_utils import PhoneticUtils

class ChinesePhoneticSystem(PhoneticSystem):
    def __init__(self):
        self.utils = PhoneticUtils()

    def to_phonetic(self, text: str) -> str:
        return self.utils.get_pinyin_string(text)

    def are_fuzzy_similar(self, pinyin1: str, pinyin2: str) -> bool:
        return self.utils.are_fuzzy_similar(pinyin1, pinyin2)

    def get_tolerance(self, word_length: int) -> float:
        # 現有邏輯
        if word_length == 2: return 0.20
        elif word_length == 3: return 0.30
        return 0.40
```

### 3️⃣ 英文實現範例（需結合 IPA + Homophone 辨識）

```python
# languages/english/phonetic_impl.py
import epitran
from spellchecker import SpellChecker

class EnglishPhoneticSystem(PhoneticSystem):
    def __init__(self, lexicon=None):
        self.epi = epitran.Epitran('eng-Latn')  # 英文 → IPA
        self.spell = SpellChecker() if lexicon is None else lexicon

    def to_phonetic(self, text: str) -> str:
        return self.epi.transliterate(text.lower())

    def are_fuzzy_similar(self, ipa1: str, ipa2: str) -> bool:
        # 單靠 IPA 會把 right / write 視為 identical，需要加上詞頻+同音詞列表
        if ipa1 == ipa2:
            return True
        return self._check_english_fuzzy_rules(ipa1, ipa2)

    def resolve_homophones(self, word: str, context: str) -> str:
        """結合詞頻、語境打分決定同音詞正解"""
        candidates = self.spell.candidates(word)
        return self._rank_by_context(candidates, context)

    def get_tolerance(self, word_length: int) -> float:
        # 英文 ASR 錯誤常牽涉同音詞，需要更寬容並依照詞頻調整
        base = 0.35 if word_length <= 4 else 0.45
        return self._adjust_by_frequency(base)
```

> ⚠️ **重要**：英文 ASR 錯誤更偏向「同音詞／詞形變化」而非單純音節差異，實務上必須同時使用 IPA + 詞頻／語境重新打分，否則 `right`、`write` 會因為 IPA 相同而無法區分。

### 4️⃣ 日文實現範例

```python
# languages/japanese/phonetic_impl.py
import pykakasi  # 漢字 → 假名/羅馬音

class JapanesePhoneticSystem(PhoneticSystem):
    def __init__(self):
        self.kks = pykakasi.kakasi()

    def to_phonetic(self, text: str) -> str:
        # 轉為羅馬音（romaji）
        result = self.kks.convert(text)
        return ''.join([item['hepburn'] for item in result])

    def are_fuzzy_similar(self, romaji1: str, romaji2: str) -> bool:
        # 日文常見模糊音：
        # - づ(zu) ↔ ず(zu)
        # - じ(ji) ↔ ぢ(di → ji)
        # - を(wo) ↔ お(o)
        return self._check_japanese_fuzzy_rules(romaji1, romaji2)

    def get_tolerance(self, word_length: int) -> float:
        # 日文可能需要不同的容錯邏輯
        return 0.30 if word_length <= 3 else 0.40
```

---

## 📊 修改幅度評估

### **小幅度修改** ✅
- 保留 80% 現有代碼（滑動視窗、上下文加權、豁免清單）
- 只需重構拼音處理部分（約 20% 代碼）

### **需要調整的部分**

| 模組 | 修改幅度 | 說明 |
|------|---------|------|
| `ChineseTextCorrector` | **中度** | 重命名為 `UnifiedCorrector`，接受 `PhoneticSystem` 參數 |
| `FuzzyDictionaryGenerator` | **小** | 改為呼叫 `PhoneticSystem.to_phonetic()` |
| `PhoneticUtils` | **中度** | 拆分為抽象介面 + 中文實現 |
| 滑動視窗 (matcher.py) | **中度** | 需改寫為依賴 `Tokenizer` 介面（支援字元/單字切分） |
| 上下文加權 | **小** | 邏輯通用，但需適配 Token 索引 |

---

## 🚀 實作步驟建議

### Phase 1: 重構現有架構（1-2 週）
1. 定義 `PhoneticSystem` 抽象介面
2. 將現有中文邏輯包裝為 `ChinesePhoneticSystem`
3. 重構 `ChineseTextCorrector` 為 `UnifiedCorrector`
4. 確保向後兼容（保留 `ChineseTextCorrector` 作為別名）

### Phase 2: 添加新語言支援（每種語言 3-5 天）
1. 研究該語言的模糊音規則（需要語言專家協助）
2. 實現對應的 `PhoneticSystem`
3. 編寫單元測試驗證模糊匹配準確度

---

## ⚠️ 關鍵挑戰

### 1️⃣ Tokenization Granularity
- 中文/日文屬字元流，可沿用目前滑動視窗實作。
- 英文/韓文必須依據空白、語素或 BPE 分詞，否則滑窗會在單字中央切斷造成大量誤判。
- 建議新增 `Tokenizer` 介面，語言實作需回傳 token list + 字符索引映射，以便 matcher 正確定位。

### 2️⃣ 模糊音規則需要專業知識
- **中文**：已有台灣國語經驗 ✅
- **英文**：需要了解 L2 學習者常見錯誤（如 /θ/ → /s/）
- **日文**：需要了解濁音、促音、長音混淆
- **韓文**：需要了解收音(받침)混淆規則

**建議**：與該語言的母語者或語言學家合作定義規則

### 3️⃣ 依賴庫選擇

| 語言 | 推薦庫 | 功能 |
|------|--------|------|
| 中文 | `pypinyin` | 漢字 → 拼音（已使用） |
| 英文 | `epitran` + 詞頻庫 (symspellpy/pyspellchecker) | 文字 → IPA + Homophone disambiguation |
| 日文 | `pykakasi` / `cutlet` | 漢字 → 假名/羅馬音 |
| 韓文 | `hangul-romanize` | 韓文 → 羅馬拼音 |

### 4️⃣ 容錯率與語料依賴

不同語言可能需要不同的容錯率策略：
- **中文**：2字詞嚴格（0.20）→ 4+字詞寬鬆（0.40）
- **英文**：同音詞多，需結合詞頻與語境調整；若無語料支援，IPA 匹配的意義有限
- **日文**：平假名/片假名混用可能需要特殊處理
- **韓文**：音節組合複雜，可能需要更精細的規則

此外，若不維護任何詞頻/語料，英文與 code-switch 場景的實用度將大幅下降，建議最少提供「可選 lexicon」或讓使用者載入自有語料。

### 5️⃣ Code-Switching / Language Routing
- 現實 ASR 文本常見「我在用 Python 寫 code」。
- UnifiedCorrector 需要能在同一輸入內切換語言模組：
    - 先進行語言偵測 / token 分段
    - 針對中文片段用 ChinesePhoneticSystem，英文片段用 EnglishPhoneticSystem
- 若路由失敗，中文模組會誤處理英文詞（或反之），導致性能崩潰。
- 建議在 `router/language_router.py` 中支援多種策略（rule-based、fastText、Whisper diarization 等）。

---

## 🎖️ 可行性評估

### ✅ 高度可行

**優勢**：
- 核心邏輯（滑動視窗、上下文加權）**完全語言無關**
- 只需要抽象出「拼音處理」部分
- 修改幅度約 20-30%，風險可控
- 架構設計已經很優秀，易於擴展

### 🏗️ 建議優先順序

1. **先重構中文部分**，導入 Tokenizer + Phonetic interface，確保架構可擴展
2. **建立 Language Router PoC**，即使是簡單 regex/fastText，也能避免中文模組誤處理英文詞
3. **添加英文支援**（IPA + 詞頻/同音詞資料，必要時整合 symspellpy）
4. **日文/韓文**根據需求優先級添加

### 📚 需要準備的資源

- [ ] 各語言模糊音規則文獻（含 tokenization 指南）
- [ ] 語言專家 review（或使用語言學研究論文）
- [ ] 各語言的測試數據集（含混合語句）
- [ ] 各語言依賴庫的評估和測試
- [ ] 可選詞頻/語料資源（供英文等語言做 Homophone 判斷）

---

## 💬 下一步行動建議

### 建議路徑

1. **先做 PoC**：用英文實現一個最小原型，驗證架構可行性
2. **保持向後兼容**：現有中文用戶無痛升級
3. **文檔先行**：為每種語言的模糊音規則撰寫詳細文檔

### 可選任務

- [ ] 設計具體的抽象介面
- [ ] 實現英文 PoC
- [ ] 規劃詳細的重構步驟
- [ ] 建立語言特定的測試案例

---

## 📝 附註

**核心價值不變**：
- 工具只提供校正引擎，不維護任何預設字典
- 使用者維護符合業務領域的專有名詞字典
- 工具負責自動生成模糊音變體與智能替換

**擴展後價值**：
- 支援多語言場景（混合語言文本、多國業務）
- 保持統一的 API 設計和使用體驗
- 各語言共享核心算法（滑動視窗、上下文加權）

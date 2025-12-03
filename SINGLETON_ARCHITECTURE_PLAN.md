# 單例架構重構計畫書

## 📋 目錄

1. [現狀分析](#現狀分析)
2. [目標架構](#目標架構)
3. [三層設計詳解](#三層設計詳解)
4. [影響範圍評估](#影響範圍評估)
5. [詳細實作計畫](#詳細實作計畫)
6. [遷移指南](#遷移指南)
7. [時程估算](#時程估算)

---

## 現狀分析

### 現有架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                         使用者程式碼                              │
│                              │                                   │
│    corrector = UnifiedCorrector(term_dict)  ← 每次都要 2 秒初始化  │
│    result = corrector.correct(text)                              │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      UnifiedCorrector                            │
│  ┌────────────────────┐  ┌────────────────────┐                 │
│  │  ChineseCorrector  │  │  EnglishCorrector  │                 │
│  │  ├─ phonetic_impl  │  │  ├─ phonetic_impl  │ ← espeak-ng 初始化│
│  │  ├─ tokenizer      │  │  ├─ tokenizer      │                 │
│  │  ├─ term_mapping   │  │  ├─ term_mapping   │                 │
│  │  └─ fuzzy_gen      │  │  └─ fuzzy_gen      │                 │
│  └────────────────────┘  └────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

### 現有問題

| 問題 | 影響 |
|------|------|
| espeak-ng 每次初始化 ~2秒 | 建立多個 Corrector 時累積延遲 |
| PhoneticSystem 每次重建 | 浪費記憶體，重複建立相同物件 |
| Tokenizer 每次重建 | 浪費記憶體 |
| IPA 快取是全域的，但 Corrector 不是 | 設計不一致 |
| 無法共享已計算的 alias IPA | 如果兩個 Corrector 有相同詞彙，會重複計算 |

---

## 目標架構

### 三層設計圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              使用者程式碼                                 │
│                                                                          │
│  # 應用程式啟動時 (一次)                                                  │
│  engine = CorrectorEngine()                                              │
│                                                                          │
│  # 需要時快速建立 Corrector (毫秒級)                                      │
│  corrector_a = engine.create_corrector(terms_a, keywords_a, ...)        │
│  corrector_b = engine.create_corrector(terms_b, keywords_b, ...)        │
│                                                                          │
│  # 使用方式不變                                                           │
│  result = corrector_a.correct(text)                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────────┐
│                                   ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              Layer 1: PhoneticBackend (全域單例)                  │    │
│  │  ┌─────────────────────────┐  ┌─────────────────────────────┐   │    │
│  │  │   EnglishBackend        │  │   ChineseBackend            │   │    │
│  │  │   ├─ espeak-ng 初始化   │  │   ├─ pypinyin 初始化        │   │    │
│  │  │   ├─ IPA 快取 (LRU)     │  │   ├─ 拼音快取 (LRU)         │   │    │
│  │  │   └─ 基礎 G2P 函數      │  │   └─ 基礎拼音函數           │   │    │
│  │  └─────────────────────────┘  └─────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│                                   ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              Layer 2: CorrectorEngine (可多個，共享 Backend)      │    │
│  │  ┌─────────────────────────┐  ┌─────────────────────────────┐   │    │
│  │  │   EnglishEngine         │  │   ChineseEngine             │   │    │
│  │  │   ├─ ref → Backend      │  │   ├─ ref → Backend          │   │    │
│  │  │   ├─ PhoneticSystem     │  │   ├─ PhoneticSystem         │   │    │
│  │  │   ├─ Tokenizer          │  │   ├─ Tokenizer              │   │    │
│  │  │   ├─ FuzzyGenerator     │  │   ├─ FuzzyGenerator         │   │    │
│  │  │   └─ 配置 (tolerance)   │  │   └─ 配置 (tolerance)       │   │    │
│  │  └─────────────────────────┘  └─────────────────────────────┘   │    │
│  │                                                                  │    │
│  │                    UnifiedEngine (整合中英文)                     │    │
│  │                    ├─ EnglishEngine                              │    │
│  │                    ├─ ChineseEngine                              │    │
│  │                    └─ LanguageRouter                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│                                   ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              Layer 3: Corrector (輕量實例，由 Engine 建立)        │    │
│  │  ┌─────────────────────────┐  ┌─────────────────────────────┐   │    │
│  │  │   EnglishCorrector      │  │   ChineseCorrector          │   │    │
│  │  │   ├─ ref → Engine       │  │   ├─ ref → Engine           │   │    │
│  │  │   ├─ term_mapping       │  │   ├─ term_mapping           │   │    │
│  │  │   ├─ keywords           │  │   ├─ keywords               │   │    │
│  │  │   ├─ exclusions         │  │   ├─ exclusions             │   │    │
│  │  │   └─ alias_phonetics    │  │   └─ search_index           │   │    │
│  │  └─────────────────────────┘  └─────────────────────────────┘   │    │
│  │                                                                  │    │
│  │                    UnifiedCorrector                              │    │
│  │                    ├─ ref → UnifiedEngine                        │    │
│  │                    ├─ EnglishCorrector                           │    │
│  │                    └─ ChineseCorrector                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│                              multi_language_corrector/                   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 層級職責

| 層級 | 名稱 | 生命週期 | 職責 |
|------|------|----------|------|
| **Layer 1** | PhoneticBackend | 全域單例 (進程生命週期) | 初始化外部引擎 (espeak-ng, pypinyin)、管理快取 |
| **Layer 2** | CorrectorEngine | 應用程式生命週期 | 持有 PhoneticSystem、Tokenizer、FuzzyGenerator、配置 |
| **Layer 3** | Corrector | 短期/按需 | 只處理詞彙映射、keywords、exclusions、執行 correct() |

---

## 三層設計詳解

### Layer 1: PhoneticBackend (單例)

```python
# multi_language_corrector/backend/english_backend.py

class EnglishPhoneticBackend:
    """
    英文語音後端 (單例)
    
    職責:
    - 初始化 espeak-ng (只做一次)
    - 提供 IPA 轉換函數
    - 管理 IPA 快取
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化 espeak-ng (~2秒，只執行一次)"""
        _setup_espeak_library()
        # 觸發 espeak-ng 載入
        self._phonemize = _get_phonemize()
        self._cache = {}  # 或繼續用 @lru_cache
    
    def to_ipa(self, text: str) -> str:
        """轉換為 IPA (使用快取)"""
        ...
    
    def get_cache_stats(self) -> dict:
        """取得快取統計"""
        ...


# 便捷函數
def get_english_backend() -> EnglishPhoneticBackend:
    return EnglishPhoneticBackend()
```

### Layer 2: CorrectorEngine

```python
# multi_language_corrector/engine/english_engine.py

class EnglishEngine:
    """
    英文修正引擎
    
    職責:
    - 持有共享的 PhoneticSystem、Tokenizer、FuzzyGenerator
    - 提供工廠方法建立 Corrector
    - 可自訂配置 (tolerance, max_window_size 等)
    """
    
    def __init__(self, config: EnglishPhoneticConfig = None):
        # 取得單例 backend
        self._backend = get_english_backend()
        
        # 建立共享元件
        self.phonetic = EnglishPhoneticSystem(backend=self._backend)
        self.tokenizer = EnglishTokenizer()
        self.fuzzy_generator = EnglishFuzzyGenerator()
        self.config = config or EnglishPhoneticConfig()
    
    def create_corrector(
        self,
        term_dict: Union[List[str], Dict],
        keywords: Dict[str, List[str]] = None,
        exclusions: Dict[str, List[str]] = None,
    ) -> "EnglishCorrector":
        """
        建立輕量 Corrector 實例 (毫秒級)
        
        Args:
            term_dict: 詞彙配置
            keywords: 關鍵字映射
            exclusions: 排除詞映射
            
        Returns:
            EnglishCorrector: 可立即使用的修正器
        """
        return EnglishCorrector(
            engine=self,
            term_dict=term_dict,
            keywords=keywords,
            exclusions=exclusions,
        )
```

### Layer 3: Corrector (輕量)

```python
# multi_language_corrector/correction/english_corrector.py

class EnglishCorrector:
    """
    英文修正器 (輕量實例)
    
    職責:
    - 持有詞彙映射 (term_mapping)
    - 持有 keywords/exclusions
    - 執行 correct() 邏輯
    - 使用 Engine 提供的共享元件
    """
    
    def __init__(
        self,
        engine: EnglishEngine,
        term_dict: Union[List[str], Dict],
        keywords: Dict[str, List[str]] = None,
        exclusions: Dict[str, List[str]] = None,
    ):
        self._engine = engine
        
        # 只處理詞彙映射 (輕量操作)
        self.term_mapping = self._build_term_mapping(term_dict)
        self.keywords = keywords or {}
        self.exclusions = exclusions or {}
        
        # 預計算 alias IPA (使用 Engine 的 phonetic)
        self.alias_phonetics = self._compute_alias_phonetics()
    
    def correct(self, text: str, full_context: str = None) -> str:
        """執行修正 (使用 Engine 的共享元件)"""
        # 使用 self._engine.tokenizer
        # 使用 self._engine.phonetic
        # 邏輯與現有相同
        ...
```

---

## 影響範圍評估

### 需要修改的檔案

```
multi_language_corrector/
├── backend/                          [新增] Layer 1
│   ├── __init__.py
│   ├── base.py                       # PhoneticBackend 抽象基類
│   ├── english_backend.py            # EnglishPhoneticBackend 單例
│   └── chinese_backend.py            # ChinesePhoneticBackend 單例
│
├── engine/                           [新增] Layer 2
│   ├── __init__.py
│   ├── base.py                       # CorrectorEngine 抽象基類
│   ├── english_engine.py             # EnglishEngine
│   ├── chinese_engine.py             # ChineseEngine
│   └── unified_engine.py             # UnifiedEngine (整合)
│
├── core/
│   ├── phonetic_interface.py         [修改] 新增 backend 參數
│   └── tokenizer_interface.py        [不變]
│
├── correction/
│   ├── corrector.py                  [重寫] 輕量版 Corrector
│   └── unified_corrector.py          [重寫] 使用 UnifiedEngine
│
├── languages/
│   ├── english/
│   │   ├── phonetic_impl.py          [重構] 拆分為 backend + phonetic_system
│   │   ├── corrector.py              [重寫] 輕量版
│   │   ├── tokenizer.py              [不變]
│   │   ├── fuzzy_generator.py        [不變]
│   │   └── config.py                 [不變]
│   │
│   └── chinese/
│       ├── phonetic_impl.py          [重構] 拆分為 backend + phonetic_system
│       ├── corrector.py              [重寫] 輕量版
│       ├── tokenizer.py              [不變]
│       ├── fuzzy_generator.py        [不變]
│       └── config.py                 [不變]
│
├── router/
│   └── language_router.py            [不變]
│
└── __init__.py                       [修改] 更新公開 API
```

### 影響統計

| 類別 | 檔案數 | 說明 |
|------|--------|------|
| 新增 | 8 | backend/, engine/ 資料夾 |
| 重寫 | 4 | 各語言的 corrector.py, unified_corrector.py |
| 重構 | 2 | 各語言的 phonetic_impl.py |
| 修改 | 2 | core/phonetic_interface.py, __init__.py |
| 不變 | 8 | tokenizer, fuzzy_generator, config, router |

---

## 詳細實作計畫

### Phase 1: 建立 Backend 層 (Layer 1)

**目標**: 將 espeak-ng/pypinyin 初始化邏輯抽取為單例

#### 1.1 建立 backend 抽象基類

```python
# backend/base.py
class PhoneticBackend(ABC):
    @abstractmethod
    def to_phonetic(self, text: str) -> str: ...
    
    @abstractmethod
    def is_initialized(self) -> bool: ...
    
    @abstractmethod
    def get_cache_stats(self) -> dict: ...
```

#### 1.2 實作 EnglishPhoneticBackend

```python
# backend/english_backend.py
- 從 languages/english/phonetic_impl.py 遷移:
  - _setup_espeak_library()
  - _get_phonemize()
  - cached_ipa_convert()
  - warmup_ipa_cache() → initialize()
- 實作單例模式
```

#### 1.3 實作 ChinesePhoneticBackend

```python
# backend/chinese_backend.py
- 從 languages/chinese/corrector.py 遷移:
  - cached_get_pinyin_string()
  - cached_get_initials()
- 實作單例模式
```

### Phase 2: 建立 Engine 層 (Layer 2)

**目標**: 建立持有共享元件的 Engine 類別

#### 2.1 建立 Engine 抽象基類

```python
# engine/base.py
class CorrectorEngine(ABC):
    @abstractmethod
    def create_corrector(self, term_dict, **kwargs) -> "Corrector": ...
```

#### 2.2 實作 EnglishEngine

```python
# engine/english_engine.py
- 持有: EnglishPhoneticSystem, EnglishTokenizer, EnglishFuzzyGenerator
- 實作: create_corrector()
```

#### 2.3 實作 ChineseEngine

```python
# engine/chinese_engine.py
- 持有: ChinesePhoneticUtils, ChineseTokenizer, ChineseFuzzyGenerator
- 實作: create_corrector()
```

#### 2.4 實作 UnifiedEngine

```python
# engine/unified_engine.py
- 持有: EnglishEngine, ChineseEngine, LanguageRouter
- 實作: create_corrector() - 自動分類詞彙並建立子 Corrector
```

### Phase 3: 重構 Corrector 層 (Layer 3)

**目標**: 將 Corrector 改為輕量實例

#### 3.1 重構 EnglishCorrector

```python
# languages/english/corrector.py
- 移除: warmup_ipa_cache() 呼叫
- 移除: 直接持有 PhoneticSystem, Tokenizer
- 改為: 透過 Engine 存取共享元件
- 保留: term_mapping, keywords, exclusions, correct() 邏輯
```

#### 3.2 重構 ChineseCorrector

```python
# languages/chinese/corrector.py
- 移除: 直接持有 utils, generator
- 改為: 透過 Engine 存取共享元件
- 保留: search_index, correct() 邏輯
```

#### 3.3 重構 UnifiedCorrector

```python
# correction/unified_corrector.py
- 移除: 直接建立 ChineseCorrector, EnglishCorrector
- 改為: 透過 UnifiedEngine.create_corrector() 建立
```

### Phase 4: 更新公開 API

#### 4.1 更新 __init__.py

```python
# multi_language_corrector/__init__.py

# 主要 API (推薦使用)
from .engine import (
    UnifiedEngine,
    EnglishEngine, 
    ChineseEngine,
)

# Corrector (由 Engine 建立，通常不直接 import)
from .correction import (
    UnifiedCorrector,
    EnglishCorrector,
    ChineseCorrector,
)

# Backend (進階用途)
from .backend import (
    get_english_backend,
    get_chinese_backend,
)
```

### Phase 5: 更新測試與範例

#### 5.1 更新測試

```python
# tests/test_english_corrector.py
- 測試 Engine 建立
- 測試多個 Corrector 共享 Engine
- 驗證第二個 Corrector 建立時間 < 100ms

# tests/test_singleton.py (新增)
- 測試 Backend 單例
- 測試跨執行緒安全
```

#### 5.2 更新範例

```python
# examples/mixed_language_examples.py
- 使用 UnifiedEngine 取代直接建立 UnifiedCorrector
```

---

## 遷移指南

### 舊版 API (不再支援)

```python
# ❌ 舊版：每次建立都要初始化
corrector1 = UnifiedCorrector({"Python": ["Pyton"]})  # ~2秒
corrector2 = UnifiedCorrector({"AWS": ["a w s"]})     # ~2秒
```

### 新版 API

```python
# ✅ 新版：Engine 初始化一次，Corrector 快速建立
from multi_language_corrector import UnifiedEngine

# 應用啟動時
engine = UnifiedEngine()  # ~2秒 (只需一次)

# 之後隨時建立 Corrector
corrector1 = engine.create_corrector({"Python": ["Pyton"]})  # ~10ms
corrector2 = engine.create_corrector({"AWS": ["a w s"]})     # ~10ms

# 使用方式不變
result = corrector1.correct("I use Pyton")
```

### 單語言使用

```python
from multi_language_corrector import EnglishEngine

engine = EnglishEngine()

corrector = engine.create_corrector({
    "Python": ["Pyton", "Pyson"],
    "EKG": {
        "aliases": ["1kg"],
        "keywords": ["device"],
        "exclusions": ["weight"],
    }
})

result = corrector.correct("I use Pyton")
```

---

## 時程估算

| Phase | 任務 | 預估時間 | 優先級 |
|-------|------|----------|--------|
| 1 | Backend 層 | 2-3 小時 | P0 |
| 2 | Engine 層 | 2-3 小時 | P0 |
| 3 | Corrector 重構 | 3-4 小時 | P0 |
| 4 | 公開 API | 1 小時 | P0 |
| 5 | 測試與範例 | 2-3 小時 | P1 |
| - | **總計** | **10-14 小時** | - |

---

## 預期效益

| 指標 | 舊版 | 新版 | 改善 |
|------|------|------|------|
| 建立第 1 個 Corrector | ~2秒 | ~2秒 | - |
| 建立第 2 個 Corrector | ~2秒 | ~10ms | **200x 加速** |
| 建立第 N 個 Corrector | ~2秒 | ~10ms | **200x 加速** |
| 記憶體 (多 Corrector) | N * 完整實例 | 1 Engine + N 輕量實例 | **大幅減少** |
| 程式碼清晰度 | 職責混雜 | 三層分離 | **顯著提升** |

---

## 附錄: 類別關係圖

```
┌─────────────────┐
│ PhoneticBackend │ (單例)
│   (ABC)         │
└────────┬────────┘
         │ implements
    ┌────┴────┐
    │         │
┌───▼───┐ ┌───▼───┐
│English│ │Chinese│
│Backend│ │Backend│
└───┬───┘ └───┬───┘
    │         │
    │ used by │
    │         │
┌───▼─────────▼───┐
│ CorrectorEngine │
│     (ABC)       │
└────────┬────────┘
         │ implements
    ┌────┼────┐
    │    │    │
┌───▼──┐ │ ┌──▼───┐
│Eng   │ │ │Chi   │
│Engine│ │ │Engine│
└───┬──┘ │ └──┬───┘
    │    │    │
    │ ┌──▼──┐ │
    │ │Uni  │ │
    │ │Engi │ │
    │ └──┬──┘ │
    │    │    │
    └────┼────┘
         │ creates
         ▼
┌─────────────────┐
│    Corrector    │ (輕量)
│     (ABC)       │
└────────┬────────┘
         │ implements
    ┌────┼────┐
    │    │    │
┌───▼──┐ │ ┌──▼───┐
│ Eng  │ │ │ Chi  │
│Corr  │ │ │Corr  │
└──────┘ │ └──────┘
      ┌──▼──┐
      │ Uni │
      │Corr │
      └─────┘
```

---

**文件版本**: v1.0  
**建立日期**: 2025-12-03  
**狀態**: 待實作

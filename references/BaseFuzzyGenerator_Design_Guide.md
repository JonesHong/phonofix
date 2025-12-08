# BaseFuzzyGenerator 設計指南

## 概述

`BaseFuzzyGenerator` 是模糊變體生成器的抽象基類，定義了統一的變體生成流程和接口，強制三語言（中文/英文/日文）架構一致。

## 核心設計理念

### 1. 模板方法模式 (Template Method Pattern)

抽象基類實現了統一的變體生成流程（模板方法），子類只需實現語言特定的抽象方法：

```
統一流程（模板方法）：
1. 文字 → 語音 key (phonetic_transform)
2. 語音 key → 模糊語音 key 變體 (generate_phonetic_variants)
3. 模糊語音 key → 文字 (phonetic_to_text)
4. 基於語音 key 去重 (deduplicate_by_phonetic)
5. 評分與排序 (score_and_rank)
```

### 2. 統一數據結構

所有語言使用統一的 `PhoneticVariant` 數據結構：

```python
@dataclass
class PhoneticVariant:
    text: str               # 顯示文字（使用者看到的）
    phonetic_key: str       # 語音 key（Pinyin/IPA/Romaji）
    score: float = 1.0      # 置信度評分 (0.0-1.0)
    source: VariantSource   # 變體來源類型
    metadata: Dict = {}     # 額外元數據
```

### 3. 語言無關性

核心算法完全語言無關，透過抽象方法適配不同語言：

- **中文**: Pinyin 系統
- **英文**: IPA 系統
- **日文**: Romaji 系統
- **未來**: 韓文 Hangul、泰文等

## 架構圖

```
BaseFuzzyGenerator (抽象基類)
├── ChineseFuzzyGenerator (Pinyin 實現)
├── EnglishFuzzyGenerator (IPA 實現)
├── JapaneseFuzzyGenerator (Romaji 實現)
└── KoreanFuzzyGenerator (Hangul 實現, 未來)
```

## 實現指南

### 步驟 1: 繼承抽象基類

```python
from phonofix.core.fuzzy_generator_interface import BaseFuzzyGenerator, PhoneticVariant, VariantSource

class MyLanguageFuzzyGenerator(BaseFuzzyGenerator):
    def __init__(self, config=None):
        super().__init__(config)
        # 初始化語言特定資源
        self.phonetic_system = MyPhoneticSystem()
```

### 步驟 2: 實現必要的抽象方法

#### 2.1 `phonetic_transform()` - 文字 → 語音 key

將文字轉換為語音表示（Pinyin/IPA/Romaji）。

**範例（中文 Pinyin）**:
```python
def phonetic_transform(self, term: str) -> str:
    """文字 → Pinyin"""
    # 台北 → "taibei"
    return self.phonetic_system.to_phonetic(term)
```

**範例（英文 IPA）**:
```python
def phonetic_transform(self, term: str) -> str:
    """文字 → IPA"""
    # Python → "ˈpaɪθɑn"
    return self.phonetic_system.to_phonetic(term)
```

**範例（日文 Romaji）**:
```python
def phonetic_transform(self, term: str) -> str:
    """文字 → Romaji"""
    # 東京 → "toukyou"
    return self.phonetic_system.to_phonetic(term)
```

#### 2.2 `generate_phonetic_variants()` - 語音 key → 模糊語音 key 變體

應用語音混淆規則生成變體。

**範例（中文 Pinyin）**:
```python
def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
    """Pinyin → 模糊 Pinyin 變體"""
    variants = {phonetic_key}

    # 應用聲母混淆 (z/zh, c/ch, s/sh)
    for s1, s2 in self.config.FUZZY_INITIALS:
        if s1 in phonetic_key:
            variants.add(phonetic_key.replace(s1, s2))

    # 應用韻母混淆 (in/ing, en/eng)
    for f1, f2 in self.config.FUZZY_FINALS:
        if f1 in phonetic_key:
            variants.add(phonetic_key.replace(f1, f2))

    return list(variants)
```

**範例（英文 IPA）**:
```python
def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
    """IPA → 模糊 IPA 變體"""
    variants = {phonetic_key}

    # 應用清濁音混淆 (p/b, t/d, k/g)
    for v1, v2 in self.config.IPA_VOICING_CONFUSIONS:
        if v1 in phonetic_key:
            variants.add(phonetic_key.replace(v1, v2))

    # 應用相似音混淆 (θ/f, l/r)
    for p1, p2 in self.config.IPA_SIMILAR_PHONE_CONFUSIONS:
        if p1 in phonetic_key:
            variants.add(phonetic_key.replace(p1, p2))

    return list(variants)
```

#### 2.3 `phonetic_to_text()` - 語音 key → 文字

將語音 key 轉換回文字表示。

**範例（中文 Pinyin）**:
```python
def phonetic_to_text(self, phonetic_key: str) -> str:
    """Pinyin → 文字（直接使用 Pinyin）"""
    # taibei → "taibei"
    return phonetic_key
```

**範例（英文 IPA）**:
```python
def phonetic_to_text(self, phonetic_key: str) -> str:
    """IPA → 拼寫（反向查找）"""
    # ˈpɪθɑn → "pithon"
    spellings = self.ipa_mapper.ipa_to_spellings(phonetic_key, max_results=1)
    return spellings[0] if spellings else phonetic_key
```

**範例（日文 Romaji）**:
```python
def phonetic_to_text(self, phonetic_key: str) -> str:
    """Romaji → 假名（轉換回來）"""
    # toukyou → "とうきょう"
    return self.romaji_to_kana(phonetic_key)
```

### 步驟 3: 實現可選方法（如需要）

#### 3.1 `apply_hardcoded_rules()` - 硬編碼規則

用於處理特殊情況（如縮寫、複合詞、常見錯誤模式）。

```python
def apply_hardcoded_rules(self, term: str) -> List[str]:
    """應用硬編碼規則"""
    variants = []

    # 處理縮寫
    if term.isupper() and len(term) <= 5:
        # "API" → ["a p i", "A P I"]
        spaced = ' '.join(list(term.lower()))
        variants.append(spaced)

    # 處理複合詞
    if self._is_compound_word(term):
        # "TensorFlow" → ["tensor flow", "ten so floor"]
        variants.extend(self._split_compound(term))

    return variants
```

#### 3.2 `calculate_score()` - 自定義評分

如果需要語言特定的評分邏輯，可以覆蓋此方法。

```python
def calculate_score(self, base_key: str, variant_key: str) -> float:
    """計算置信度評分"""
    # 基於編輯距離
    import Levenshtein
    dist = Levenshtein.distance(base_key, variant_key)
    max_len = max(len(base_key), len(variant_key))

    if max_len == 0:
        return 1.0

    # 語言特定調整
    similarity = 1.0 - (dist / max_len)

    # 例如：對聲母混淆給予更高評分
    if self._is_initial_confusion(base_key, variant_key):
        similarity *= 1.1

    return max(0.0, min(1.0, similarity))
```

### 步驟 4: 使用生成器

```python
# 創建生成器
generator = MyLanguageFuzzyGenerator()

# 生成變體
variants = generator.generate_variants("測試詞彙", max_variants=10)

# 遍歷變體
for variant in variants:
    print(f"{variant.text} (評分: {variant.score:.2f}, 來源: {variant.source.value})")
```

## 完整範例：英文 IPA 生成器

```python
from phonofix.core.fuzzy_generator_interface import (
    BaseFuzzyGenerator, PhoneticVariant, VariantSource
)
from phonofix.languages.english.phonetic_impl import EnglishPhoneticSystem
from phonofix.languages.english.ipa_to_spelling import IPAToSpellingMapper
from phonofix.languages.english.config import EnglishPhoneticConfig

class EnglishFuzzyGenerator(BaseFuzzyGenerator):
    """英文 IPA 模糊變體生成器"""

    def __init__(self, config=None):
        super().__init__(config or EnglishPhoneticConfig)
        self.phonetic = EnglishPhoneticSystem()
        self.ipa_mapper = IPAToSpellingMapper(config=self.config)

    def phonetic_transform(self, term: str) -> str:
        """文字 → IPA"""
        return self.phonetic.to_phonetic(term)

    def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
        """IPA → 模糊 IPA 變體"""
        variants = {phonetic_key}

        # 清濁音混淆
        for s1, s2 in self.config.IPA_VOICING_CONFUSIONS:
            if s1 in phonetic_key:
                variants.add(phonetic_key.replace(s1, s2))

        # 相似音混淆
        for p1, p2 in self.config.IPA_SIMILAR_PHONE_CONFUSIONS:
            if p1 in phonetic_key:
                variants.add(phonetic_key.replace(p1, p2))

        return list(variants)

    def phonetic_to_text(self, phonetic_key: str) -> str:
        """IPA → 拼寫"""
        spellings = self.ipa_mapper.ipa_to_spellings(phonetic_key, max_results=1)
        return spellings[0] if spellings else phonetic_key

    def apply_hardcoded_rules(self, term: str) -> List[str]:
        """硬編碼規則"""
        variants = []

        # 縮寫處理
        if term.isupper() and len(term) <= 5:
            variants.append(' '.join(list(term.lower())))

        return variants
```

## 數據結構說明

### PhoneticVariant

```python
@dataclass
class PhoneticVariant:
    text: str               # 顯示文字
    phonetic_key: str       # 語音 key
    score: float = 1.0      # 置信度評分
    source: VariantSource   # 來源類型
    metadata: Dict = {}     # 元數據
```

**使用範例**:
```python
variant = PhoneticVariant(
    text="pithon",
    phonetic_key="ˈpɪθɑn",
    score=0.92,
    source=VariantSource.PHONETIC_FUZZY,
    metadata={"rule": "vowel_length", "edit_distance": 1}
)
```

### VariantSource

```python
class VariantSource(Enum):
    PHONETIC_FUZZY = "phonetic_fuzzy"    # 語音模糊規則
    HARDCODED_PATTERN = "hardcoded"      # 硬編碼模式
    PHRASE_RULE = "phrase_rule"          # 整詞規則
    ROMANIZATION = "romanization"        # 羅馬化變體
```

## 驗收標準檢查清單

### Task 6.1: 設計抽象基類

- ✅ **抽象基類定義清晰**
  - `BaseFuzzyGenerator` 定義了完整的接口
  - 三個抽象方法：`phonetic_transform`, `generate_phonetic_variants`, `phonetic_to_text`
  - 兩個可選方法：`apply_hardcoded_rules`, `calculate_score`

- ✅ **PhoneticVariant 數據結構完整**
  - 包含所有必要欄位：text, phonetic_key, score, source, metadata
  - 實現驗證邏輯（`__post_init__`）
  - 提供清晰的文檔和範例

- ✅ **模板方法實現統一流程**
  - `generate_variants()` 實現完整的 5 步驟流程
  - 語音維度生成
  - 硬編碼規則補充
  - 基於語音 key 去重
  - 過濾原詞
  - 評分與排序

- ✅ **文檔註釋詳盡**
  - 每個方法都有完整的 docstring
  - 包含參數說明、返回值說明、範例代碼
  - 提供使用指南和設計文檔

## 測試覆蓋

### 單元測試 (tests/test_fuzzy_generator_base.py)

- ✅ PhoneticVariant 數據結構測試 (4 個測試)
- ✅ VariantSource 枚舉測試 (1 個測試)
- ✅ BaseFuzzyGenerator 功能測試 (7 個測試)
- ✅ 硬編碼規則測試 (2 個測試)
- ✅ 便捷函數測試 (1 個測試)
- ✅ 邊界情況測試 (3 個測試)
- ✅ 降級機制測試 (1 個測試)

**總計**: 19 個測試，全部通過 ✅

## 未來擴展

### 新語言支援

只需實現三個抽象方法即可支援新語言：

```python
class KoreanFuzzyGenerator(BaseFuzzyGenerator):
    def phonetic_transform(self, term: str) -> str:
        # 韓文 → Hangul 音素
        pass

    def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
        # Hangul 音素混淆規則
        pass

    def phonetic_to_text(self, phonetic_key: str) -> str:
        # Hangul → 韓文
        pass
```

### 進階功能

1. **自定義評分算法**: 覆蓋 `calculate_score()` 方法
2. **特殊規則處理**: 覆蓋 `apply_hardcoded_rules()` 方法
3. **元數據追蹤**: 在 `metadata` 中添加自定義資訊
4. **評分調整**: 基於來源類型調整評分權重

## 總結

`BaseFuzzyGenerator` 提供了：

1. **統一接口**: 所有語言使用相同的 API
2. **模板方法**: 核心流程語言無關，易於擴展
3. **數據結構**: 統一的 PhoneticVariant 格式
4. **可擴展性**: 輕鬆添加新語言支援
5. **完整測試**: 19 個單元測試確保正確性

這為後續的中文、英文、日文模組重構奠定了堅實基礎。

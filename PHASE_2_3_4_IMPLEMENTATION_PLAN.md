# 📋 Phase 2-4 實施詳細計劃

> **基於**：COMPREHENSIVE_FUZZY_ANALYSIS.md
> **創建日期**：2025-12-08
> **Phase 1 完成狀態**：✅ 4個任務全部完成
> **預估總工時**：3-4週

---

## ✅ Phase 1 完成總結

**完成日期**：2025-12-08
**完成任務**：
- ✅ Task 1: 修復中文延遲導入bug (5分鐘)
- ✅ Task 2: 添加中文笛卡爾積上限 (3小時)
- ✅ Task 3: 修復英文排序穩定性 (3小時)
- ✅ Task 4: 實現日文語音key正規化 (1天)

**成果**：
- 修復了1個真實bug（延遲導入）
- 防止中文長詞卡死（笛卡爾積爆炸）
- 確保英文輸出確定性（穩定排序）
- 實現日文假名層級長音/促音正規化

---

## 🎯 Phase 2: 英文 IPA 重構（1-2週）

### 📌 核心目標

**將英文模組從「硬編碼規則」轉換為「基於IPA的語音維度生成」**

**當前問題**：
- ❌ Docstring聲稱 "從IPA音標反推"，但實際未實現
- ❌ 僅使用硬編碼規則（ASR_SPLIT_PATTERNS, SPELLING_PATTERNS）
- ❌ 無法泛化到新詞（如 "Ollama", "LangChain"）
- ❌ 違背「語音維度」核心理念（符合度僅33%）

**目標架構**：
```
Term → IPA → Fuzzy IPA Variants → Possible Spellings → Deduplication
```

---

### 📅 詳細任務分解

#### Task 5.1: 建立 IPA 音素模糊規則系統（2天）

**文件**：`src/phonofix/languages/english/config.py`

**任務描述**：
1. 研究常見 ASR 音素混淆模式
2. 定義 IPA 模糊規則配置
3. 實現音素替換邏輯

**新增配置項**：
```python
# src/phonofix/languages/english/config.py

class EnglishPhoneticConfig:
    """
    英文語音配置（基於 IPA）
    """

    # IPA 清濁音混淆
    IPA_VOICING_CONFUSIONS = [
        ('p', 'b'),   # pit ↔ bit
        ('t', 'd'),   # ten ↔ den
        ('k', 'ɡ'),   # cap ↔ gap
        ('f', 'v'),   # fan ↔ van
        ('s', 'z'),   # seal ↔ zeal
        ('θ', 'ð'),   # think ↔ this
        ('ʃ', 'ʒ'),   # mesh ↔ measure
    ]

    # IPA 長短元音混淆
    IPA_VOWEL_LENGTH_CONFUSIONS = [
        ('iː', 'ɪ'),  # sheep ↔ ship
        ('uː', 'ʊ'),  # pool ↔ pull
        ('ɔː', 'ɒ'),  # bought ↔ bot (UK)
        ('ɑː', 'æ'),  # bath ↔ bat (UK vs US)
    ]

    # IPA 相似音素混淆
    IPA_SIMILAR_PHONE_CONFUSIONS = [
        ('θ', 'f'),   # think → fink
        ('ð', 'v'),   # this → vis
        ('r', 'l'),   # rice ↔ lice (L2 speakers)
        ('n', 'm'),   # 鼻音混淆
        ('ŋ', 'n'),   # sing ↔ sin
    ]

    # IPA 音節簡化規則
    IPA_REDUCTION_RULES = [
        ('ə', ''),    # schwa deletion
        ('t̬', 'd'),   # flapping (water → wader)
        ('kw', 'k'),  # 音節簡化
    ]
```

**驗收標準**：
- [ ] 配置文件包含至少 20 條音素規則
- [ ] 規則涵蓋清濁音、長短音、相似音、簡化音
- [ ] 每條規則有實際範例註釋

---

#### Task 5.2: 實現 IPA 變體生成器（3天）

**文件**：`src/phonofix/languages/english/fuzzy_generator.py`

**任務描述**：
1. 添加 `_generate_ipa_fuzzy_variants()` 方法
2. 應用音素規則生成變體
3. 實現 Levenshtein 距離過濾

**新增方法**：
```python
class EnglishFuzzyGenerator:

    def _generate_ipa_fuzzy_variants(self, ipa: str) -> List[str]:
        """
        基於 IPA 音素規則生成模糊變體

        Args:
            ipa: IPA 音標字串（如 "ˈpaɪθɑn"）

        Returns:
            List[str]: IPA 變體列表
        """
        variants = {ipa}

        # 1. 應用清濁音混淆
        for s1, s2 in self.config.IPA_VOICING_CONFUSIONS:
            if s1 in ipa:
                variants.add(ipa.replace(s1, s2))
            if s2 in ipa:
                variants.add(ipa.replace(s2, s1))

        # 2. 應用長短元音混淆
        for long_v, short_v in self.config.IPA_VOWEL_LENGTH_CONFUSIONS:
            if long_v in ipa:
                variants.add(ipa.replace(long_v, short_v))
            if short_v in ipa:
                variants.add(ipa.replace(short_v, long_v))

        # 3. 應用相似音素混淆
        for p1, p2 in self.config.IPA_SIMILAR_PHONE_CONFUSIONS:
            if p1 in ipa:
                variants.add(ipa.replace(p1, p2))
            if p2 in ipa:
                variants.add(ipa.replace(p2, p1))

        # 4. 應用音節簡化
        for full, reduced in self.config.IPA_REDUCTION_RULES:
            if full in ipa:
                variants.add(ipa.replace(full, reduced))

        return list(variants)
```

**驗收標準**：
- [ ] 能為單個 IPA 生成 5-20 個變體
- [ ] 變體覆蓋所有配置的規則類型
- [ ] 通過單元測試（如 "ˈpaɪθɑn" → "ˈpaɪfɑn", "ˈbaɪθɑn" 等）

---

#### Task 5.3: 實現 IPA → 拼寫反查（4天）⭐

**文件**：`src/phonofix/languages/english/ipa_to_spelling.py`（新建）

**任務描述**：
1. 整合 CMU Pronouncing Dictionary
2. 實現 IPA → 拼寫映射
3. 處理一音多字情況

**新增模組**：
```python
# src/phonofix/languages/english/ipa_to_spelling.py

from typing import List, Dict
import re

class IPAToSpellingMapper:
    """
    IPA 音標到拼寫的反向映射

    使用策略：
    1. CMU Pronouncing Dictionary（主要）
    2. 音素→字母規則映射（補充）
    """

    def __init__(self):
        self._cmu_dict = self._load_cmu_dict()
        self._ipa_to_grapheme_rules = self._build_ipa_grapheme_rules()

    def _load_cmu_dict(self) -> Dict[str, List[str]]:
        """
        載入 CMU 發音字典

        Returns:
            Dict[IPA, List[spelling]]: IPA → 可能拼寫列表
        """
        # TODO: 載入 CMUdict，轉換為 IPA 索引
        # 使用 eng_to_ipa 或 phonemizer
        return {}

    def _build_ipa_grapheme_rules(self) -> Dict[str, List[str]]:
        """
        建立 IPA 音素 → 字母組合的規則

        Returns:
            Dict[IPA, List[grapheme]]: 音素 → 可能字母組合
        """
        return {
            'θ': ['th'],
            'ð': ['th'],
            'ʃ': ['sh', 'ti', 'ci'],
            'ʒ': ['s', 'si', 'zi'],
            'tʃ': ['ch', 'tch'],
            'dʒ': ['j', 'g', 'dge'],
            'ŋ': ['ng', 'n'],
            'iː': ['ee', 'ea', 'e', 'ie'],
            'eɪ': ['ay', 'ai', 'a_e', 'ey'],
            # ... 更多規則
        }

    def ipa_to_spellings(self, ipa: str, max_results: int = 10) -> List[str]:
        """
        將 IPA 轉換為可能的拼寫

        Args:
            ipa: IPA 音標
            max_results: 最多返回幾個拼寫

        Returns:
            List[str]: 可能的拼寫列表
        """
        spellings = []

        # 1. 從 CMU 字典查詢
        if ipa in self._cmu_dict:
            spellings.extend(self._cmu_dict[ipa][:max_results])

        # 2. 使用音素→字母規則生成
        if len(spellings) < max_results:
            rule_based = self._apply_grapheme_rules(ipa)
            spellings.extend(rule_based[:max_results - len(spellings)])

        return spellings[:max_results]

    def _apply_grapheme_rules(self, ipa: str) -> List[str]:
        """應用音素→字母規則"""
        # 簡化實現：逐個音素替換
        result = ipa
        for phone, graphemes in self._ipa_to_grapheme_rules.items():
            if phone in result:
                # 選擇最常見的字母組合
                result = result.replace(phone, graphemes[0])

        return [result]
```

**驗收標準**：
- [ ] 整合 CMU Pronouncing Dictionary（或使用 phonemizer）
- [ ] 對於常見詞，能反查出正確拼寫（如 "ˈpaɪθɑn" → "python"）
- [ ] 對於生僻詞，能基於規則生成合理近似拼寫
- [ ] 通過 20+ 個測試案例

---

#### Task 5.4: 重構 `generate_variants()` 主流程（2天）

**文件**：`src/phonofix/languages/english/fuzzy_generator.py`

**任務描述**：
1. 重構主方法，整合 IPA 流程
2. 保留硬編碼規則作為補充
3. 實現基於 IPA 的去重

**重構後的主方法**：
```python
class EnglishFuzzyGenerator:

    def __init__(self, config=None):
        self.config = config or EnglishPhoneticConfig()
        self.phonetic = EnglishPhoneticSystem()  # 使用現有的 IPA backend
        self.ipa_mapper = IPAToSpellingMapper()

    def generate_variants(self, term: str, max_variants: int = 30) -> List[str]:
        """
        基於 IPA 的變體生成（重構版）

        策略：
        1. IPA 維度生成（主要）
        2. 硬編碼規則（補充）
        3. 基於 IPA 去重
        """
        all_variants = {}  # Dict[str, str]：{spelling: ipa}

        # ========== 方法 1: IPA 維度生成 ==========
        try:
            base_ipa = self.phonetic.to_phonetic(term)

            # 生成 IPA 變體
            ipa_variants = self._generate_ipa_fuzzy_variants(base_ipa)

            # IPA → 拼寫反查
            for ipa_var in ipa_variants:
                spellings = self.ipa_mapper.ipa_to_spellings(ipa_var, max_results=5)
                for spelling in spellings:
                    if spelling not in all_variants:
                        all_variants[spelling] = ipa_var

        except Exception as e:
            # IPA 生成失敗時降級到規則模式
            logger.warning(f"IPA generation failed for '{term}': {e}")

        # ========== 方法 2: 硬編碼規則（補充）==========
        # 保留現有的 ASR_SPLIT_PATTERNS、SPELLING_PATTERNS 等
        pattern_variants = self._apply_asr_patterns(term)
        for variant in pattern_variants:
            if variant not in all_variants:
                # 計算變體的 IPA 用於去重
                try:
                    variant_ipa = self.phonetic.to_phonetic(variant)
                    all_variants[variant] = variant_ipa
                except:
                    all_variants[variant] = ""  # 無法獲取 IPA，保留拼寫

        # ========== 去重與過濾 ==========
        # 移除原詞
        all_variants.pop(term, None)
        all_variants.pop(term.lower(), None)

        # 基於 IPA 去重（phonetic key 相同的只保留第一個）
        unique_variants = self._deduplicate_by_ipa(all_variants)

        # 基於 IPA 距離過濾
        filtered = self._filter_by_ipa_distance(term, unique_variants)

        # 穩定排序（按字母順序）
        sorted_variants = sorted(filtered)

        return sorted_variants[:max_variants]

    def _deduplicate_by_ipa(self, variants: Dict[str, str]) -> List[str]:
        """基於 IPA phonetic key 去重"""
        seen_ipa = set()
        unique = []

        for spelling, ipa in variants.items():
            if ipa and ipa not in seen_ipa:
                unique.append(spelling)
                seen_ipa.add(ipa)
            elif not ipa:  # IPA 缺失，保留拼寫
                unique.append(spelling)

        return unique

    def _filter_by_ipa_distance(self, original: str, variants: List[str]) -> List[str]:
        """基於 IPA 編輯距離過濾"""
        try:
            original_ipa = self.phonetic.to_phonetic(original)
        except:
            return variants  # 無法獲取 IPA，跳過過濾

        filtered = []

        for variant in variants:
            try:
                variant_ipa = self.phonetic.to_phonetic(variant)

                # 動態閾值：根據 IPA 長度
                ipa_len = len(original_ipa)
                threshold = max(2, int(ipa_len * 0.35))

                dist = Levenshtein.distance(original_ipa, variant_ipa)

                if dist <= threshold:
                    filtered.append(variant)
            except:
                # 無法獲取 IPA，保留變體
                filtered.append(variant)

        return filtered

    def _apply_asr_patterns(self, term: str) -> List[str]:
        """應用現有硬編碼規則（保留）"""
        # 保留現有的 _generate_full_word_variants()
        # _generate_acronym_variants()
        # _generate_compound_variants()
        # _apply_spelling_patterns()
        # 等方法，不做修改
        pass
```

**驗收標準**：
- [ ] 主流程完整實現「Term → IPA → Fuzzy IPA → Spellings」
- [ ] 硬編碼規則作為補充保留
- [ ] 基於 IPA phonetic key 正確去重
- [ ] 基於 IPA 距離正確過濾
- [ ] 通過所有現有測試 + 新增 IPA 測試

---

#### Task 5.5: 測試與驗證（2天）

**文件**：`tests/test_english_fuzzy_ipa.py`（新建）

**任務描述**：
1. 編寫 IPA 變體生成測試
2. 驗證新詞泛化能力
3. 性能測試

**測試案例**：
```python
# tests/test_english_fuzzy_ipa.py

import pytest
from phonofix.languages.english.fuzzy_generator import EnglishFuzzyGenerator

class TestEnglishIPAGeneration:

    def setup_method(self):
        self.generator = EnglishFuzzyGenerator()

    def test_ipa_fuzzy_variants(self):
        """測試 IPA 音素模糊生成"""
        ipa = "ˈpaɪθɑn"
        variants = self.generator._generate_ipa_fuzzy_variants(ipa)

        # 應包含清濁音變體
        assert any('b' in v or 'p' in v for v in variants)
        # 應包含相似音變體
        assert any('f' in v or 'θ' in v for v in variants)
        # 變體數量合理
        assert 5 <= len(variants) <= 30

    def test_new_word_generalization(self):
        """測試新詞泛化能力（關鍵測試）"""
        # 這些詞在硬編碼字典中不存在
        new_words = ["Ollama", "LangChain", "Huggingface"]

        for word in new_words:
            variants = self.generator.generate_variants(word)

            # 應該能生成變體（不應該是空列表）
            assert len(variants) > 0, f"Failed to generate variants for '{word}'"

            # 變體應該與原詞音素相似
            # （這裡需要實際檢查 IPA 距離）

    def test_deduplication_by_ipa(self):
        """測試基於 IPA 的去重"""
        # "read" (現在時) 和 "reed" 發音相同
        variants_read = self.generator.generate_variants("read")

        # 不應該同時包含 "reed" 和其他 IPA 相同的變體
        # （需要檢查 IPA phonetic key）

    def test_ipa_distance_filtering(self):
        """測試 IPA 距離過濾"""
        variants = self.generator.generate_variants("Python")

        # 所有變體的 IPA 與原詞的距離應在閾值內
        base_ipa = self.generator.phonetic.to_phonetic("Python")

        for variant in variants:
            variant_ipa = self.generator.phonetic.to_phonetic(variant)
            dist = Levenshtein.distance(base_ipa, variant_ipa)

            threshold = max(2, int(len(base_ipa) * 0.35))
            assert dist <= threshold, f"'{variant}' IPA distance too large: {dist}"

    def test_hybrid_approach(self):
        """測試混合方法（IPA + 硬編碼規則）"""
        variants = self.generator.generate_variants("TensorFlow")

        # 應包含 IPA 生成的變體
        # 也應包含硬編碼規則的變體（如 "ten so floor"）
        assert "ten so floor" in [v.lower() for v in variants]
```

**驗收標準**：
- [ ] 所有測試通過
- [ ] 新詞泛化測試證明 IPA 方法有效
- [ ] IPA 去重測試驗證正確性
- [ ] 性能測試：生成 30 個變體 < 500ms

---

#### Task 5.6: 文檔更新（1天）

**文件**：
- `src/phonofix/languages/english/fuzzy_generator.py`（docstring）
- `README.md`
- `references/API_Documentation.md`

**任務描述**：
1. 更新 docstring 反映 IPA 實現
2. 更新 README 範例
3. 添加 IPA 配置說明

**驗收標準**：
- [ ] 所有 docstring 準確反映實現
- [ ] README 包含 IPA 變體生成範例
- [ ] API 文檔更新完整

---

### 🎯 Phase 2 驗收標準總表

| 任務 | 驗收標準 | 優先級 |
|------|---------|--------|
| 5.1 IPA 音素規則 | ≥20 條規則，涵蓋 4 種類型 | P0 |
| 5.2 IPA 變體生成 | 通過單元測試 | P0 |
| 5.3 IPA→拼寫反查 | 整合 CMU Dict，通過 20+ 測試 | P0 |
| 5.4 主流程重構 | 通過所有測試，IPA 去重正確 | P0 |
| 5.5 測試與驗證 | 新詞泛化測試通過 | P0 |
| 5.6 文檔更新 | 文檔準確完整 | P1 |

**Phase 2 總工時**：1-2週（10-14 工作日）

---

## 🏗️ Phase 3: 統一架構 BaseFuzzyGenerator（1週）

### 📌 核心目標

**建立統一抽象基類，強制三語言架構一致**

**當前問題**：
- ❌ 接口不一致（中文/日文/英文各自為政）
- ❌ 重複代碼（每個語言都實現相似邏輯）
- ❌ 難以添加新語言（韓文、泰文等）
- ❌ 缺少統一的變體評分機制

**目標架構**：
```
BaseFuzzyGenerator (抽象基類)
├── ChineseFuzzyGenerator (Pinyin 實現)
├── EnglishFuzzyGenerator (IPA 實現)
├── JapaneseFuzzyGenerator (Romaji 實現)
└── KoreanFuzzyGenerator (Hangul 實現, 未來)
```

---

### 📅 詳細任務分解

#### Task 6.1: 設計抽象基類（2天）

**文件**：`src/phonofix/core/fuzzy_generator_interface.py`（新建）

**任務描述**：
1. 定義統一的變體數據結構
2. 設計抽象方法接口
3. 實現模板方法

**新增模組**：
```python
# src/phonofix/core/fuzzy_generator_interface.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

class VariantSource(Enum):
    """變體來源類型"""
    PHONETIC_FUZZY = "phonetic_fuzzy"    # 語音模糊規則
    HARDCODED_PATTERN = "hardcoded"      # 硬編碼模式
    PHRASE_RULE = "phrase_rule"          # 整詞規則
    ROMANIZATION = "romanization"        # 羅馬化變體

@dataclass
class PhoneticVariant:
    """
    語音變體結構（統一格式）

    Attributes:
        text: 顯示文字（使用者看到的）
        phonetic_key: 語音key（Pinyin/IPA/Romaji，用於去重）
        score: 置信度評分 (0.0-1.0)
        source: 變體來源類型
        metadata: 額外元數據（如音素規則類型）
    """
    text: str
    phonetic_key: str
    score: float = 1.0
    source: VariantSource = VariantSource.PHONETIC_FUZZY
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseFuzzyGenerator(ABC):
    """
    模糊變體生成器抽象基類

    統一流程（模板方法）：
    1. 文字 → 語音key (phonetic_transform)
    2. 語音key → 模糊語音key變體 (generate_phonetic_variants)
    3. 模糊語音key → 文字 (phonetic_to_text)
    4. 基於語音key去重 (deduplicate_by_phonetic)
    5. 評分與排序 (score_and_rank)
    """

    def __init__(self, config=None):
        self.config = config

    # ========== 抽象方法（子類必須實現）==========

    @abstractmethod
    def phonetic_transform(self, term: str) -> str:
        """
        文字 → 語音key

        Args:
            term: 輸入文字（如 "台北", "Python", "東京"）

        Returns:
            str: 語音key（如 "taibei", "ˈpaɪθɑn", "toukyou"）
        """
        pass

    @abstractmethod
    def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
        """
        語音key → 模糊語音key變體

        Args:
            phonetic_key: 標準語音key

        Returns:
            List[str]: 模糊語音key列表
        """
        pass

    @abstractmethod
    def phonetic_to_text(self, phonetic_key: str) -> str:
        """
        語音key → 代表文字（用於 UX 展示）

        Args:
            phonetic_key: 語音key

        Returns:
            str: 代表性文字
        """
        pass

    # ========== 可選方法（子類可覆蓋）==========

    def apply_hardcoded_rules(self, term: str) -> List[str]:
        """
        應用硬編碼規則（補充）

        Args:
            term: 輸入文字

        Returns:
            List[str]: 硬編碼規則生成的變體
        """
        return []

    def calculate_score(self, base_key: str, variant_key: str) -> float:
        """
        計算變體置信度評分

        Args:
            base_key: 原始語音key
            variant_key: 變體語音key

        Returns:
            float: 評分 (0.0-1.0)
        """
        import Levenshtein

        # 基於編輯距離計算評分
        dist = Levenshtein.distance(base_key, variant_key)
        max_len = max(len(base_key), len(variant_key))

        if max_len == 0:
            return 1.0

        similarity = 1.0 - (dist / max_len)
        return max(0.0, similarity)

    # ========== 模板方法（統一流程）==========

    def generate_variants(
        self,
        term: str,
        max_variants: int = 30,
        include_hardcoded: bool = True
    ) -> List[PhoneticVariant]:
        """
        統一的變體生成流程（模板方法）

        Args:
            term: 輸入詞彙
            max_variants: 最大變體數量
            include_hardcoded: 是否包含硬編碼規則

        Returns:
            List[PhoneticVariant]: 變體列表（已排序）
        """
        variants = []

        # ========== Step 1: 語音維度生成 ==========
        try:
            # 1.1 文字 → 語音key
            base_phonetic = self.phonetic_transform(term)

            # 1.2 語音key → 模糊語音key變體
            phonetic_variants = self.generate_phonetic_variants(base_phonetic)

            # 1.3 模糊語音key → 文字
            for p_var in phonetic_variants:
                text = self.phonetic_to_text(p_var)
                score = self.calculate_score(base_phonetic, p_var)

                variants.append(PhoneticVariant(
                    text=text,
                    phonetic_key=p_var,
                    score=score,
                    source=VariantSource.PHONETIC_FUZZY
                ))

        except Exception as e:
            # 語音生成失敗，記錄錯誤但繼續
            import logging
            logging.warning(f"Phonetic generation failed for '{term}': {e}")

        # ========== Step 2: 硬編碼規則（補充）==========
        if include_hardcoded:
            hardcoded_texts = self.apply_hardcoded_rules(term)

            for text in hardcoded_texts:
                try:
                    p_key = self.phonetic_transform(text)
                    variants.append(PhoneticVariant(
                        text=text,
                        phonetic_key=p_key,
                        score=0.8,  # 硬編碼規則評分稍低
                        source=VariantSource.HARDCODED_PATTERN
                    ))
                except:
                    # 無法獲取語音key，使用文字本身
                    variants.append(PhoneticVariant(
                        text=text,
                        phonetic_key=text,
                        score=0.7,
                        source=VariantSource.HARDCODED_PATTERN
                    ))

        # ========== Step 3: 基於語音key去重 ==========
        unique_variants = self._deduplicate_by_phonetic(variants)

        # ========== Step 4: 過濾原詞 ==========
        filtered = [
            v for v in unique_variants
            if v.text.lower() != term.lower()
        ]

        # ========== Step 5: 評分與排序 ==========
        sorted_variants = sorted(
            filtered,
            key=lambda v: (-v.score, len(v.text), v.text)
        )

        return sorted_variants[:max_variants]

    def _deduplicate_by_phonetic(self, variants: List[PhoneticVariant]) -> List[PhoneticVariant]:
        """基於語音key去重（保留評分最高的）"""
        seen_keys = {}

        for variant in variants:
            key = variant.phonetic_key

            if key not in seen_keys:
                seen_keys[key] = variant
            else:
                # 保留評分更高的
                if variant.score > seen_keys[key].score:
                    seen_keys[key] = variant

        return list(seen_keys.values())

    def filter_homophones(self, term_list: List[str]) -> Dict[str, List[str]]:
        """
        過濾同音詞（基於語音key）

        Args:
            term_list: 詞彙列表

        Returns:
            Dict: {"kept": [...], "filtered": [...]}
        """
        kept = []
        filtered = []
        seen_keys = set()

        for term in term_list:
            try:
                key = self.phonetic_transform(term)
            except:
                key = term  # 無法獲取語音key，使用文字

            if key in seen_keys:
                filtered.append(term)
            else:
                kept.append(term)
                seen_keys.add(key)

        return {"kept": kept, "filtered": filtered}
```

**驗收標準**：
- [ ] 抽象基類定義清晰
- [ ] PhoneticVariant 數據結構完整
- [ ] 模板方法實現統一流程
- [ ] 文檔註釋詳盡

---

#### Task 6.2: 重構中文模組（1天）

**文件**：`src/phonofix/languages/chinese/fuzzy_generator.py`

**任務描述**：
1. 繼承 BaseFuzzyGenerator
2. 實現抽象方法
3. 保留現有功能

**重構後的類**：
```python
# src/phonofix/languages/chinese/fuzzy_generator.py

from phonofix.core.fuzzy_generator_interface import (
    BaseFuzzyGenerator,
    PhoneticVariant,
    VariantSource
)
from .config import ChinesePhoneticConfig
from .utils import ChinesePhoneticUtils

class ChineseFuzzyGenerator(BaseFuzzyGenerator):
    """中文模糊變體生成器（基於 Pinyin）"""

    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or ChinesePhoneticConfig
        self.utils = ChinesePhoneticUtils(config=self.config)
        self._dag_params = None
        self._logger = get_logger("fuzzy.chinese")

    # ========== 實現抽象方法 ==========

    def phonetic_transform(self, term: str) -> str:
        """文字 → Pinyin"""
        return self.utils.get_pinyin_string(term)

    def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
        """Pinyin → 模糊 Pinyin 變體"""
        return self.utils.generate_fuzzy_pinyin_variants(
            phonetic_key,
            bidirectional=True
        )

    def phonetic_to_text(self, phonetic_key: str) -> str:
        """Pinyin → 漢字（使用反查）"""
        # 使用現有的 _pinyin_to_chars 方法
        chars = self._pinyin_to_chars(phonetic_key, max_chars=1)
        return chars[0] if chars else phonetic_key

    def apply_hardcoded_rules(self, term: str) -> List[str]:
        """應用黏音/懶音規則"""
        hardcoded = []

        if term in self.config.STICKY_PHRASE_MAP:
            hardcoded.extend(self.config.STICKY_PHRASE_MAP[term])

        return hardcoded

    # ========== 保留現有方法 ==========
    # _get_char_variations()
    # _generate_char_combinations()
    # _add_sticky_phrase_aliases()
    # 等方法保持不變
```

**驗收標準**：
- [ ] 繼承 BaseFuzzyGenerator
- [ ] 實現所有抽象方法
- [ ] 通過所有現有測試
- [ ] 保持向後兼容

---

#### Task 6.3: 重構英文模組（1天）

**文件**：`src/phonofix/languages/english/fuzzy_generator.py`

**任務描述**：
1. 繼承 BaseFuzzyGenerator
2. 實現抽象方法
3. 整合 Phase 2 的 IPA 實現

**重構後的類**：
```python
# src/phonofix/languages/english/fuzzy_generator.py

from phonofix.core.fuzzy_generator_interface import (
    BaseFuzzyGenerator,
    PhoneticVariant,
    VariantSource
)
from .config import EnglishPhoneticConfig
from .ipa_to_spelling import IPAToSpellingMapper
from phonofix.core.phonetic_interface import PhoneticSystem

class EnglishFuzzyGenerator(BaseFuzzyGenerator):
    """英文模糊變體生成器（基於 IPA）"""

    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or EnglishPhoneticConfig()
        self.phonetic = EnglishPhoneticSystem()
        self.ipa_mapper = IPAToSpellingMapper()

    # ========== 實現抽象方法 ==========

    def phonetic_transform(self, term: str) -> str:
        """文字 → IPA"""
        return self.phonetic.to_phonetic(term)

    def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
        """IPA → 模糊 IPA 變體"""
        return self._generate_ipa_fuzzy_variants(phonetic_key)

    def phonetic_to_text(self, phonetic_key: str) -> str:
        """IPA → 拼寫"""
        spellings = self.ipa_mapper.ipa_to_spellings(phonetic_key, max_results=1)
        return spellings[0] if spellings else phonetic_key

    def apply_hardcoded_rules(self, term: str) -> List[str]:
        """應用 ASR 分詞模式和拼寫規則"""
        hardcoded = []

        # 保留現有方法
        hardcoded.extend(self._generate_full_word_variants(term))
        hardcoded.extend(self._generate_acronym_variants(term))
        hardcoded.extend(self._generate_compound_variants(term))
        hardcoded.extend(self._apply_spelling_patterns(term))

        return hardcoded

    # ========== 保留現有方法（Phase 2 實現）==========
    # _generate_ipa_fuzzy_variants()
    # _generate_full_word_variants()
    # ...
```

**驗收標準**：
- [ ] 繼承 BaseFuzzyGenerator
- [ ] 實現所有抽象方法
- [ ] 整合 IPA 實現
- [ ] 通過所有測試

---

#### Task 6.4: 重構日文模組（1天）

**文件**：`src/phonofix/languages/japanese/fuzzy_generator.py`

**任務描述**：
1. 繼承 BaseFuzzyGenerator
2. 實現抽象方法
3. 保留假名/羅馬字雙重邏輯

**重構後的類**：
```python
# src/phonofix/languages/japanese/fuzzy_generator.py

from phonofix.core.fuzzy_generator_interface import (
    BaseFuzzyGenerator,
    PhoneticVariant,
    VariantSource
)
from .config import JapanesePhoneticConfig
from .utils import _get_fugashi, _get_cutlet

class JapaneseFuzzyGenerator(BaseFuzzyGenerator):
    """日文模糊變體生成器（基於 Romaji）"""

    def __init__(self, config=None):
        super().__init__(config)
        self.config = config or JapanesePhoneticConfig()

    # ========== 實現抽象方法 ==========

    def phonetic_transform(self, term: str) -> str:
        """文字 → Romaji（使用 Phase 1 的正規化邏輯）"""
        return self._get_phonetic_key(term)  # 保留 Phase 1 實現

    def generate_phonetic_variants(self, phonetic_key: str) -> List[str]:
        """Romaji → 模糊 Romaji 變體"""
        return list(self._apply_romaji_config_rules(phonetic_key))

    def phonetic_to_text(self, phonetic_key: str) -> str:
        """Romaji → 假名/漢字"""
        # 簡化實現：直接返回 phonetic_key
        # 未來可擴展：反查假名或漢字
        return phonetic_key

    def apply_hardcoded_rules(self, term: str) -> List[str]:
        """應用假名層級規則"""
        hardcoded = []

        # 假名變體生成（保留現有邏輯）
        hira_parts = self._kanji_to_hiragana_list(term)
        base_hira = "".join(hira_parts)

        # 應用假名規則
        kana_variants = self._apply_kana_phrase_rules(base_hira)
        hardcoded.extend(kana_variants)

        return hardcoded

    # ========== 保留現有方法 ==========
    # _kata_to_hira()
    # _kanji_to_hiragana_list()
    # _get_kana_variations()
    # _apply_kana_phrase_rules()
    # _get_phonetic_key() (Phase 1 實現)
    # ...
```

**驗收標準**：
- [ ] 繼承 BaseFuzzyGenerator
- [ ] 實現所有抽象方法
- [ ] 保持假名/羅馬字雙重生成
- [ ] 通過所有測試

---

#### Task 6.5: 測試與驗證（1天）

**文件**：`tests/test_base_fuzzy_generator.py`（新建）

**任務描述**：
1. 測試統一接口
2. 驗證三語言一致性
3. 性能測試

**測試案例**：
```python
# tests/test_base_fuzzy_generator.py

import pytest
from phonofix.languages.chinese.fuzzy_generator import ChineseFuzzyGenerator
from phonofix.languages.english.fuzzy_generator import EnglishFuzzyGenerator
from phonofix.languages.japanese.fuzzy_generator import JapaneseFuzzyGenerator
from phonofix.core.fuzzy_generator_interface import PhoneticVariant

class TestUnifiedInterface:
    """測試統一接口"""

    def test_all_generators_have_same_interface(self):
        """所有生成器應有相同的接口"""
        generators = [
            ChineseFuzzyGenerator(),
            EnglishFuzzyGenerator(),
            JapaneseFuzzyGenerator()
        ]

        for gen in generators:
            # 應有 generate_variants 方法
            assert hasattr(gen, 'generate_variants')

            # 應有抽象方法
            assert hasattr(gen, 'phonetic_transform')
            assert hasattr(gen, 'generate_phonetic_variants')
            assert hasattr(gen, 'phonetic_to_text')

    def test_return_type_consistency(self):
        """返回類型應一致"""
        test_cases = [
            (ChineseFuzzyGenerator(), "台北"),
            (EnglishFuzzyGenerator(), "Python"),
            (JapaneseFuzzyGenerator(), "東京")
        ]

        for gen, term in test_cases:
            variants = gen.generate_variants(term)

            # 應返回 List[PhoneticVariant]
            assert isinstance(variants, list)

            for variant in variants:
                assert isinstance(variant, PhoneticVariant)
                assert hasattr(variant, 'text')
                assert hasattr(variant, 'phonetic_key')
                assert hasattr(variant, 'score')

    def test_phonetic_deduplication(self):
        """基於語音key的去重應正確"""
        # 中文同音詞
        gen_zh = ChineseFuzzyGenerator()
        homophones_zh = ["台北", "苔背"]  # 同音
        result_zh = gen_zh.filter_homophones(homophones_zh)

        assert len(result_zh["kept"]) == 1
        assert len(result_zh["filtered"]) == 1

    def test_scoring_consistency(self):
        """評分應在 0.0-1.0 範圍內"""
        generators = [
            (ChineseFuzzyGenerator(), "測試"),
            (EnglishFuzzyGenerator(), "test"),
            (JapaneseFuzzyGenerator(), "テスト")
        ]

        for gen, term in generators:
            variants = gen.generate_variants(term)

            for variant in variants:
                assert 0.0 <= variant.score <= 1.0
```

**驗收標準**：
- [ ] 統一接口測試通過
- [ ] 三語言一致性驗證通過
- [ ] 性能測試無回歸
- [ ] 所有現有測試仍然通過

---

### 🎯 Phase 3 驗收標準總表

| 任務 | 驗收標準 | 優先級 |
|------|---------|--------|
| 6.1 抽象基類設計 | 接口清晰，文檔完整 | P0 |
| 6.2 重構中文模組 | 向後兼容，通過測試 | P0 |
| 6.3 重構英文模組 | 整合 IPA，通過測試 | P0 |
| 6.4 重構日文模組 | 保留雙重邏輯，通過測試 | P0 |
| 6.5 測試與驗證 | 統一接口測試通過 | P0 |

**Phase 3 總工時**：1週（5 工作日）

---

## 🌟 Phase 4: 持續優化與功能增強（2-3天）

### 📌 核心目標

**添加日文漢字變體生成 + 其他優化**

---

### 📅 詳細任務分解

#### Task 7.1: 日文漢字變體生成（2天）⭐

**文件**：`src/phonofix/languages/japanese/fuzzy_generator.py`

**任務描述**：
1. 實現假名 → 漢字反查
2. 保留原詞的漢字形式
3. 生成同音異字變體

**實現方案**：
```python
class JapaneseFuzzyGenerator(BaseFuzzyGenerator):

    def generate_variants(self, term: str, max_variants: int = 30) -> List[PhoneticVariant]:
        """
        生成日文變體（包含漢字）

        重寫父類方法以支持漢字變體
        """
        variants = []

        # ========== 1. 語音維度生成 ==========
        # 調用父類方法獲取假名/羅馬字變體
        phonetic_variants = super().generate_variants(
            term,
            max_variants=max_variants * 2,  # 多生成一些，後續過濾
            include_hardcoded=True
        )
        variants.extend(phonetic_variants)

        # ========== 2. 漢字變體生成（新增）==========
        if self._has_kanji(term):
            kanji_variants = self._generate_kanji_variants(term)
            variants.extend(kanji_variants)

        # ========== 3. 去重與排序 ==========
        unique = self._deduplicate_by_phonetic(variants)
        sorted_variants = sorted(
            unique,
            key=lambda v: (-v.score, len(v.text), v.text)
        )

        return sorted_variants[:max_variants]

    def _has_kanji(self, text: str) -> bool:
        """檢查是否包含漢字"""
        return any('\u4e00' <= ch <= '\u9fff' for ch in text)

    def _generate_kanji_variants(self, term: str) -> List[PhoneticVariant]:
        """
        生成漢字變體

        策略：
        1. 保留原詞的漢字形式
        2. 使用 fugashi/mecab 的字典獲取同音異字
        """
        variants = []

        # 1. 保留原詞漢字
        base_phonetic = self.phonetic_transform(term)
        variants.append(PhoneticVariant(
            text=term,
            phonetic_key=base_phonetic,
            score=1.0,
            source=VariantSource.PHONETIC_FUZZY,
            metadata={"type": "original_kanji"}
        ))

        # 2. 生成同音異字（使用 mecab 字典）
        kanji_candidates = self._lookup_homophones_from_dict(term)

        for candidate in kanji_candidates:
            candidate_phonetic = self.phonetic_transform(candidate)
            score = self.calculate_score(base_phonetic, candidate_phonetic)

            variants.append(PhoneticVariant(
                text=candidate,
                phonetic_key=candidate_phonetic,
                score=score * 0.9,  # 同音異字評分稍低
                source=VariantSource.PHONETIC_FUZZY,
                metadata={"type": "kanji_variant"}
            ))

        return variants

    def _lookup_homophones_from_dict(self, term: str) -> List[str]:
        """
        從 mecab 字典中查找同音詞

        Args:
            term: 原始詞（漢字）

        Returns:
            List[str]: 同音異字列表
        """
        tagger = _get_fugashi()

        # 1. 獲取原詞的讀音
        base_reading = None
        for word in tagger(term):
            try:
                base_reading = word.feature.kana
                break
            except AttributeError:
                continue

        if not base_reading:
            return []

        # 2. 查找具有相同讀音的其他詞
        # TODO: 這需要建立反向索引（reading → kanji）
        # 暫時返回空列表，未來可整合 mecab-ipadic 字典

        # 簡化實現：使用預定義的同音異字表
        COMMON_HOMOPHONES = {
            "東京": ["凍京", "東經"],
            "会社": ["會社", "回社"],
            # ... 更多常見同音詞
        }

        return COMMON_HOMOPHONES.get(term, [])
```

**驗收標準**：
- [ ] 保留原詞漢字形式
- [ ] 能查找常見同音異字（至少 10 個詞）
- [ ] 通過測試案例
- [ ] 評分機制合理

---

#### Task 7.2: 移除未使用的代碼（半天）

**任務描述**：
1. 移除 `_romaji_reverse_map`（Line 24-29）
2. 移除其他未使用的方法
3. 代碼清理

**驗收標準**：
- [ ] 移除所有未使用代碼
- [ ] 通過所有測試
- [ ] 代碼覆蓋率 >90%

---

#### Task 7.3: 性能優化（1天）

**任務描述**：
1. 添加 LRU 緩存
2. 並行處理優化
3. 性能測試

**優化方案**：
```python
from functools import lru_cache

class BaseFuzzyGenerator:

    @lru_cache(maxsize=1000)
    def phonetic_transform(self, term: str) -> str:
        """添加緩存"""
        return self._phonetic_transform_impl(term)

    @abstractmethod
    def _phonetic_transform_impl(self, term: str) -> str:
        """實際實現（由子類實現）"""
        pass
```

**驗收標準**：
- [ ] 緩存命中率 >80%
- [ ] 性能提升 30-50%
- [ ] 通過性能測試

---

### 🎯 Phase 4 驗收標準總表

| 任務 | 驗收標準 | 優先級 |
|------|---------|--------|
| 7.1 日文漢字變體 | 保留漢字，查找同音詞 | P1 |
| 7.2 代碼清理 | 移除未使用代碼 | P2 |
| 7.3 性能優化 | 性能提升 30-50% | P1 |

**Phase 4 總工時**：2-3天

---

## 📊 總體時間表與里程碑

| Phase | 核心目標 | 工時 | 開始日期 | 完成日期 | 狀態 |
|-------|---------|------|---------|---------|------|
| Phase 1 | 快速修復 | 1週 | 2025-12-08 | 2025-12-08 | ✅ 完成 |
| Phase 2 | 英文 IPA 重構 | 1-2週 | TBD | TBD | ⏳ 待開始 |
| Phase 3 | 統一架構 | 1週 | TBD | TBD | ⏳ 待開始 |
| Phase 4 | 持續優化 | 2-3天 | TBD | TBD | ⏳ 待開始 |
| **總計** | | **3-4週** | | | |

---

## 🎯 關鍵風險與應對

### 風險1：IPA → 拼寫反查困難（Phase 2）

**風險描述**：CMU Pronouncing Dictionary 可能無法覆蓋所有詞彙

**應對策略**：
- 主要：整合 CMU Dict（覆蓋 13 萬詞）
- 補充：音素→字母規則映射
- 兜底：保留硬編碼 ASR_SPLIT_PATTERNS

**優先級**：P0

---

### 風險2：性能回歸（Phase 3）

**風險描述**：統一架構可能導致性能下降

**應對策略**：
- 添加性能測試基準
- 使用 LRU 緩存
- 保留優化後的實現

**優先級**：P1

---

### 風險3：向後兼容性（Phase 3）

**風險描述**：重構可能破壞現有 API

**應對策略**：
- 保留現有方法簽名
- 添加兼容性測試
- 提供遷移文檔

**優先級**：P0

---

## 📋 每日檢查清單

### Phase 2 每日檢查
- [ ] IPA 規則配置完整
- [ ] 單元測試通過率 >95%
- [ ] 新詞泛化測試通過
- [ ] 性能測試無回歸
- [ ] 文檔更新同步

### Phase 3 每日檢查
- [ ] 抽象接口清晰
- [ ] 三語言一致性驗證通過
- [ ] 所有現有測試通過
- [ ] 代碼覆蓋率 >90%
- [ ] 性能無回歸

### Phase 4 每日檢查
- [ ] 日文漢字變體正確
- [ ] 代碼清理完成
- [ ] 性能優化達標
- [ ] 文檔更新完整

---

## 💡 成功標準

### Phase 2 成功標準
- ✅ 英文模組完全基於 IPA
- ✅ 新詞泛化能力驗證通過
- ✅ 符合「語音維度」核心理念
- ✅ 文檔準確反映實現

### Phase 3 成功標準
- ✅ 三語言繼承統一抽象
- ✅ 強制架構一致性
- ✅ 易於添加新語言
- ✅ 統一變體評分機制

### Phase 4 成功標準
- ✅ 日文漢字變體功能完整
- ✅ 性能提升 30-50%
- ✅ 代碼質量提升
- ✅ 技術債務減少

---

**文檔版本**：v1.0
**最後更新**：2025-12-08
**維護者**：Claude Sonnet 4.5
**狀態**：Phase 1 完成，Phase 2-4 待執行

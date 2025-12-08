# 📊 Phonofix 變體生成器深度分析報告

## ✅ 核心理念驗證

你的理念非常清晰且正確：**「在拼音維度進行比對，變體的拼寫只是 UX 展示」**

通過代碼追蹤，我確認了：
- ✅ Chinese: 變體去重基於 Pinyin (`_filter_aliases_by_pinyin`)
- ✅ Japanese: 變體去重基於 Romaji (`filter_homophones`)
- ⚠️ **English: 設計與理念不一致**（詳見下方）

---

## 🔴 關鍵問題：按優先級排序

### P0 - 必須修復

#### 1️⃣ **English 模組架構問題** ⭐⭐⭐⭐⭐
**問題**：完全沒有在 IPA 音標維度生成變體
- 當前實現：基於拼寫規則的硬編碼模式匹配
- 理想實現：term → IPA → 模糊 IPA 變體 → 反推拼寫
- **影響**：無法泛化到新詞，與中文/日文設計理念不一致

**證據**：
```python
# fuzzy_generator.py 完全沒有調用 phonetic_impl.py
# 只有硬編碼的 ASR_SPLIT_PATTERNS 和 SPELLING_PATTERNS
```

**建議方案**：
```python
class EnglishFuzzyGenerator:
    def generate_variants(self, term: str) -> List[str]:
        # 1. term → IPA
        ipa = self.phonetic.to_phonetic(term)

        # 2. 生成 IPA 模糊變體 (基於音素相似度規則)
        ipa_variants = self._generate_ipa_fuzzy_variants(ipa)

        # 3. IPA → 拼寫 (可用 CMU Pronouncing Dictionary)
        spelling_variants = self._ipa_to_spellings(ipa_variants)

        # 4. 補充硬編碼規則 (作為後備)
        spelling_variants.extend(self._apply_asr_patterns(term))

        return self._deduplicate_by_ipa(spelling_variants)
```

**實現難點**：
- IPA → 拼寫的反向映射困難 (一對多)
- 建議：結合 CMU Dict + 保留現有 ASR_SPLIT_PATTERNS 作為補充

---

#### 2️⃣ **Chinese 模組性能問題** ⭐⭐⭐⭐
**問題**：笛卡爾積爆炸 + 後置去重效率低

**當前流程**：
```python
# 1. 生成所有字的組合 (可能 625+ 組合)
for combo in itertools.product(*char_options_list):
    word = "".join([item["char"] for item in combo])
    combinations.append(word)

# 2. 後續在 corrector.py 中去重
filtered = _filter_aliases_by_pinyin(aliases, utils)
```

**問題分析**：
- 4字詞 × 5變體/字 = 625 個組合
- 其中很多拼音重複（不同字但同音）
- 在 `corrector.py` 才去重，浪費計算

**優化方案**：
```python
def _generate_char_combinations(self, char_options_list):
    """在生成階段就基於拼音去重"""
    seen_pinyins = set()
    combinations = []

    # 限制組合數
    MAX_COMBOS = 200

    for i, combo in enumerate(itertools.product(*char_options_list)):
        if i >= MAX_COMBOS:
            break

        # 提前計算拼音並去重
        pinyin = "".join([item["pinyin"] for item in combo])
        if pinyin in seen_pinyins:
            continue

        word = "".join([item["char"] for item in combo])
        combinations.append(word)
        seen_pinyins.add(pinyin)

    return combinations
```

**預期效果**：
- 減少 60-80% 無效組合
- 降低後續處理負擔

---

#### 3️⃣ **Japanese 模組的任意限制** ⭐⭐⭐
**問題**：硬編碼的數字限制沒有依據

```python
# Line 189-191: 為什麼是 50？
for i, combo in enumerate(itertools.product(*char_options)):
    if i > 50:
        break

# Line 201: 為什麼是 10？
for k_var in list(final_kana_variants)[:10]:
```

**建議**：基於詞長動態調整
```python
def generate_variants(self, term: str, max_variants: int = 30):
    hira_parts = self._kanji_to_hiragana_list(term)
    base_hira = "".join(hira_parts)

    # 動態計算上限
    max_kana_combos = min(200, 10 ** min(len(base_hira), 3))
    max_romaji_sources = min(20, len(base_hira) * 2)

    # 使用動態上限
    for i, combo in enumerate(itertools.product(*char_options)):
        if i >= max_kana_combos:
            break

    for k_var in list(final_kana_variants)[:max_romaji_sources]:
        # 轉羅馬字
```

---

### P1 - 重要改進

#### 4️⃣ **統一架構缺失** ⭐⭐⭐⭐
**問題**：三個語言模組沒有統一抽象

**建議**：抽象 `BaseFuzzyGenerator`
```python
# src/phonofix/core/fuzzy_generator_interface.py
from abc import ABC, abstractmethod

class BaseFuzzyGenerator(ABC):
    """變體生成器抽象基類"""

    @abstractmethod
    def phonetic_transform(self, term: str) -> str:
        """文字 → 音標 (Pinyin/IPA/Romaji)"""
        pass

    @abstractmethod
    def generate_phonetic_variants(self, phonetic: str) -> List[str]:
        """音標 → 模糊音標變體"""
        pass

    @abstractmethod
    def phonetic_to_representative_text(self, phonetic: str) -> str:
        """音標 → 代表文字 (UX展示)"""
        pass

    def generate_variants(self, term: str) -> List[str]:
        """統一流程"""
        # 1. 轉音標
        phonetic = self.phonetic_transform(term)

        # 2. 生成音標變體
        phonetic_variants = self.generate_phonetic_variants(phonetic)

        # 3. 音標 → 代表文字
        text_variants = []
        for p_var in phonetic_variants:
            text = self.phonetic_to_representative_text(p_var)
            text_variants.append(text)

        # 4. 基於音標去重
        return self.deduplicate_by_phonetic(text_variants)
```

**優點**：
- 強制三個語言使用相同架構
- 容易添加新語言 (韓文、泰文)
- English 模組被迫正確實現

---

#### 5️⃣ **變體質量評分缺失** ⭐⭐⭐
**問題**：所有變體平等對待，沒有重要性區分

**建議**：添加置信度評分
```python
@dataclass
class FuzzyVariant:
    text: str           # 變體拼寫
    phonetic: str       # 音標
    score: float        # 置信度 (0.0-1.0)
    source: str         # 來源: "initial"|"final"|"special"|"sticky"

def generate_scored_variants(self, term: str) -> List[FuzzyVariant]:
    """生成帶評分的變體"""
    variants = []

    # 聲母變體 (常見) - 高分
    for v in self._generate_initial_variants(term):
        variants.append(FuzzyVariant(v, ..., score=0.8, source="initial"))

    # 韻母變體 (較常見) - 中高分
    for v in self._generate_final_variants(term):
        variants.append(FuzzyVariant(v, ..., score=0.6, source="final"))

    # 特殊音節 (少見) - 中分
    for v in self._generate_special_variants(term):
        variants.append(FuzzyVariant(v, ..., score=0.4, source="special"))

    # 按分數排序
    return sorted(variants, key=lambda x: x.score, reverse=True)
```

**用途**：
- 使用者可設定最小置信度閾值
- 限制變體數量時優先保留高分變體
- 比對時高分變體權重更高

---

#### 6️⃣ **Config 可擴展性不足** ⭐⭐⭐
**問題**：硬編碼規則無法動態擴展

**English Config 問題最嚴重**：
```python
# 140+ 行硬編碼字典
ASR_SPLIT_PATTERNS = {
    'tensorflow': [...],
    'pytorch': [...],
    # 新技術詞彙如 "Ollama", "LangChain" 無法處理
}
```

**建議方案**：
```python
class EnglishPhoneticConfig:
    # 內建規則
    _DEFAULT_ASR_PATTERNS = {...}

    def __init__(self):
        self.asr_patterns = self._DEFAULT_ASR_PATTERNS.copy()

    def register_asr_pattern(self, term: str, variants: List[str]):
        """允許使用者動態添加規則"""
        self.asr_patterns[term.lower()] = variants

    def load_patterns_from_file(self, path: str):
        """從 YAML/JSON 載入規則"""
        import yaml
        with open(path) as f:
            custom = yaml.safe_load(f)
        self.asr_patterns.update(custom)

# 使用
config = EnglishPhoneticConfig()
config.register_asr_pattern("ollama", ["oh llama", "o lama"])
engine = EnglishEngine(config=config)
```

---

### P2 - 優化建議

#### 7️⃣ **邊界條件處理不完整** ⭐⭐

**Chinese 混合文本問題**：
```python
# 當前: "PyTorch模型" → "P", "y", "T", ... 都返回原樣
# _get_char_variations() Line 137
if not ('\u4e00' <= char <= '\u9fff'):
    return [{"pinyin": char, "char": char}]

# 問題: 英文字母沒有變體，但實際可能有拼寫錯誤
```

**建議**：
```python
def _get_char_variations(self, char):
    if '\u4e00' <= char <= '\u9fff':
        # 中文字符處理
        return self._get_chinese_variations(char)
    elif char.isalpha():
        # 英文字符：返回常見拼寫錯誤
        return [{"pinyin": char, "char": char},
                {"pinyin": char.lower(), "char": char.lower()},
                {"pinyin": char.upper(), "char": char.upper()}]
    else:
        # 其他字符
        return [{"pinyin": char, "char": char}]
```

---

#### 8️⃣ **錯誤處理不夠友好** ⭐⭐

**Japanese 模組**：
```python
# Line 202-209: try-except 太寬泛
try:
    r_base = cutlet_katsu.romaji(k_var)
    # ...
except Exception:  # 吃掉所有錯誤！
    continue
```

**建議**：
```python
try:
    r_base = cutlet_katsu.romaji(k_var)
except Exception as e:
    logger.warning(f"Romaji conversion failed for '{k_var}': {e}")
    continue
```

---

#### 9️⃣ **候選字數限制過於保守** ⭐⭐

**Chinese fuzzy_generator.py**：
```python
# Line 86: max_chars=2 太少
def _pinyin_to_chars(self, pinyin_str, max_chars=2):
```

**問題**：某些拼音有 5+ 個常用同音字（如 "yi"）

**建議**：
```python
def _pinyin_to_chars(self, pinyin_str, max_chars=None):
    """動態調整候選數"""
    if max_chars is None:
        # 短音節取更多候選 (常用音節同音字多)
        max_chars = 6 if len(pinyin_str) <= 3 else 3

    # ... DAG 查詢
```

---

## 🎯 具體代碼改進範例

### Chinese: 在生成階段去重

```python
# src/phonofix/languages/chinese/fuzzy_generator.py
def _generate_char_combinations(self, char_options_list):
    """生成字符組合 (優化版：提前基於拼音去重)"""
    seen_pinyins = set()
    combinations = []

    # 根據詞長動態設定上限
    word_len = len(char_options_list)
    MAX_COMBOS = min(300, 100 * word_len)

    for i, combo in enumerate(itertools.product(*char_options_list)):
        if i >= MAX_COMBOS:
            logger.warning(f"達到組合上限 {MAX_COMBOS}，截斷變體生成")
            break

        # 計算拼音並提前去重
        pinyin = "".join([item["pinyin"] for item in combo])
        if pinyin in seen_pinyins:
            continue

        word = "".join([item["char"] for item in combo])
        combinations.append(word)
        seen_pinyins.add(pinyin)

    return combinations
```

---

### English: IPA 維度重構

```python
# src/phonofix/languages/english/fuzzy_generator.py
class EnglishFuzzyGenerator:
    def __init__(self, config=None):
        self.config = config or EnglishPhoneticConfig()
        self.phonetic = EnglishPhoneticSystem()

        # 載入 CMU Pronouncing Dictionary (可選)
        self.cmu_dict = self._load_cmu_dict()

    def generate_variants(self, term: str, max_variants: int = 30) -> List[str]:
        """基於 IPA 的變體生成"""
        variants = set()

        # 方法 1: IPA 維度生成 (主要方法)
        ipa_variants = self._generate_ipa_based_variants(term)
        variants.update(ipa_variants)

        # 方法 2: 硬編碼規則 (補充方法)
        pattern_variants = self._generate_pattern_based_variants(term)
        variants.update(pattern_variants)

        # 基於 IPA 去重
        return self._deduplicate_by_ipa(list(variants))[:max_variants]

    def _generate_ipa_based_variants(self, term: str) -> Set[str]:
        """IPA 維度變體生成 (新增)"""
        # 1. term → IPA
        ipa = self.phonetic.to_phonetic(term)

        # 2. 生成 IPA 變體
        ipa_variants = self._apply_ipa_fuzzy_rules(ipa)

        # 3. IPA → 拼寫候選
        spelling_variants = set()
        for ipa_var in ipa_variants:
            spellings = self._ipa_to_spellings(ipa_var, term)
            spelling_variants.update(spellings)

        return spelling_variants

    def _apply_ipa_fuzzy_rules(self, ipa: str) -> List[str]:
        """應用 IPA 音素模糊規則"""
        variants = {ipa}

        # 音素替換規則 (類似 Chinese 的聲母/韻母規則)
        IPA_FUZZY_RULES = {
            # 清濁音混淆
            ('p', 'b'), ('t', 'd'), ('k', 'ɡ'),
            # 長短元音
            ('iː', 'ɪ'), ('uː', 'ʊ'),
            # 常見混淆
            ('θ', 'f'), ('ð', 'v'),  # think -> fink
        }

        for rule in IPA_FUZZY_RULES:
            for sound1, sound2 in [rule, rule[::-1]]:
                if sound1 in ipa:
                    variants.add(ipa.replace(sound1, sound2))

        return list(variants)

    def _ipa_to_spellings(self, ipa: str, original: str) -> List[str]:
        """IPA → 可能拼寫 (使用 CMU Dict + 規則推測)"""
        candidates = []

        # 1. CMU Dict 反查
        if self.cmu_dict:
            candidates.extend(self.cmu_dict.get(ipa, []))

        # 2. 基於原詞的音素編輯
        candidates.append(original.lower())

        # 3. 常見音素→字母映射
        # (簡化示例，實際需要更複雜的 G2P 反向)
        spelling = ipa.replace('ð', 'th').replace('θ', 'th')
        candidates.append(spelling)

        return candidates
```

---

### Japanese: 動態限制

```python
# src/phonofix/languages/japanese/fuzzy_generator.py
def generate_variants(self, term: str, max_variants: int = 30) -> List[str]:
    """生成日文變體 (優化版：動態限制)"""
    hira_parts = self._kanji_to_hiragana_list(term)
    base_hira = "".join(hira_parts)

    # 動態計算上限
    word_len = len(base_hira)
    max_kana_combos = min(200, 10 ** min(word_len, 3))
    max_romaji_sources = min(30, word_len * 3)

    char_options = [self._get_kana_variations(ch) for ch in base_hira]

    kana_combinations = []
    for i, combo in enumerate(itertools.product(*char_options)):
        if i >= max_kana_combos:
            logger.debug(f"達到假名組合上限 {max_kana_combos}")
            break
        kana_combinations.append("".join(combo))

    # 應用整詞規則
    final_kana_variants = set()
    for combo in kana_combinations:
        final_kana_variants.update(self._apply_kana_phrase_rules(combo))

    # 轉羅馬字 (動態限制)
    cutlet_katsu = _get_cutlet()
    romaji_variants = set()

    for k_var in sorted(final_kana_variants)[:max_romaji_sources]:
        try:
            r_base = cutlet_katsu.romaji(k_var)
            if r_base:
                r_clean = r_base.replace(" ", "")
                romaji_variants.update(self._apply_romaji_config_rules(r_clean))
        except Exception as e:
            logger.warning(f"羅馬字轉換失敗 '{k_var}': {e}")
            continue

    all_variants = final_kana_variants.union(romaji_variants)
    all_variants.discard(term)

    # 同音去重
    variant_list = sorted(list(all_variants), key=lambda x: (len(x), x))
    filtered = self.filter_homophones(variant_list)

    return filtered["kept"][:max_variants]
```

---

## 📋 實施優先級建議

如果你時間有限，建議按此順序：

### Phase 1: 修復關鍵問題 (1-2 週)
1. **English 模組重構** - 實現 IPA 維度生成
2. **Chinese 性能優化** - 在生成階段去重
3. **Japanese 動態限制** - 移除硬編碼數字

### Phase 2: 架構改進 (1 週)
4. **統一抽象** - 實現 BaseFuzzyGenerator
5. **Config 可擴展** - 提供動態添加規則 API

### Phase 3: 質量提升 (1 週)
6. **變體評分** - 添加置信度機制
7. **邊界條件** - 處理混合文本、錯誤處理

---

## 💡 額外建議

### 測試數據收集
建議收集真實 ASR/LLM 錯誤數據：
```python
# 使用 Azure Speech/Google STT 測試你的專有名詞
test_terms = ["台北車站", "TensorFlow", "アスピリン"]
asr_outputs = [run_asr_test(term) for term in test_terms]

# 對比你的變體是否涵蓋了真實錯誤
for term, asr_output in zip(test_terms, asr_outputs):
    variants = generator.generate_variants(term)
    if asr_output not in variants:
        print(f"遺漏: {term} → {asr_output}")
```

### 性能基準測試
```python
import time

def benchmark_variant_generation():
    terms = ["台北車站", "永和豆漿", "勇者鬥惡龍"]
    generator = ChineseFuzzyGenerator()

    start = time.time()
    for term in terms * 100:
        variants = generator.generate_variants(term)
    elapsed = time.time() - start

    print(f"平均每詞: {elapsed/300*1000:.2f}ms")
    print(f"平均變體數: {sum(len(v) for v in variants)/len(terms):.1f}")
```

---

## 🎯 總結

### 核心發現
1. ✅ **核心理念正確**：在拼音/音標維度比對，變體拼寫只是 UX
2. ✅ **Chinese/Japanese 符合理念**：實現正確，但有性能問題
3. ❌ **English 偏離理念**：沒有 IPA 維度生成（P0 關鍵問題）
4. ⚠️ **缺少統一架構**：三個模組設計不一致

### 關鍵改進方向
1. **English 模組重構** (P0) - 實現 IPA 維度變體生成
2. **Chinese 性能優化** (P0) - 在生成階段基於拼音去重
3. **Japanese 動態調整** (P0) - 移除任意硬編碼限制
4. **統一架構抽象** (P1) - BaseFuzzyGenerator 基類
5. **變體質量提升** (P1) - 置信度評分機制
6. **Config 可擴展性** (P1) - 動態添加規則 API

### 實施建議
- 優先修復 P0 問題 (1-2 週)
- 逐步完善 P1 改進 (2-3 週)
- 持續優化 P2 建議 (長期)
- 收集真實 ASR/LLM 錯誤數據驗證效果

---

**報告生成時間**: 2025-12-07
**分析對象**: Phonofix v0.2.0
**分析者**: Claude Sonnet 4.5

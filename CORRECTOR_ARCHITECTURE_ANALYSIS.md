# Corrector 架構分析報告

**分析日期**: 2025-12-09
**問題來源**: Phase 4 完成後的架構審查
**分析師**: Claude Sonnet 4.5

---

## 📋 執行摘要

用戶在 Phase 4 重構過程中發現：**Corrector 組件缺少 ABC interface in core/**，與其他核心組件（PhoneticSystem, Tokenizer, FuzzyGenerator）的架構不一致。

**結論**: 用戶的觀察完全正確！應立即創建 `core/corrector_interface.py` 定義 `BaseCorrector(ABC)`。

---

## 🔍 問題分析

### 1. 架構不一致性

#### ✅ 已有 ABC 的組件（在 `core/`）

| 組件 | 文件位置 | 基類 | 狀態 |
|------|---------|------|------|
| PhoneticSystem | `core/phonetic_interface.py` | ABC | ✅ 正常 |
| Tokenizer | `core/tokenizer_interface.py` | ABC | ✅ 正常 |
| FuzzyGenerator | `core/fuzzy_generator_interface.py` | ABC | ✅ 正常 |

#### ❌ 沒有 ABC 的組件

| 組件 | 文件位置 | 當前接口 | 狀態 |
|------|---------|---------|------|
| **Corrector** | `correction/protocol.py` | **Protocol 只有** | ❌ 不一致 |

**問題**: Corrector 只有 Protocol，沒有 ABC！這與其他三個核心組件不一致。

---

### 2. 方法簽名不一致

檢查三個語言的 Corrector 實現，發現方法簽名不統一：

```python
# ❌ ChineseCorrector (src/phonofix/languages/chinese/corrector.py)
class ChineseCorrector:  # 沒有繼承 ABC
    def correct(self, asr_text: str, silent: bool = False) -> str:
        """參數名: asr_text, 缺少 full_context"""
        pass

# ✅ EnglishCorrector (src/phonofix/languages/english/corrector.py)
class EnglishCorrector:  # 沒有繼承 ABC
    def correct(self, text: str, full_context: str = None, silent: bool = False) -> str:
        """參數名: text, 有 full_context"""
        pass

# ✅ JapaneseCorrector (src/phonofix/languages/japanese/corrector.py)
class JapaneseCorrector:  # 沒有繼承 ABC
    def correct(self, text: str, full_context: str = None, silent: bool = False) -> str:
        """參數名: text, 有 full_context"""
        pass
```

**差異點**:
1. **參數名不同**: `asr_text` (Chinese) vs `text` (English/Japanese)
2. **參數缺失**: ChineseCorrector 沒有 `full_context` 參數
3. **無繼承約束**: 所有 Corrector 都是獨立類，沒有繼承統一基類

---

### 3. 代碼重複

所有 Corrector 都重複實現了相同模式的 `_from_engine()` 工廠方法：

```python
# ChineseCorrector._from_engine() - 47 行實現
@classmethod
def _from_engine(cls, engine: "ChineseEngine", term_dict, **kwargs):
    # 重複的工廠邏輯
    pass

# EnglishCorrector._from_engine() - 類似實現
@classmethod
def _from_engine(cls, engine: "EnglishEngine", term_dict, **kwargs):
    # 重複的工廠邏輯
    pass

# JapaneseCorrector._from_engine() - 類似實現
@classmethod
def _from_engine(cls, engine: "JapaneseEngine", term_dict, **kwargs):
    # 重複的工廠邏輯
    pass
```

**問題**: 如果有 ABC 基類，這個方法可以提升到基類共享，減少代碼重複。

---

### 4. 缺乏編譯時檢查

因為只有 Protocol（鴨子類型），無法在開發時發現問題：

- ❌ IDE 無法提前警告接口不一致
- ❌ mypy 類型檢查無法發現簽名差異
- ❌ 開發者容易犯錯（如 ChineseCorrector 用了不同的參數名）
- ❌ 測試期才能發現接口問題

---

## 💡 Protocol vs ABC 權衡分析

### Protocol 的優勢（當前）

| 優勢 | 說明 |
|------|------|
| 鴨子類型 | 不需要顯式繼承，靈活 |
| 結構子類型 | 只要有正確的方法就符合協議 |
| 非侵入式 | 第三方可以提供自己的 Corrector 實現 |

### Protocol 的劣勢（當前問題）

| 劣勢 | 實際影響 |
|------|---------|
| ❌ 無法強制接口一致性 | 導致 `asr_text` vs `text` 不一致 |
| ❌ 無法共享實現 | `_from_engine()` 在每個子類重複 |
| ❌ 無編譯時類型檢查 | 直到運行時才發現接口不匹配 |
| ❌ 架構不一致 | 其他組件都用 ABC |

### ABC 的優勢（建議改用）

| 優勢 | 具體效果 |
|------|---------|
| ✅ 強制接口統一 | 確保所有子類有一致的方法簽名 |
| ✅ 共享實現代碼 | `_from_engine()` 可以提升到基類 |
| ✅ 編譯時檢查 | IDE 和 mypy 可以檢查接口實現 |
| ✅ 架構一致 | 與 PhoneticSystem, Tokenizer, FuzzyGenerator 對齊 |
| ✅ 文檔清晰 | ABC 明確定義接口契約 |

### ABC 的劣勢

| 劣勢 | 評估 |
|------|------|
| ⚠️ 需要顯式繼承 | 對我們項目不是問題（內部組件） |

---

## 🎯 解決方案設計

### 方案：創建 `core/corrector_interface.py`

```python
"""
修正器抽象基類

定義所有語言修正器必須實作的統一接口。
"""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from phonofix.engine.base import CorrectorEngine


class BaseCorrector(ABC):
    """
    修正器抽象基類

    職責：
    - 定義統一的修正接口 (correct 方法)
    - 定義統一的工廠方法 (_from_engine)
    - 強制子類實現一致的接口

    設計原則：
    - 統一方法簽名（text, full_context, silent）
    - 共享工廠方法模式
    - 強制接口一致性

    使用範例：
        >>> class MyCorrector(BaseCorrector):
        ...     def correct(self, text, full_context=None, silent=False):
        ...         return text.upper()
        ...
        ...     @classmethod
        ...     def _from_engine(cls, engine, term_dict, **kwargs):
        ...         return cls()
    """

    @abstractmethod
    def correct(
        self,
        text: str,
        full_context: Optional[str] = None,
        silent: bool = False
    ) -> str:
        """
        執行文本修正

        Args:
            text: 待修正的文本
            full_context: 完整上下文（用於 keyword/exclude_when 判斷）
            silent: 是否靜默模式（不打印修正日誌）

        Returns:
            str: 修正後的文本

        範例:
            >>> corrector = ChineseCorrector(...)
            >>> result = corrector.correct("我在北車", full_context="我在北車等你")
            >>> print(result)
            我在台北車站
        """
        pass

    @classmethod
    @abstractmethod
    def _from_engine(
        cls,
        engine: "CorrectorEngine",
        term_dict,
        **kwargs
    ) -> "BaseCorrector":
        """
        由 Engine 調用的工廠方法

        這個方法讓 Engine 可以建立輕量的 Corrector 實例，
        共享 Engine 中的昂貴資源（PhoneticSystem, Tokenizer 等）。

        Args:
            engine: CorrectorEngine 實例
            term_dict: 詞彙配置（List[str] 或 Dict）
            **kwargs: 額外配置選項

        Returns:
            BaseCorrector: 修正器實例

        範例:
            >>> engine = ChineseEngine()
            >>> corrector = ChineseCorrector._from_engine(
            ...     engine,
            ...     ["台北車站", "牛奶"]
            ... )
        """
        pass
```

---

## 📊 影響評估

### 破壞性變更

| 變更項目 | 影響範圍 | 嚴重程度 |
|---------|---------|---------|
| `asr_text` → `text` 參數重命名 | ChineseCorrector | 🟡 中等 |
| 添加 `full_context` 參數 | ChineseCorrector | 🟢 低（可選參數） |
| 繼承 BaseCorrector | 所有 Corrector | 🟢 低（純增加） |

### 用戶影響分析

**情境 1: 使用位置參數（大多數用戶）**
```python
# ✅ 不受影響
result = corrector.correct("我在北車")
```

**情境 2: 使用關鍵字參數（少數用戶）**
```python
# ❌ 需要修改
result = corrector.correct(asr_text="我在北車")  # 舊寫法
result = corrector.correct(text="我在北車")      # 新寫法
```

### 遷移成本評估

- **預估影響用戶**: <10%（大部分使用位置參數）
- **遷移難度**: 低（簡單的參數重命名）
- **測試需更新**: `tests/test_chinese_corrector.py`
- **文檔需更新**: README.md, examples/

---

## 🚀 實施計劃

### Phase 1: 創建基礎接口 ✅

**任務**:
1. 創建 `src/phonofix/core/corrector_interface.py`
2. 定義 `BaseCorrector(ABC)` 包含：
   - `correct(text, full_context=None, silent=False)` 抽象方法
   - `_from_engine(cls, engine, ...)` 類方法
3. 保留 `correction/protocol.py` 用於類型註解（Protocol 和 ABC 可共存）

**預估時間**: 30 分鐘

---

### Phase 2: 重構 ChineseCorrector 🔧

**任務**:
1. 繼承 `BaseCorrector`
2. **參數重命名**: `asr_text` → `text`
3. **添加參數**: `full_context` 可選參數（向後兼容）
4. 更新 `tests/test_chinese_corrector.py` 中所有使用 `asr_text` 的地方
5. 運行測試確保通過

**預估時間**: 1 小時

**風險**: 🟡 中等（需要更新測試，可能影響少數用戶）

---

### Phase 3: 重構 EnglishCorrector 和 JapaneseCorrector ✅

**任務**:
1. 繼承 `BaseCorrector`（已經符合接口，只需聲明繼承）
2. 運行測試確保通過

**預估時間**: 15 分鐘

**風險**: 🟢 低（無破壞性變更）

---

### Phase 4: 更新 UnifiedCorrector 📝

**任務**:
1. 確認與 BaseCorrector 接口兼容
2. 更新類型註解使用 BaseCorrector
3. 運行測試確保通過

**預估時間**: 15 分鐘

---

### Phase 5: 更新文檔 📚

**任務**:
1. 更新 `CLAUDE.md` 架構說明
   - 添加 Corrector ABC 到架構圖
   - 更新「Critical Architecture Decisions」章節
2. 更新 `README.md`
   - 更新 API 使用範例（如有 `asr_text` 的範例）
3. 更新 `examples/chinese_examples.py`
   - 確保使用新的參數名
4. 創建遷移指南 `MIGRATION_0.2_TO_0.3.md`（如需發布）

**預估時間**: 45 分鐘

---

### Phase 6: 版本號更新 🏷️

**任務**:
1. 更新 `pyproject.toml` 版本號
   - `0.2.0` → `0.3.0`（因為有破壞性變更）
2. 更新 `CHANGELOG.md`

**預估時間**: 10 分鐘

---

## 📈 預期效益

### 短期效益（立即）

| 效益 | 說明 |
|------|------|
| ✅ 架構一致性 | Corrector 與其他核心組件對齊 |
| ✅ 接口統一 | 所有 Corrector 使用相同的方法簽名 |
| ✅ 編譯時檢查 | IDE 和 mypy 可以提前發現問題 |

### 長期效益（未來）

| 效益 | 說明 |
|------|------|
| ✅ 代碼重用 | 共享工廠方法實現 |
| ✅ 維護性提升 | 更清晰的接口契約 |
| ✅ 擴展性增強 | 新增語言更容易（強制實現接口） |
| ✅ 文檔改善 | ABC docstring 提供更好的文檔 |

---

## 🎯 為什麼現在是好時機？

| 理由 | 說明 |
|------|------|
| 📅 項目還很新 | 0.2.0 版本，可以接受破壞性變更 |
| 👥 用戶基數小 | 遷移成本低 |
| 🎉 日文剛完成 | 正好是架構整理的好時機 |
| 🔧 命名本就不好 | `asr_text` 太具體，應該改成 `text` |
| 🏗️ Phase 4 完成 | 性能優化完成，可以專注架構改進 |

---

## ✅ 最終建議

**強烈建議立即執行這個重構！**

**理由**:
1. ✅ 用戶的觀察完全正確
2. ✅ 解決了實際存在的架構問題
3. ✅ 長期收益遠大於短期成本
4. ✅ 現在是最佳時機（0.2.0 → 0.3.0）

**優先級**: 🔴 高（應在下一個版本發布前完成）

---

## 📎 附錄

### A. 對比其他語言框架

其他成熟的多語言 NLP 框架也採用類似架構：

- **spaCy**: `Language` 類作為基類，各語言繼承
- **NLTK**: `TaggerI`, `TokenizerI` 等接口定義
- **Transformers**: `PreTrainedModel` 基類

**結論**: 使用 ABC 定義接口是業界標準做法。

---

### B. Protocol vs ABC 的使用場景

| 使用場景 | 推薦方案 |
|---------|---------|
| 內部組件（如本項目） | ABC（強制接口） |
| 外部插件系統 | Protocol（靈活接口） |
| 類型註解 | Protocol（非侵入式） |
| 共享實現 | ABC（代碼重用） |

**本項目**: Corrector 是內部組件，應使用 ABC。

---

### C. 參考文件

- `src/phonofix/core/phonetic_interface.py` - PhoneticSystem ABC 範例
- `src/phonofix/core/tokenizer_interface.py` - Tokenizer ABC 範例
- `src/phonofix/core/fuzzy_generator_interface.py` - FuzzyGenerator ABC 範例
- `src/phonofix/correction/protocol.py` - 當前的 Protocol 定義
- `src/phonofix/engine/base.py` - CorrectorEngine ABC 參考

---

**報告結束**

**下一步**: 請參考 `CORRECTOR_REFACTORING_TODO.md` 開始實施。

# Corrector 重構實施計劃

**項目**: Corrector ABC Interface 重構
**版本**: 0.2.0 → 0.3.0
**優先級**: 🔴 高
**預計完成時間**: 3-4 小時

---

## 📋 總覽

### 目標
創建 `core/corrector_interface.py` 定義 `BaseCorrector(ABC)`，統一所有語言 Corrector 的接口。

### 主要變更
1. ✅ 創建 BaseCorrector ABC
2. 🔧 ChineseCorrector: `asr_text` → `text` 參數重命名
3. ✅ EnglishCorrector 和 JapaneseCorrector: 繼承 BaseCorrector
4. 📝 更新測試和文檔

### 破壞性變更
- ChineseCorrector 的 `asr_text` 參數重命名為 `text`
- 影響使用關鍵字參數的用戶（預估 <10%）

---

## 🎯 Phase 1: 創建 BaseCorrector ABC

**優先級**: 🔴 P0 - 最高
**預估時間**: 30 分鐘
**風險**: 🟢 低

### Task 1.1: 創建 core/corrector_interface.py

**文件路徑**: `src/phonofix/core/corrector_interface.py`

**內容**:
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
                         某些修正器會利用完整上下文來判斷是否應該進行修正
                         例如：根據 keywords 或 exclude_when 規則
            silent: 是否靜默模式（不打印修正日誌）
                   設為 True 時，修正器不會輸出 [發音修正] 日誌

        Returns:
            str: 修正後的文本

        範例:
            >>> corrector = ChineseCorrector(...)
            >>> # 基本使用
            >>> result = corrector.correct("我在北車")
            >>> print(result)
            我在台北車站

            >>> # 使用完整上下文
            >>> result = corrector.correct("我在北車", full_context="我在北車等你")
            >>> print(result)
            我在台北車站

            >>> # 靜默模式
            >>> result = corrector.correct("我在北車", silent=True)
            >>> # 不會打印 [發音修正] 日誌
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
            engine: CorrectorEngine 實例，提供共享的語音系統和分詞器
            term_dict: 詞彙配置，支援多種格式：
                - List[str]: 純詞彙列表，自動生成別名
                - Dict[str, List[str]]: 詞彙 + 手動別名
                - Dict[str, dict]: 完整配置 (含 aliases, keywords, exclusions)
            **kwargs: 額外配置選項（如 protected_terms, enable_fuzzy 等）

        Returns:
            BaseCorrector: 修正器實例

        範例:
            >>> engine = ChineseEngine()
            >>> # 簡單用法
            >>> corrector = ChineseCorrector._from_engine(
            ...     engine,
            ...     ["台北車站", "牛奶"]
            ... )
            >>>
            >>> # 進階用法
            >>> corrector = ChineseCorrector._from_engine(
            ...     engine,
            ...     {
            ...         "台北車站": {
            ...             "aliases": ["北車"],
            ...             "keywords": ["等", "車站"],
            ...             "weight": 0.3
            ...         }
            ...     },
            ...     protected_terms=["北側"]
            ... )
        """
        pass
```

**驗收標準**:
- [ ] 文件創建成功
- [ ] 包含 `BaseCorrector(ABC)` 類定義
- [ ] 包含 `correct()` 抽象方法
- [ ] 包含 `_from_engine()` 類方法
- [ ] 包含完整的 docstring 和範例
- [ ] 使用 TYPE_CHECKING 避免循環導入

---

### Task 1.2: 更新 core/__init__.py

**文件路徑**: `src/phonofix/core/__init__.py`

**操作**: 添加 BaseCorrector 到導出

```python
from phonofix.core.corrector_interface import BaseCorrector

__all__ = [
    # ... 現有導出
    "BaseCorrector",
]
```

**驗收標準**:
- [ ] BaseCorrector 成功導出
- [ ] 可以透過 `from phonofix.core import BaseCorrector` 導入

---

### Task 1.3: 驗證 BaseCorrector 可導入

**命令**:
```bash
# 測試導入
uv run python -c "from phonofix.core import BaseCorrector; print('✅ BaseCorrector imported')"
```

**驗收標準**:
- [ ] 導入成功，無錯誤

---

## 🔧 Phase 2: 重構 ChineseCorrector

**優先級**: 🔴 P0 - 最高
**預估時間**: 1 小時
**風險**: 🟡 中等（有破壞性變更）

### Task 2.1: 修改 ChineseCorrector 類定義

**文件路徑**: `src/phonofix/languages/chinese/corrector.py`

**變更 1: 添加繼承**
```python
# 修改前
class ChineseCorrector:
    """中文修正器"""

# 修改後
from phonofix.core import BaseCorrector

class ChineseCorrector(BaseCorrector):
    """中文修正器（繼承 BaseCorrector）"""
```

**變更 2: 修改 correct() 方法簽名**
```python
# 修改前
def correct(self, asr_text: str, silent: bool = False) -> str:
    """
    執行中文文本修正

    Args:
        asr_text: ASR 識別的文本
        silent: 是否靜默模式
    """

# 修改後
def correct(
    self,
    text: str,
    full_context: Optional[str] = None,
    silent: bool = False
) -> str:
    """
    執行中文文本修正

    Args:
        text: 待修正的文本
        full_context: 完整上下文（可選，用於 keyword 判斷）
        silent: 是否靜默模式
    """
    # 注意：函數內部所有使用 asr_text 的地方都要改為 text
```

**變更 3: 更新內部實現**
```python
# 修改前
def correct(self, asr_text: str, silent: bool = False) -> str:
    if not asr_text or not self.normalized_dict:
        return asr_text

    # ... 其他使用 asr_text 的地方

# 修改後
def correct(
    self,
    text: str,
    full_context: Optional[str] = None,
    silent: bool = False
) -> str:
    # full_context 參數目前可以忽略（中文修正器暫時不需要）
    # 保留此參數是為了接口統一，未來可能會使用

    if not text or not self.normalized_dict:
        return text

    # ... 其他使用 text 的地方
```

**驗收標準**:
- [ ] ChineseCorrector 繼承 BaseCorrector
- [ ] `asr_text` 參數改為 `text`
- [ ] 添加 `full_context` 可選參數
- [ ] 內部所有 `asr_text` 引用都改為 `text`
- [ ] docstring 更新完整

---

### Task 2.2: 更新 ChineseCorrector 測試

**文件路徑**: `tests/test_chinese_corrector.py`

**搜尋並替換**:
```bash
# 搜尋所有使用 asr_text 的地方
grep -n "asr_text" tests/test_chinese_corrector.py
```

**替換模式**:
```python
# 修改前
result = corrector.correct(asr_text="我在北車")

# 修改後
result = corrector.correct(text="我在北車")
# 或使用位置參數（推薦）
result = corrector.correct("我在北車")
```

**預計修改位置**（需實際檢查）:
1. `test_basic_correction()` - 基本修正測試
2. `test_fuzzy_matching()` - 模糊匹配測試
3. `test_context_keywords()` - 上下文關鍵字測試
4. `test_exclude_when()` - 排除規則測試
5. 其他所有測試方法

**驗收標準**:
- [ ] 所有 `asr_text=` 改為 `text=`
- [ ] 測試全部通過（運行 `uv run pytest tests/test_chinese_corrector.py -v`）

---

### Task 2.3: 更新 ChineseCorrector 使用範例

**文件路徑**: `examples/chinese_examples.py`

**搜尋並替換**:
```bash
# 搜尋所有使用 asr_text 的地方
grep -n "asr_text" examples/chinese_examples.py
```

**驗收標準**:
- [ ] 範例代碼使用新的參數名
- [ ] 範例可以正常運行

---

### Task 2.4: 運行完整測試套件

**命令**:
```bash
# 運行中文測試
uv run pytest tests/test_chinese_corrector.py -v

# 運行所有測試
uv run pytest tests/ -v

# 檢查覆蓋率
uv run pytest --cov=src/phonofix tests/
```

**驗收標準**:
- [ ] 所有中文測試通過
- [ ] 所有測試通過（沒有破壞其他模組）
- [ ] 測試覆蓋率維持 >90%

---

## ✅ Phase 3: 重構 EnglishCorrector 和 JapaneseCorrector

**優先級**: 🟡 P1 - 高
**預估時間**: 15 分鐘
**風險**: 🟢 低（無破壞性變更）

### Task 3.1: 修改 EnglishCorrector

**文件路徑**: `src/phonofix/languages/english/corrector.py`

**變更**: 添加繼承
```python
# 修改前
class EnglishCorrector:
    """英文修正器"""

# 修改後
from phonofix.core import BaseCorrector

class EnglishCorrector(BaseCorrector):
    """英文修正器（繼承 BaseCorrector）"""
```

**驗收標準**:
- [ ] EnglishCorrector 繼承 BaseCorrector
- [ ] 現有接口已經符合（不需要修改 correct() 方法）
- [ ] 英文測試全部通過

---

### Task 3.2: 修改 JapaneseCorrector

**文件路徑**: `src/phonofix/languages/japanese/corrector.py`

**變更**: 添加繼承
```python
# 修改前
class JapaneseCorrector:
    """日文修正器"""

# 修改後
from phonofix.core import BaseCorrector

class JapaneseCorrector(BaseCorrector):
    """日文修正器（繼承 BaseCorrector）"""
```

**驗收標準**:
- [ ] JapaneseCorrector 繼承 BaseCorrector
- [ ] 現有接口已經符合（不需要修改 correct() 方法）
- [ ] 日文測試全部通過

---

### Task 3.3: 運行測試驗證

**命令**:
```bash
# 英文測試
uv run pytest tests/test_english_corrector.py -v

# 日文測試
uv run pytest tests/test_japanese_corrector.py -v

# 所有測試
uv run pytest tests/ -v
```

**驗收標準**:
- [ ] 英文測試全部通過
- [ ] 日文測試全部通過
- [ ] 所有測試通過

---

## 📝 Phase 4: 更新 UnifiedCorrector

**優先級**: 🟡 P1 - 高
**預估時間**: 15 分鐘
**風險**: 🟢 低

### Task 4.1: 更新類型註解

**文件路徑**: `src/phonofix/correction/unified_corrector.py`

**變更**: 使用 BaseCorrector 替代 CorrectorProtocol（可選，保留 Protocol 也可）

```python
# 可以選擇以下任一方式：

# 方式 1: 繼續使用 Protocol（推薦，保持靈活性）
from phonofix.correction.protocol import CorrectorProtocol
correctors: Dict[str, CorrectorProtocol]

# 方式 2: 使用 ABC（更嚴格）
from phonofix.core import BaseCorrector
correctors: Dict[str, BaseCorrector]

# 方式 3: 使用 Union（最靈活）
from typing import Union
from phonofix.core import BaseCorrector
from phonofix.correction.protocol import CorrectorProtocol
correctors: Dict[str, Union[BaseCorrector, CorrectorProtocol]]
```

**建議**: 保持使用 Protocol，因為 UnifiedCorrector 是協調層，保持靈活性更好。

**驗收標準**:
- [ ] 類型註解更新（或確認不需要更新）
- [ ] UnifiedCorrector 測試全部通過

---

### Task 4.2: 運行 UnifiedCorrector 測試

**命令**:
```bash
uv run pytest tests/test_unified_corrector.py -v
```

**驗收標準**:
- [ ] 所有 Unified 測試通過

---

## 📚 Phase 5: 更新文檔

**優先級**: 🟢 P2 - 中等
**預估時間**: 45 分鐘
**風險**: 🟢 低

### Task 5.1: 更新 CLAUDE.md 架構說明

**文件路徑**: `CLAUDE.md`

**變更 1: 更新架構圖**
```markdown
## Architecture

### Module Structure

src/phonofix/
├── core/                          # Language abstraction layer
│   ├── phonetic_interface.py      # PhoneticSystem abstract interface
│   ├── tokenizer_interface.py     # Tokenizer abstract interface
│   ├── corrector_interface.py     # BaseCorrector abstract interface (NEW!)
│   └── fuzzy_generator_interface.py # BaseFuzzyGenerator abstract interface
```

**變更 2: 更新 Critical Architecture Decisions**
```markdown
### Critical Architecture Decisions

**Singleton Pattern for Backends**: ...

**Language Abstraction Layer**:
- `PhoneticSystem` interface unifies different phonetic systems
- `Tokenizer` interface handles character-level vs word-level tokenization
- `BaseCorrector` interface unifies correction logic (NEW!)
- `LanguageRouter` handles mixed-language text segmentation
```

**變更 3: 添加接口一致性說明**
```markdown
### Interface Consistency

All core components follow ABC pattern:
- ✅ `PhoneticSystem(ABC)` in `core/phonetic_interface.py`
- ✅ `Tokenizer(ABC)` in `core/tokenizer_interface.py`
- ✅ `BaseFuzzyGenerator(ABC)` in `core/fuzzy_generator_interface.py`
- ✅ `BaseCorrector(ABC)` in `core/corrector_interface.py` (0.3.0+)
- ✅ `CorrectorEngine(ABC)` in `engine/base.py`

This ensures:
- Compile-time interface checking
- Consistent method signatures across languages
- Shared implementation patterns
- Clear documentation contracts
```

**驗收標準**:
- [ ] 架構圖包含 BaseCorrector
- [ ] Critical Architecture Decisions 更新
- [ ] 添加接口一致性說明

---

### Task 5.2: 更新 README.md

**文件路徑**: `README.md`

**搜尋**: 檢查是否有使用 `asr_text` 的範例

```bash
grep -n "asr_text" README.md
```

**變更**: 如果有，替換為 `text`

**驗收標準**:
- [ ] README.md 不包含 `asr_text` 參數
- [ ] 所有範例使用新的參數名

---

### Task 5.3: 更新 README.zh-TW.md

**文件路徑**: `README.zh-TW.md`

**操作**: 與 README.md 相同

**驗收標準**:
- [ ] README.zh-TW.md 不包含 `asr_text` 參數
- [ ] 所有範例使用新的參數名

---

### Task 5.4: 檢查並更新所有範例文件

**文件列表**:
- `examples/chinese_examples.py` (已在 Phase 2 處理)
- `examples/english_examples.py`
- `examples/japanese_examples.py`
- `examples/mixed_language_examples.py`
- `examples/realtime_streaming_examples.py`

**命令**:
```bash
# 搜尋所有範例文件中的 asr_text
grep -rn "asr_text" examples/
```

**驗收標準**:
- [ ] 所有範例文件更新完成
- [ ] 所有範例可以正常運行

---

### Task 5.5: 創建遷移指南（可選）

**文件路徑**: `MIGRATION_0.2_TO_0.3.md`

**內容**:
```markdown
# Migration Guide: 0.2.0 → 0.3.0

## Breaking Changes

### ChineseCorrector: `asr_text` parameter renamed to `text`

**Impact**: Users using keyword argument `asr_text=` need to update.

**Before (0.2.0)**:
```python
result = corrector.correct(asr_text="我在北車")
```

**After (0.3.0)**:
```python
result = corrector.correct(text="我在北車")
# or use positional argument (recommended)
result = corrector.correct("我在北車")
```

**Who is affected**:
- Users using `asr_text=` keyword argument (~10%)
- Users using positional argument are NOT affected

## Non-breaking Changes

### New BaseCorrector ABC

All correctors now inherit from `BaseCorrector(ABC)`:
- ChineseCorrector
- EnglishCorrector
- JapaneseCorrector

**Benefit**: Compile-time interface checking, better IDE support.

## Upgrade Steps

1. Update phonofix:
   ```bash
   pip install --upgrade phonofix
   ```

2. Search and replace (if using keyword arguments):
   ```bash
   # Find all uses
   grep -rn "asr_text=" your_project/

   # Replace
   sed -i 's/asr_text=/text=/g' your_project/*.py
   ```

3. Run tests to verify.

## Questions?

Please open an issue at https://github.com/YOUR_REPO/issues
```

**驗收標準**:
- [ ] 遷移指南創建完成
- [ ] 包含清晰的升級步驟

---

## 🏷️ Phase 6: 版本號更新

**優先級**: 🟢 P2 - 中等
**預估時間**: 10 分鐘
**風險**: 🟢 低

### Task 6.1: 更新 pyproject.toml

**文件路徑**: `pyproject.toml`

**變更**:
```toml
# 修改前
version = "0.2.0"

# 修改後
version = "0.3.0"
```

**驗收標準**:
- [ ] 版本號更新為 0.3.0

---

### Task 6.2: 更新 CHANGELOG.md

**文件路徑**: `CHANGELOG.md`

**添加新版本記錄**:
```markdown
## [0.3.0] - 2025-12-09

### 💥 Breaking Changes
- **ChineseCorrector**: Renamed `asr_text` parameter to `text` for consistency (#XX)
  - Users using keyword argument `asr_text=` need to update to `text=`
  - Positional argument users are not affected

### ✨ Features
- Added `BaseCorrector(ABC)` in `core/corrector_interface.py` (#XX)
  - All correctors now inherit from unified base class
  - Enforces consistent method signatures across languages
  - Improves IDE support and type checking

### 📝 Documentation
- Updated architecture documentation with BaseCorrector
- Added interface consistency section to CLAUDE.md
- Created migration guide: MIGRATION_0.2_TO_0.3.md

### 🔧 Internal
- ChineseCorrector now supports `full_context` parameter (optional)
- Improved architecture consistency across all core components

## [0.2.0] - 2025-12-09
(previous entries...)
```

**驗收標準**:
- [ ] CHANGELOG.md 包含 0.3.0 版本記錄
- [ ] 記錄所有重要變更

---

## ✅ 最終驗收

**優先級**: 🔴 P0 - 最高

### Task 7.1: 運行完整測試套件

**命令**:
```bash
# 運行所有測試
uv run pytest tests/ -v

# 檢查覆蓋率
uv run pytest --cov=src/phonofix tests/ --cov-report=html

# 類型檢查
uv run mypy src/phonofix
```

**驗收標準**:
- [ ] 所有測試通過（46/46，允許 28 個跳過）
- [ ] 測試覆蓋率 >90%
- [ ] mypy 類型檢查通過（無錯誤）

---

### Task 7.2: 手動驗證範例

**命令**:
```bash
# 中文範例
uv run python examples/chinese_examples.py

# 英文範例（需要 espeak-ng）
uv run python examples/english_examples.py

# 日文範例（需要 cutlet）
uv run python examples/japanese_examples.py

# 混合語言範例
uv run python examples/mixed_language_examples.py
```

**驗收標準**:
- [ ] 所有範例正常運行
- [ ] 輸出結果正確

---

### Task 7.3: 檢查代碼品質

**命令**:
```bash
# 格式化代碼
uv run ruff format .

# Lint 檢查
uv run ruff check .
```

**驗收標準**:
- [ ] 代碼格式化完成
- [ ] 無 linting 錯誤

---

### Task 7.4: 創建完成報告

**文件路徑**: `CORRECTOR_REFACTORING_COMPLETION_REPORT.md`

**內容**:
```markdown
# Corrector 重構完成報告

**完成日期**: 2025-12-09
**版本**: 0.2.0 → 0.3.0

## ✅ 完成任務

- [x] Phase 1: 創建 BaseCorrector ABC
- [x] Phase 2: 重構 ChineseCorrector
- [x] Phase 3: 重構 EnglishCorrector 和 JapaneseCorrector
- [x] Phase 4: 更新 UnifiedCorrector
- [x] Phase 5: 更新文檔
- [x] Phase 6: 版本號更新
- [x] 最終驗收

## 📊 測試結果

- 總測試數: 46/46 通過（28 個跳過）
- 測試覆蓋率: >90%
- mypy 類型檢查: 通過

## 💥 破壞性變更

- ChineseCorrector: `asr_text` → `text` 參數重命名

## 📚 文檔更新

- ✅ CLAUDE.md 架構說明更新
- ✅ README.md 範例更新
- ✅ CHANGELOG.md 版本記錄添加
- ✅ 遷移指南創建

## 🎯 效益

- ✅ 架構一致性提升
- ✅ 接口統一
- ✅ 類型檢查增強
- ✅ 文檔改善
```

**驗收標準**:
- [ ] 完成報告創建
- [ ] 記錄所有完成的任務

---

## 📋 檢查清單

### 必須完成（P0）
- [ ] Task 1.1: 創建 core/corrector_interface.py
- [ ] Task 1.2: 更新 core/__init__.py
- [ ] Task 1.3: 驗證 BaseCorrector 可導入
- [ ] Task 2.1: 修改 ChineseCorrector 類定義
- [ ] Task 2.2: 更新 ChineseCorrector 測試
- [ ] Task 2.4: 運行完整測試套件
- [ ] Task 7.1: 運行完整測試套件（最終）

### 建議完成（P1）
- [ ] Task 3.1: 修改 EnglishCorrector
- [ ] Task 3.2: 修改 JapaneseCorrector
- [ ] Task 3.3: 運行測試驗證
- [ ] Task 4.1: 更新 UnifiedCorrector 類型註解
- [ ] Task 4.2: 運行 UnifiedCorrector 測試

### 可選完成（P2）
- [ ] Task 2.3: 更新 ChineseCorrector 使用範例
- [ ] Task 5.1-5.5: 更新所有文檔
- [ ] Task 6.1-6.2: 版本號更新
- [ ] Task 7.2-7.4: 最終驗收

---

## 🚨 注意事項

### 破壞性變更提醒
⚠️ **重要**: `asr_text` → `text` 是破壞性變更
- 影響使用關鍵字參數的用戶
- 需要在 CHANGELOG 和文檔中明確標註

### 測試策略
- 每個 Phase 完成後運行測試
- 不要等到最後才測試
- 發現問題立即修復

### Git 提交建議
```bash
# Phase 1
git commit -m "feat(core): add BaseCorrector ABC interface

- Create core/corrector_interface.py
- Define unified corrector interface
- Add abstract methods: correct(), _from_engine()"

# Phase 2
git commit -m "refactor(chinese)!: rename asr_text to text parameter

BREAKING CHANGE: ChineseCorrector.correct() parameter renamed
- asr_text → text (for consistency)
- Add full_context optional parameter
- Update all tests"

# Phase 3
git commit -m "refactor(corrector): inherit BaseCorrector for all languages

- EnglishCorrector inherits BaseCorrector
- JapaneseCorrector inherits BaseCorrector
- No breaking changes"

# Phase 5
git commit -m "docs: update architecture and API documentation

- Update CLAUDE.md with BaseCorrector
- Update README examples
- Add MIGRATION_0.2_TO_0.3.md"

# Phase 6
git commit -m "chore: bump version to 0.3.0

- Update pyproject.toml version
- Update CHANGELOG.md"
```

---

## 📞 支援

如果在執行過程中遇到問題：
1. 檢查錯誤訊息和堆疊追蹤
2. 確認所有依賴已安裝（`uv sync`）
3. 查看測試輸出找出具體失敗原因
4. 回滾到上一個可用狀態（使用 git）

---

**預祝重構順利！** 🎉

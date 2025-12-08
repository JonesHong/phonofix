# Migration Guide: 0.2.0 → 0.3.0

本文檔說明從 Phonofix 0.2.0 遷移到 0.3.0 的步驟。

## 💥 破壞性變更

### ChineseCorrector 參數重命名

**變更內容**: `ChineseCorrector.correct()` 方法的第一個參數從 `asr_text` 改為 `text`

**影響範圍**:
- ✅ **不受影響**: 使用位置參數的代碼（約 90% 用戶）
- ⚠️ **需要更新**: 使用關鍵字參數 `asr_text=` 的代碼

### 遷移步驟

#### 情況 1: 使用位置參數（不需要修改）

```python
# ✅ 0.2.0 - 可以繼續使用
corrector.correct("我在北車")

# ✅ 0.3.0 - 完全相同
corrector.correct("我在北車")
```

#### 情況 2: 使用關鍵字參數（需要修改）

```python
# ❌ 0.2.0 - 舊的方式
corrector.correct(asr_text="我在北車", silent=True)

# ✅ 0.3.0 - 新的方式
corrector.correct(text="我在北車", silent=True)
```

#### 情況 3: 僅位置參數（推薦）

```python
# ✅ 推薦寫法（適用於 0.2.0 和 0.3.0）
corrector.correct("我在北車", None, True)
# 或更清楚的寫法
corrector.correct("我在北車", silent=True)
```

### 兼容性檢查

使用以下腳本檢查您的代碼是否使用了 `asr_text` 關鍵字參數：

```bash
# 搜尋可能需要更新的代碼
grep -r "asr_text=" your_project_directory/

# 或使用 Python
python -c "
import ast
import sys

# 檢查特定文件
with open('your_script.py', 'r') as f:
    tree = ast.parse(f.read())

for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        for keyword in node.keywords:
            if keyword.arg == 'asr_text':
                print(f'Found asr_text at line {node.lineno}')
"
```

## ✨ 新功能

### BaseCorrector ABC

**新增**: 所有修正器現在繼承自 `BaseCorrector` 抽象基類

**優點**:
- ✅ 編譯時接口檢查（IDE 支援更好）
- ✅ 統一的方法簽名
- ✅ 更好的類型安全
- ✅ 架構一致性

**影響**: 無需修改使用者代碼

### 統一的 `full_context` 參數

**新增**: 所有 `correct()` 方法現在支援 `full_context` 參數

```python
# 0.3.0 新功能
corrector.correct(
    text="我在北車",
    full_context="昨天我在北車買了牛奶",  # 完整上下文
    silent=False
)
```

**用途**:
- 用於 `keywords` 和 `exclude_when` 條件判斷
- 未來可能用於更複雜的上下文相關修正

**兼容性**:
- 此參數為可選參數，不使用不會影響現有功能
- 目前 ChineseCorrector 尚未完全使用此參數

## 📝 類型註解更新

### UnifiedCorrector

**變更**: 更新類型註解以支援 `BaseCorrector`

```python
# 0.2.0
correctors: Dict[str, CorrectorProtocol]

# 0.3.0
correctors: Dict[str, Union[BaseCorrector, CorrectorProtocol]]
```

**影響**:
- 僅影響類型檢查工具（mypy, pyright）
- 運行時行為無變化

## 🔧 內部改進

### 架構一致性

所有核心組件現在使用 ABC 模式：

| 組件 | 文件位置 | 基類 | 狀態 |
|------|---------|------|------|
| PhoneticSystem | `core/phonetic_interface.py` | ABC | ✅ |
| Tokenizer | `core/tokenizer_interface.py` | ABC | ✅ |
| BaseFuzzyGenerator | `core/fuzzy_generator_interface.py` | ABC | ✅ |
| **BaseCorrector** | `core/corrector_interface.py` | **ABC** | **✅ 新增** |
| CorrectorEngine | `engine/base.py` | ABC | ✅ |

## 📊 測試與驗證

### 運行測試確保兼容性

```bash
# 安裝新版本
pip install --upgrade phonofix

# 運行您的測試套件
pytest tests/

# 或手動測試
python your_script.py
```

### 預期結果

- ✅ 使用位置參數的代碼應該完全正常運作
- ✅ 所有功能行為與 0.2.0 一致
- ⚠️ 使用 `asr_text=` 關鍵字參數的代碼會報錯

### 常見錯誤處理

#### TypeError: got an unexpected keyword argument 'asr_text'

```python
# ❌ 錯誤
corrector.correct(asr_text="我在北車")

# ✅ 修正
corrector.correct(text="我在北車")
# 或
corrector.correct("我在北車")  # 推薦
```

## 🎯 最佳實踐

### 推薦的調用方式

```python
# ✅ 最佳: 使用位置參數（簡潔）
corrector.correct("我在北車")
corrector.correct("我在北車", None, True)  # 帶 silent

# ✅ 良好: 僅對需要的參數使用關鍵字
corrector.correct("我在北車", silent=True)

# ✅ 良好: 完整的關鍵字參數（最清楚）
corrector.correct(
    text="我在北車",
    full_context=None,
    silent=False
)

# ⚠️ 避免: 僅第一個參數使用關鍵字
corrector.correct(text="我在北車")  # 可行但不必要
```

## 📚 額外資源

- [完整 API 文檔](references/API_Documentation.md)
- [架構說明](CLAUDE.md)
- [重構分析報告](CORRECTOR_ARCHITECTURE_ANALYSIS.md)
- [進度報告](CORRECTOR_REFACTORING_PROGRESS_REPORT.md)

## 🆘 獲取幫助

如果遇到遷移問題:

1. 檢查本文檔的「常見錯誤處理」章節
2. 查看 [GitHub Issues](https://github.com/yourusername/phonofix/issues)
3. 運行相容性檢查腳本
4. 回滾到 0.2.0 如果無法立即遷移:
   ```bash
   pip install phonofix==0.2.0
   ```

## 📅 版本時間線

- **0.2.0**: 2025-10-XX - 日文支援與跨語言映射
- **0.3.0**: 2025-12-09 - BaseCorrector ABC 與接口統一
- **未來版本**: 規劃中的功能請參考 TODO 文件

---

**總結**: 大多數用戶無需任何修改。僅使用 `asr_text=` 關鍵字參數的少數用戶需要更新為 `text=`。

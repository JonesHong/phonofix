# 更新日誌

## v1.0.1 - 2025-01-XX (Bug 修正版)

### 🐛 Bug 修正
- **修正 Unicode 轉義錯誤**: 將 `\\u4e00` 改為 `\u4e00`,修復漢字檢測失效問題
  - 影響檔案: `correction/corrector.py` (line 255)
  - 影響檔案: `dictionary/generator.py` (lines 73, 91)
  - 症狀: 所有校正功能都無法正常運作,因為漢字無法被正確識別

### ✅ 驗證通過
- ✅ 模糊音詞典生成功能正常
- ✅ 同音詞過濾功能正常
- ✅ ASR 文本校正功能正常
- ✅ 上下文關鍵字校正功能正常
- ✅ 權重系統功能正常
- ✅ 豁免清單功能正常
- ✅ 台灣國語特徵處理 (n/l, r/l, f/h) 正常
- ✅ 韻母模糊匹配功能正常
- ✅ 英文混用詞處理功能正常
- ✅ 綜合測試通過

### 📝 測試範例
所有 10 個範例都已驗證通過:
1. ✅ 模糊音詞典生成
2. ✅ 同音詞過濾
3. ✅ 開啟歸一化 (修正為標準詞)
4. ✅ 關閉歸一化 (保留簡稱)
5. ✅ 上下文關鍵字校正
6. ✅ 英文混用詞
7. ✅ 台灣國語特徵 (n/l, r/l, f/h 混淆)
8. ✅ 韻母模糊測試 (ue/ie, uan/uang)
9. ✅ 綜合測試 (多種混淆規則)
10. ✅ 權重系統測試

---

## v1.0.0 - 2025-01-XX (初始版本)

### ✨ 新功能
- 🎯 整合 `corrector.py` 和 `fuzzy_toolbox.py` 成統一工具包
- 📦 模組化設計: core, dictionary, correction
- 🔧 共用配置: PhoneticConfig 統一管理拼音規則
- 🛠️ 工具函數: PhoneticUtils 提供通用拼音處理
- 📚 完整文件: README.md 和 10 個範例
- 🧪 功能驗證: examples.py 包含所有使用場景

### 🏗️ 架構設計
```
chinese_text_corrector/
├── core/              # 核心配置與工具
├── dictionary/        # 詞典生成
└── correction/        # 文本校正
```

### 📖 主要類別
- `ChineseTextCorrector`: ASR 文本校正器
- `FuzzyDictionaryGenerator`: 模糊音詞典生成器
- `PhoneticConfig`: 拼音配置類別
- `PhoneticUtils`: 拼音工具類別

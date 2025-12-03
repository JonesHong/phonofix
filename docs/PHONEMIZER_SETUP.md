# phonemizer + espeak-ng 安裝指南

本專案使用 `phonemizer` 搭配 `espeak-ng` 作為英文 G2P（Grapheme-to-Phoneme）引擎。

## 快速安裝（推薦）

我們提供了自動化腳本，可一鍵完成安裝與環境設定：

### Windows

```powershell
# 方法一：使用 PowerShell 腳本（推薦）
# 以管理員權限執行 PowerShell，然後執行：
.\scripts\setup_espeak.ps1

# 方法二：使用 Batch 腳本
# 雙擊執行 scripts\setup_espeak_windows.bat
```

### macOS / Linux

```bash
# 給予執行權限
chmod +x scripts/setup_espeak.sh

# 執行腳本
./scripts/setup_espeak.sh
```

腳本會自動：
1. 偵測/安裝 espeak-ng
2. 設定必要的環境變數
3. 驗證 phonemizer 是否可正常運作

---

## 手動安裝步驟

如果自動腳本無法使用，可按以下步驟手動安裝：

## 系統需求

- Python >= 3.9
- espeak-ng (系統層級安裝)

## 安裝步驟

### 1. 安裝 espeak-ng

#### Windows

1. 從官方 GitHub 下載最新版本:
   - https://github.com/espeak-ng/espeak-ng/releases
   - 下載 `espeak-ng-X64.msi` (64位元) 或 `espeak-ng-X86.msi` (32位元)

2. 執行安裝程式，使用預設安裝路徑：
   - `C:\Program Files\eSpeak NG\`

3. **重要**: 設定環境變數 `PHONEMIZER_ESPEAK_LIBRARY`：
   
   方法一：透過 PowerShell (臨時設定)
   ```powershell
   $env:PHONEMIZER_ESPEAK_LIBRARY = "C:\Program Files\eSpeak NG\libespeak-ng.dll"
   ```
   
   方法二：永久設定
   - 開啟「系統內容」「進階」「環境變數」
   - 新增使用者變數：
     - 變數名稱: `PHONEMIZER_ESPEAK_LIBRARY`
     - 變數值: `C:\Program Files\eSpeak NG\libespeak-ng.dll`

4. 驗證安裝：
   ```powershell
   espeak-ng --version
   # 應顯示: eSpeak NG text-to-speech: 1.52-dev ...
   ```

#### macOS

```bash
brew install espeak-ng
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get install espeak-ng
```

#### Linux (Fedora/CentOS)

```bash
sudo dnf install espeak-ng
```

### 2. 安裝 Python 套件

```bash
pip install phonemizer
```

或安裝本專案的完整依賴：

```bash
pip install -e .
```

## 驗證安裝

執行以下 Python 程式碼驗證安裝是否成功：

```python
from phonemizer import phonemize

# 測試基本功能
result = phonemize("hello world", language="en-us", backend="espeak")
print(result)  # 應輸出: həloʊ wɜːld 或類似的 IPA
```

如果出現錯誤 `RuntimeError: espeak not installed on your system`，請檢查：

1. espeak-ng 是否已正確安裝
2. (Windows) `PHONEMIZER_ESPEAK_LIBRARY` 環境變數是否已設定
3. (Windows) 重新啟動終端機或 IDE

## 常見問題

### Q: Windows 上出現 "failed to find espeak library" 錯誤

A: 這是因為 phonemizer 找不到 `libespeak-ng.dll`。請確認：
1. espeak-ng 已安裝
2. 已設定 `PHONEMIZER_ESPEAK_LIBRARY` 環境變數指向 DLL 檔案

### Q: 本專案如何自動處理這個問題？

A: 本專案的 `phonetic_impl.py` 會自動嘗試偵測 espeak-ng 的安裝位置並設定環境變數。如果偵測失敗，會顯示明確的錯誤訊息指引您手動設定。

### Q: 如何檢查 phonemizer 是否可用？

A: 使用本專案提供的函式：

```python
from multi_language_corrector.languages.english.phonetic_impl import is_phonemizer_available

if is_phonemizer_available():
    print("phonemizer 已就緒")
else:
    print("phonemizer 不可用，請檢查 espeak-ng 安裝")
```

## 效能說明

- phonemizer + espeak-ng 的效能非常好，底層使用 C/C++ 實作
- 本專案使用 LRU cache 快取轉換結果，避免重複計算
- 可使用 `warmup_ipa_cache()` 預熱常見詞彙，進一步提升效能

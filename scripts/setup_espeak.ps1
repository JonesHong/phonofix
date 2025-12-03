# ============================================================
# espeak-ng 安裝與環境設定腳本 (Windows PowerShell)
# ============================================================
# 本腳本會：
# 1. 檢查 espeak-ng 是否已安裝
# 2. 設定 PHONEMIZER_ESPEAK_LIBRARY 環境變數
# 3. 驗證 phonemizer 是否可正常運作
# ============================================================
# 使用方式：
#   以管理員權限執行 PowerShell，然後執行：
#   .\scripts\setup_espeak.ps1
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  espeak-ng 安裝與環境設定腳本 (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 檢查是否以管理員權限執行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[警告] 建議以管理員權限執行此腳本以設定系統環境變數" -ForegroundColor Yellow
    Write-Host "       右鍵點擊 PowerShell，選擇「以系統管理員身分執行」" -ForegroundColor Yellow
    Write-Host ""
}

# 常見的 espeak-ng 安裝路徑
$espeakPaths = @(
    "C:\Program Files\eSpeak NG",
    "C:\Program Files (x86)\eSpeak NG"
)
$espeakDll = "libespeak-ng.dll"
$foundDll = $null

Write-Host "[1/4] 檢查 espeak-ng 安裝狀態..." -ForegroundColor Blue
Write-Host ""

foreach ($path in $espeakPaths) {
    $dllPath = Join-Path $path $espeakDll
    if (Test-Path $dllPath) {
        $foundDll = $dllPath
        Write-Host "[OK] 找到 espeak-ng: $path" -ForegroundColor Green
        break
    }
}

if (-not $foundDll) {
    Write-Host "[錯誤] 未找到 espeak-ng 安裝" -ForegroundColor Red
    Write-Host ""
    Write-Host "請先安裝 espeak-ng:" -ForegroundColor Yellow
    Write-Host "  1. 前往 https://github.com/espeak-ng/espeak-ng/releases"
    Write-Host "  2. 下載 espeak-ng-X64.msi (64位元) 或 espeak-ng-X86.msi (32位元)"
    Write-Host "  3. 執行安裝程式，使用預設路徑"
    Write-Host "  4. 安裝完成後，重新執行此腳本"
    Write-Host ""
    
    $openBrowser = Read-Host "是否開啟下載頁面? (y/n)"
    if ($openBrowser -eq "y" -or $openBrowser -eq "Y") {
        Start-Process "https://github.com/espeak-ng/espeak-ng/releases"
    }
    exit 1
}

Write-Host ""
Write-Host "[2/4] 設定環境變數 PHONEMIZER_ESPEAK_LIBRARY..." -ForegroundColor Blue
Write-Host "      路徑: $foundDll" -ForegroundColor Gray
Write-Host ""

try {
    # 設定使用者環境變數 (永久)
    [Environment]::SetEnvironmentVariable("PHONEMIZER_ESPEAK_LIBRARY", $foundDll, "User")
    Write-Host "[OK] 已設定使用者環境變數 (永久生效)" -ForegroundColor Green
} catch {
    Write-Host "[警告] 無法設定永久環境變數: $_" -ForegroundColor Yellow
}

# 設定當前 session 的環境變數
$env:PHONEMIZER_ESPEAK_LIBRARY = $foundDll
Write-Host "[OK] 已設定當前 session 環境變數" -ForegroundColor Green

Write-Host ""
Write-Host "[3/4] 驗證 espeak-ng 執行檔..." -ForegroundColor Blue
Write-Host ""

$espeakExe = Get-Command espeak-ng -ErrorAction SilentlyContinue
if ($espeakExe) {
    Write-Host "[OK] espeak-ng 已在 PATH 中" -ForegroundColor Green
    & espeak-ng --version
} else {
    Write-Host "[警告] espeak-ng 不在 PATH 中，但 DLL 已設定，phonemizer 應可正常運作" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[4/4] 驗證 phonemizer 整合..." -ForegroundColor Blue
Write-Host ""

try {
    $result = python -c "from phonemizer import phonemize; print(phonemize('hello world', language='en-us', backend='espeak'))" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] phonemizer 測試成功: $result" -ForegroundColor Green
    } else {
        throw "phonemizer 測試失敗"
    }
} catch {
    Write-Host "[警告] phonemizer 測試失敗，請確認已安裝 phonemizer:" -ForegroundColor Yellow
    Write-Host "       pip install phonemizer" -ForegroundColor Gray
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  設定完成！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "環境變數已設定，您可以開始使用 phonemizer 了。" -ForegroundColor White
Write-Host ""
Write-Host "注意：如果在其他終端機視窗中使用，請先重新開啟終端機" -ForegroundColor Yellow
Write-Host "      或在 PowerShell 中執行以下命令重新載入環境變數:" -ForegroundColor Yellow
Write-Host ""
Write-Host "      `$env:PHONEMIZER_ESPEAK_LIBRARY = `"$foundDll`"" -ForegroundColor Gray
Write-Host ""

Read-Host "按 Enter 鍵結束"

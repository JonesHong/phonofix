@echo off
REM ============================================================
REM espeak-ng 安裝與環境設定腳本 (Windows)
REM ============================================================
REM 本腳本會：
REM 1. 檢查 espeak-ng 是否已安裝
REM 2. 設定 PHONEMIZER_ESPEAK_LIBRARY 環境變數
REM 3. 驗證 phonemizer 是否可正常運作
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   espeak-ng 安裝與環境設定腳本 (Windows)
echo ============================================================
echo.

REM 檢查是否以管理員權限執行
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 建議以管理員權限執行此腳本以設定系統環境變數
    echo        右鍵點擊此腳本，選擇「以系統管理員身分執行」
    echo.
)

REM 常見的 espeak-ng 安裝路徑
set "ESPEAK_PATH_64=C:\Program Files\eSpeak NG"
set "ESPEAK_PATH_32=C:\Program Files (x86)\eSpeak NG"
set "ESPEAK_DLL=libespeak-ng.dll"
set "FOUND_DLL="

echo [1/4] 檢查 espeak-ng 安裝狀態...
echo.

REM 檢查 64 位元路徑
if exist "%ESPEAK_PATH_64%\%ESPEAK_DLL%" (
    set "FOUND_DLL=%ESPEAK_PATH_64%\%ESPEAK_DLL%"
    echo [OK] 找到 espeak-ng (64-bit): %ESPEAK_PATH_64%
)

REM 檢查 32 位元路徑
if exist "%ESPEAK_PATH_32%\%ESPEAK_DLL%" (
    set "FOUND_DLL=%ESPEAK_PATH_32%\%ESPEAK_DLL%"
    echo [OK] 找到 espeak-ng (32-bit): %ESPEAK_PATH_32%
)

REM 如果都沒找到
if "%FOUND_DLL%"=="" (
    echo [錯誤] 未找到 espeak-ng 安裝
    echo.
    echo 請先安裝 espeak-ng:
    echo   1. 前往 https://github.com/espeak-ng/espeak-ng/releases
    echo   2. 下載 espeak-ng-X64.msi (64位元) 或 espeak-ng-X86.msi (32位元)
    echo   3. 執行安裝程式，使用預設路徑
    echo   4. 安裝完成後，重新執行此腳本
    echo.
    echo 按任意鍵開啟下載頁面...
    pause >nul
    start https://github.com/espeak-ng/espeak-ng/releases
    exit /b 1
)

echo.
echo [2/4] 設定環境變數 PHONEMIZER_ESPEAK_LIBRARY...
echo      路徑: %FOUND_DLL%
echo.

REM 設定使用者環境變數 (永久)
setx PHONEMIZER_ESPEAK_LIBRARY "%FOUND_DLL%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] 已設定使用者環境變數 (永久生效)
) else (
    echo [警告] 無法設定永久環境變數，將只設定當前 session
)

REM 設定當前 session 的環境變數
set "PHONEMIZER_ESPEAK_LIBRARY=%FOUND_DLL%"
echo [OK] 已設定當前 session 環境變數

echo.
echo [3/4] 驗證 espeak-ng 執行檔...
echo.

where espeak-ng >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] espeak-ng 已在 PATH 中
    espeak-ng --version
) else (
    echo [警告] espeak-ng 不在 PATH 中，但 DLL 已設定，phonemizer 應可正常運作
)

echo.
echo [4/4] 驗證 phonemizer 整合...
echo.

python -c "from phonemizer import phonemize; print('[OK] phonemizer 測試:', phonemize('hello world', language='en-us', backend='espeak'))" 2>nul
if %errorlevel% neq 0 (
    echo [警告] phonemizer 測試失敗，請確認已安裝 phonemizer:
    echo        pip install phonemizer
) else (
    echo.
    echo ============================================================
    echo   設定完成！
    echo ============================================================
    echo.
    echo 環境變數已設定，您可以開始使用 phonemizer 了。
    echo.
    echo 注意：如果在其他終端機視窗中使用，請先重新開啟終端機
    echo       或執行以下命令重新載入環境變數:
    echo.
    echo       $env:PHONEMIZER_ESPEAK_LIBRARY = "%FOUND_DLL%"
    echo.
)

echo.
pause

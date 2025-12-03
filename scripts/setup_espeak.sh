#!/bin/bash
# ============================================================
# espeak-ng 安裝與環境設定腳本 (macOS / Linux)
# ============================================================
# 本腳本會：
# 1. 偵測作業系統並安裝 espeak-ng
# 2. 設定 PHONEMIZER_ESPEAK_LIBRARY 環境變數 (如需要)
# 3. 驗證 phonemizer 是否可正常運作
# ============================================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "============================================================"
echo "  espeak-ng 安裝與環境設定腳本 (macOS / Linux)"
echo "============================================================"
echo ""

# 偵測作業系統
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # 進一步偵測 Linux 發行版
        if [ -f /etc/debian_version ]; then
            echo "debian"
        elif [ -f /etc/redhat-release ]; then
            echo "redhat"
        elif [ -f /etc/arch-release ]; then
            echo "arch"
        else
            echo "linux"
        fi
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo -e "${BLUE}[INFO]${NC} 偵測到作業系統: $OS"
echo ""

# 步驟 1: 安裝 espeak-ng
echo -e "${BLUE}[1/4]${NC} 檢查/安裝 espeak-ng..."
echo ""

install_espeak() {
    case $OS in
        macos)
            if command -v brew &> /dev/null; then
                if brew list espeak-ng &> /dev/null; then
                    echo -e "${GREEN}[OK]${NC} espeak-ng 已安裝 (via Homebrew)"
                else
                    echo -e "${YELLOW}[INFO]${NC} 正在透過 Homebrew 安裝 espeak-ng..."
                    brew install espeak-ng
                    echo -e "${GREEN}[OK]${NC} espeak-ng 安裝完成"
                fi
            else
                echo -e "${RED}[錯誤]${NC} 未找到 Homebrew，請先安裝 Homebrew:"
                echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;
        debian)
            if dpkg -s espeak-ng &> /dev/null; then
                echo -e "${GREEN}[OK]${NC} espeak-ng 已安裝"
            else
                echo -e "${YELLOW}[INFO]${NC} 正在透過 apt 安裝 espeak-ng..."
                sudo apt-get update
                sudo apt-get install -y espeak-ng
                echo -e "${GREEN}[OK]${NC} espeak-ng 安裝完成"
            fi
            ;;
        redhat)
            if rpm -q espeak-ng &> /dev/null; then
                echo -e "${GREEN}[OK]${NC} espeak-ng 已安裝"
            else
                echo -e "${YELLOW}[INFO]${NC} 正在透過 dnf/yum 安裝 espeak-ng..."
                if command -v dnf &> /dev/null; then
                    sudo dnf install -y espeak-ng
                else
                    sudo yum install -y espeak-ng
                fi
                echo -e "${GREEN}[OK]${NC} espeak-ng 安裝完成"
            fi
            ;;
        arch)
            if pacman -Qs espeak-ng &> /dev/null; then
                echo -e "${GREEN}[OK]${NC} espeak-ng 已安裝"
            else
                echo -e "${YELLOW}[INFO]${NC} 正在透過 pacman 安裝 espeak-ng..."
                sudo pacman -S --noconfirm espeak-ng
                echo -e "${GREEN}[OK]${NC} espeak-ng 安裝完成"
            fi
            ;;
        *)
            echo -e "${RED}[錯誤]${NC} 無法自動安裝 espeak-ng，請手動安裝:"
            echo "  https://github.com/espeak-ng/espeak-ng"
            exit 1
            ;;
    esac
}

install_espeak

echo ""

# 步驟 2: 找到 espeak-ng 動態庫並設定環境變數
echo -e "${BLUE}[2/4]${NC} 設定環境變數..."
echo ""

find_espeak_library() {
    # macOS
    if [[ "$OS" == "macos" ]]; then
        # Homebrew 路徑
        local brew_prefix=$(brew --prefix 2>/dev/null || echo "/usr/local")
        local lib_paths=(
            "$brew_prefix/lib/libespeak-ng.dylib"
            "$brew_prefix/lib/libespeak-ng.1.dylib"
            "/usr/local/lib/libespeak-ng.dylib"
            "/opt/homebrew/lib/libespeak-ng.dylib"
        )
        for path in "${lib_paths[@]}"; do
            if [ -f "$path" ]; then
                echo "$path"
                return
            fi
        done
    else
        # Linux
        local lib_paths=(
            "/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1"
            "/usr/lib/libespeak-ng.so.1"
            "/usr/lib64/libespeak-ng.so.1"
            "/usr/local/lib/libespeak-ng.so.1"
        )
        for path in "${lib_paths[@]}"; do
            if [ -f "$path" ]; then
                echo "$path"
                return
            fi
        done
        
        # 使用 ldconfig 查找
        ldconfig -p 2>/dev/null | grep libespeak-ng | awk '{print $NF}' | head -1
    fi
}

ESPEAK_LIB=$(find_espeak_library)

if [ -n "$ESPEAK_LIB" ]; then
    echo -e "${GREEN}[OK]${NC} 找到 espeak-ng 動態庫: $ESPEAK_LIB"
    
    # 設定環境變數
    export PHONEMIZER_ESPEAK_LIBRARY="$ESPEAK_LIB"
    
    # 決定要更新哪個 shell 配置檔
    SHELL_RC=""
    if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ] || [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.profile" ]; then
        SHELL_RC="$HOME/.profile"
    fi
    
    if [ -n "$SHELL_RC" ]; then
        # 檢查是否已經設定過
        if grep -q "PHONEMIZER_ESPEAK_LIBRARY" "$SHELL_RC" 2>/dev/null; then
            echo -e "${YELLOW}[INFO]${NC} 環境變數已存在於 $SHELL_RC"
        else
            echo "" >> "$SHELL_RC"
            echo "# espeak-ng for phonemizer" >> "$SHELL_RC"
            echo "export PHONEMIZER_ESPEAK_LIBRARY=\"$ESPEAK_LIB\"" >> "$SHELL_RC"
            echo -e "${GREEN}[OK]${NC} 已將環境變數加入 $SHELL_RC"
        fi
    fi
else
    echo -e "${YELLOW}[INFO]${NC} 在 Linux/macOS 上通常不需要設定 PHONEMIZER_ESPEAK_LIBRARY"
    echo "         phonemizer 會自動找到系統安裝的 espeak-ng"
fi

echo ""

# 步驟 3: 驗證 espeak-ng
echo -e "${BLUE}[3/4]${NC} 驗證 espeak-ng..."
echo ""

if command -v espeak-ng &> /dev/null; then
    echo -e "${GREEN}[OK]${NC} espeak-ng 版本:"
    espeak-ng --version
else
    echo -e "${RED}[錯誤]${NC} espeak-ng 不在 PATH 中"
    exit 1
fi

echo ""

# 步驟 4: 驗證 phonemizer
echo -e "${BLUE}[4/4]${NC} 驗證 phonemizer 整合..."
echo ""

if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}[錯誤]${NC} 未找到 Python"
    exit 1
fi

# 檢查 phonemizer 是否已安裝
if $PYTHON -c "import phonemizer" 2>/dev/null; then
    RESULT=$($PYTHON -c "from phonemizer import phonemize; print(phonemize('hello world', language='en-us', backend='espeak'))" 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK]${NC} phonemizer 測試成功: $RESULT"
    else
        echo -e "${RED}[錯誤]${NC} phonemizer 測試失敗: $RESULT"
        exit 1
    fi
else
    echo -e "${YELLOW}[警告]${NC} phonemizer 未安裝，請執行:"
    echo "         pip install phonemizer"
fi

echo ""
echo "============================================================"
echo -e "  ${GREEN}設定完成！${NC}"
echo "============================================================"
echo ""
echo "如果這是新安裝，請重新載入 shell 配置:"
echo ""
if [ -n "$SHELL_RC" ]; then
    echo "  source $SHELL_RC"
fi
echo ""
echo "或開啟新的終端機視窗。"
echo ""

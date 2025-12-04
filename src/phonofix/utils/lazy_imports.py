"""
延遲導入管理模組 (Lazy Import Manager)

此模組負責管理可選依賴的延遲導入，確保：
1. 使用者未安裝可選依賴時，不會在 import 階段就失敗
2. 當真正需要使用這些依賴時，提供清楚的安裝指引

使用方式:
    from phonofix.utils.lazy_imports import (
        get_pypinyin,
        get_pinyin2hanzi,
        get_hanziconv,
        is_chinese_available,
        is_english_available,
    )

安裝指引:
    預設安裝 (全部): pip install phonofix
    僅中文支援: pip install "phonofix[ch]"
    僅英文支援: pip install "phonofix[en]"
    完整安裝: pip install "phonofix[all]"
"""

from typing import Optional, Callable, Any, Tuple


# =============================================================================
# 全域狀態 - 中文依賴
# =============================================================================

_pypinyin_available: Optional[bool] = None
_pypinyin_module = None

_pinyin2hanzi_available: Optional[bool] = None
_pinyin2hanzi_dag = None
_pinyin2hanzi_params = None

_hanziconv_available: Optional[bool] = None
_hanziconv_module = None


# =============================================================================
# 安裝提示訊息
# =============================================================================

CHINESE_INSTALL_HINT = (
    "缺少中文依賴。請執行:\n"
    "  pip install \"phonofix[ch]\"\n"
    "或安裝完整版本:\n"
    "  pip install phonofix"
)

ENGLISH_INSTALL_HINT = (
    "缺少英文依賴。請執行:\n"
    "  pip install \"phonofix[en]\"\n"
    "或安裝完整版本:\n"
    "  pip install phonofix\n\n"
    "注意: 英文支援還需要安裝 espeak-ng 系統套件:\n"
    "  Windows: https://github.com/espeak-ng/espeak-ng/releases\n"
    "  macOS: brew install espeak-ng\n"
    "  Linux: apt install espeak-ng"
)


# =============================================================================
# 中文依賴 - pypinyin
# =============================================================================

def get_pypinyin():
    """
    延遲載入 pypinyin 模組
    
    Returns:
        pypinyin 模組
        
    Raises:
        ImportError: 如果 pypinyin 未安裝
    """
    global _pypinyin_available, _pypinyin_module
    
    if _pypinyin_available is not None:
        if _pypinyin_available:
            return _pypinyin_module
        else:
            raise ImportError(CHINESE_INSTALL_HINT)
    
    try:
        import pypinyin
        _pypinyin_module = pypinyin
        _pypinyin_available = True
        return _pypinyin_module
    except ImportError:
        _pypinyin_available = False
        raise ImportError(CHINESE_INSTALL_HINT)


def is_pypinyin_available() -> bool:
    """檢查 pypinyin 是否可用"""
    try:
        get_pypinyin()
        return True
    except ImportError:
        return False


# =============================================================================
# 中文依賴 - Pinyin2Hanzi
# =============================================================================

def get_pinyin2hanzi() -> Tuple[Any, Callable]:
    """
    延遲載入 Pinyin2Hanzi 模組
    
    Returns:
        Tuple[DefaultDagParams, dag]: (預設參數類別, dag 函數)
        
    Raises:
        ImportError: 如果 Pinyin2Hanzi 未安裝
    """
    global _pinyin2hanzi_available, _pinyin2hanzi_dag, _pinyin2hanzi_params
    
    if _pinyin2hanzi_available is not None:
        if _pinyin2hanzi_available:
            return _pinyin2hanzi_params, _pinyin2hanzi_dag
        else:
            raise ImportError(CHINESE_INSTALL_HINT)
    
    try:
        from Pinyin2Hanzi import DefaultDagParams, dag
        _pinyin2hanzi_params = DefaultDagParams
        _pinyin2hanzi_dag = dag
        _pinyin2hanzi_available = True
        return _pinyin2hanzi_params, _pinyin2hanzi_dag
    except ImportError:
        _pinyin2hanzi_available = False
        raise ImportError(CHINESE_INSTALL_HINT)


def is_pinyin2hanzi_available() -> bool:
    """檢查 Pinyin2Hanzi 是否可用"""
    try:
        get_pinyin2hanzi()
        return True
    except ImportError:
        return False


# =============================================================================
# 中文依賴 - hanziconv
# =============================================================================

def get_hanziconv():
    """
    延遲載入 hanziconv 模組
    
    Returns:
        HanziConv 類別
        
    Raises:
        ImportError: 如果 hanziconv 未安裝
    """
    global _hanziconv_available, _hanziconv_module
    
    if _hanziconv_available is not None:
        if _hanziconv_available:
            return _hanziconv_module
        else:
            raise ImportError(CHINESE_INSTALL_HINT)
    
    try:
        from hanziconv import HanziConv
        _hanziconv_module = HanziConv
        _hanziconv_available = True
        return _hanziconv_module
    except ImportError:
        _hanziconv_available = False
        raise ImportError(CHINESE_INSTALL_HINT)


def is_hanziconv_available() -> bool:
    """檢查 hanziconv 是否可用"""
    try:
        get_hanziconv()
        return True
    except ImportError:
        return False


# =============================================================================
# 語言可用性檢查
# =============================================================================

def is_chinese_available() -> bool:
    """
    檢查中文支援是否可用
    
    需要 pypinyin, Pinyin2Hanzi, hanziconv 都安裝才返回 True
    """
    return (
        is_pypinyin_available() and 
        is_pinyin2hanzi_available() and 
        is_hanziconv_available()
    )


def is_english_available() -> bool:
    """
    檢查英文支援是否可用
    
    需要 phonemizer 安裝且 espeak-ng 可用才返回 True
    """
    try:
        # 使用現有的 backend 檢查邏輯
        from phonofix.backend.english_backend import _get_phonemize
        _get_phonemize()
        return True
    except (ImportError, RuntimeError):
        return False


def check_chinese_dependencies():
    """
    檢查中文依賴是否已安裝，未安裝則拋出清楚的錯誤
    
    Raises:
        ImportError: 如果任何中文依賴未安裝
    """
    get_pypinyin()
    get_pinyin2hanzi()
    get_hanziconv()


def check_english_dependencies():
    """
    檢查英文依賴是否已安裝，未安裝則拋出清楚的錯誤
    
    Raises:
        ImportError: 如果英文依賴未安裝
        RuntimeError: 如果 espeak-ng 不可用
    """
    try:
        from phonofix.backend.english_backend import _get_phonemize
        _get_phonemize()
    except ImportError:
        raise ImportError(ENGLISH_INSTALL_HINT)
    except RuntimeError as e:
        raise RuntimeError(f"{e}\n\n{ENGLISH_INSTALL_HINT}")

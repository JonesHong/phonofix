"""
日文工具模組

提供日文處理相關的輔助函式。

注意：
- `cutlet` / `fugashi` 的延遲載入、初始化與快取共用由 `JapanesePhoneticBackend` 管理
- 本模組僅保留「純文字」相關的輔助函式，不再直接提供依賴取得的 wrapper
"""

def is_japanese_char(char: str) -> bool:
    """
    判斷字元是否為日文 (平假名、片假名)

    注意：漢字 (Kanji) 與中文重疊，此處不包含漢字判斷。
    漢字的語言歸屬通常由上下文決定。

    Args:
        char: 單個字元

    Returns:
        bool: 是否為平假名或片假名
    """
    if not char:
        return False

    code = ord(char)

    # 平假名 (Hiragana): 0x3040 - 0x309F
    if 0x3040 <= code <= 0x309F:
        return True

    # 片假名 (Katakana): 0x30A0 - 0x30FF
    if 0x30A0 <= code <= 0x30FF:
        return True

    return False

"""
examples/ 共用工具

目標：
- 讓所有 examples 腳本都能以相同方式載入專案（repo root + src）
- 提供一致的輸出格式（print_case）
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional


import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "src"))
from tools.translation_client import translate_text


def add_repo_to_sys_path() -> Path:
    """
    將 repo root 與 src 加入 sys.path，方便直接以 `python examples/*.py` 執行。

    Returns:
        Path: repo root 路徑
    """
    root_dir = Path(__file__).resolve().parent.parent
    for path in (root_dir, root_dir / "src"):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
    return root_dir

is_translate_enabled = False  # 設為 True 可啟用翻譯功能
def print_case(
    title: str,
    text: str,
    result: str,
    explanation: str,
) -> None:
    """統一的輸出格式（可選翻譯）"""
    print(f"--- {title} ---")
    print(f"原文 (Original):  {text}")
    if is_translate_enabled:
        print(f"譯文 (Trans):     {translate_text(text)}")
    print(f"修正 (Corrected): {result}")
    if is_translate_enabled:
        print(f"譯文 (Trans):     {translate_text(result)}")
    print(f"說明 (Note):      {explanation}")
    print()


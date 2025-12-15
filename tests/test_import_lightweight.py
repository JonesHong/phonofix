"""
import 輕量契約測試

目的：
- 確保 `import phonofix` 不會立刻載入各語言引擎與其重依賴（phonemizer / pypinyin / cutlet / fugashi）。
- 這個契約對「extras 安裝模式」很重要：使用者只裝某語言時，不應因為 import 而被迫觸發其他語言依賴。

做法：
- 使用 subprocess 開新 Python 行程，避免 pytest 本身已經 import 太多模組造成干擾。
"""

from __future__ import annotations

import os
import subprocess
import sys


def test_import_phonofix_is_lightweight():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(repo_root, "src")

    code = r"""
import sys
import phonofix  # noqa: F401

blocked = [
    "phonofix.languages.english",
    "phonofix.languages.chinese",
    "phonofix.languages.japanese",
    "phonemizer",
    "pypinyin",
    "cutlet",
    "fugashi",
]

loaded = sorted([m for m in blocked if m in sys.modules])
if loaded:
    raise SystemExit("Unexpected imports: " + ", ".join(loaded))

print("OK")
"""

    out = subprocess.check_output([sys.executable, "-c", code], env=env, text=True)
    assert "OK" in out


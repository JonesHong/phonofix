"""
中文 corrector 的型別定義

目的：
- 固定 drafts / candidates / index items 的資料形狀，降低模組拆分風險
- 不改動既有執行期行為（皆為 typing 層級）

相容性：
- 專案宣告 `requires-python >= 3.9`，但範例可能用 `uv` 跑在 Python 3.10
- 因此這裡避免使用 Python 3.11+ 才有的 typing 物件（例如 `typing.NotRequired`）
"""

from __future__ import annotations

from typing import TypedDict


class ChineseIndexItem(TypedDict):
    """
    單一索引項目（term 或 alias）的統一資料結構。

    用途：
    - indexing/build_search_index 會將 canonical 與 aliases 都轉成這種固定形狀
    - candidates 模組在生成 draft 時會把對應的 index item 帶著走
    """
    term: str
    canonical: str
    keywords: list[str]
    exclude_when: list[str]
    weight: float
    pinyin_str: str
    pinyin_syllables: tuple[str, ...]
    initials: list[str]
    len: int
    is_mixed: bool
    is_alias: bool


class ChineseCandidateDraft(TypedDict):
    """
    候選草稿（draft）。

    特性：
    - 由候選生成器產生，尚未完成最終替換字串/衝突解決
    - draft 會包含 `item`（索引項目）與基礎的 error_ratio/context 資訊
    """
    start: int
    end: int
    original: str
    error_ratio: float
    has_context: bool
    context_distance: float | None
    item: ChineseIndexItem


class ChineseCandidate(TypedDict):
    """
    最終候選（candidate）。

    特性：
    - 已完成 replacement/canonical/alias 的決策
    - 已計算最終 score，可用於 conflict resolver 進行排序與去重疊
    """
    start: int
    end: int
    original: str
    replacement: str
    canonical: str
    alias: str
    score: float
    has_context: bool

"""
英文 corrector 的型別定義

目的：
- 固定 drafts / candidates / index items 的資料形狀，降低模組拆分風險
- 不改動既有執行期行為（皆為 typing 層級）

相容性：
- 專案宣告 `requires-python >= 3.9`；因此這裡避免使用 Python 3.11+ 才有的 typing 物件
"""

from __future__ import annotations

from typing import TypedDict


class EnglishIndexItem(TypedDict, total=False):
    """
    單一索引項目（term 或 alias）

    說明：
    - indexing 階段會先產出基本欄位（term/canonical/phonetic/token_count...）
    - fuzzy buckets 建立時會再補上 phonetic_len/first_group/max_len_diff 等便宜 pruning 欄位
    """

    term: str
    canonical: str
    phonetic: str
    token_count: int
    keywords: list[str]
    exclude_when: list[str]
    weight: float
    is_alias: bool

    # fuzzy bucket 預計算欄位（在 build_fuzzy_buckets 時補上）
    phonetic_len: int
    first_group: int | None
    max_len_diff: float


class EnglishCandidateDraft(TypedDict):
    """
    候選草稿（draft）。

    - 由候選生成器產生，尚未完成最終替換字串/衝突解決
    - draft 會包含 `item`（索引項目）與基礎 error_ratio/context 資訊
    """
    start: int
    end: int
    original: str
    error_ratio: float
    has_context: bool
    context_distance: float | None
    item: EnglishIndexItem


class EnglishCandidate(TypedDict):
    """
    最終候選（candidate）。

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

"""
日文 corrector：索引建立

此模組把「term_mapping -> search_index / exact matcher / fuzzy buckets」集中管理，
讓 JapaneseCorrector 保持為薄的 orchestrator。

term_mapping 格式（由 Engine normalize 後傳入）：
- `{"アスピリン": {"aliases": ["asupirin"], "keywords": [...], "exclude_when": [...], "weight": 1.0}}`

設計原則（以中文/英文為 reference）：
- search_index 只做「一次性預處理」（計算 romaji、token_count 等），換取後續掃描更省
- fuzzy buckets 以「窗口長度 + 首音群組」做分桶，避免每個窗口對所有 items 計算相似度
"""

from __future__ import annotations

from typing import Any, Dict

from phonofix.utils.aho_corasick import AhoCorasick

from .types import JapaneseIndexItem


def first_romaji_group(romaji: str) -> int | None:
    """
    取得 Romaji 的「首音群組」

    用途：
    - fuzzy buckets 分桶
    - fuzzy 掃描時以視窗首音群組做 pruning（避免對所有 item 計算相似度）
    """
    if not romaji:
        return None
    first: str | None = None
    for ch in romaji:
        if ch == " ":
            continue
        first = ch.lower()
        break
    if not first:
        return None

    vowels = {"a", "e", "i", "o", "u"}
    if first in vowels:
        return 0
    if first in {"p", "b"}:
        return 1
    if first in {"t", "d"}:
        return 2
    if first in {"k", "g"}:
        return 3
    if first in {"s", "z"}:
        return 4
    if first in {"h", "f"}:
        return 5
    if first in {"m", "n"}:
        return 6
    if first in {"r", "l"}:
        return 7
    if first in {"w", "y"}:
        return 8
    if first in {"j", "c"}:
        return 9
    return None


def build_search_index(
    *,
    phonetic: Any,
    tokenizer: Any,
    term_mapping: Dict[str, Dict],
) -> list[JapaneseIndexItem]:
    """
    建立搜尋索引

    將別名映射轉換為列表結構，並預先計算 romaji 與 token 數量。
    索引按 token 數量降序排列，以優先匹配長詞。

    注意：
    - phonetic.to_phonetic() 底層會走 backend LRU 快取（cutlet/romaji），避免重複轉換
    - tokenizer 會走 backend 共享 tagger；token_count 主要用於 window 掃描的長度 pruning
    """
    search_index: list[JapaneseIndexItem] = []

    for canonical, config in term_mapping.items():
        aliases = config.get("aliases", [])
        weight = config.get("weight", 1.0)
        keywords = config.get("keywords", [])
        exclude_when = config.get("exclude_when", [])

        targets = set(aliases) | {canonical}

        for alias in targets:
            is_alias = alias != canonical
            phonetic_value = phonetic.to_phonetic(alias)
            if not phonetic_value:
                continue

            tokens = tokenizer.tokenize(alias)
            token_count = len(tokens)

            search_index.append(
                {
                    "term": alias,
                    "canonical": canonical,
                    "phonetic": phonetic_value,
                    "token_count": token_count,
                    "weight": weight,
                    "keywords": keywords,
                    "exclude_when": exclude_when,
                    "is_alias": is_alias,
                }
            )

    search_index.sort(key=lambda x: int(x.get("token_count", 0)), reverse=True)
    return search_index


def build_exact_matcher(
    search_index: list[JapaneseIndexItem],
) -> tuple[AhoCorasick[str] | None, dict[str, list[JapaneseIndexItem]]]:
    """
    建立 surface alias 的 exact-match 索引（Aho-Corasick）。

    - 只納入 aliases（不納入 canonical 本身），用來快速找候選區間
    - 回傳 (matcher, items_by_alias)；其中 matcher 可能為 None（代表沒有任何 alias）
    """
    items_by_alias: dict[str, list[JapaneseIndexItem]] = {}
    for item in search_index:
        if not item.get("is_alias"):
            continue
        alias = item.get("term") or ""
        if not alias:
            continue
        items_by_alias.setdefault(alias, []).append(item)

    if not items_by_alias:
        return None, {}

    matcher: AhoCorasick[str] = AhoCorasick()
    for alias in items_by_alias.keys():
        matcher.add(alias, alias)
    matcher.build()

    return matcher, items_by_alias


def build_fuzzy_buckets(*, search_index: list[JapaneseIndexItem]) -> dict[int, dict[int, list[JapaneseIndexItem]]]:
    """
    建立便宜 pruning 用的分桶索引

    分桶維度：
    - window token 長度（token_count 的容許範圍）
    - 首音群組（Romaji 第一個字母）

    欄位備註：
    - `phonetic_len`：item 的 romaji 長度
    - `max_len_diff`：允許的長度差上限（越長允許越寬鬆），用來做便宜 pruning
    """
    buckets: dict[int, dict[int, list[JapaneseIndexItem]]] = {}

    for item in search_index:
        token_count = int(item.get("token_count", 0) or 0)
        min_len = max(1, token_count - 2)
        max_len = token_count + 2

        phonetic_value = str(item.get("phonetic") or "")
        item["phonetic_len"] = len(phonetic_value)
        item["first_group"] = first_romaji_group(phonetic_value)
        item["max_len_diff"] = max(len(phonetic_value), 5) * 0.5

        group_id = item.get("first_group")
        group_key = -1 if group_id is None else int(group_id)

        for window_len in range(min_len, max_len + 1):
            buckets.setdefault(window_len, {}).setdefault(group_key, []).append(item)

    return buckets

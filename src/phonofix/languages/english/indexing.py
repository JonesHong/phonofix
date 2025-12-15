"""
英文 corrector：索引建立

此模組把「term_mapping -> search_index / exact matcher / fuzzy buckets」集中管理，
讓 EnglishCorrector 保持為薄的 orchestrator。

term_mapping 格式（由 Engine normalize 後傳入）：
- `{"Python": {"aliases": ["Pyton"], "keywords": [...], "exclude_when": [...], "weight": 0.5}}`

設計原則（以中文/日文為 reference）：
- search_index 只做「一次性預處理」（計算 IPA、token_count 等），換取後續掃描更省
- fuzzy buckets 以「窗口長度 + 首音素群組」做分桶，避免每個窗口對所有 items 計算相似度
"""

from __future__ import annotations

from typing import Any, Dict

from phonofix.utils.aho_corasick import AhoCorasick

from .config import EnglishPhoneticConfig
from .types import EnglishIndexItem


def first_ipa_symbol(ipa: str) -> str | None:
    """
    取得 IPA 字串的第一個「有效音素字元」。

    會略過：
    - 空白
    - 重音符號（ˈ, ˌ）

    用途：
    - fuzzy buckets 分桶：用首音素群組做便宜 pruning
    """
    for ch in ipa or "":
        if ch in {" ", "ˈ", "ˌ"}:
            continue
        return ch
    return None


def first_phoneme_group(ipa: str, *, config: Any = EnglishPhoneticConfig) -> int | None:
    """
    取得 IPA 的「首音素群組」

    用途：
    - fuzzy buckets 分桶
    - fuzzy 掃描時以視窗首音素群組做 pruning（避免對所有 item 計算相似度）
    """
    first = first_ipa_symbol(ipa)
    if not first:
        return None
    for idx, group in enumerate(config.FUZZY_PHONEME_GROUPS):
        if first in group:
            return idx
    return None


def build_search_index(
    *,
    engine: Any,
    tokenizer: Any,
    term_mapping: Dict[str, Dict],
) -> list[EnglishIndexItem]:
    """
    建立搜尋索引

    將別名映射轉換為列表結構，並預先計算 IPA。
    索引按 Token 數量降序排列，以優先匹配長詞。

    效能備註：
    - 這裡會批次計算所有 token 的 IPA（backend batch），避免逐項呼叫造成大量 overhead
    - indexing 屬於一次性成本，換取後續 correct() 的窗口掃描更省
    """
    all_tokens: set[str] = set()
    alias_tokens_map: dict[str, list[str]] = {}

    flat_mapping: list[dict[str, Any]] = []
    for canonical, config in term_mapping.items():
        aliases = list(config.get("aliases", []))
        targets = set(aliases) | {canonical}

        for alias in targets:
            is_alias = alias != canonical
            flat_mapping.append(
                {
                    "term": alias,
                    "canonical": canonical,
                    "keywords": config.get("keywords", []),
                    "exclude_when": config.get("exclude_when", []),
                    "weight": config.get("weight", 0.0),
                    "is_alias": is_alias,
                }
            )

            tokens = tokenizer.tokenize(alias)
            alias_tokens_map[alias] = tokens
            all_tokens.update(tokens)

    token_ipa_map = engine.backend.to_phonetic_batch(list(all_tokens))

    search_index: list[EnglishIndexItem] = []
    for item in flat_mapping:
        alias = str(item["term"])
        tokens = alias_tokens_map.get(alias, [])
        ipa_parts = [token_ipa_map.get(t, "") for t in tokens]
        alias_phonetic = "".join(ipa_parts)

        search_index.append(
            {
                "term": alias,
                "canonical": str(item["canonical"]),
                "phonetic": alias_phonetic,
                "token_count": len(tokens),
                "keywords": list(item.get("keywords", [])),
                "exclude_when": list(item.get("exclude_when", [])),
                "weight": float(item.get("weight", 0.0) or 0.0),
                "is_alias": bool(item.get("is_alias", False)),
            }
        )

    search_index.sort(key=lambda x: int(x.get("token_count", 0)), reverse=True)
    return search_index


def build_exact_matcher(
    search_index: list[EnglishIndexItem],
) -> tuple[AhoCorasick[str] | None, dict[str, list[EnglishIndexItem]]]:
    """
    建立 surface alias 的 exact-match 索引（Aho-Corasick）

    - 只納入 aliases（不納入 canonical 本身），用來快速找候選區間
    - 每個 alias 可能對應多個 item（理論上應盡量避免，但這裡保守處理）
    """
    items_by_alias: dict[str, list[EnglishIndexItem]] = {}
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


def build_fuzzy_buckets(
    *,
    search_index: list[EnglishIndexItem],
    config: Any = EnglishPhoneticConfig,
) -> dict[int, dict[int, list[EnglishIndexItem]]]:
    """
    建立便宜 pruning 用的分桶索引

    分桶維度：
    - window token 長度（token_count 的容許範圍）
    - 首音素群組（IPA 第一個音素）

    欄位備註：
    - `phonetic_len`：item 的 IPA 長度（去空白後的近似尺度）
    - `max_len_diff`：允許的長度差上限（越長允許越寬鬆），用來做便宜 pruning
    """
    buckets: dict[int, dict[int, list[EnglishIndexItem]]] = {}

    for item in search_index:
        token_count = int(item.get("token_count", 0) or 0)
        min_len = max(1, token_count - 2)
        max_len = token_count + 3

        phonetic = str(item.get("phonetic") or "")
        item["phonetic_len"] = len(phonetic)
        item["first_group"] = first_phoneme_group(phonetic, config=config)
        item["max_len_diff"] = max(len(phonetic), 5) * 0.6

        group_id = item.get("first_group")
        group_key = -1 if group_id is None else int(group_id)

        for window_len in range(min_len, max_len + 1):
            buckets.setdefault(window_len, {}).setdefault(group_key, []).append(item)

    return buckets

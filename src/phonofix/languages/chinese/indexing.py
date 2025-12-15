"""
中文 corrector：索引建立

此模組把「term_mapping -> search_index / exact matcher / fuzzy buckets」集中管理，
讓 ChineseCorrector 保持為薄的 orchestrator。

term_mapping 格式（由 Engine normalize 後傳入）：
- `{"台北車站": ["北車", "台北站"]}`：list 視為 aliases（keywords/exclude_when/weight 皆為預設）
- `{"台北車站": {"aliases": [...], "keywords": [...], "exclude_when": [...], "weight": 0.5}}`

效能備註：
- 拼音/音節/聲母等特徵計算會透過 `ChinesePhoneticBackend` 的快取（LRU）完成
- indexing 階段屬於「一次性成本」，換取後續 correct() 的窗口掃描更省
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from phonofix.utils.aho_corasick import AhoCorasick

from .types import ChineseIndexItem


def parse_term_data(data: Any) -> tuple[list[str], list[str], list[str], float]:
    """解析專有名詞資料結構，提取別名、關鍵字、上下文排除條件與權重"""
    if isinstance(data, list):
        aliases = data
        keywords: list[str] = []
        exclude_when: list[str] = []
        weight = 0.0
    else:
        aliases = list(data.get("aliases", []))
        keywords = list(data.get("keywords", []))
        exclude_when = list(data.get("exclude_when", []))
        weight = float(data.get("weight", 0.0))
    return aliases, keywords, exclude_when, weight


def create_index_item(
    *,
    engine: Any,
    utils: Any,
    term: str,
    canonical: str,
    keywords: list[str],
    exclude_when: list[str],
    weight: float,
) -> ChineseIndexItem:
    """建立單個索引項目，預先計算拼音與聲母特徵"""
    backend = engine.backend
    pinyin_str = backend.to_phonetic(term)
    pinyin_syllables = backend.get_pinyin_syllables(term)
    initials_list = list(backend.get_initials(term))
    is_alias = term != canonical
    return {
        "term": term,
        "canonical": canonical,
        "keywords": [k.lower() for k in keywords],
        "exclude_when": [e.lower() for e in exclude_when],
        "weight": weight,
        "pinyin_str": pinyin_str,
        "pinyin_syllables": pinyin_syllables,
        "initials": initials_list,
        "len": len(term),
        "is_mixed": bool(utils.contains_english(term)),
        "is_alias": is_alias,
    }


def build_search_index(*, engine: Any, utils: Any, term_mapping: Dict[str, Dict]) -> list[ChineseIndexItem]:
    """
    建立搜尋索引

    將標準化的專有名詞庫轉換為便於搜尋的列表結構。
    每個索引項目包含:
    - 原始詞彙 (term)
    - 標準詞彙 (canonical)
    - 關鍵字 (keywords)
    - 權重 (weight)
    - 拼音字串 (pinyin_str)
    - 聲母列表 (initials)
    - 長度 (len)
    - 是否混合語言 (is_mixed)

    索引按詞長降序排列，以優先匹配長詞。
    """
    search_index: list[ChineseIndexItem] = []
    for canonical, data in term_mapping.items():
        aliases, keywords, exclude_when, weight = parse_term_data(data)
        targets = set(aliases) | {canonical}
        for term in targets:
            index_item = create_index_item(
                engine=engine,
                utils=utils,
                term=term,
                canonical=canonical,
                keywords=keywords,
                exclude_when=exclude_when,
                weight=weight,
            )
            search_index.append(index_item)
    search_index.sort(key=lambda x: x["len"], reverse=True)
    return search_index


def build_exact_matcher(
    search_index: list[ChineseIndexItem],
) -> tuple[AhoCorasick[str] | None, dict[str, list[ChineseIndexItem]]]:
    """
    建立 surface alias 的 exact-match 索引（Aho-Corasick）。

    - 只納入 aliases（不納入 canonical 本身），用來快速找候選區間
    - 回傳 (matcher, items_by_alias)；其中 matcher 可能為 None（代表沒有任何 alias）
    """
    items_by_alias: dict[str, list[ChineseIndexItem]] = {}
    for item in search_index:
        if not item.get("is_alias"):
            continue
        alias = item["term"]
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


def build_fuzzy_buckets(*, search_index: list[ChineseIndexItem], config: Any) -> dict[int, dict[str, list[ChineseIndexItem]]]:
    """
    建立便宜 pruning 用的分桶索引

    分桶維度：
    - 片段長度（len）
    - 首聲母群組（FUZZY_INITIALS_MAP）
    """
    buckets: dict[int, dict[str, list[ChineseIndexItem]]] = {}
    for item in search_index:
        word_len = int(item["len"])
        initials = item.get("initials") or []
        first = initials[0] if initials else ""
        group = config.FUZZY_INITIALS_MAP.get(first) or first or ""
        buckets.setdefault(word_len, {}).setdefault(group, []).append(item)
    return buckets

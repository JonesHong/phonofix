"""
Term config normalization

以中文（reference implementation）的語意為基準，提供跨語言共用的 term_dict 正規化工具。

設計重點：
- 使用者輸入的 dict key 永遠是 canonical（正確拼寫）
- aliases 不包含 canonical（canonical 由 key 表達）
- 正規化只處理「輸入形狀」與欄位預設，不做語言特定的 fuzzy 產生策略
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict, Union

TermDictInput = Union[List[str], Dict[str, Any]]


class NormalizedTermConfig(TypedDict, total=False):
    aliases: list[str]
    keywords: list[str]
    exclude_when: list[str]
    weight: float
    max_variants: int

    # 允許保留輸入中的其他欄位（例如歷史的 auto_fuzzy），避免在 Phase 3 破壞既有用法


def normalize_term_dict(
    term_dict: TermDictInput,
    *,
    default_weight: float = 0.0,
    default_max_variants: int = 30,
) -> dict[str, NormalizedTermConfig]:
    """
    將使用者輸入的 term_dict 統一成 canonical -> NormalizedTermConfig

    支援：
    - ["台北車站"]（list）
    - {"台北車站": ["北車"]}（dict[str, list[str]]）
    - {"台北車站": {"aliases": [...], "keywords": [...], ...}}（dict[str, dict]）
    """
    if isinstance(term_dict, list):
        return {
            term: {
                "aliases": [],
                "keywords": [],
                "exclude_when": [],
                "weight": default_weight,
                "max_variants": default_max_variants,
            }
            for term in term_dict
        }

    normalized: dict[str, NormalizedTermConfig] = {}
    for canonical, value in term_dict.items():
        if isinstance(value, list):
            config: dict[str, Any] = {"aliases": value}
        elif isinstance(value, dict):
            config = dict(value)
        else:
            config = {}

        raw_aliases = list(config.get("aliases") or [])
        aliases = [a for a in raw_aliases if isinstance(a, str) and a != canonical]
        keywords = list(config.get("keywords") or [])
        exclude_when = list(config.get("exclude_when") or [])
        weight = float(config.get("weight", default_weight) or 0.0)
        max_variants = int(config.get("max_variants", default_max_variants) or default_max_variants)

        normalized[canonical] = {
            **config,
            "aliases": aliases,
            "keywords": keywords,
            "exclude_when": exclude_when,
            "weight": weight,
            "max_variants": max_variants,
        }

    return normalized

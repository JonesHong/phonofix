"""Dict schema v2 validator (mode: protect | replace) — Phase 2."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DictSchemaError(ValueError):
    """Raised when yaml dict fails schema validation."""

    pass


class TermMode(Enum):
    REPLACE = "replace"  # active replacement (alias → canonical)
    PROTECT = "protect"  # negative protection (canonical 不被 alias 子字串取代)


@dataclass
class Term:
    canonical: str
    mode: TermMode
    aliases: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    weight: float = 0.0


@dataclass
class DictV2:
    version: int  # must be 2
    language: str  # zh | ja | en | ko
    terms: list[Term]
    confusion_overrides: dict[str, list[str]] = field(default_factory=dict)


_VALID_LANGUAGES = {"zh", "ja", "en", "ko"}
_VALID_MODES = {m.value for m in TermMode}


def validate_dict(raw: dict) -> DictV2:
    """
    Validate raw yaml dict against schema v2 (SPEC.md Appendix A).

    拒絕 ambiguous 寫法：
    - mode=replace 但 aliases 空 → DictSchemaError
    - mode=protect 但有 aliases / keywords / weight → DictSchemaError
    - language 不在 {zh, ja, en, ko} → DictSchemaError
    - version != 2 → DictSchemaError
    - canonical 重複 → DictSchemaError
    """
    if not isinstance(raw, dict):
        raise DictSchemaError(f"Dict must be a mapping, got {type(raw).__name__!r}")

    # --- version ---
    version = raw.get("version")
    if version is None:
        raise DictSchemaError("Missing required field: 'version'")
    if not isinstance(version, int) or version != 2:
        raise DictSchemaError(f"Invalid version {version!r}: must be integer 2 (got {version!r})")

    # --- language ---
    language = raw.get("language")
    if language is None:
        raise DictSchemaError("Missing required field: 'language'")
    if not isinstance(language, str):
        raise DictSchemaError(f"Invalid language {language!r}: must be a string")
    if language not in _VALID_LANGUAGES:
        raise DictSchemaError(
            f"Invalid language {language!r}: must be one of {sorted(_VALID_LANGUAGES)}"
        )

    # --- terms ---
    raw_terms = raw.get("terms")
    if raw_terms is None:
        raise DictSchemaError("Missing required field: 'terms'")
    if not isinstance(raw_terms, list):
        raise DictSchemaError(f"Field 'terms' must be a list, got {type(raw_terms).__name__!r}")

    terms: list[Term] = []
    seen_canonicals: set[str] = set()

    for idx, raw_term in enumerate(raw_terms):
        term = _validate_term(raw_term, idx)

        # duplicate canonical check
        if term.canonical in seen_canonicals:
            raise DictSchemaError(
                f"Duplicate canonical {term.canonical!r} at terms[{idx}]: "
                f"each canonical must appear at most once per dict"
            )
        seen_canonicals.add(term.canonical)
        terms.append(term)

    # --- confusion_overrides (optional) ---
    raw_overrides = raw.get("confusion_overrides", {})
    if not isinstance(raw_overrides, dict):
        raise DictSchemaError(
            f"Field 'confusion_overrides' must be a mapping, got {type(raw_overrides).__name__!r}"
        )
    confusion_overrides: dict[str, list[str]] = {}
    for k, v in raw_overrides.items():
        if not isinstance(k, str):
            raise DictSchemaError(f"confusion_overrides key must be str, got {type(k).__name__!r}")
        if not isinstance(v, list) or not all(isinstance(s, str) for s in v):
            raise DictSchemaError(f"confusion_overrides[{k!r}] must be a list of strings")
        confusion_overrides[k] = list(v)

    return DictV2(
        version=version,
        language=language,
        terms=terms,
        confusion_overrides=confusion_overrides,
    )


def _validate_term(raw_term: object, idx: int) -> Term:
    """Validate a single term entry dict and return a Term dataclass."""
    if not isinstance(raw_term, dict):
        raise DictSchemaError(f"terms[{idx}] must be a mapping, got {type(raw_term).__name__!r}")

    # --- canonical ---
    canonical = raw_term.get("canonical")
    if canonical is None:
        raise DictSchemaError(f"terms[{idx}] missing required field 'canonical'")
    if not isinstance(canonical, str) or not canonical.strip():
        raise DictSchemaError(
            f"terms[{idx}].canonical must be a non-empty string, got {canonical!r}"
        )

    # --- mode ---
    raw_mode = raw_term.get("mode")
    if raw_mode is None:
        raise DictSchemaError(f"terms[{idx}] ({canonical!r}) missing required field 'mode'")
    if raw_mode not in _VALID_MODES:
        raise DictSchemaError(
            f"terms[{idx}] ({canonical!r}) invalid mode {raw_mode!r}: "
            f"must be one of {sorted(_VALID_MODES)}"
        )
    mode = TermMode(raw_mode)

    # --- aliases ---
    raw_aliases = raw_term.get("aliases", [])
    if raw_aliases is None:
        raw_aliases = []
    if not isinstance(raw_aliases, list):
        raise DictSchemaError(
            f"terms[{idx}] ({canonical!r}) 'aliases' must be a list, "
            f"got {type(raw_aliases).__name__!r}"
        )
    aliases = [str(a) for a in raw_aliases]

    # --- keywords ---
    raw_keywords = raw_term.get("keywords", [])
    if raw_keywords is None:
        raw_keywords = []
    if not isinstance(raw_keywords, list):
        raise DictSchemaError(
            f"terms[{idx}] ({canonical!r}) 'keywords' must be a list, "
            f"got {type(raw_keywords).__name__!r}"
        )
    keywords = [str(kw) for kw in raw_keywords]

    # --- weight ---
    raw_weight = raw_term.get("weight", 0.0)
    if raw_weight is None:
        raw_weight = 0.0
    try:
        weight = float(raw_weight)
    except (TypeError, ValueError):
        raise DictSchemaError(
            f"terms[{idx}] ({canonical!r}) 'weight' must be a float, got {raw_weight!r}"
        )

    # --- mode-specific constraints ---
    if mode == TermMode.REPLACE:
        if not aliases:
            raise DictSchemaError(
                f"terms[{idx}] ({canonical!r}) mode=replace requires a non-empty 'aliases' list"
            )

    elif mode == TermMode.PROTECT:
        if aliases:
            raise DictSchemaError(
                f"terms[{idx}] ({canonical!r}) mode=protect must not have 'aliases' "
                f"(got {aliases!r})"
            )
        if keywords:
            raise DictSchemaError(
                f"terms[{idx}] ({canonical!r}) mode=protect must not have 'keywords' "
                f"(got {keywords!r})"
            )
        if weight != 0.0:
            raise DictSchemaError(
                f"terms[{idx}] ({canonical!r}) mode=protect must not have 'weight' (got {weight!r})"
            )

    return Term(
        canonical=canonical,
        mode=mode,
        aliases=aliases,
        keywords=keywords,
        weight=weight,
    )

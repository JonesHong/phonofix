# PHASE2-COMPAT-DESIGN.md

phonofix v0.4.0 — Phase 2 Compatibility Layer Design
Frozen: 2026-05-26 | Status: reference for Phase 3 implementation

---

## Section 1: P0 Bug Audit — alias-is-substring-of-canonical

### 1.1 Test Suite Results (v0.4-dev HEAD)

```
tests/test_canonical_substring_preservation.py — 7 tests, 7 PASSED (0.08s)

TestChineseCanonicalSubstringPreservation:
  test_canonical_literal_not_destroyed_when_alias_is_substring
  test_alias_substring_still_replaceable
  test_mixed_canonical_and_alias_in_same_text
  test_phonetic_alias_with_canonical_substring_pattern

TestJapaneseCanonicalSubstringPreservation:
  test_canonical_literal_not_destroyed_when_alias_is_substring
  test_alias_substring_still_replaceable
  test_mixed_canonical_and_alias_in_same_text
```

### 1.2 Mask Implementation Location

```
src/phonofix/languages/chinese/corrector.py:90
  # Auto-protect canonical literals so input containing a canonical (e.g. "台北車站")
  # is not destroyed by an alias that is its substring (e.g. "北車") — without this,
  # AC matcher would re-replace the embedded alias and yield "台台北車站站".
  instance.protected_terms = (protected_terms or set()) | set(term_mapping.keys())
```

Pattern: canonical keys are collected into `protected_terms`; a `_protected_matcher`
runs a pre-pass to mask canonical spans before alias AC scan.

### 1.3 Conclusion

**v0.4.0 does NOT need a new P0 fix.** The mask logic is already implemented in
`ChineseCorrector` and verified by 7 passing tests.

**Phase 3 obligation:** `PhoneticMatcher` (the new language-agnostic core) MUST
replicate the same `protected_terms` mask pattern. The Phase 3 Phonemizer protocol
must expose canonical set to the matcher so the pre-pass can run before any AC
scan. Without this, the bug regresses.

---

## Section 2: Thin Compat Layer Design

Three legacy entry-points (`ChineseEngine`, `JapaneseEngine`, `EnglishEngine`) are
retained in v0.4.0 as thin wrappers around `PhoneticMatcher`. They emit a
`DeprecationWarning` on every `__init__` and will be **removed in v0.5.0**
(≥ 3 months after v0.4.0 release, per SPEC.md Appendix B).

### 2.1 Code Skeleton

```python
# src/phonofix/__init__.py (Phase 3 rewrite target)
import warnings
from phonofix.core.matcher import PhoneticMatcher
from phonofix import phonemizers

_REMOVE_VERSION = "v0.5.0"
_MIGRATION_URL = "https://phonofix.readthedocs.io/migration"


class ChineseEngine:
    """Deprecated thin wrapper — removed in v0.5.0.

    Replace with::

        import phonofix
        matcher = phonofix.load("dict-zh-v2.yaml")
        # or
        matcher = phonofix.PhoneticMatcher(
            phonemizer=phonofix.phonemizers.chinese(), dictionary={...}
        )
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            f"ChineseEngine is deprecated and will be removed in {_REMOVE_VERSION}. "
            f"Migrate to phonofix.load() or phonofix.PhoneticMatcher. "
            f"See {_MIGRATION_URL} for 1:1 examples.",
            DeprecationWarning,
            stacklevel=2,
        )
        # on_event forwarded transparently so existing event subscribers keep working
        self._matcher = PhoneticMatcher(
            phonemizer=phonemizers.chinese(),
            dictionary=kwargs.get("dictionary"),
            on_event=kwargs.get("on_event"),
        )

    def create_corrector(self, terms, **kwargs):
        """Deprecated. Use PhoneticMatcher(dictionary=terms).correct() directly."""
        warnings.warn(
            "create_corrector() is removed in v0.4.0. "
            "Pass terms as dictionary= to PhoneticMatcher.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._matcher.with_dictionary(terms)

    def correct(self, text: str) -> str:
        return self._matcher.correct(text)

    # Same pattern applies 1:1 to JapaneseEngine and EnglishEngine.
    # JapaneseEngine  → phonemizer=phonemizers.japanese()
    # EnglishEngine   → phonemizer=phonemizers.english()
```

### 2.2 Design Constraints

- `DeprecationWarning` fires at `__init__`, **not** at `correct()` — avoids per-call
  spam in hot loops while still surfacing the warning on first use.
- `stacklevel=2` ensures the warning points to caller's line, not the wrapper.
- `create_corrector()` path is separately warned as removed in v0.4.0
  (it is in the no-compat-layer break list, but callers going through the thin
  `ChineseEngine` path may still call it; surface clearly rather than AttributeError).
- The wrapper must NOT alter behaviour — any argument the old engine accepted that
  maps to a `PhoneticMatcher` kwarg must be forwarded verbatim.

---

## Section 3: Phase 3 Engine Rewrite Migration Plan

Phase 3 implements `PhoneticMatcher` Tier 1–4 algorithms. The thin compat layer
goes live at the same time. Ordered execution:

1. **PhoneticMatcher Phase 3 Tier 1–4 complete** — `core/matcher.py` passes full
   benchmark suite (zh 8k+/s, ja 2.5k+/s, en 1k+/s). Protected-terms mask
   ported from `ChineseCorrector` into matcher pre-pass.

2. **Rewrite `src/phonofix/__init__.py`** — replace current direct Engine exports
   with thin-wrapper classes (`ChineseEngine`, `JapaneseEngine`, `EnglishEngine`)
   per the skeleton in Section 2.1. `phonofix.load()` and `phonofix.PhoneticMatcher`
   become the canonical public API.

3. **Mark `src/phonofix/languages/{zh,ja,en}/engine.py` as deprecated** — add module-
   level `DeprecationWarning` so any direct `from phonofix.languages.zh.engine import
   ChineseEngine` import also warns. Source files kept for the thin wrapper's internal
   import until v0.5.0.

4. **Existing `tests/` must stay green** — no existing test may be deleted or skipped.
   Run full suite (`uv run pytest`) as the merge gate for Phase 3 PR.

5. **Add `tests/test_thin_compat.py`** — new test file verifying:
   - `ChineseEngine()` raises `DeprecationWarning` (via `pytest.warns`)
   - `JapaneseEngine()` raises `DeprecationWarning`
   - `EnglishEngine()` raises `DeprecationWarning`
   - `engine.correct(text)` output matches `PhoneticMatcher.correct(text)` 1:1
     for the same dictionary (behaviour parity)

---

## Section 4: yaml v1 → v2 Auto-Conversion Strategy

The thin compat layer inherits `PhoneticMatcher`'s loader, which auto-upgrades
v1 dict specs at load time. No caller-side changes required for inline list/dict usage.

```python
# Pseudo-code: PhoneticMatcher loader (already in Phase 2 core)

def _load_dict(raw):
    version = raw.get("version") if isinstance(raw, dict) else None

    if version == 2:
        return raw  # v2: use as-is

    # v1 upgrade path
    terms = raw if isinstance(raw, list) else raw.get("terms", [])
    upgraded = []
    for item in terms:
        if isinstance(item, str):
            # bare canonical string → v2 replace entry, no aliases
            upgraded.append({"canonical": item, "mode": "replace", "aliases": []})
        elif isinstance(item, dict) and "canonical" in item:
            # old dict form → inject mode=replace if absent
            upgraded.append({**item, "mode": item.get("mode", "replace")})
    return {"version": 2, "terms": upgraded}
```

Complex YAML files with custom fields that cannot survive auto-upgrade should be
migrated with the CLI tool (`phonofix migrate-dict`), documented in MIGRATION.md §4.

---

## Section 5: Advanced API Break List (v0.4.0, no thin compat)

The following symbols are **removed without a compatibility shim** in v0.4.0
(Q1 decision, per plan §二.5 and SPEC.md Appendix B). Callers MUST migrate
before upgrading; no runtime warning — import will raise `ImportError`.

| Symbol | Location | Migration target |
|--------|----------|-----------------|
| `phonofix.PhoneticBackend` | `phonofix/__init__.py` | `phonofix.Phonemizer` protocol |
| `phonofix.EnglishPhoneticBackend` | `phonofix/__init__.py` | `phonemizers.english()` |
| `phonofix.ChinesePhoneticBackend` | `phonofix/__init__.py` | `phonemizers.chinese()` |
| `phonofix.JapanesePhoneticBackend` | `phonofix/__init__.py` | `phonemizers.japanese()` |
| `phonofix.PipelineCorrector` | `phonofix/__init__.py` | `PhoneticMatcher` |
| `phonofix.PipelineCorrectorBase` | `core/pipeline_corrector.py` | `PhoneticMatcher` + `on_event` hook |
| `Engine.create_corrector()` | all language engines | `phonofix.load()` or `PhoneticMatcher(dictionary=...)` |

Callers that subclassed `PhoneticBackend` or `PipelineCorrectorBase` to add custom
phonemization logic must rewrite against the `phonofix.Phonemizer` protocol or the
`PhoneticMatcher` `on_event` callback. Full 1:1 examples are in MIGRATION.md §2.

---

*End of PHASE2-COMPAT-DESIGN.md*

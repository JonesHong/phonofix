# phonofix Migration Guide: v0.3.x → v0.4.0

This guide covers all breaking changes, 1:1 code migration examples, and the
deprecation timeline for callers upgrading from phonofix 0.3.x to 0.4.0.

---

## Section 1: Why Upgrade?

### 0.3.x — Over-engineered 8-layer architecture

phonofix 0.3.x grew into an 8-layer stack:
`Engine` → `create_corrector()` → `PipelineCorrectorBase` → `PhoneticBackend`
→ `AhoCorasickEngine` (self-impl) → surface-variant generation → fuzzy
sliding window → Levenshtein scoring.

This made extending or debugging any single layer unnecessarily expensive,
and the fuzzy sliding window path accounted for **82–98% of wall time** across
all three languages.

### 0.4.0 — Two-layer abstraction + Phase 3 algorithm overhaul

The new stack is two conceptual layers:

```
Caller
  └─ PhoneticMatcher   (language-agnostic — matching, arbitration, events)
       └─ Phonemizer<L> (per-language — G2P, confusion rules, tokenizer)
            └─ pyahocorasick  (C extension, replacing self-impl AC)
```

#### Performance wins (estimated, Phase 3 verification pending)

| Language | dict size | v0.3.x baseline | v0.4.0 target | Speedup |
|----------|-----------|-----------------|---------------|---------|
| zh | 200 | 2,167 ops/s | 8,000–12,000 ops/s | 4–5× |
| ja | 50 | 28 ops/s | 2,500–4,000 ops/s | ~100× |
| ja | 200 | 6 ops/s | 3,000–5,000 ops/s | 500–800× |
| en | 30 | 29 ops/s (+ 14–29 s init) | 1,000–1,500 ops/s | 35–50× |

> Note: Phase 3 (algorithm upgrade) ships in the same v0.4.0 release. If you
> install v0.4.0 before Phase 3 lands, throughput may be on par with 0.3.x
> until the full release is tagged.

#### AC engine swap: `pyahocorasick` (C extension)

The self-implemented `utils/aho_corasick.py` is replaced by `pyahocorasick`:

| Metric | Self-impl | pyahocorasick | Improvement |
|--------|-----------|---------------|-------------|
| Normal AC query | baseline | ~7–9× | 7–9× |
| Delete-1 fuzzy query | baseline | ~5× | 5× |
| Memory (automaton) | 17.42 MB | 0.07 MB | 100×+ |

---

## Section 2: Breaking Changes

### 2.1 Advanced API — no thin-compat layer (MUST migrate)

Per the v0.4.0 Q1 decision, the following advanced APIs are **removed without
a compatibility shim**. Any caller using these must migrate before upgrading:

| Symbol | Status in v0.4.0 |
|--------|-----------------|
| `PhoneticBackend` | **Removed** |
| `EnglishPhoneticBackend` | **Removed** |
| `ChinesePhoneticBackend` | **Removed** |
| `JapanesePhoneticBackend` | **Removed** |
| `PipelineCorrectorBase` | **Removed** |
| `Engine.create_corrector()` | **Removed** — use `phonofix.load()` or `PhoneticMatcher` directly |

Callers that subclassed `PhoneticBackend` or `PipelineCorrectorBase` must
rewrite their customization against `phonofix.Phonemizer` (the new per-language
protocol) or `PhoneticMatcher`'s `on_event` hook.

### 2.2 dict yaml: schema v1 → v2

v0.3.x accepted a list-of-dict or plain list spec inline in Python or via a
YAML file with no enforced schema version. v0.4.0 formalises **schema v2** with
a required `version: 2` header and a mandatory `mode` field per term.

The `PhoneticMatcher` loader **automatically up-converts** simple list/dict
specs (the most common inline usage) to v2 at runtime. Complex YAML files with
custom fields should be migrated with the CLI tool (see Section 4).

### 2.3 Engine entry-points — thin compat + `DeprecationWarning`

`ChineseEngine`, `JapaneseEngine`, and `EnglishEngine` are kept as **thin
wrappers** around `PhoneticMatcher` in v0.4.0. They emit a
`DeprecationWarning` on every instantiation and will be **removed in v0.5.0**.

```python
# This still works in v0.4.0, but you will see:
# DeprecationWarning: ChineseEngine is deprecated and will be removed in
# v0.5.0. Migrate to phonofix.load() or phonofix.PhoneticMatcher.
# See MIGRATION.md for 1:1 examples.
engine = ChineseEngine(verbose=False)
```

---

## Section 3: 1:1 Migration Examples

### 3.1 Chinese (zh)

```python
# ── v0.3.x ──────────────────────────────────────────────────────────────────
from phonofix import ChineseEngine

engine = ChineseEngine(verbose=False)
corrector = engine.create_corrector(
    [
        {"canonical": "雷電将軍", "aliases": ["雷霆将軍", "Raiden Shogun"], "keywords": ["原神"]},
        "崩壞星穹鐵道",
    ]
)
result = corrector.correct("雷霆将軍又在打原神了")

# ── v0.4.0 ──────────────────────────────────────────────────────────────────
import phonofix

matcher = phonofix.load("dict-zh-v2.yaml")          # auto-detect language from yaml
result = matcher.correct("雷霆将軍又在打原神了")

# Or construct inline without a yaml file:
matcher = phonofix.PhoneticMatcher(
    phonemizer=phonofix.phonemizers.chinese(),
    dictionary={
        "version": 2,
        "language": "zh",
        "terms": [
            {
                "canonical": "雷電将軍",
                "mode": "replace",
                "aliases": ["雷霆将軍", "Raiden Shogun"],
                "keywords": ["原神"],
            },
            {"canonical": "崩壞星穹鐵道", "mode": "replace", "aliases": []},
        ],
    },
)
result = matcher.correct("雷霆将軍又在打原神了")
```

### 3.2 Japanese (ja)

```python
# ── v0.3.x ──────────────────────────────────────────────────────────────────
from phonofix import JapaneseEngine

engine = JapaneseEngine(verbose=False)
corrector = engine.create_corrector(
    [
        {"canonical": "ポケモン", "aliases": ["ぽけもん", "pokémon"]},
        "スターレイル",
    ]
)
result = corrector.correct("ぽけもんマスターになる")

# ── v0.4.0 ──────────────────────────────────────────────────────────────────
import phonofix

matcher = phonofix.load("dict-ja-v2.yaml")
result = matcher.correct("ぽけもんマスターになる")

# Or inline:
matcher = phonofix.PhoneticMatcher(
    phonemizer=phonofix.phonemizers.japanese(),
    dictionary={
        "version": 2,
        "language": "ja",
        "terms": [
            {
                "canonical": "ポケモン",
                "mode": "replace",
                "aliases": ["ぽけもん", "pokémon"],
            },
            {"canonical": "スターレイル", "mode": "replace", "aliases": []},
        ],
    },
)
result = matcher.correct("ぽけもんマスターになる")
```

### 3.3 English (en)

```python
# ── v0.3.x ──────────────────────────────────────────────────────────────────
from phonofix import EnglishEngine

engine = EnglishEngine(verbose=False)
corrector = engine.create_corrector(
    {
        "Anthropic": {"aliases": ["Anthropick", "Ann Tropic"], "keywords": ["AI", "Claude"]},
        "Claude":    {"aliases": ["Clod", "Cloud"]},
    }
)
result = corrector.correct("I work at Ann Tropic building Clod")

# ── v0.4.0 ──────────────────────────────────────────────────────────────────
import phonofix

matcher = phonofix.load("dict-en-v2.yaml")
result = matcher.correct("I work at Ann Tropic building Clod")

# Or inline:
matcher = phonofix.PhoneticMatcher(
    phonemizer=phonofix.phonemizers.english(),
    dictionary={
        "version": 2,
        "language": "en",
        "terms": [
            {
                "canonical": "Anthropic",
                "mode": "replace",
                "aliases": ["Anthropick", "Ann Tropic"],
                "keywords": ["AI", "Claude"],
            },
            {
                "canonical": "Claude",
                "mode": "replace",
                "aliases": ["Clod", "Cloud"],
            },
        ],
    },
)
result = matcher.correct("I work at Ann Tropic building Clod")
```

---

## Section 4: dict yaml v1 → v2 Schema Migration

### v1 schema (0.3.x — two common forms)

**Form A — plain list:**

```yaml
# dict-v1.yaml  (Form A)
- 雷電将軍
- 崩壞星穹鐵道
- 枝節
```

**Form B — list of dicts:**

```yaml
# dict-v1.yaml  (Form B)
- canonical: "雷電将軍"
  aliases: ["雷霆将軍", "Raiden Shogun"]
  keywords: ["原神"]
  weight: 0.0
- canonical: "枝節"
  protected: true          # 0.3.x protection convention (not formally spec'd)
```

### v2 schema (0.4.0)

```yaml
# dict-v2.yaml
version: 2
language: zh

terms:
  # active replacement — aliases must be non-empty
  - canonical: "雷電将軍"
    mode: replace
    aliases: ["雷霆将軍", "Raiden Shogun"]
    keywords: ["原神"]
    weight: 0.0

  # negative protection — aliases / keywords / weight fields are rejected
  - canonical: "枝節"
    mode: protect

# optional: per-dict confusion rule overrides
confusion_overrides:
  "ㄢ": ["ㄤ"]
```

Key schema v2 rules enforced at `add_terms()` entry:

| Rule | Reason |
|------|--------|
| `mode` is required for every term | Prevents ambiguous intent |
| `mode: replace` requires non-empty `aliases` | Avoids a replace term that can never match |
| `mode: protect` forbids `aliases`, `keywords`, `weight` | Protection is canonical-only |
| `version: 2` header required in YAML files | Enables unambiguous forward migration |

### CLI migration tool

```bash
# Migrate a v1 yaml file to v2 in one command
phonofix migrate dict-v1.yaml --out dict-v2.yaml

# Validate the result
phonofix lint dict-v2.yaml
```

The `migrate` command infers `mode: replace` for entries that have aliases, and
`mode: protect` for entries flagged with `protected: true`. Entries that are
plain strings without aliases become `mode: replace` with an empty `aliases`
list (the loader will auto-generate phonetic variants at runtime).

For edge cases (custom fields, non-standard keys), review the output of
`phonofix migrate` before committing — the tool emits a `WARNING` line for
every entry it could not unambiguously convert.

---

## Section 5: Deprecation Timeline

| Version | `ChineseEngine` / `JapaneseEngine` / `EnglishEngine` | Action required |
|---------|------------------------------------------------------|-----------------|
| **v0.4.0** | Thin wrapper — emits `DeprecationWarning` once per instantiation. Warning text: *"XxxEngine is deprecated and will be removed in v0.5.0. Migrate to `phonofix.load()` or `phonofix.PhoneticMatcher`. See MIGRATION.md."* | Begin migration; no urgency |
| **v0.4.x** | Same thin wrapper — warning text updated to: *"XxxEngine will be removed in v0.5.0 (scheduled ≥ 3 months from v0.4.0 release). See MIGRATION.md."* | Migrate before v0.5.0 |
| **v0.5.0** | **Removed** — `ImportError` on access | Must be migrated |

Grace period guarantee: v0.5.0 will not be released sooner than 3 months after
v0.4.0 or before 2 minor releases have shipped, whichever is later.

**Advanced API (`PhoneticBackend`, `PipelineCorrectorBase`) — no grace period:**
These are removed in v0.4.0 with no thin compat. If your `pip install
phonofix==0.4.0` fails with `ImportError` on these names, that is expected
behaviour. See Section 2.1 for the migration path.

---

## Section 6: FAQ

**Q1: I subclassed `PhoneticBackend` or `PipelineCorrectorBase`. What do I do?**

There is no thin compat for these classes — v0.4.0 removes them entirely. You
have two options:

- **Simple customisation** (custom confusion rules, custom G2P lookup): pass
  your logic via `phonofix.phonemizers.chinese(confusion_overrides={...})` or
  a per-dict `confusion_overrides` block in your yaml.
- **Deep customisation** (custom tokenizer, custom scoring): implement the new
  `phonofix.Phonemizer` protocol and pass it to `PhoneticMatcher`. The protocol
  requires three methods: `phonemize(text)`, `confusion(phoneme)`, and
  `cost(a, b)`.

Reach out via a GitHub issue if your use-case isn't covered by either path.

---

**Q2: Does the yaml schema convert automatically?**

Partially. The `PhoneticMatcher` loader **auto-converts** the two most common
0.3.x inline formats (plain list of strings, list of dicts with `canonical` +
`aliases`) to v2 at runtime, so existing Python code that passes a dict/list
directly to the old Engine will continue to work through the thin compat layer.

YAML files on disk are **not** silently converted — run
`phonofix migrate dict-v1.yaml --out dict-v2.yaml` to produce a v2 file and
then update your load path. The `lint` command will report a clear error if you
pass a v1 file to `phonofix.load()`.

---

**Q3: Will v0.4.0 be slower than v0.3.x while Phase 3 is still in progress?**

If you install v0.4.0 before the Phase 3 algorithm upgrade (Tier 1–3 canonical
key + AC delete-1 + mutation set) lands in the tagged release, throughput for
fuzzy matching may be comparable to 0.3.x. The AC engine swap alone (Section 1)
gives 7–9× on normal queries and 100×+ memory reduction, but the dominant
bottleneck (82–98% of wall time) is in the fuzzy match path, which Phase 3
addresses. The full performance gains are only available in the final v0.4.0
release tag.

---

**Q4: I use `on_event` callbacks with the old Engine. Do they still work?**

`create_corrector(on_event=...)` is removed with the advanced API. In v0.4.0
pass `on_event` directly to `PhoneticMatcher`:

```python
matcher = phonofix.PhoneticMatcher(
    phonemizer=phonofix.phonemizers.chinese(),
    dictionary=my_dict,
    on_event=my_handler,   # same callback signature, richer event taxonomy
)
```

The v0.4.0 event taxonomy is a superset of what 0.3.x emitted. See `SPEC.md`
for the full list of event types and payload schemas.

---

**Q5: I only use `ChineseEngine` / `JapaneseEngine` / `EnglishEngine` with a
simple term list — do I need to change anything right now?**

Not immediately. The thin compat wrapper in v0.4.0 means your code continues to
run. You will see a `DeprecationWarning` in your logs once per process start per
engine instantiation. Plan your migration before v0.5.0 (≥ 3 months out). The
1:1 examples in Section 3 are designed to be a near-copy-paste replacement.

"""phonofix CLI — 5 subcommands per plan §二.4 + §七 Q2 + Q5."""

from __future__ import annotations

import argparse
import pickle
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_lint(args) -> int:
    """phonofix lint dict.yaml — schema 檢查."""
    import yaml

    from phonofix.core.dict_schema import DictSchemaError, validate_dict

    path = args.dict_path
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 2
    except yaml.YAMLError as exc:
        print(f"Error: invalid YAML in {path}: {exc}", file=sys.stderr)
        return 1

    try:
        d = validate_dict(raw)
    except DictSchemaError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"OK: {path} — version={d.version}, language={d.language}, terms={len(d.terms)}")
    return 0


def cmd_build(args) -> int:
    """phonofix build dict.yaml --out dict.pcom — 預編譯 (disk cache).

    Phase 4 minimal: validate dict then pickle-serialise DictV2 to --out.
    Full AC index cache wired in Phase 5.
    """
    import yaml

    from phonofix.core.dict_schema import DictSchemaError, validate_dict

    path = args.dict_path
    out = args.out

    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 2
    except yaml.YAMLError as exc:
        print(f"Error: invalid YAML in {path}: {exc}", file=sys.stderr)
        return 1

    try:
        d = validate_dict(raw)
    except DictSchemaError as exc:
        print(f"Error: schema validation failed: {exc}", file=sys.stderr)
        return 1

    try:
        with open(out, "wb") as f:
            pickle.dump(d, f, protocol=pickle.HIGHEST_PROTOCOL)
    except OSError as exc:
        print(f"Error: cannot write output file {out}: {exc}", file=sys.stderr)
        return 1

    print(f"Built: {out} ({len(d.terms)} terms, language={d.language})")
    return 0


def cmd_correct(args) -> int:
    """phonofix correct dict.yaml --input text.txt — 一次性校正.

    Phase 4: CLI dispatch path is complete; PhoneticMatcher.correct() is
    NotImplementedError (Phase 3 wire-up); surface a friendly message.
    """
    import yaml

    from phonofix.core.dict_schema import DictSchemaError, validate_dict

    path = args.dict_path
    input_path = args.input

    # Validate dict
    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 2
    except yaml.YAMLError as exc:
        print(f"Error: invalid YAML in {path}: {exc}", file=sys.stderr)
        return 1

    try:
        validate_dict(raw)
    except DictSchemaError as exc:
        print(f"Error: schema validation failed: {exc}", file=sys.stderr)
        return 1

    # Read input
    try:
        with open(input_path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 2

    # Attempt correction — PhoneticMatcher.correct raises NotImplementedError in Phase 3
    try:
        from phonofix.core.matcher import PhoneticMatcher

        matcher = PhoneticMatcher(phonemizer=None, dictionary=raw)
        result = matcher.correct(text)
        print(result)
        return 0
    except NotImplementedError:
        print(
            "Note: PhoneticMatcher.correct() is Phase 3 implementation pending. "
            "Correction engine not yet available — text returned unchanged.",
            file=sys.stderr,
        )
        print(text)
        return 0


def cmd_bench(args) -> int:
    """phonofix bench dict.yaml --suite default — 性能 benchmark.

    Phase 4 stub: accept --suite but defer execution to Phase 5.
    """
    import yaml

    from phonofix.core.dict_schema import DictSchemaError, validate_dict

    path = args.dict_path
    suite = args.suite

    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 2
    except yaml.YAMLError as exc:
        print(f"Error: invalid YAML in {path}: {exc}", file=sys.stderr)
        return 1

    try:
        d = validate_dict(raw)
    except DictSchemaError as exc:
        print(f"Error: schema validation failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Benchmark suite '{suite}' accepted "
        f"(dict: {len(d.terms)} terms, language={d.language}). "
        f"Phase 5 deliverable — full benchmark engine not yet implemented."
    )
    return 0


def cmd_migrate(args) -> int:
    """phonofix migrate dict-v1.yaml --out dict-v2.yaml — 字典 schema v1 → v2.

    v1 formats accepted:
      A) list of str:           ["word1", "word2"]
      B) dict of {str: str}:   {"alias": "canonical", ...}
      C) dict of {str: dict}:  {"canonical": {"aliases": [...], "keywords": [...], "weight": N}}
      D) top-level dict with "terms" list (already v2-like but version != 2 or missing)
    """
    import yaml

    from phonofix.core.dict_schema import DictSchemaError, validate_dict

    path = args.dict_path
    out = args.out

    try:
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        return 2
    except yaml.YAMLError as exc:
        print(f"Error: invalid YAML in {path}: {exc}", file=sys.stderr)
        return 1

    # Check if already v2 — nothing to do
    if isinstance(raw, dict) and raw.get("version") == 2:
        try:
            validate_dict(raw)
            print(f"Already v2 schema: {path} — no migration needed.")
            return 0
        except DictSchemaError:
            pass  # fall through to attempt re-normalisation

    # Detect language from top-level key if present
    language = "zh"
    if isinstance(raw, dict):
        language = raw.get("language", "zh")

    terms_out: list[dict] = []

    # --- Format A: list of str ---
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                # plain string → protect mode (no aliases, just canonical)
                terms_out.append({"canonical": item, "mode": "protect"})
            elif isinstance(item, dict):
                # could be an inline term dict already
                terms_out.append(_normalise_term_dict(item))
            else:
                print(
                    f"Warning: skipping unrecognised list item: {item!r}",
                    file=sys.stderr,
                )

    # --- Format B/C: top-level mapping (not v2 structure) ---
    elif isinstance(raw, dict) and "terms" not in raw and "version" not in raw:
        for canonical, value in raw.items():
            if canonical in ("language", "version", "confusion_overrides"):
                continue
            if isinstance(value, str):
                # Format B: {"alias": "canonical"} — treat key as alias, value as canonical
                terms_out.append({"canonical": value, "mode": "replace", "aliases": [canonical]})
            elif isinstance(value, dict):
                # Format C: {"canonical": {aliases, keywords, weight}}
                aliases = value.get("aliases") or []
                keywords = value.get("keywords") or []
                weight = value.get("weight", 0.0)
                if aliases:
                    terms_out.append(
                        {
                            "canonical": canonical,
                            "mode": "replace",
                            "aliases": list(aliases),
                            "keywords": list(keywords),
                            "weight": float(weight),
                        }
                    )
                else:
                    terms_out.append({"canonical": canonical, "mode": "protect"})
            else:
                # bare scalar value — treat as a protect entry
                terms_out.append({"canonical": canonical, "mode": "protect"})

    # --- Format D: top-level mapping with "terms" key (old v1 wrapper) ---
    elif isinstance(raw, dict) and "terms" in raw:
        raw_terms = raw.get("terms", [])
        if isinstance(raw_terms, list):
            for item in raw_terms:
                if isinstance(item, str):
                    terms_out.append({"canonical": item, "mode": "protect"})
                elif isinstance(item, dict):
                    terms_out.append(_normalise_term_dict(item))
        elif isinstance(raw_terms, dict):
            for canonical, value in raw_terms.items():
                if isinstance(value, str):
                    terms_out.append(
                        {"canonical": value, "mode": "replace", "aliases": [canonical]}
                    )
                elif isinstance(value, dict):
                    aliases = value.get("aliases") or []
                    terms_out.append(
                        {
                            "canonical": canonical,
                            "mode": "replace" if aliases else "protect",
                            "aliases": list(aliases),
                            "keywords": list(value.get("keywords") or []),
                            "weight": float(value.get("weight", 0.0)),
                        }
                    )
        language = raw.get("language", language)
    else:
        print(
            f"Error: unrecognised v1 format in {path} — cannot auto-detect schema.",
            file=sys.stderr,
        )
        return 1

    v2_dict: dict = {
        "version": 2,
        "language": language,
        "terms": terms_out,
    }
    # preserve confusion_overrides if present
    if isinstance(raw, dict) and "confusion_overrides" in raw:
        v2_dict["confusion_overrides"] = raw["confusion_overrides"]

    # Validate resulting v2
    try:
        validate_dict(v2_dict)
    except DictSchemaError as exc:
        print(
            f"Error: migration produced invalid v2 schema: {exc}\nPlease fix source dict manually.",
            file=sys.stderr,
        )
        return 1

    try:
        with open(out, "w", encoding="utf-8") as f:
            yaml.dump(v2_dict, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    except OSError as exc:
        print(f"Error: cannot write output file {out}: {exc}", file=sys.stderr)
        return 1

    print(f"Migrated: {path} → {out} ({len(terms_out)} terms, language={language})")
    return 0


def _normalise_term_dict(item: dict) -> dict:
    """Convert an inline dict term (various v1 shapes) into a v2 term dict."""
    canonical = item.get("canonical") or item.get("word") or item.get("name", "")
    aliases = item.get("aliases") or []
    mode = item.get("mode", "replace" if aliases else "protect")
    result: dict = {"canonical": str(canonical), "mode": mode}
    if aliases:
        result["aliases"] = list(aliases)
        if item.get("keywords"):
            result["keywords"] = list(item["keywords"])
        if item.get("weight") is not None:
            result["weight"] = float(item["weight"])
    return result


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def make_parser() -> argparse.ArgumentParser:
    """Build full CLI parser."""
    parser = argparse.ArgumentParser(prog="phonofix", description="phonofix CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_lint = sub.add_parser("lint", help="Validate dict yaml schema")
    p_lint.add_argument("dict_path", type=str)
    p_lint.set_defaults(func=cmd_lint)

    p_build = sub.add_parser("build", help="Pre-compile dict (disk cache)")
    p_build.add_argument("dict_path", type=str)
    p_build.add_argument("--out", required=True, type=str)
    p_build.set_defaults(func=cmd_build)

    p_correct = sub.add_parser("correct", help="Apply correction to text file")
    p_correct.add_argument("dict_path", type=str)
    p_correct.add_argument("--input", required=True, type=str)
    p_correct.set_defaults(func=cmd_correct)

    p_bench = sub.add_parser("bench", help="Run performance benchmark suite")
    p_bench.add_argument("dict_path", type=str)
    p_bench.add_argument("--suite", default="default", choices=["default", "ci"])
    p_bench.set_defaults(func=cmd_bench)

    p_migrate = sub.add_parser("migrate", help="Convert dict yaml v1 schema to v2")
    p_migrate.add_argument("dict_path", type=str)
    p_migrate.add_argument("--out", required=True, type=str)
    p_migrate.set_defaults(func=cmd_migrate)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

"""CLI integration tests — phonofix 5 subcommands (Phase 4)."""

from __future__ import annotations

import pickle
from pathlib import Path

import pytest
import yaml

from phonofix.cli.__main__ import main

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_V2_YAML = {
    "version": 2,
    "language": "zh",
    "terms": [
        {
            "canonical": "雷電将軍",
            "mode": "replace",
            "aliases": ["雷霆将軍"],
            "keywords": ["原神"],
            "weight": 0.0,
        },
        {
            "canonical": "枝節",
            "mode": "protect",
        },
    ],
}

INVALID_V2_YAML = {
    "version": 2,
    "language": "zh",
    "terms": [
        # mode=replace but no aliases → schema error
        {"canonical": "壞詞條", "mode": "replace"},
    ],
}

V1_LIST_YAML = ["台北車站", "牛奶", "發揮"]

V1_DICT_YAML = {
    "永和豆漿": {
        "aliases": ["永豆", "勇豆"],
        "keywords": ["吃", "喝"],
        "weight": 0.3,
    },
    "Python": {
        "aliases": ["Pyton", "pythn"],
    },
}


@pytest.fixture
def valid_dict(tmp_path: Path) -> Path:
    p = tmp_path / "dict_valid.yaml"
    p.write_text(yaml.dump(VALID_V2_YAML, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture
def invalid_dict(tmp_path: Path) -> Path:
    p = tmp_path / "dict_invalid.yaml"
    p.write_text(yaml.dump(INVALID_V2_YAML, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture
def v1_list_dict(tmp_path: Path) -> Path:
    p = tmp_path / "dict_v1_list.yaml"
    p.write_text(yaml.dump(V1_LIST_YAML, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture
def v1_dict_dict(tmp_path: Path) -> Path:
    p = tmp_path / "dict_v1_dict.yaml"
    content = {
        "language": "zh",
        **V1_DICT_YAML,
    }
    p.write_text(yaml.dump(content, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture
def sample_text(tmp_path: Path) -> Path:
    p = tmp_path / "text.txt"
    p.write_text("我在北車買了流奶，用Pyton寫code。", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# lint tests
# ---------------------------------------------------------------------------


class TestLint:
    def test_valid_yaml_exits_0(self, valid_dict: Path, capsys):
        rc = main(["lint", str(valid_dict)])
        out, _ = capsys.readouterr()
        assert rc == 0
        assert "OK" in out

    def test_valid_yaml_shows_term_count(self, valid_dict: Path, capsys):
        main(["lint", str(valid_dict)])
        out, _ = capsys.readouterr()
        assert "terms=2" in out

    def test_invalid_schema_exits_1(self, invalid_dict: Path, capsys):
        rc = main(["lint", str(invalid_dict)])
        _, err = capsys.readouterr()
        assert rc == 1
        assert "Error" in err

    def test_invalid_schema_shows_error_message(self, invalid_dict: Path, capsys):
        main(["lint", str(invalid_dict)])
        _, err = capsys.readouterr()
        assert len(err.strip()) > 0

    def test_missing_file_exits_2(self, tmp_path: Path, capsys):
        rc = main(["lint", str(tmp_path / "nonexistent.yaml")])
        _, err = capsys.readouterr()
        assert rc == 2
        assert "not found" in err.lower()

    def test_no_args_raises_argparse_error(self):
        with pytest.raises(SystemExit) as exc:
            main(["lint"])
        assert exc.value.code != 0


# ---------------------------------------------------------------------------
# migrate tests
# ---------------------------------------------------------------------------


class TestMigrate:
    def test_v1_list_produces_v2(self, v1_list_dict: Path, tmp_path: Path, capsys):
        out_path = tmp_path / "out.yaml"
        rc = main(["migrate", str(v1_list_dict), "--out", str(out_path)])
        assert rc == 0
        assert out_path.exists()

    def test_v1_list_content_is_valid_v2(self, v1_list_dict: Path, tmp_path: Path):
        from phonofix.core.dict_schema import validate_dict

        out_path = tmp_path / "out.yaml"
        main(["migrate", str(v1_list_dict), "--out", str(out_path)])
        raw = yaml.safe_load(out_path.read_text(encoding="utf-8"))
        d = validate_dict(raw)
        assert d.version == 2
        assert len(d.terms) == 3

    def test_v1_list_canonicals_preserved(self, v1_list_dict: Path, tmp_path: Path):
        out_path = tmp_path / "out.yaml"
        main(["migrate", str(v1_list_dict), "--out", str(out_path)])
        raw = yaml.safe_load(out_path.read_text(encoding="utf-8"))
        canonicals = {t["canonical"] for t in raw["terms"]}
        assert "台北車站" in canonicals
        assert "牛奶" in canonicals
        assert "發揮" in canonicals

    def test_v1_dict_with_aliases_produces_replace_mode(self, v1_dict_dict: Path, tmp_path: Path):
        out_path = tmp_path / "out.yaml"
        rc = main(["migrate", str(v1_dict_dict), "--out", str(out_path)])
        assert rc == 0
        raw = yaml.safe_load(out_path.read_text(encoding="utf-8"))
        replace_terms = [t for t in raw["terms"] if t["mode"] == "replace"]
        assert len(replace_terms) >= 1

    def test_v1_dict_aliases_included(self, v1_dict_dict: Path, tmp_path: Path):
        out_path = tmp_path / "out.yaml"
        main(["migrate", str(v1_dict_dict), "--out", str(out_path)])
        raw = yaml.safe_load(out_path.read_text(encoding="utf-8"))
        doudou = next((t for t in raw["terms"] if t["canonical"] == "永和豆漿"), None)
        assert doudou is not None
        assert "永豆" in doudou.get("aliases", [])

    def test_migrate_prints_success_message(self, v1_list_dict: Path, tmp_path: Path, capsys):
        out_path = tmp_path / "out.yaml"
        main(["migrate", str(v1_list_dict), "--out", str(out_path)])
        out, _ = capsys.readouterr()
        assert "Migrated" in out

    def test_migrate_missing_source_exits_2(self, tmp_path: Path, capsys):
        rc = main(["migrate", str(tmp_path / "ghost.yaml"), "--out", str(tmp_path / "out.yaml")])
        _, err = capsys.readouterr()
        assert rc == 2
        assert "not found" in err.lower()

    def test_already_v2_no_migration_needed(self, valid_dict: Path, tmp_path: Path, capsys):
        out_path = tmp_path / "out.yaml"
        rc = main(["migrate", str(valid_dict), "--out", str(out_path)])
        out, _ = capsys.readouterr()
        assert rc == 0
        assert "Already v2" in out or "no migration needed" in out


# ---------------------------------------------------------------------------
# build tests
# ---------------------------------------------------------------------------


class TestBuild:
    def test_build_exits_0(self, valid_dict: Path, tmp_path: Path, capsys):
        out = tmp_path / "dict.pcom"
        rc = main(["build", str(valid_dict), "--out", str(out)])
        assert rc == 0

    def test_build_creates_file(self, valid_dict: Path, tmp_path: Path):
        out = tmp_path / "dict.pcom"
        main(["build", str(valid_dict), "--out", str(out)])
        assert out.exists()

    def test_build_file_is_valid_pickle(self, valid_dict: Path, tmp_path: Path):
        from phonofix.core.dict_schema import DictV2

        out = tmp_path / "dict.pcom"
        main(["build", str(valid_dict), "--out", str(out)])
        with open(out, "rb") as f:
            obj = pickle.load(f)
        assert isinstance(obj, DictV2)
        assert obj.version == 2

    def test_build_prints_success(self, valid_dict: Path, tmp_path: Path, capsys):
        out = tmp_path / "dict.pcom"
        main(["build", str(valid_dict), "--out", str(out)])
        stdout, _ = capsys.readouterr()
        assert "Built" in stdout

    def test_build_invalid_dict_exits_1(self, invalid_dict: Path, tmp_path: Path, capsys):
        out = tmp_path / "dict.pcom"
        rc = main(["build", str(invalid_dict), "--out", str(out)])
        _, err = capsys.readouterr()
        assert rc == 1
        assert "Error" in err


# ---------------------------------------------------------------------------
# correct tests
# ---------------------------------------------------------------------------


class TestCorrect:
    def test_correct_graceful_phase3_pending(self, valid_dict: Path, sample_text: Path, capsys):
        rc = main(["correct", str(valid_dict), "--input", str(sample_text)])
        out, err = capsys.readouterr()
        # Should exit 0 (graceful) and produce output or friendly message
        assert rc == 0
        combined = out + err
        assert len(combined.strip()) > 0

    def test_correct_missing_dict_exits_2(self, tmp_path: Path, sample_text: Path, capsys):
        rc = main(["correct", str(tmp_path / "ghost.yaml"), "--input", str(sample_text)])
        _, err = capsys.readouterr()
        assert rc == 2

    def test_correct_missing_input_exits_2(self, valid_dict: Path, tmp_path: Path, capsys):
        rc = main(["correct", str(valid_dict), "--input", str(tmp_path / "ghost.txt")])
        _, err = capsys.readouterr()
        assert rc == 2

    def test_correct_phase3_message_or_text(self, valid_dict: Path, sample_text: Path, capsys):
        """Either prints original text or a Phase-3-pending message — either is acceptable."""
        main(["correct", str(valid_dict), "--input", str(sample_text)])
        out, err = capsys.readouterr()
        # Friendly notice should mention phase or implementation
        combined = out + err
        assert "Phase 3" in combined or "pending" in combined or "北車" in combined


# ---------------------------------------------------------------------------
# bench tests
# ---------------------------------------------------------------------------


class TestBench:
    def test_bench_default_suite_graceful(self, valid_dict: Path, capsys):
        rc = main(["bench", str(valid_dict), "--suite", "default"])
        out, _ = capsys.readouterr()
        assert rc == 0
        assert "Phase 5" in out or "deliverable" in out.lower() or "benchmark" in out.lower()

    def test_bench_ci_suite_accepted(self, valid_dict: Path, capsys):
        rc = main(["bench", str(valid_dict), "--suite", "ci"])
        assert rc == 0

    def test_bench_invalid_suite_error(self, valid_dict: Path):
        with pytest.raises(SystemExit) as exc:
            main(["bench", str(valid_dict), "--suite", "unknown"])
        assert exc.value.code != 0


# ---------------------------------------------------------------------------
# global parser tests
# ---------------------------------------------------------------------------


class TestParser:
    def test_help_shows_5_subcommands(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0
        out, _ = capsys.readouterr()
        for cmd in ("lint", "build", "correct", "bench", "migrate"):
            assert cmd in out

    def test_unknown_subcommand_argparse_error(self):
        with pytest.raises(SystemExit) as exc:
            main(["unknown"])
        assert exc.value.code != 0

    def test_no_subcommand_argparse_error(self):
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code != 0

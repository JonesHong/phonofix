"""Bench suite tests — plumbing + contract checks for phonofix.bench.runner."""

from __future__ import annotations

import json
from pathlib import Path

from phonofix.bench.runner import (
    CI_SUITE,
    CI_THRESHOLDS,
    DEFAULT_SUITE,
    BenchResult,
    BenchScenario,
    check_ci_thresholds,
    run_scenario,
    run_suite,
)

# ---------------------------------------------------------------------------
# Suite definitions
# ---------------------------------------------------------------------------


def test_default_suite_has_at_least_8_scenarios():
    assert len(DEFAULT_SUITE) >= 8


def test_default_suite_covers_zh_ja_en():
    langs = {s.language for s in DEFAULT_SUITE}
    assert "zh" in langs
    assert "ja" in langs
    assert "en" in langs


def test_ci_suite_is_smaller_than_default():
    assert len(CI_SUITE) < len(DEFAULT_SUITE)


def test_ci_thresholds_keys_match_ci_suite_names():
    ci_names = {s.name for s in CI_SUITE}
    for key in CI_THRESHOLDS:
        assert key in ci_names, f"CI_THRESHOLDS key '{key}' not in CI_SUITE names"


def test_ci_suite_all_scenario_names_unique():
    names = [s.name for s in CI_SUITE]
    assert len(names) == len(set(names))


def test_default_suite_all_scenario_names_unique():
    names = [s.name for s in DEFAULT_SUITE]
    assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# run_scenario — mock matcher_factory
# ---------------------------------------------------------------------------


class _FastMatcher:
    """Instant no-op matcher that always returns the input text unchanged."""

    def correct(self, text: str) -> str:
        return text


class _NotImplMatcher:
    """Matcher that always raises NotImplementedError — simulates Phase 3 stub."""

    def correct(self, text: str) -> str:
        raise NotImplementedError("stub")


def _fast_factory(language: str, dict_size: int) -> _FastMatcher:
    return _FastMatcher()


def _notimpl_factory(language: str, dict_size: int) -> _NotImplMatcher:
    return _NotImplMatcher()


def test_run_scenario_returns_bench_result():
    scenario = BenchScenario("test_zh", "zh", 10, 50, iterations=5)
    result = run_scenario(scenario, _fast_factory)
    assert isinstance(result, BenchResult)


def test_run_scenario_throughput_positive_with_fast_matcher():
    scenario = BenchScenario("test_en", "en", 10, 50, iterations=10)
    result = run_scenario(scenario, _fast_factory)
    assert result.throughput_ops_per_sec > 0


def test_run_scenario_latencies_nonnegative():
    scenario = BenchScenario("test_ja", "ja", 10, 50, iterations=5)
    result = run_scenario(scenario, _fast_factory)
    assert result.latency_p50_ms >= 0
    assert result.latency_p99_ms >= 0


def test_run_scenario_mem_peak_nonnegative():
    scenario = BenchScenario("test_mem", "zh", 10, 50, iterations=5)
    result = run_scenario(scenario, _fast_factory)
    assert result.mem_peak_mb >= 0


def test_run_scenario_not_implemented_sets_notes_and_zero_throughput():
    scenario = BenchScenario("test_stub", "zh", 10, 50, iterations=5)
    result = run_scenario(scenario, _notimpl_factory)
    assert result.notes == "implementation pending"
    assert result.throughput_ops_per_sec == 0.0


def test_run_scenario_scenario_attached_to_result():
    scenario = BenchScenario("attached", "en", 30, 100, iterations=3)
    result = run_scenario(scenario, _fast_factory)
    assert result.scenario is scenario


# ---------------------------------------------------------------------------
# run_suite
# ---------------------------------------------------------------------------


def test_run_suite_default_calls_each_scenario():
    called: list[str] = []

    def counting_factory(language: str, dict_size: int) -> _FastMatcher:
        called.append(language)
        return _FastMatcher()

    results = run_suite("default", matcher_factory=counting_factory)
    assert len(results) == len(DEFAULT_SUITE)
    assert len(called) == len(DEFAULT_SUITE)


def test_run_suite_ci_returns_fewer_results_than_default():
    results_ci = run_suite("ci", matcher_factory=_fast_factory)
    results_default = run_suite("default", matcher_factory=_fast_factory)
    assert len(results_ci) < len(results_default)


def test_run_suite_with_output_path_writes_json(tmp_path: Path):
    out = tmp_path / "bench_out.json"
    run_suite("ci", matcher_factory=_fast_factory, output_path=out)
    assert out.exists()
    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert len(data) == len(CI_SUITE)
    # Each entry must have key fields
    for entry in data:
        assert "throughput_ops_per_sec" in entry
        assert "latency_p50_ms" in entry
        assert "latency_p99_ms" in entry
        assert "mem_peak_mb" in entry
        assert "scenario" in entry


def test_run_suite_no_factory_uses_noop_and_returns_results():
    # Should not raise even with no matcher_factory supplied
    results = run_suite("ci", matcher_factory=None)
    assert len(results) == len(CI_SUITE)
    for r in results:
        assert r.throughput_ops_per_sec >= 0


# ---------------------------------------------------------------------------
# check_ci_thresholds
# ---------------------------------------------------------------------------


def _make_result(name: str, throughput: float) -> BenchResult:
    scenario = BenchScenario(name, "zh", 200, 100, iterations=1)
    return BenchResult(
        scenario=scenario,
        throughput_ops_per_sec=throughput,
        latency_p50_ms=0.0,
        latency_p99_ms=0.0,
        mem_peak_mb=0.0,
    )


def test_check_ci_thresholds_all_pass():
    results = [
        _make_result("zh_200_ci", 10000.0),
        _make_result("ja_200_ci", 2000.0),
        _make_result("en_small_ci", 1000.0),
    ]
    all_pass, failures = check_ci_thresholds(results)
    assert all_pass is True
    assert failures == []


def test_check_ci_thresholds_fail_returns_failures():
    results = [
        _make_result("zh_200_ci", 100.0),  # below 5000
        _make_result("ja_200_ci", 2000.0),
        _make_result("en_small_ci", 1000.0),
    ]
    all_pass, failures = check_ci_thresholds(results)
    assert all_pass is False
    assert len(failures) == 1
    assert "zh_200_ci" in failures[0]


def test_check_ci_thresholds_missing_scenario_skipped():
    # Only provide en_small_ci above threshold — zh/ja absent → skipped, not failed
    results = [_make_result("en_small_ci", 1000.0)]
    all_pass, failures = check_ci_thresholds(results)
    assert all_pass is True
    assert failures == []


def test_check_ci_thresholds_multiple_failures():
    results = [
        _make_result("zh_200_ci", 1.0),
        _make_result("ja_200_ci", 1.0),
        _make_result("en_small_ci", 1.0),
    ]
    all_pass, failures = check_ci_thresholds(results)
    assert all_pass is False
    assert len(failures) == 3

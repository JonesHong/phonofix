"""Benchmark runner — used by `phonofix bench --suite default|ci`.

Suite definitions:
  default: full perf comparison (zh/ja/en three langs × small/medium/large dict)
  ci: fast subset (< 60s) for CI perf regression gate

Output: JSON with throughput / latency / memory per scenario.
Reuses baseline_bench.py fixture for v0.3.2 baseline comparison.
"""

from __future__ import annotations

import json
import statistics
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass
class BenchScenario:
    name: str
    language: str  # zh | ja | en | ko
    dict_size: int
    text_length: int
    iterations: int = 100


@dataclass
class BenchResult:
    scenario: BenchScenario
    throughput_ops_per_sec: float
    latency_p50_ms: float
    latency_p99_ms: float
    mem_peak_mb: float
    notes: str = ""


DEFAULT_SUITE = [
    BenchScenario("zh_small", "zh", 30, 100, iterations=200),
    BenchScenario("zh_medium", "zh", 50, 100, iterations=200),
    BenchScenario("zh_large", "zh", 200, 100, iterations=100),
    BenchScenario("ja_small", "ja", 30, 100, iterations=200),
    BenchScenario("ja_medium", "ja", 50, 100, iterations=100),
    BenchScenario("ja_large", "ja", 200, 100, iterations=50),
    BenchScenario("en_small", "en", 30, 100, iterations=200),
    BenchScenario("en_medium", "en", 50, 100, iterations=100),
]

CI_SUITE = [
    BenchScenario("zh_200_ci", "zh", 200, 100, iterations=20),
    BenchScenario("ja_200_ci", "ja", 200, 100, iterations=20),
    BenchScenario("en_small_ci", "en", 30, 100, iterations=20),
]

# CI perf regression thresholds — fail PR if any below (plan §六.5)
CI_THRESHOLDS = {
    "zh_200_ci": 5000,  # ops/sec
    "ja_200_ci": 1000,  # ops/sec (v0.4.0 target; baseline was 6)
    "en_small_ci": 500,  # ops/sec
}


def _make_dummy_text(length: int) -> str:
    """Generate a fixed-length dummy text for bench input."""
    base = "test input text for phonofix benchmark scenario "
    repeats = (length // len(base)) + 1
    return (base * repeats)[:length]


def run_scenario(
    scenario: BenchScenario,
    matcher_factory: Callable,
) -> BenchResult:
    """
    Run a single scenario, return BenchResult.
    matcher_factory(language, dict_size) -> PhoneticMatcher instance

    Phase 5 stub: PhoneticMatcher.correct() may still be NotImplementedError —
    catch and report with notes="implementation pending"; still emit metrics for
    bench-suite plumbing tests.
    """
    matcher = matcher_factory(scenario.language, scenario.dict_size)
    text = _make_dummy_text(scenario.text_length)

    latencies_ms: list[float] = []
    implementation_pending = False

    tracemalloc.start()
    try:
        for _ in range(scenario.iterations):
            t0 = time.perf_counter()
            try:
                matcher.correct(text)
            except NotImplementedError:
                implementation_pending = True
                # Still record timing so bench plumbing tests get real metrics
            t1 = time.perf_counter()
            latencies_ms.append((t1 - t0) * 1000.0)
    finally:
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    mem_peak_mb = peak_bytes / (1024 * 1024)

    if latencies_ms:
        sorted_lat = sorted(latencies_ms)
        p50 = statistics.median(sorted_lat)
        p99_idx = max(0, int(len(sorted_lat) * 0.99) - 1)
        p99 = sorted_lat[p99_idx]
        total_sec = sum(latencies_ms) / 1000.0
        throughput = scenario.iterations / total_sec if total_sec > 0 else 0.0
    else:
        p50 = 0.0
        p99 = 0.0
        throughput = 0.0

    notes = "implementation pending" if implementation_pending else ""
    if implementation_pending:
        throughput = 0.0

    return BenchResult(
        scenario=scenario,
        throughput_ops_per_sec=throughput,
        latency_p50_ms=p50,
        latency_p99_ms=p99,
        mem_peak_mb=mem_peak_mb,
        notes=notes,
    )


def run_suite(
    suite_name: str = "default",
    matcher_factory: Optional[Callable] = None,
    output_path: Optional[Path] = None,
) -> list[BenchResult]:
    """Run all scenarios in suite, optionally write JSON output, return results."""
    if suite_name == "ci":
        suite = CI_SUITE
    else:
        suite = DEFAULT_SUITE

    if matcher_factory is None:
        # Default no-op factory for smoke-testing suite plumbing
        class _NoopMatcher:
            def correct(self, text: str) -> str:
                return text

        def matcher_factory(language: str, dict_size: int) -> _NoopMatcher:
            return _NoopMatcher()

    results: list[BenchResult] = []
    for scenario in suite:
        result = run_scenario(scenario, matcher_factory)
        results.append(result)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "scenario": asdict(r.scenario),
                "throughput_ops_per_sec": r.throughput_ops_per_sec,
                "latency_p50_ms": r.latency_p50_ms,
                "latency_p99_ms": r.latency_p99_ms,
                "mem_peak_mb": r.mem_peak_mb,
                "notes": r.notes,
            }
            for r in results
        ]
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    return results


def check_ci_thresholds(results: list[BenchResult]) -> tuple[bool, list[str]]:
    """Validate CI scenario results against CI_THRESHOLDS. Returns (all_pass, failure_messages)."""
    failures: list[str] = []
    by_name = {r.scenario.name: r for r in results}
    for name, threshold in CI_THRESHOLDS.items():
        if name not in by_name:
            continue
        if by_name[name].throughput_ops_per_sec < threshold:
            failures.append(
                f"{name}: {by_name[name].throughput_ops_per_sec:.0f} < {threshold} ops/sec threshold"
            )
    return (len(failures) == 0, failures)

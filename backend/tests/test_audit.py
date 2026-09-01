"""Comprehensive unit and benchmark tests for the AutoVerify Audit Engine."""

import time
import pytest

from app.audit import (
    AuditConfig,
    AuditStatus,
    BuggyConverter,
    CorrectConverter,
    ErrorRaisingConverter,
    InvalidOutputConverter,
    TimeoutConverter,
    calculate_verified_conversion_rate,
    run_audit,
)
from app.core.algorithms.simulation import simulate_dfa, simulate_epsilon_nfa
from app.core.automata.models import DFA
from app.core.generators import GeneratorConfig, generate_test_suite


# ============================================================================
# 1. CORRECT CONVERTER TESTS
# ============================================================================


def test_correct_converter_10_tests():
    """Correct converter evaluated on 10 tests must have 100% verified conversion rate."""
    suite = generate_test_suite(GeneratorConfig(count=10), seed=101, include_edge_cases=True)
    report = run_audit(CorrectConverter(), suite)

    assert report.total_tests == len(suite)
    assert report.verified_count == len(suite)
    assert report.failed_count == 0
    assert report.invalid_output_count == 0
    assert report.execution_error_count == 0
    assert report.timeout_count == 0
    assert report.verified_conversion_rate == 1.0
    assert len(report.failures) == 0


def test_correct_converter_100_tests():
    """Correct converter evaluated on 100 tests must achieve 100% VERIFIED."""
    suite = generate_test_suite(GeneratorConfig(count=100), seed=102, include_edge_cases=True)
    report = run_audit(CorrectConverter(), suite)

    assert report.total_tests == len(suite)
    assert report.verified_count == len(suite)
    assert report.failed_count == 0
    assert report.verified_conversion_rate == 1.0


# ============================================================================
# 2. BUGGY CONVERTER & COUNTEREXAMPLE TESTS
# ============================================================================


def test_buggy_converter_detects_failures():
    """Buggy converter must be caught with NOT_EQUIVALENT outcomes."""
    suite = generate_test_suite(GeneratorConfig(count=30), seed=103, include_edge_cases=True)
    report = run_audit(BuggyConverter(), suite, config=AuditConfig(include_verification_trace=True))

    assert report.failed_count > 0
    assert report.verified_conversion_rate is not None
    assert report.verified_conversion_rate < 1.0
    assert len(report.mathematical_failures) == report.failed_count


def test_counterexamples_are_valid_and_distinguishing():
    """Every NOT_EQUIVALENT failure must include a counterexample that distinguishes the automata."""
    suite = generate_test_suite(GeneratorConfig(count=40), seed=104, include_edge_cases=True)
    report = run_audit(BuggyConverter(), suite)

    math_failures = report.mathematical_failures
    assert len(math_failures) > 0

    # Build lookup map of original test cases
    case_map = {c.metadata.test_id: c.automaton for c in suite}

    for fail in math_failures:
        assert fail.status == AuditStatus.NOT_EQUIVALENT
        assert fail.counterexample is not None
        ce = fail.counterexample

        # Retrieve original ε-NFA and generated DFA
        enfa = case_map[fail.test_id]
        gen_dfa = DFA.from_dict(fail.generated_dfa)

        # Invariant: simulate(enfa, ce) != simulate(gen_dfa, ce)
        enfa_acc = simulate_epsilon_nfa(enfa, ce)
        dfa_acc = simulate_dfa(gen_dfa, ce)
        assert enfa_acc != dfa_acc, (
            f"Counterexample '{ce}' failed to distinguish automata for test {fail.test_id}"
        )
        assert enfa_acc == fail.expected_acceptance
        assert dfa_acc == fail.generated_acceptance


# ============================================================================
# 3. OPERATIONAL FAILURE CLASSIFICATION TESTS
# ============================================================================


def test_invalid_output_converter():
    """Converter returning malformed output must be classified as INVALID_OUTPUT."""
    suite = generate_test_suite(GeneratorConfig(count=5), seed=105, include_edge_cases=False)
    report = run_audit(InvalidOutputConverter(), suite)

    assert report.total_tests == len(suite)
    assert report.invalid_output_count == len(suite)
    assert report.verified_count == 0
    assert report.failed_count == 0
    # No valid outputs produced -> VCR is None
    assert report.verified_conversion_rate is None
    for res in report.results:
        assert res.status == AuditStatus.INVALID_OUTPUT
        assert res.error_message is not None


def test_exception_raising_converter():
    """Converter throwing runtime errors must be classified as EXECUTION_ERROR."""
    suite = generate_test_suite(GeneratorConfig(count=5), seed=106, include_edge_cases=False)
    report = run_audit(ErrorRaisingConverter(), suite)

    assert report.total_tests == len(suite)
    assert report.execution_error_count == len(suite)
    assert report.verified_count == 0
    assert report.verified_conversion_rate is None
    for res in report.results:
        assert res.status == AuditStatus.EXECUTION_ERROR
        assert "RuntimeError" in (res.error_message or "")


def test_timeout_converter():
    """Converter exceeding time limit must be classified as TIMEOUT."""
    suite = generate_test_suite(GeneratorConfig(count=2), seed=107, include_edge_cases=False)
    # Configure 0.1s timeout with converter sleeping 2.0s
    config = AuditConfig(timeout_seconds=0.1)
    report = run_audit(TimeoutConverter(delay_seconds=2.0), suite, config=config)

    assert report.total_tests == len(suite)
    assert report.timeout_count == len(suite)
    assert report.verified_count == 0
    assert report.verified_conversion_rate is None
    for res in report.results:
        assert res.status == AuditStatus.TIMEOUT
        assert "timed out" in (res.error_message or "").lower()


# ============================================================================
# 4. METRICS & CATEGORY STATISTICS TESTS
# ============================================================================


def test_verified_conversion_rate_calculation():
    """Test VCR formula and edge conditions."""
    assert calculate_verified_conversion_rate(10, 0) == 1.0
    assert calculate_verified_conversion_rate(8, 2) == 0.8
    assert calculate_verified_conversion_rate(0, 5) == 0.0
    assert calculate_verified_conversion_rate(0, 0) is None


def test_category_statistics_aggregation():
    """Verify that category statistics are correctly tabulated per category."""
    suite = generate_test_suite(GeneratorConfig(count=20), seed=108, include_edge_cases=True)
    report = run_audit(BuggyConverter(), suite)

    assert len(report.category_statistics) > 0
    for cat_name, stats in report.category_statistics.items():
        assert stats.total > 0
        assert stats.total == (
            stats.verified
            + stats.not_equivalent
            + stats.invalid_output
            + stats.execution_error
            + stats.timeout
        )


def test_empty_test_suite():
    """Empty test suite produces empty report with zero division safety."""
    report = run_audit(CorrectConverter(), [])
    assert report.total_tests == 0
    assert report.verified_count == 0
    assert report.verified_conversion_rate is None
    assert report.average_execution_time_seconds == 0.0


def test_audit_reproducibility():
    """Identical suite and converter must produce identical reports."""
    suite = generate_test_suite(GeneratorConfig(count=15), seed=555, include_edge_cases=True)
    report1 = run_audit(BuggyConverter(), suite, audit_id="fixed_id")
    report2 = run_audit(BuggyConverter(), suite, audit_id="fixed_id")

    assert report1.verified_count == report2.verified_count
    assert report1.failed_count == report2.failed_count
    assert report1.verified_conversion_rate == report2.verified_conversion_rate

    for r1, r2 in zip(report1.results, report2.results):
        assert r1.status == r2.status
        assert r1.counterexample == r2.counterexample


# ============================================================================
# 5. AUDIT PERFORMANCE BENCHMARKS (100, 500, 1000 TESTS)
# ============================================================================


def test_audit_benchmarks_100_500_1000():
    """Run full audit benchmark on 100, 500, and 1000 tests with CorrectConverter."""
    converter = CorrectConverter()

    # 100 tests
    suite_100 = generate_test_suite(GeneratorConfig(count=100), seed=1001, include_edge_cases=False)
    t0 = time.perf_counter()
    report_100 = run_audit(converter, suite_100)
    t1 = time.perf_counter()
    time_100 = t1 - t0
    assert report_100.verified_count == 100
    print(f"\n[BENCHMARK] 100 tests: {time_100:.3f}s (avg: {time_100/100*1000:.2f}ms/test)")

    # 500 tests
    suite_500 = generate_test_suite(GeneratorConfig(count=500), seed=1002, include_edge_cases=False)
    t0 = time.perf_counter()
    report_500 = run_audit(converter, suite_500)
    t1 = time.perf_counter()
    time_500 = t1 - t0
    assert report_500.verified_count == 500
    print(f"[BENCHMARK] 500 tests: {time_500:.3f}s (avg: {time_500/500*1000:.2f}ms/test)")

    # 1000 tests
    suite_1000 = generate_test_suite(GeneratorConfig(count=1000), seed=1003, include_edge_cases=False)
    t0 = time.perf_counter()
    report_1000 = run_audit(converter, suite_1000)
    t1 = time.perf_counter()
    time_1000 = t1 - t0
    assert report_1000.verified_count == 1000
    print(f"[BENCHMARK] 1000 tests: {time_1000:.3f}s (avg: {time_1000/1000*1000:.2f}ms/test)")

    # Audit performance assertion: 1000 tests audited well under 5 seconds
    assert time_1000 < 5.0

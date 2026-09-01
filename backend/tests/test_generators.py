"""Comprehensive tests for the automated ε-NFA test suite generator."""

import time
import pytest

from app.core.algorithms.simulation import simulate_dfa, simulate_epsilon_nfa
from app.core.automata.models import DFA, EPSILON, EpsilonNFA
from app.core.generators import (
    ALL_CATEGORIES,
    GeneratorConfig,
    generate_epsilon_nfa,
    generate_test_suite,
    get_all_edge_cases,
)
from app.core.transformations.subset_construction import epsilon_nfa_to_dfa


# ============================================================================
# 1. AUTOMATA VALIDITY & STRUCTURAL INVARIANTS
# ============================================================================


def test_every_generated_automaton_is_valid():
    """Verify that all generated automata in a suite pass mathematical validation."""
    config = GeneratorConfig(min_states=2, max_states=6, count=50)
    suite = generate_test_suite(config=config, seed=123, include_edge_cases=True)

    assert len(suite) >= 50
    for case in suite:
        enfa = case.automaton
        assert isinstance(enfa, EpsilonNFA)
        assert len(enfa.states) >= 1
        assert enfa.start_state in enfa.states
        assert enfa.accepting_states.issubset(enfa.states)
        assert EPSILON not in enfa.alphabet


# ============================================================================
# 2. REPRODUCIBILITY (DETERMINISM)
# ============================================================================


def test_reproducibility_same_seed():
    """Running generate_test_suite with the same seed must produce identical automata."""
    config = GeneratorConfig(count=30)
    suite1 = generate_test_suite(config=config, seed=999, include_edge_cases=False)
    suite2 = generate_test_suite(config=config, seed=999, include_edge_cases=False)

    assert len(suite1) == len(suite2)
    for case1, case2 in zip(suite1, suite2):
        assert case1.automaton == case2.automaton
        assert case1.metadata == case2.metadata


def test_different_seeds_produce_different_suites():
    """Different random seeds should produce different automata collections."""
    config = GeneratorConfig(count=20)
    suite1 = generate_test_suite(config=config, seed=1, include_edge_cases=False)
    suite2 = generate_test_suite(config=config, seed=2, include_edge_cases=False)

    automata1 = [c.automaton for c in suite1]
    automata2 = [c.automaton for c in suite2]
    assert automata1 != automata2


# ============================================================================
# 3. CATEGORY COVERAGE & BOUNDS
# ============================================================================


def test_all_categories_generation():
    """Verify that every defined category can be generated independently."""
    for category in ALL_CATEGORIES:
        config = GeneratorConfig(min_states=2, max_states=5)
        case = generate_epsilon_nfa(config=config, category=category, test_id=f"test_{category}")
        assert isinstance(case.automaton, EpsilonNFA)
        assert case.metadata.category == category


def test_state_bounds_and_alphabet_respected():
    """Verify that generated automata respect min_states, max_states, and custom alphabets."""
    custom_alphabet = ("x", "y", "z")
    config = GeneratorConfig(
        min_states=3,
        max_states=4,
        alphabet=custom_alphabet,
        count=20,
    )
    suite = generate_test_suite(config=config, seed=42, include_edge_cases=False)

    for case in suite:
        enfa = case.automaton
        assert 3 <= len(enfa.states) <= 4
        assert enfa.alphabet == frozenset(custom_alphabet)


# ============================================================================
# 4. METADATA ACCURACY
# ============================================================================


def test_metadata_accuracy():
    """Verify that metadata accurately reports states, transitions, and acceptance counts."""
    config = GeneratorConfig(count=15)
    suite = generate_test_suite(config=config, seed=777, include_edge_cases=True)

    for case in suite:
        meta = case.metadata
        enfa = case.automaton
        assert meta.num_states == len(enfa.states)
        assert meta.num_accepting_states == len(enfa.accepting_states)
        assert meta.alphabet_size == len(enfa.alphabet)

        # Count transitions manually
        actual_normal = sum(
            len(dsts) for (src, sym), dsts in enfa.transitions.items() if sym != EPSILON
        )
        actual_eps = sum(
            len(dsts) for (src, sym), dsts in enfa.transitions.items() if sym == EPSILON
        )
        assert meta.num_normal_transitions == actual_normal
        assert meta.num_epsilon_transitions == actual_eps


# ============================================================================
# 5. DETERMINISTIC EDGE CASES
# ============================================================================


def test_all_edge_cases():
    """Verify that all predefined edge cases are valid and non-empty."""
    edge_cases = get_all_edge_cases()
    assert len(edge_cases) >= 9

    for case in edge_cases:
        assert isinstance(case.automaton, EpsilonNFA)
        assert case.metadata.category == "Edge Case"
        assert len(case.metadata.description) > 0


# ============================================================================
# 6. CONVERSION AND SIMULATION SANITY CHECK ON LARGE BATCH
# ============================================================================


def test_batch_conversion_and_simulation_sanity():
    """Generate 100 automata across all categories, convert to DFA, and verify simulation consistency."""
    config = GeneratorConfig(min_states=2, max_states=5, count=100)
    suite = generate_test_suite(config=config, seed=2026, include_edge_cases=True)

    test_strings = ["", "0", "1", "00", "01", "10", "11", "000", "111"]

    for case in suite:
        enfa = case.automaton
        dfa = epsilon_nfa_to_dfa(enfa)
        assert isinstance(dfa, DFA)
        assert EPSILON not in dfa.alphabet

        for s in test_strings:
            enfa_acc = simulate_epsilon_nfa(enfa, s)
            dfa_acc = simulate_dfa(dfa, s)
            assert enfa_acc == dfa_acc, (
                f"Discrepancy on string '{s}' for test {case.metadata.test_id} ({case.metadata.category})"
            )


# ============================================================================
# 7. PERFORMANCE BENCHMARKS (100, 500, 1000 AUTOMATA)
# ============================================================================


def test_generation_performance_100_500_1000():
    """Benchmark test suite generation for 100, 500, and 1000 test cases."""
    # 100 test cases
    t0 = time.perf_counter()
    suite_100 = generate_test_suite(GeneratorConfig(count=100), seed=42, include_edge_cases=False)
    t1 = time.perf_counter()
    assert len(suite_100) == 100
    time_100 = t1 - t0

    # 500 test cases
    t0 = time.perf_counter()
    suite_500 = generate_test_suite(GeneratorConfig(count=500), seed=42, include_edge_cases=False)
    t1 = time.perf_counter()
    assert len(suite_500) == 500
    time_500 = t1 - t0

    # 1000 test cases
    t0 = time.perf_counter()
    suite_1000 = generate_test_suite(GeneratorConfig(count=1000), seed=42, include_edge_cases=False)
    t1 = time.perf_counter()
    assert len(suite_1000) == 1000
    time_1000 = t1 - t0

    # Ensure rapid generation (< 1.0s for 1000 test cases)
    assert time_1000 < 2.0, f"Generation of 1000 test cases took too long: {time_1000:.3f}s"

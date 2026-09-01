"""Tests for ε-NFA -> DFA Subset Construction and exhaustive verification."""

import itertools
import pytest
from app.core.algorithms.simulation import simulate_dfa, simulate_epsilon_nfa
from app.core.automata.models import DFA, EPSILON, EpsilonNFA, NFA
from app.core.transformations.subset_construction import (
    SubsetConstruction,
    epsilon_nfa_to_dfa,
    epsilon_nfa_to_dfa_with_trace,
)


def generate_test_strings(alphabet: frozenset[str], max_len: int = 4) -> list[str]:
    """Generate all strings over alphabet up to max_len (including empty string)."""
    strings = [""]
    for length in range(1, max_len + 1):
        for p in itertools.product(sorted(alphabet), repeat=length):
            strings.append("".join(p))
    return strings


def verify_conversion(enfa: EpsilonNFA, dfa: DFA, max_len: int = 4) -> None:
    """Verify that generated DFA is valid and accepts identical strings to ε-NFA."""
    # 1. Structural properties
    assert isinstance(dfa, DFA)
    assert EPSILON not in dfa.alphabet
    assert dfa.alphabet == enfa.alphabet
    assert dfa.start_state in dfa.states
    assert dfa.accepting_states.issubset(dfa.states)

    # 2. Exhaustive test string simulation equivalence
    for test_str in generate_test_strings(enfa.alphabet, max_len=max_len):
        enfa_acc = simulate_epsilon_nfa(enfa, test_str)
        dfa_acc = simulate_dfa(dfa, test_str)
        assert enfa_acc == dfa_acc, (
            f"Equivalence failure on string '{test_str}': "
            f"ε-NFA accepted={enfa_acc}, DFA accepted={dfa_acc}"
        )


# ============================================================================
# 10 MANDATORY SUBSET CONSTRUCTION TEST SCENARIOS
# ============================================================================


def test_1_no_epsilon_transitions():
    """Scenario 1: Standard NFA with no epsilon transitions."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2"},
        alphabet={"a", "b"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", "a"): {"q0", "q1"},
            ("q0", "b"): {"q0"},
            ("q1", "b"): {"q2"},
        },
    )
    dfa = epsilon_nfa_to_dfa(enfa)
    verify_conversion(enfa, dfa)


def test_2_one_epsilon_transition():
    """Scenario 2: ε-NFA with a single epsilon transition."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", "0"): {"q0"},
            ("q0", "1"): {"q1"},
            ("q1", EPSILON): {"q2"},
            ("q2", "0"): {"q2"},
            ("q2", "1"): {"q2"},
        },
    )
    dfa = epsilon_nfa_to_dfa(enfa)
    verify_conversion(enfa, dfa)


def test_3_epsilon_chains():
    """Scenario 3: ε-NFA with a chain of epsilon transitions q0 -> q1 -> q2 -> q3."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2", "q3"},
        alphabet={"a", "b"},
        start_state="q0",
        accepting_states={"q3"},
        transitions={
            ("q0", EPSILON): {"q1"},
            ("q1", EPSILON): {"q2"},
            ("q2", EPSILON): {"q3"},
            ("q3", "a"): {"q3"},
            ("q3", "b"): {"q0"},
        },
    )
    dfa = epsilon_nfa_to_dfa(enfa)
    verify_conversion(enfa, dfa)


def test_4_epsilon_cycles():
    """Scenario 4: ε-NFA with epsilon cycles q0 <-> q1 and self-loops."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", EPSILON): {"q1"},
            ("q1", EPSILON): {"q0", "q2"},
            ("q2", "1"): {"q0"},
            ("q0", "0"): {"q2"},
        },
    )
    dfa = epsilon_nfa_to_dfa(enfa)
    verify_conversion(enfa, dfa)


def test_5_multiple_epsilon_destinations():
    """Scenario 5: Multiple branching epsilon transitions from single states."""
    enfa = EpsilonNFA(
        states={"start", "branch_a", "branch_b", "accept_a", "accept_b"},
        alphabet={"a", "b"},
        start_state="start",
        accepting_states={"accept_a", "accept_b"},
        transitions={
            ("start", EPSILON): {"branch_a", "branch_b"},
            ("branch_a", "a"): {"accept_a"},
            ("branch_b", "b"): {"accept_b"},
            ("accept_a", "a"): {"accept_a"},
            ("accept_b", "b"): {"accept_b"},
        },
    )
    dfa = epsilon_nfa_to_dfa(enfa)
    verify_conversion(enfa, dfa)


def test_6_multiple_accepting_states():
    """Scenario 6: Multiple accepting states across different branches."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2", "q3", "q4"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q2", "q4"},
        transitions={
            ("q0", "0"): {"q1"},
            ("q0", "1"): {"q3"},
            ("q1", EPSILON): {"q2"},
            ("q3", EPSILON): {"q4"},
            ("q2", "0"): {"q2"},
            ("q4", "1"): {"q4"},
        },
    )
    dfa = epsilon_nfa_to_dfa(enfa)
    verify_conversion(enfa, dfa)


def test_7_empty_language():
    """Scenario 7: Automaton that recognizes the empty language (no accepting states reachable)."""
    enfa = EpsilonNFA(
        states={"q0", "q1"},
        alphabet={"a", "b"},
        start_state="q0",
        accepting_states={"q1"},
        transitions={
            ("q0", "a"): {"q0"},
            ("q0", "b"): {"q0"},
        },
    )
    dfa = epsilon_nfa_to_dfa(enfa)
    verify_conversion(enfa, dfa)
    assert len(dfa.accepting_states) == 0


def test_8_universal_language():
    """Scenario 8: Automaton that accepts all strings Sigma*."""
    enfa = EpsilonNFA(
        states={"q0", "q1"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q0", "q1"},
        transitions={
            ("q0", EPSILON): {"q1"},
            ("q0", "0"): {"q0"},
            ("q0", "1"): {"q1"},
            ("q1", "0"): {"q0"},
            ("q1", "1"): {"q1"},
        },
    )
    dfa = epsilon_nfa_to_dfa(enfa)
    verify_conversion(enfa, dfa)
    # Every reachable state in DFA must be accepting
    assert dfa.accepting_states == dfa.states


def test_9_unreachable_states():
    """Scenario 9: Automaton containing dead/unreachable states."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "unreachable_1", "unreachable_2"},
        alphabet={"a", "b"},
        start_state="q0",
        accepting_states={"q1", "unreachable_2"},
        transitions={
            ("q0", "a"): {"q1"},
            ("unreachable_1", EPSILON): {"unreachable_2"},
            ("unreachable_2", "b"): {"q1"},
        },
    )
    dfa = epsilon_nfa_to_dfa(enfa)
    verify_conversion(enfa, dfa)


def test_10_epsilon_closure_changes_acceptance():
    """Scenario 10: Start state has epsilon transition directly to accepting state."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2"},
        alphabet={"a", "b"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", EPSILON): {"q2"},  # Empty string is accepted!
            ("q0", "a"): {"q1"},
            ("q1", "b"): {"q2"},
        },
    )
    dfa = epsilon_nfa_to_dfa(enfa)
    verify_conversion(enfa, dfa)
    assert simulate_dfa(dfa, "") is True
    assert dfa.start_state in dfa.accepting_states


def test_conversion_trace_details():
    """Test detailed step-by-step conversion trace output."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", EPSILON): {"q1"},
            ("q1", "0"): {"q2"},
        },
    )
    result = epsilon_nfa_to_dfa_with_trace(enfa)
    trace = result.trace

    assert trace.start_closure == frozenset({"q0", "q1"})
    assert len(trace.discovered_subsets) >= 1
    assert len(trace.steps) > 0

    trace_dict = trace.to_dict()
    assert "start_closure" in trace_dict
    assert "discovered_subsets" in trace_dict
    assert "steps" in trace_dict
    assert "accepting_subsets" in trace_dict


def test_nfa_to_dfa_conversion():
    """Direct conversion of pure NFA (no epsilons) to DFA."""
    nfa = NFA(
        states={"q0", "q1"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q1"},
        transitions={
            ("q0", "0"): {"q0", "q1"},
            ("q0", "1"): {"q0"},
        },
    )
    dfa = SubsetConstruction().transform(nfa)
    assert isinstance(dfa, DFA)
    assert dfa.alphabet == frozenset({"0", "1"})

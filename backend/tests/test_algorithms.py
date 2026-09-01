"""Unit tests for epsilon closure, move, and string simulation algorithms."""

import pytest
from app.core.algorithms.closure import epsilon_closure, move
from app.core.algorithms.simulation import (
    simulate_automaton,
    simulate_dfa,
    simulate_epsilon_nfa,
    simulate_nfa,
)
from app.core.automata.models import DFA, EPSILON, NFA, AutomataValidationError, EpsilonNFA


def test_epsilon_closure_single_state_no_eps():
    """State with no epsilon transitions has closure containing only itself."""
    enfa = EpsilonNFA(
        states={"q0", "q1"},
        alphabet={"a"},
        start_state="q0",
        accepting_states={"q1"},
        transitions={("q0", "a"): {"q1"}},
    )
    assert epsilon_closure(enfa, "q0") == frozenset({"q0"})
    assert epsilon_closure(enfa, {"q1"}) == frozenset({"q1"})


def test_epsilon_closure_chain():
    """Epsilon chain q0 --ε--> q1 --ε--> q2."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2"},
        alphabet={"a"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", EPSILON): {"q1"},
            ("q1", EPSILON): {"q2"},
        },
    )
    assert epsilon_closure(enfa, "q0") == frozenset({"q0", "q1", "q2"})
    assert epsilon_closure(enfa, "q1") == frozenset({"q1", "q2"})
    assert epsilon_closure(enfa, "q2") == frozenset({"q2"})


def test_epsilon_closure_cycle():
    """Epsilon cycle q0 --ε--> q1 --ε--> q0."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2"},
        alphabet={"a"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", EPSILON): {"q1"},
            ("q1", EPSILON): {"q0", "q2"},
        },
    )
    assert epsilon_closure(enfa, "q0") == frozenset({"q0", "q1", "q2"})
    assert epsilon_closure(enfa, "q1") == frozenset({"q0", "q1", "q2"})
    assert epsilon_closure(enfa, "q2") == frozenset({"q2"})


def test_epsilon_closure_branching():
    """Multiple epsilon transitions from a single state."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2", "q3", "q4"},
        alphabet={"a"},
        start_state="q0",
        accepting_states={"q4"},
        transitions={
            ("q0", EPSILON): {"q1", "q2"},
            ("q1", EPSILON): {"q3"},
            ("q2", EPSILON): {"q4"},
        },
    )
    assert epsilon_closure(enfa, "q0") == frozenset({"q0", "q1", "q2", "q3", "q4"})
    assert epsilon_closure(enfa, {"q1", "q2"}) == frozenset({"q1", "q2", "q3", "q4"})


def test_epsilon_closure_invalid_state():
    """Computing epsilon closure on non-existent state raises AutomataValidationError."""
    enfa = EpsilonNFA(
        states={"q0", "q1"},
        alphabet={"a"},
        start_state="q0",
        accepting_states={"q1"},
        transitions={},
    )
    with pytest.raises(AutomataValidationError, match="not in automaton"):
        epsilon_closure(enfa, "q_unknown")


def test_move_basic():
    """Test move function for single non-epsilon symbol."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2", "q3"},
        alphabet={"a", "b"},
        start_state="q0",
        accepting_states={"q3"},
        transitions={
            ("q0", "a"): {"q1", "q2"},
            ("q1", "b"): {"q3"},
            ("q2", "a"): {"q3"},
            ("q1", EPSILON): {"q2"},
        },
    )
    # move does NOT include epsilon closure
    assert move(enfa, "q0", "a") == frozenset({"q1", "q2"})
    assert move(enfa, "q0", "b") == frozenset()
    assert move(enfa, {"q1", "q2"}, "a") == frozenset({"q3"})
    assert move(enfa, {"q1", "q2"}, "b") == frozenset({"q3"})


def test_move_invalid_symbol():
    """Move on invalid symbol raises AutomataValidationError."""
    enfa = EpsilonNFA(
        states={"q0", "q1"},
        alphabet={"a"},
        start_state="q0",
        accepting_states={"q1"},
        transitions={},
    )
    with pytest.raises(AutomataValidationError, match="not in automaton alphabet"):
        move(enfa, "q0", "invalid_sym")


def test_simulation_dfa_nfa_enfa():
    """Test string simulations across DFA, NFA, and EpsilonNFA."""
    # Language: strings ending with '1'
    dfa = DFA(
        states={"even", "odd"},
        alphabet={"0", "1"},
        start_state="even",
        accepting_states={"odd"},
        transitions={
            ("even", "0"): "even",
            ("even", "1"): "odd",
            ("odd", "0"): "even",
            ("odd", "1"): "odd",
        },
    )
    assert simulate_dfa(dfa, "1") is True
    assert simulate_dfa(dfa, "01") is True
    assert simulate_dfa(dfa, "0") is False
    assert simulate_dfa(dfa, "10") is False
    assert simulate_automaton(dfa, "101") is True

    # NFA for (0|1)* 1
    nfa = NFA(
        states={"q0", "q1"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q1"},
        transitions={
            ("q0", "0"): {"q0"},
            ("q0", "1"): {"q0", "q1"},
        },
    )
    assert simulate_nfa(nfa, "1") is True
    assert simulate_nfa(nfa, "001") is True
    assert simulate_nfa(nfa, "00") is False

    # ε-NFA for (0* 1*) with ε-transition
    enfa = EpsilonNFA(
        states={"q0", "q1"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q1"},
        transitions={
            ("q0", "0"): {"q0"},
            ("q0", EPSILON): {"q1"},
            ("q1", "1"): {"q1"},
        },
    )
    assert simulate_epsilon_nfa(enfa, "") is True
    assert simulate_epsilon_nfa(enfa, "00") is True
    assert simulate_epsilon_nfa(enfa, "11") is True
    assert simulate_epsilon_nfa(enfa, "0011") is True
    assert simulate_epsilon_nfa(enfa, "10") is False

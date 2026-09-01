"""Comprehensive unit tests for DFA, NFA, and EpsilonNFA core data models."""

import pytest
from app.core.automata.models import (
    DFA,
    EPSILON,
    NFA,
    AutomataValidationError,
    EpsilonNFA,
)
from app.core.automata.serialization import (
    automaton_from_json,
    automaton_to_json,
    deserialize_automaton,
    serialize_automaton,
)


# ============================================================================
# DFA TESTS
# ============================================================================


def test_valid_dfa():
    """Test standard valid DFA instantiation and property inspection."""
    dfa = DFA(
        states={"q0", "q1", "q2"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", "0"): "q1",
            ("q0", "1"): "q0",
            ("q1", "0"): "q2",
            ("q1", "1"): "q0",
            ("q2", "0"): "q2",
            ("q2", "1"): "q2",
        },
    )
    assert dfa.states == frozenset({"q0", "q1", "q2"})
    assert dfa.alphabet == frozenset({"0", "1"})
    assert dfa.start_state == "q0"
    assert dfa.accepting_states == frozenset({"q2"})
    assert dfa.get_transition("q0", "0") == "q1"
    assert dfa.get_transition("q0", "1") == "q0"
    assert dfa.get_transition("q2", "0") == "q2"
    assert dfa.get_transition("q2", "missing") is None


def test_dfa_empty_states():
    """DFA with empty states must raise AutomataValidationError."""
    with pytest.raises(AutomataValidationError, match="States set cannot be empty"):
        DFA(
            states=set(),
            alphabet={"a"},
            start_state="q0",
            accepting_states=set(),
            transitions={},
        )


def test_dfa_invalid_start_state():
    """Start state not in states must raise AutomataValidationError."""
    with pytest.raises(AutomataValidationError, match="Start state 'q_missing' is not in states"):
        DFA(
            states={"q0", "q1"},
            alphabet={"a"},
            start_state="q_missing",
            accepting_states={"q1"},
            transitions={("q0", "a"): "q1"},
        )


def test_dfa_invalid_accepting_state():
    """Accepting states not a subset of states must raise AutomataValidationError."""
    with pytest.raises(AutomataValidationError, match="Accepting states must be a subset of states"):
        DFA(
            states={"q0", "q1"},
            alphabet={"a"},
            start_state="q0",
            accepting_states={"q1", "q_invalid"},
            transitions={("q0", "a"): "q1"},
        )


def test_dfa_invalid_transition_source():
    """Transition source not in states must raise AutomataValidationError."""
    with pytest.raises(AutomataValidationError, match="Transition source state 'q_unknown' not in states"):
        DFA(
            states={"q0", "q1"},
            alphabet={"a"},
            start_state="q0",
            accepting_states={"q1"},
            transitions={("q_unknown", "a"): "q1"},
        )


def test_dfa_invalid_transition_destination():
    """Transition destination not in states must raise AutomataValidationError."""
    with pytest.raises(AutomataValidationError, match="Transition destination state 'q_unknown'"):
        DFA(
            states={"q0", "q1"},
            alphabet={"a"},
            start_state="q0",
            accepting_states={"q1"},
            transitions={("q0", "a"): "q_unknown"},
        )


def test_dfa_invalid_alphabet_symbol():
    """Transition symbol not in alphabet must raise AutomataValidationError."""
    with pytest.raises(AutomataValidationError, match="Transition symbol 'b' for state 'q0' not in alphabet"):
        DFA(
            states={"q0", "q1"},
            alphabet={"a"},
            start_state="q0",
            accepting_states={"q1"},
            transitions={("q0", "b"): "q1"},
        )


def test_dfa_nondeterministic_transition():
    """A DFA must reject multiple transitions for the same (state, symbol)."""
    with pytest.raises(AutomataValidationError, match="Nondeterministic transition detected in DFA"):
        DFA(
            states={"q0", "q1", "q2"},
            alphabet={"a"},
            start_state="q0",
            accepting_states={"q1"},
            transitions=[
                {"from_state": "q0", "symbol": "a", "to_state": "q1"},
                {"from_state": "q0", "symbol": "a", "to_state": "q2"},
            ],
        )


def test_dfa_rejects_epsilon_in_alphabet():
    """Alphabet must not allow epsilon."""
    with pytest.raises(AutomataValidationError, match="Alphabet must not contain epsilon"):
        DFA(
            states={"q0", "q1"},
            alphabet={"a", EPSILON},
            start_state="q0",
            accepting_states={"q1"},
            transitions={("q0", "a"): "q1"},
        )


# ============================================================================
# NFA TESTS
# ============================================================================


def test_valid_nfa_multiple_destinations():
    """Test valid NFA with multiple destination states for single symbol."""
    nfa = NFA(
        states={"q0", "q1", "q2"},
        alphabet={"a", "b"},
        start_state="q0",
        accepting_states={"q1", "q2"},
        transitions={
            ("q0", "a"): {"q0", "q1"},
            ("q0", "b"): {"q0"},
            ("q1", "b"): "q2",
        },
    )
    assert nfa.get_transitions("q0", "a") == frozenset({"q0", "q1"})
    assert nfa.get_transitions("q0", "b") == frozenset({"q0"})
    assert nfa.get_transitions("q1", "b") == frozenset({"q2"})
    assert nfa.get_transitions("q1", "a") == frozenset()  # Missing transition returns empty set
    assert nfa.get_transitions("q2", "a") == frozenset()
    assert nfa.accepting_states == frozenset({"q1", "q2"})


def test_nfa_invalid_destination():
    """NFA with destination outside states must raise AutomataValidationError."""
    with pytest.raises(AutomataValidationError, match="Transition destination states .* not in states"):
        NFA(
            states={"q0", "q1"},
            alphabet={"a"},
            start_state="q0",
            accepting_states={"q1"},
            transitions={("q0", "a"): {"q1", "q_ghost"}},
        )


# ============================================================================
# EPSILON-NFA TESTS
# ============================================================================


def test_valid_epsilon_nfa():
    """Test valid ε-NFA with epsilon and symbol transitions."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2", "q3"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q3"},
        transitions={
            ("q0", EPSILON): {"q1", "q2"},
            ("q1", "0"): {"q3"},
            ("q2", "1"): {"q3"},
        },
    )
    assert enfa.get_epsilon_transitions("q0") == frozenset({"q1", "q2"})
    assert enfa.get_transitions("q1", "0") == frozenset({"q3"})
    assert enfa.get_epsilon_transitions("q1") == frozenset()


def test_epsilon_nfa_cycles_and_chains():
    """Test ε-NFA with epsilon cycles and epsilon-only paths."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2", "q3"},
        alphabet={"a"},
        start_state="q0",
        accepting_states={"q3"},
        transitions={
            # Epsilon cycle between q0 and q1
            ("q0", "eps"): {"q1"},
            ("q1", "eps"): {"q0", "q2"},
            # Epsilon chain to q3
            ("q2", "eps"): {"q3"},
            # Normal symbol transition
            ("q3", "a"): {"q3"},
        },
    )
    assert enfa.get_epsilon_transitions("q0") == frozenset({"q1"})
    assert enfa.get_epsilon_transitions("q1") == frozenset({"q0", "q2"})
    assert enfa.get_epsilon_transitions("q2") == frozenset({"q3"})
    assert enfa.get_transitions("q3", "a") == frozenset({"q3"})


def test_epsilon_nfa_invalid_symbol():
    """EpsilonNFA rejecting symbol not in alphabet and not epsilon."""
    with pytest.raises(AutomataValidationError, match="neither in alphabet .* nor epsilon"):
        EpsilonNFA(
            states={"q0", "q1"},
            alphabet={"a"},
            start_state="q0",
            accepting_states={"q1"},
            transitions={("q0", "b"): {"q1"}},
        )


# ============================================================================
# SERIALIZATION & ROUND-TRIP TESTS
# ============================================================================


def test_dfa_json_roundtrip():
    """DFA -> JSON -> DFA preserves complete automaton and structural equality."""
    original = DFA(
        states={"q0", "q1", "q2"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", "0"): "q1",
            ("q0", "1"): "q0",
            ("q1", "0"): "q2",
            ("q1", "1"): "q0",
            ("q2", "0"): "q2",
            ("q2", "1"): "q2",
        },
    )
    json_str = original.to_json()
    reconstructed = DFA.from_json(json_str)

    assert isinstance(reconstructed, DFA)
    assert reconstructed == original
    assert reconstructed.states == original.states
    assert reconstructed.alphabet == original.alphabet
    assert reconstructed.start_state == original.start_state
    assert reconstructed.accepting_states == original.accepting_states
    assert reconstructed.transitions == original.transitions


def test_nfa_json_roundtrip():
    """NFA -> JSON -> NFA preserves complete automaton and structural equality."""
    original = NFA(
        states={"q0", "q1", "q2"},
        alphabet={"a", "b"},
        start_state="q0",
        accepting_states={"q1", "q2"},
        transitions={
            ("q0", "a"): {"q0", "q1"},
            ("q0", "b"): {"q0"},
            ("q1", "b"): {"q2"},
        },
    )
    json_str = automaton_to_json(original)
    reconstructed = automaton_from_json(json_str)

    assert isinstance(reconstructed, NFA)
    assert reconstructed == original
    assert reconstructed.transitions == original.transitions


def test_epsilon_nfa_json_roundtrip():
    """EpsilonNFA -> JSON -> EpsilonNFA preserves complete automaton and structural equality."""
    original = EpsilonNFA(
        states={"q0", "q1", "q2", "q3"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q3"},
        transitions={
            ("q0", EPSILON): {"q1", "q2"},
            ("q1", "0"): {"q3"},
            ("q2", "1"): {"q3"},
            ("q3", EPSILON): {"q0"},
        },
    )
    json_str = original.to_json()
    reconstructed = EpsilonNFA.from_json(json_str)

    assert isinstance(reconstructed, EpsilonNFA)
    assert reconstructed == original
    assert reconstructed.transitions == original.transitions


# ============================================================================
# STRUCTURAL EQUALITY TESTS
# ============================================================================


def test_structural_equality():
    """Structural equality checks exact component matching."""
    dfa1 = DFA(
        states={"q0", "q1"},
        alphabet={"a"},
        start_state="q0",
        accepting_states={"q1"},
        transitions={("q0", "a"): "q1"},
    )
    dfa2 = DFA(
        states=["q1", "q0"],  # Different order in set/list
        alphabet=["a"],
        start_state="q0",
        accepting_states=["q1"],
        transitions=[{"from_state": "q0", "symbol": "a", "to_state": "q1"}],
    )
    dfa3 = DFA(
        states={"q0", "q1"},
        alphabet={"a"},
        start_state="q0",
        accepting_states={"q0"},  # Different accepting state
        transitions={("q0", "a"): "q1"},
    )

    assert dfa1 == dfa2
    assert dfa1 != dfa3
    assert dfa1 != "not an automaton"

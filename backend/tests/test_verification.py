"""Formal verification engine test suite."""

import random
import pytest

from app.core.algorithms.simulation import simulate_dfa, simulate_epsilon_nfa
from app.core.automata.models import DFA, EPSILON, EpsilonNFA
from app.core.transformations.subset_construction import epsilon_nfa_to_dfa
from app.core.verification.equivalence import (
    verify_dfa_equivalence,
    verify_epsilon_nfa_against_dfa,
)


# ============================================================================
# CASE 1: DFA compared with itself
# ============================================================================


def test_case_1_dfa_compared_with_itself():
    """A DFA must always be formally equivalent to itself."""
    dfa = DFA(
        states={"q0", "q1"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q1"},
        transitions={
            ("q0", "0"): "q0",
            ("q0", "1"): "q1",
            ("q1", "0"): "q0",
            ("q1", "1"): "q1",
        },
    )
    result = verify_dfa_equivalence(dfa, dfa)
    assert result.equivalent is True
    assert result.counterexample is None
    assert result.states_explored >= 1


# ============================================================================
# CASE 2: Structurally different DFAs recognizing the same language
# ============================================================================


def test_case_2_structurally_different_same_language():
    """Two structurally different DFAs accepting strings with even number of 'a's."""
    # DFA 1: 2 states (minimal)
    dfa1 = DFA(
        states={"even", "odd"},
        alphabet={"a", "b"},
        start_state="even",
        accepting_states={"even"},
        transitions={
            ("even", "a"): "odd",
            ("even", "b"): "even",
            ("odd", "a"): "even",
            ("odd", "b"): "odd",
        },
    )

    # DFA 2: 4 states with redundant equivalent paths
    dfa2 = DFA(
        states={"s0", "s1", "s2", "s3"},
        alphabet={"a", "b"},
        start_state="s0",
        accepting_states={"s0", "s2"},
        transitions={
            ("s0", "a"): "s1",
            ("s0", "b"): "s2",
            ("s1", "a"): "s0",
            ("s1", "b"): "s3",
            ("s2", "a"): "s3",
            ("s2", "b"): "s0",
            ("s3", "a"): "s2",
            ("s3", "b"): "s1",
        },
    )

    result = verify_dfa_equivalence(dfa1, dfa2)
    assert result.equivalent is True
    assert result.counterexample is None


# ============================================================================
# CASE 3: Two DFAs recognizing different languages
# ============================================================================


def test_case_3_different_languages_counterexample():
    """DFAs for different languages must yield equivalent=False and a valid counterexample."""
    # DFA A: Strings ending with '1'
    dfa_a = DFA(
        states={"q0", "q1"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q1"},
        transitions={
            ("q0", "0"): "q0",
            ("q0", "1"): "q1",
            ("q1", "0"): "q0",
            ("q1", "1"): "q1",
        },
    )

    # DFA B: Strings containing at least one '1'
    dfa_b = DFA(
        states={"p0", "p1"},
        alphabet={"0", "1"},
        start_state="p0",
        accepting_states={"p1"},
        transitions={
            ("p0", "0"): "p0",
            ("p0", "1"): "p1",
            ("p1", "0"): "p1",
            ("p1", "1"): "p1",
        },
    )

    result = verify_dfa_equivalence(dfa_a, dfa_b, include_trace=True)
    assert result.equivalent is False
    assert result.counterexample is not None
    assert result.trace is not None

    # Verify counterexample distinguishes them: "10" is accepted by B but rejected by A
    ce = result.counterexample
    acc_a = simulate_dfa(dfa_a, ce)
    acc_b = simulate_dfa(dfa_b, ce)
    assert acc_a != acc_b
    assert acc_a == result.automaton_a_accepts
    assert acc_b == result.automaton_b_accepts


# ============================================================================
# CASE 4: Different state names but same language
# ============================================================================


def test_case_4_different_state_names_same_language():
    """Verification must never rely on state names."""
    dfa1 = DFA(
        states={"ALPHA", "BETA"},
        alphabet={"0", "1"},
        start_state="ALPHA",
        accepting_states={"BETA"},
        transitions={
            ("ALPHA", "0"): "ALPHA",
            ("ALPHA", "1"): "BETA",
            ("BETA", "0"): "ALPHA",
            ("BETA", "1"): "BETA",
        },
    )

    dfa2 = DFA(
        states={"state_999", "state_1000"},
        alphabet={"0", "1"},
        start_state="state_999",
        accepting_states={"state_1000"},
        transitions={
            ("state_999", "0"): "state_999",
            ("state_999", "1"): "state_1000",
            ("state_1000", "0"): "state_999",
            ("state_1000", "1"): "state_1000",
        },
    )

    result = verify_dfa_equivalence(dfa1, dfa2)
    assert result.equivalent is True
    assert result.counterexample is None


# ============================================================================
# CASE 5: Different numbers of states but same language
# ============================================================================


def test_case_5_different_number_of_states():
    """Verifier must correctly prove equivalence regardless of state counts."""
    # 1-state DFA: (a|b)*
    dfa1 = DFA(
        states={"q0"},
        alphabet={"a", "b"},
        start_state="q0",
        accepting_states={"q0"},
        transitions={
            ("q0", "a"): "q0",
            ("q0", "b"): "q0",
        },
    )

    # 3-state redundant DFA: (a|b)*
    dfa2 = DFA(
        states={"s0", "s1", "s2"},
        alphabet={"a", "b"},
        start_state="s0",
        accepting_states={"s0", "s1", "s2"},
        transitions={
            ("s0", "a"): "s1",
            ("s0", "b"): "s2",
            ("s1", "a"): "s2",
            ("s1", "b"): "s0",
            ("s2", "a"): "s0",
            ("s2", "b"): "s1",
        },
    )

    result = verify_dfa_equivalence(dfa1, dfa2)
    assert result.equivalent is True


# ============================================================================
# CASE 6: Empty language vs non-empty language
# ============================================================================


def test_case_6_empty_language_vs_non_empty():
    """Empty language vs non-empty language."""
    empty_dfa = DFA(
        states={"q0"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states=set(),
        transitions={("q0", "0"): "q0", ("q0", "1"): "q0"},
    )

    non_empty_dfa = DFA(
        states={"p0", "p1"},
        alphabet={"0", "1"},
        start_state="p0",
        accepting_states={"p1"},
        transitions={
            ("p0", "0"): "p0",
            ("p0", "1"): "p1",
            ("p1", "0"): "p1",
            ("p1", "1"): "p1",
        },
    )

    result = verify_dfa_equivalence(empty_dfa, non_empty_dfa)
    assert result.equivalent is False
    assert result.counterexample is not None
    assert simulate_dfa(empty_dfa, result.counterexample) is False
    assert simulate_dfa(non_empty_dfa, result.counterexample) is True


# ============================================================================
# CASE 7: Empty string is the shortest counterexample
# ============================================================================


def test_case_7_empty_string_counterexample():
    """When one DFA accepts empty string and the other does not, counterexample must be ''."""
    # Accepts epsilon
    dfa_accepts_eps = DFA(
        states={"q0"},
        alphabet={"a"},
        start_state="q0",
        accepting_states={"q0"},
        transitions={("q0", "a"): "q0"},
    )

    # Rejects epsilon (accepts a+)
    dfa_rejects_eps = DFA(
        states={"p0", "p1"},
        alphabet={"a"},
        start_state="p0",
        accepting_states={"p1"},
        transitions={("p0", "a"): "p1", ("p1", "a"): "p1"},
    )

    result = verify_dfa_equivalence(dfa_accepts_eps, dfa_rejects_eps)
    assert result.equivalent is False
    assert result.counterexample == ""
    assert result.automaton_a_accepts is True
    assert result.automaton_b_accepts is False


# ============================================================================
# CASE 8: Shortest counterexample is a longer string (BFS guarantee)
# ============================================================================


def test_case_8_shortest_distinguishing_string_bfs():
    """DFA A accepts all strings except '0101', DFA B accepts all strings."""
    # DFA B: accepts (0|1)*
    dfa_b = DFA(
        states={"u0"},
        alphabet={"0", "1"},
        start_state="u0",
        accepting_states={"u0"},
        transitions={("u0", "0"): "u0", ("u0", "1"): "u0"},
    )

    # DFA A: rejects exactly prefix '0101'
    dfa_a = DFA(
        states={"q0", "q1", "q2", "q3", "reject", "sink"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q0", "q1", "q2", "q3", "sink"},
        transitions={
            ("q0", "0"): "q1",
            ("q0", "1"): "sink",
            ("q1", "0"): "sink",
            ("q1", "1"): "q2",
            ("q2", "0"): "q3",
            ("q2", "1"): "sink",
            ("q3", "0"): "sink",
            ("q3", "1"): "reject",
            ("reject", "0"): "reject",
            ("reject", "1"): "reject",
            ("sink", "0"): "sink",
            ("sink", "1"): "sink",
        },
    )

    result = verify_dfa_equivalence(dfa_a, dfa_b)
    assert result.equivalent is False
    assert result.counterexample == "0101"
    assert simulate_dfa(dfa_a, "0101") is False
    assert simulate_dfa(dfa_b, "0101") is True


# ============================================================================
# CASE 9: Equivalent ε-NFA and correct DFA
# ============================================================================


def test_case_9_enfa_vs_correct_dfa():
    """ε-NFA verified against a correct candidate DFA."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", "0"): {"q0"},
            ("q0", "1"): {"q0", "q1"},
            ("q1", EPSILON): {"q2"},
            ("q2", "1"): {"q2"},
        },
    )

    # Reference DFA generated
    correct_dfa = epsilon_nfa_to_dfa(enfa)

    result = verify_epsilon_nfa_against_dfa(enfa, correct_dfa)
    assert result.equivalent is True
    assert result.counterexample is None


# ============================================================================
# CASE 10: ε-NFA vs deliberately incorrect DFA
# ============================================================================


def test_case_10_enfa_vs_incorrect_dfa():
    """ε-NFA verified against a flawed candidate DFA."""
    enfa = EpsilonNFA(
        states={"q0", "q1"},
        alphabet={"a", "b"},
        start_state="q0",
        accepting_states={"q1"},
        transitions={
            ("q0", "a"): {"q1"},
            ("q1", EPSILON): {"q0"},
        },
    )

    # Flawed DFA accepting empty set
    incorrect_dfa = DFA(
        states={"s0"},
        alphabet={"a", "b"},
        start_state="s0",
        accepting_states=set(),
        transitions={("s0", "a"): "s0", ("s0", "b"): "s0"},
    )

    result = verify_epsilon_nfa_against_dfa(enfa, incorrect_dfa)
    assert result.equivalent is False
    assert result.counterexample is not None

    ce = result.counterexample
    assert simulate_epsilon_nfa(enfa, ce) != simulate_dfa(incorrect_dfa, ce)


# ============================================================================
# CASE 11: Invariant validation for all counterexamples
# ============================================================================


def test_case_11_counterexample_invariant():
    """Every generated counterexample must strictly distinguish both automata."""
    dfa1 = DFA(
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

    # Mutated version
    dfa2 = DFA(
        states={"q0", "q1", "q2"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q1"},  # Changed accepting state
        transitions=dfa1.transitions,
    )

    result = verify_dfa_equivalence(dfa1, dfa2)
    assert result.equivalent is False
    assert result.counterexample is not None

    # Invariant: simulate(A, ce) != simulate(B, ce)
    res_a = simulate_dfa(dfa1, result.counterexample)
    res_b = simulate_dfa(dfa2, result.counterexample)
    assert res_a != res_b


# ============================================================================
# CASE 12: Randomized verification and mutation suite
# ============================================================================


def test_case_12_randomized_equivalence_and_mutation():
    """Property testing: generate random automata, test isomorphic equivalence and mutations."""
    rng = random.Random(42)

    for i in range(15):
        num_states = rng.randint(2, 5)
        states = {f"q{s}" for s in range(num_states)}
        alphabet = {"0", "1"}
        start_state = "q0"
        num_acc = rng.randint(1, num_states)
        accepting_states = set(rng.sample(sorted(states), num_acc))

        transitions: dict[tuple[str, str], set[str]] = {}
        for s in states:
            for a in ["0", "1", EPSILON]:
                if rng.random() < 0.4:
                    dest = rng.choice(sorted(states))
                    transitions.setdefault((s, a), set()).add(dest)

        enfa = EpsilonNFA(
            states=states,
            alphabet=alphabet,
            start_state=start_state,
            accepting_states=accepting_states,
            transitions=transitions,
        )

        ref_dfa = epsilon_nfa_to_dfa(enfa)

        # 1. Test against itself -> Must be equivalent
        eq_res = verify_epsilon_nfa_against_dfa(enfa, ref_dfa)
        assert eq_res.equivalent is True, f"Self-equivalence failed on iteration {i}"

        # 2. Test renamed isomorphic states -> Must be equivalent
        name_map = {s: f"state_iso_{idx}" for idx, s in enumerate(sorted(ref_dfa.states))}
        iso_dfa = DFA(
            states={name_map[s] for s in ref_dfa.states},
            alphabet=ref_dfa.alphabet,
            start_state=name_map[ref_dfa.start_state],
            accepting_states={name_map[s] for s in ref_dfa.accepting_states},
            transitions={
                (name_map[src], sym): name_map[dst]
                for (src, sym), dst in ref_dfa.transitions.items()
            },
        )
        iso_res = verify_dfa_equivalence(ref_dfa, iso_dfa)
        assert iso_res.equivalent is True, f"Isomorphic equivalence failed on iteration {i}"

        # 3. Deliberately mutate accepting states if possible -> Must be not equivalent
        if ref_dfa.states - ref_dfa.accepting_states:
            new_acc = set(ref_dfa.accepting_states)
            to_toggle = rng.choice(sorted(ref_dfa.states))
            if to_toggle in new_acc:
                new_acc.remove(to_toggle)
            else:
                new_acc.add(to_toggle)

            mutated_dfa = DFA(
                states=ref_dfa.states,
                alphabet=ref_dfa.alphabet,
                start_state=ref_dfa.start_state,
                accepting_states=new_acc,
                transitions=ref_dfa.transitions,
            )
            mut_res = verify_dfa_equivalence(ref_dfa, mutated_dfa)
            assert mut_res.equivalent is False
            assert mut_res.counterexample is not None
            # Verify counterexample invariant
            assert simulate_dfa(ref_dfa, mut_res.counterexample) != simulate_dfa(mutated_dfa, mut_res.counterexample)


def test_alphabet_mismatch():
    """Verify alphabet mismatch is caught and clearly reported."""
    dfa_a = DFA(
        states={"q0"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q0"},
        transitions={("q0", "0"): "q0", ("q0", "1"): "q0"},
    )
    dfa_b = DFA(
        states={"p0"},
        alphabet={"a", "b"},
        start_state="p0",
        accepting_states={"p0"},
        transitions={("p0", "a"): "p0", ("p0", "b"): "p0"},
    )

    result = verify_dfa_equivalence(dfa_a, dfa_b)
    assert result.equivalent is False
    assert result.counterexample is None
    assert result.error is not None
    assert "Alphabet mismatch" in result.error

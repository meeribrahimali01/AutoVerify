"""Deterministic boundary and edge-case automata suite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.core.automata.models import EPSILON, EpsilonNFA


@dataclass(frozen=True)
class TestCaseMetadata:
    """Metadata describing a generated test automaton."""

    test_id: str
    category: str
    seed: int | None
    num_states: int
    alphabet_size: int
    num_normal_transitions: int
    num_epsilon_transitions: int
    num_accepting_states: int
    description: str = ""

    def to_dict(self) -> dict:
        """Convert metadata to dictionary."""
        return {
            "test_id": self.test_id,
            "category": self.category,
            "seed": self.seed,
            "num_states": self.num_states,
            "alphabet_size": self.alphabet_size,
            "num_normal_transitions": self.num_normal_transitions,
            "num_epsilon_transitions": self.num_epsilon_transitions,
            "num_accepting_states": self.num_accepting_states,
            "description": self.description,
        }


@dataclass(frozen=True)
class GeneratedTestCase:
    """An automaton coupled with descriptive metadata."""

    automaton: EpsilonNFA
    metadata: TestCaseMetadata


def compute_metadata(
    automaton: EpsilonNFA,
    test_id: str,
    category: str,
    seed: int | None = None,
    description: str = "",
) -> TestCaseMetadata:
    """Compute accurate metadata from an EpsilonNFA instance."""
    num_normal = 0
    num_eps = 0
    for (src, sym), dsts in automaton.transitions.items():
        if sym == EPSILON:
            num_eps += len(dsts)
        else:
            num_normal += len(dsts)

    return TestCaseMetadata(
        test_id=test_id,
        category=category,
        seed=seed,
        num_states=len(automaton.states),
        alphabet_size=len(automaton.alphabet),
        num_normal_transitions=num_normal,
        num_epsilon_transitions=num_eps,
        num_accepting_states=len(automaton.accepting_states),
        description=description,
    )


# ============================================================================
# DETERMINISTIC BOUNDARY AND EDGE CASES
# ============================================================================


def edge_case_empty_language() -> GeneratedTestCase:
    """Automaton with no accepting states (L = ∅)."""
    enfa = EpsilonNFA(
        states={"q0", "q1"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states=set(),
        transitions={
            ("q0", "0"): {"q1"},
            ("q1", "1"): {"q0"},
        },
    )
    meta = compute_metadata(enfa, "edge_empty_lang", "Edge Case", description="Empty language (no accepting states)")
    return GeneratedTestCase(enfa, meta)


def edge_case_universal_language() -> GeneratedTestCase:
    """Automaton accepting all strings (L = Σ*)."""
    enfa = EpsilonNFA(
        states={"q0"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q0"},
        transitions={
            ("q0", "0"): {"q0"},
            ("q0", "1"): {"q0"},
        },
    )
    meta = compute_metadata(enfa, "edge_universal_lang", "Edge Case", description="Universal language (accepts all Σ*)")
    return GeneratedTestCase(enfa, meta)


def edge_case_single_state_rejecting() -> GeneratedTestCase:
    """Single state with no transitions and no acceptance (L = ∅)."""
    enfa = EpsilonNFA(
        states={"q0"},
        alphabet={"a"},
        start_state="q0",
        accepting_states=set(),
        transitions={},
    )
    meta = compute_metadata(enfa, "edge_single_reject", "Edge Case", description="Single isolated state rejecting")
    return GeneratedTestCase(enfa, meta)


def edge_case_single_state_accepting() -> GeneratedTestCase:
    """Single state with no transitions accepting only empty string (L = {ε})."""
    enfa = EpsilonNFA(
        states={"q0"},
        alphabet={"a"},
        start_state="q0",
        accepting_states={"q0"},
        transitions={},
    )
    meta = compute_metadata(enfa, "edge_single_accept", "Edge Case", description="Single state accepting only epsilon")
    return GeneratedTestCase(enfa, meta)


def edge_case_epsilon_only_acceptance() -> GeneratedTestCase:
    """Acceptance reachable strictly through epsilon chain."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", EPSILON): {"q1"},
            ("q1", EPSILON): {"q2"},
            ("q2", "0"): {"q0"},
        },
    )
    meta = compute_metadata(enfa, "edge_eps_only_acc", "Edge Case", description="Epsilon-only path to accepting state")
    return GeneratedTestCase(enfa, meta)


def edge_case_epsilon_cycle() -> GeneratedTestCase:
    """Epsilon cycle without infinite loop."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2"},
        alphabet={"a", "b"},
        start_state="q0",
        accepting_states={"q2"},
        transitions={
            ("q0", EPSILON): {"q1"},
            ("q1", EPSILON): {"q0", "q2"},
            ("q2", "a"): {"q2"},
        },
    )
    meta = compute_metadata(enfa, "edge_eps_cycle", "Edge Case", description="Epsilon cycle between q0 and q1")
    return GeneratedTestCase(enfa, meta)


def edge_case_unreachable_states() -> GeneratedTestCase:
    """Automaton containing disconnected / unreachable components."""
    enfa = EpsilonNFA(
        states={"start", "active", "dead_island_1", "dead_island_2"},
        alphabet={"0", "1"},
        start_state="start",
        accepting_states={"active", "dead_island_2"},
        transitions={
            ("start", "0"): {"active"},
            ("dead_island_1", EPSILON): {"dead_island_2"},
            ("dead_island_2", "1"): {"dead_island_1"},
        },
    )
    meta = compute_metadata(enfa, "edge_unreachable", "Edge Case", description="Unreachable disconnected states")
    return GeneratedTestCase(enfa, meta)


def edge_case_dead_states() -> GeneratedTestCase:
    """Automaton with reachable trap state that can never reach accepting."""
    enfa = EpsilonNFA(
        states={"q0", "accept", "trap"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"accept"},
        transitions={
            ("q0", "0"): {"accept"},
            ("q0", "1"): {"trap"},
            ("trap", "0"): {"trap"},
            ("trap", "1"): {"trap"},
        },
    )
    meta = compute_metadata(enfa, "edge_dead_state", "Edge Case", description="Reachable trap/dead state")
    return GeneratedTestCase(enfa, meta)


def edge_case_dense_epsilon_clique() -> GeneratedTestCase:
    """Dense all-to-all epsilon clique."""
    enfa = EpsilonNFA(
        states={"q0", "q1", "q2", "q3"},
        alphabet={"0", "1"},
        start_state="q0",
        accepting_states={"q3"},
        transitions={
            ("q0", EPSILON): {"q1", "q2", "q3"},
            ("q1", EPSILON): {"q0", "q2", "q3"},
            ("q2", EPSILON): {"q0", "q1", "q3"},
            ("q3", EPSILON): {"q0", "q1", "q2"},
            ("q0", "0"): {"q1"},
            ("q3", "1"): {"q0"},
        },
    )
    meta = compute_metadata(enfa, "edge_dense_eps_clique", "Edge Case", description="All-to-all epsilon clique")
    return GeneratedTestCase(enfa, meta)


def get_all_edge_cases() -> List[GeneratedTestCase]:
    """Retrieve all deterministic edge cases."""
    return [
        edge_case_empty_language(),
        edge_case_universal_language(),
        edge_case_single_state_rejecting(),
        edge_case_single_state_accepting(),
        edge_case_epsilon_only_acceptance(),
        edge_case_epsilon_cycle(),
        edge_case_unreachable_states(),
        edge_case_dead_states(),
        edge_case_dense_epsilon_clique(),
    ]

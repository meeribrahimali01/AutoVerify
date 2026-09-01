"""Subset Construction algorithm (ε-NFA -> DFA).

This module implements the standard subset construction with epsilon-closure to convert
any ε-NFA (or NFA) into an equivalent deterministic finite automaton (DFA).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Sequence, Set

from app.core.algorithms.closure import epsilon_closure, move
from app.core.automata.models import DFA, EpsilonNFA, NFA
from app.core.transformations.base import BaseTransformation


def default_state_namer(subset: frozenset[str]) -> str:
    """Generate a clean, sorted canonical name for a subset of states."""
    if not subset:
        return "∅"
    return "{" + ",".join(sorted(subset)) + "}"


@dataclass
class SubsetStepTrace:
    """Detailed step record during subset construction."""

    source_subset: frozenset[str]
    source_name: str
    symbol: str
    move_result: frozenset[str]
    closure_result: frozenset[str]
    target_name: str
    is_new_subset: bool


@dataclass
class SubsetConstructionTrace:
    """Full execution trace of the subset construction algorithm."""

    start_closure: frozenset[str]
    start_state_name: str
    discovered_subsets: list[frozenset[str]]
    steps: list[SubsetStepTrace]
    accepting_subsets: list[frozenset[str]]
    state_names: dict[frozenset[str], str]

    def to_dict(self) -> dict[str, Any]:
        """Convert trace to a JSON-serializable dictionary for API/UI visualization."""
        return {
            "start_closure": sorted(self.start_closure),
            "start_state_name": self.start_state_name,
            "discovered_subsets": [
                {"name": self.state_names[s], "states": sorted(s)}
                for s in self.discovered_subsets
            ],
            "steps": [
                {
                    "source_name": step.source_name,
                    "source_subset": sorted(step.source_subset),
                    "symbol": step.symbol,
                    "move_result": sorted(step.move_result),
                    "closure_result": sorted(step.closure_result),
                    "target_name": step.target_name,
                    "is_new_subset": step.is_new_subset,
                }
                for step in self.steps
            ],
            "accepting_subsets": [
                {"name": self.state_names[s], "states": sorted(s)}
                for s in self.accepting_subsets
            ],
        }


@dataclass
class SubsetConstructionResult:
    """Result containing the converted DFA and optional step trace."""

    dfa: DFA
    trace: SubsetConstructionTrace
    subset_map: dict[frozenset[str], str]


class SubsetConstruction(BaseTransformation[EpsilonNFA | NFA, DFA]):
    """Subset Construction transformation engine."""

    def __init__(
        self,
        state_namer: Callable[[frozenset[str]], str] | None = None,
        include_dead_state: bool = False,
    ):
        """Initialize Subset Construction.

        Args:
            state_namer: Custom function to assign string names to state subsets.
            include_dead_state: If True, include the empty set (∅ / dead state)
                                even if transitions are partial. By default False,
                                meaning transitions to empty set are omitted unless reached.
        """
        self.state_namer = state_namer or default_state_namer
        self.include_dead_state = include_dead_state

    def transform(self, automaton: EpsilonNFA | NFA) -> DFA:
        """Convert an ε-NFA or NFA into an equivalent DFA."""
        return self.transform_with_trace(automaton).dfa

    def transform_with_trace(self, automaton: EpsilonNFA | NFA) -> SubsetConstructionResult:
        """Convert an ε-NFA into a DFA and capture the complete step-by-step trace."""
        # Step 1: Compute epsilon-closure of the start state
        if isinstance(automaton, EpsilonNFA):
            start_subset = epsilon_closure(automaton, {automaton.start_state})
            enfa = automaton
        else:
            # Wrap NFA as EpsilonNFA seamlessly if needed
            enfa = EpsilonNFA(
                states=automaton.states,
                alphabet=automaton.alphabet,
                start_state=automaton.start_state,
                accepting_states=automaton.accepting_states,
                transitions=automaton.to_dict()["transitions"],
            )
            start_subset = frozenset({automaton.start_state})

        # State naming and discovery tracker
        state_names: dict[frozenset[str], str] = {}
        start_name = self.state_namer(start_subset)
        state_names[start_subset] = start_name

        discovered_subsets: list[frozenset[str]] = [start_subset]
        queue: deque[frozenset[str]] = deque([start_subset])
        seen_subsets: set[frozenset[str]] = {start_subset}

        dfa_transitions: dict[tuple[str, str], str] = {}
        step_traces: list[SubsetStepTrace] = []

        # Sort alphabet to ensure deterministic iteration order
        sorted_alphabet = sorted(automaton.alphabet)

        # Step 2: BFS over discovered state subsets
        while queue:
            current_subset = queue.popleft()
            current_name = state_names[current_subset]

            for symbol in sorted_alphabet:
                # a. Compute move(current_subset, symbol)
                move_res = move(enfa, current_subset, symbol)

                # b. Compute epsilon-closure of move result
                if move_res:
                    closure_res = epsilon_closure(enfa, move_res)
                else:
                    closure_res = frozenset()

                # Determine if target subset is new
                is_new = False
                if closure_res or self.include_dead_state:
                    if closure_res not in seen_subsets:
                        is_new = True
                        seen_subsets.add(closure_res)
                        target_name = self.state_namer(closure_res)
                        state_names[closure_res] = target_name
                        discovered_subsets.append(closure_res)
                        queue.append(closure_res)
                    else:
                        target_name = state_names[closure_res]

                    dfa_transitions[(current_name, symbol)] = target_name

                    step_traces.append(
                        SubsetStepTrace(
                            source_subset=current_subset,
                            source_name=current_name,
                            symbol=symbol,
                            move_result=move_res,
                            closure_result=closure_res,
                            target_name=target_name,
                            is_new_subset=is_new,
                        )
                    )
                else:
                    # Target is empty and dead state not retained
                    step_traces.append(
                        SubsetStepTrace(
                            source_subset=current_subset,
                            source_name=current_name,
                            symbol=symbol,
                            move_result=move_res,
                            closure_result=closure_res,
                            target_name=self.state_namer(frozenset()),
                            is_new_subset=False,
                        )
                    )

        # Step 3: Identify accepting states in DFA
        # A DFA subset is accepting iff it contains at least one accepting state of original enfa
        accepting_subsets = [
            subset
            for subset in discovered_subsets
            if bool(subset & automaton.accepting_states)
        ]
        dfa_accepting_names = {state_names[s] for s in accepting_subsets}
        dfa_all_states = {state_names[s] for s in discovered_subsets}

        # Step 4: Construct and return the verified DFA
        dfa = DFA(
            states=dfa_all_states,
            alphabet=automaton.alphabet,
            start_state=start_name,
            accepting_states=dfa_accepting_names,
            transitions=dfa_transitions,
        )

        trace = SubsetConstructionTrace(
            start_closure=start_subset,
            start_state_name=start_name,
            discovered_subsets=discovered_subsets,
            steps=step_traces,
            accepting_subsets=accepting_subsets,
            state_names=state_names,
        )

        return SubsetConstructionResult(
            dfa=dfa,
            trace=trace,
            subset_map=state_names,
        )


def epsilon_nfa_to_dfa(enfa: EpsilonNFA | NFA) -> DFA:
    """Convenience function: Convert an ε-NFA (or NFA) into an equivalent DFA."""
    return SubsetConstruction().transform(enfa)


def epsilon_nfa_to_dfa_with_trace(enfa: EpsilonNFA | NFA) -> SubsetConstructionResult:
    """Convenience function: Convert an ε-NFA to DFA and return the step trace."""
    return SubsetConstruction().transform_with_trace(enfa)

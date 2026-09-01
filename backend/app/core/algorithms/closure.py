"""Epsilon closure and state transition algorithms for finite automata."""

from __future__ import annotations

from collections import deque
from typing import Iterable, Set

from app.core.automata.models import EPSILON, AutomataValidationError, EpsilonNFA, NFA


def epsilon_closure(enfa: EpsilonNFA, states: str | Iterable[str]) -> frozenset[str]:
    """Compute the epsilon closure of a state or set of states.

    The epsilon closure of a set S is the set of all states reachable from any state in S
    using ZERO OR MORE epsilon (ε) transitions.

    - S is always a subset of epsilon_closure(S).
    - Cycles of epsilon transitions are handled gracefully without infinite loops.
    - Chains and multiple branching epsilon transitions are fully explored.

    Args:
        enfa: The EpsilonNFA instance.
        states: A single state string or an iterable of state strings.

    Returns:
        frozenset[str]: The complete epsilon closure set.
    """
    if isinstance(states, str):
        initial_states: Set[str] = {states}
    else:
        initial_states = set(states)

    # Validate that initial states belong to the automaton
    invalid_states = initial_states - enfa.states
    if invalid_states:
        raise AutomataValidationError(
            f"Cannot compute epsilon closure for states not in automaton: {sorted(invalid_states)}"
        )

    closure: set[str] = set(initial_states)
    queue: deque[str] = deque(initial_states)

    while queue:
        current = queue.popleft()
        # Retrieve all states directly reachable via epsilon
        epsilon_destinations = enfa.get_epsilon_transitions(current)
        for dest in epsilon_destinations:
            if dest not in closure:
                closure.add(dest)
                queue.append(dest)

    return frozenset(closure)


def move(
    automaton: EpsilonNFA | NFA,
    states: str | Iterable[str],
    symbol: str,
) -> frozenset[str]:
    """Compute the set of states reachable from `states` via a NON-EPSILON input symbol.

    Note:
        `move` does NOT compute the epsilon closure of the resulting destinations.
        It strictly computes:
            move(S, a) = { q' | exists q in S such that q' in delta(q, a) }

    Args:
        automaton: An NFA or EpsilonNFA instance.
        states: A single state string or an iterable of state strings.
        symbol: A valid symbol in the automaton's alphabet.

    Returns:
        frozenset[str]: The set of directly reachable states on `symbol`.
    """
    if isinstance(states, str):
        source_states: Set[str] = {states}
    else:
        source_states = set(states)

    # Validate states
    invalid_states = source_states - automaton.states
    if invalid_states:
        raise AutomataValidationError(
            f"Cannot perform move from states not in automaton: {sorted(invalid_states)}"
        )

    # Validate symbol
    if symbol not in automaton.alphabet:
        raise AutomataValidationError(
            f"Symbol '{symbol}' is not in automaton alphabet: {sorted(automaton.alphabet)}"
        )

    destinations: set[str] = set()
    for state in source_states:
        destinations.update(automaton.get_transitions(state, symbol))

    return frozenset(destinations)

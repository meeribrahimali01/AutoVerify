"""String acceptance simulation for DFA, NFA, and EpsilonNFA."""

from __future__ import annotations

from typing import Iterable, Sequence

from app.core.algorithms.closure import epsilon_closure
from app.core.automata.models import DFA, NFA, BaseAutomaton, EpsilonNFA


def tokenize_input_string(alphabet: Iterable[str], input_string: Sequence[str] | str) -> list[str]:
    """Tokenize an input sequence or raw string against the automaton's alphabet.

    1. If input_string is already a sequence of tokens (list/tuple), returns [str(t) for t in input_string].
    2. If input_string is empty (""), returns [].
    3. If all alphabet symbols are length 1 (or alphabet is empty), splits by character.
    4. If alphabet contains multi-character symbols, performs greedy prefix maximal-munch tokenization.
    """
    if isinstance(input_string, (list, tuple)):
        return [str(s) for s in input_string]

    raw_str = str(input_string)
    if not raw_str:
        return []

    alpha_set = set(str(s) for s in alphabet)
    # Check if any symbol in alphabet has length > 1
    has_multichar = any(len(s) > 1 for s in alpha_set)
    if not has_multichar:
        return list(raw_str)

    # Greedy maximal-munch tokenization
    tokens: list[str] = []
    idx = 0
    sorted_symbols = sorted(alpha_set, key=len, reverse=True)
    while idx < len(raw_str):
        matched = False
        for sym in sorted_symbols:
            if raw_str.startswith(sym, idx):
                tokens.append(sym)
                idx += len(sym)
                matched = True
                break
        if not matched:
            # Single character fallback
            tokens.append(raw_str[idx])
            idx += 1
    return tokens


def simulate_dfa(dfa: DFA, input_string: Sequence[str] | str) -> bool:
    """Check whether a DFA accepts a given input string."""
    tokens = tokenize_input_string(dfa.alphabet, input_string)
    current_state = dfa.start_state
    for sym in tokens:
        if sym not in dfa.alphabet:
            return False
        next_state = dfa.get_transition(current_state, sym)
        if next_state is None:
            return False
        current_state = next_state
    return current_state in dfa.accepting_states


def simulate_nfa(nfa: NFA, input_string: Sequence[str] | str) -> bool:
    """Check whether an NFA accepts a given input string."""
    tokens = tokenize_input_string(nfa.alphabet, input_string)
    current_states: frozenset[str] = frozenset({nfa.start_state})
    for sym in tokens:
        if sym not in nfa.alphabet:
            return False
        next_states: set[str] = set()
        for state in current_states:
            next_states.update(nfa.get_transitions(state, sym))
        current_states = frozenset(next_states)
        if not current_states:
            return False
    return bool(current_states & nfa.accepting_states)


def simulate_epsilon_nfa(enfa: EpsilonNFA, input_string: Sequence[str] | str) -> bool:
    """Check whether an EpsilonNFA accepts a given input string."""
    tokens = tokenize_input_string(enfa.alphabet, input_string)
    current_states = epsilon_closure(enfa, {enfa.start_state})
    for sym in tokens:
        if sym not in enfa.alphabet:
            return False
        direct_dests: set[str] = set()
        for state in current_states:
            direct_dests.update(enfa.get_transitions(state, sym))
        if not direct_dests:
            current_states = frozenset()
            break
        current_states = epsilon_closure(enfa, direct_dests)
        if not current_states:
            break
    return bool(current_states & enfa.accepting_states)


def simulate_automaton(automaton: BaseAutomaton, input_string: Sequence[str] | str) -> bool:
    """Universal string acceptance simulator for any supported automaton."""
    if isinstance(automaton, DFA):
        return simulate_dfa(automaton, input_string)
    elif isinstance(automaton, EpsilonNFA):
        return simulate_epsilon_nfa(automaton, input_string)
    elif isinstance(automaton, NFA):
        return simulate_nfa(automaton, input_string)
    raise TypeError(f"Unsupported automaton type: {type(automaton).__name__}")

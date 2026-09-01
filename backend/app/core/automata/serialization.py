"""Automata serialization and deserialization module.

Provides a unified, stable JSON/Dict representation for DFA, NFA, and EpsilonNFA.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from app.core.automata.models import (
    DFA,
    EPSILON,
    EPSILON_ALIASES,
    NFA,
    AutomataValidationError,
    BaseAutomaton,
    EpsilonNFA,
)


def serialize_automaton(automaton: BaseAutomaton) -> dict[str, Any]:
    """Serialize an automaton to its canonical dictionary form."""
    return automaton.to_dict()


def automaton_to_json(automaton: BaseAutomaton, indent: int | None = None) -> str:
    """Serialize an automaton to a formatted JSON string."""
    return json.dumps(serialize_automaton(automaton), indent=indent, sort_keys=True)


def deserialize_automaton(data: Mapping[str, Any]) -> BaseAutomaton:
    """Deserialize a dictionary into a DFA, NFA, or EpsilonNFA instance.

    Expected schema:
    {
        "type": "DFA" | "NFA" | "EPSILON_NFA",
        "states": ["q0", "q1", ...],
        "alphabet": ["0", "1", ...],
        "start_state": "q0",
        "accepting_states": ["q1", ...],
        "transitions": [
            {"from_state": "q0", "symbol": "0", "to_state": "q1"},
            ...
        ]
    }
    """
    if not isinstance(data, Mapping):
        raise AutomataValidationError(
            f"Automaton data must be a mapping/dict, got {type(data).__name__}."
        )

    required_keys = {"states", "alphabet", "start_state", "accepting_states", "transitions"}
    missing = required_keys - set(data.keys())
    if missing:
        raise AutomataValidationError(f"Missing required keys in automaton data: {sorted(missing)}.")

    raw_type = str(data.get("type", "")).strip()
    auto_type = raw_type.upper()
    states = list(data["states"])
    alphabet = list(data["alphabet"])
    start_state = str(data["start_state"])
    accepting_states = list(data["accepting_states"])
    transitions = data["transitions"]

    # Infer transition symbols into alphabet if not explicitly included
    alpha_set = set(str(s) for s in alphabet)
    if isinstance(transitions, (list, tuple)):
        for tr in transitions:
            if isinstance(tr, Mapping) and "symbol" in tr:
                sym = str(tr["symbol"])
                if sym.lower() not in EPSILON_ALIASES and sym != EPSILON:
                    alpha_set.add(sym)
    elif isinstance(transitions, Mapping):
        for k in transitions.keys():
            if isinstance(k, tuple) and len(k) == 2:
                sym = str(k[1])
                if sym.lower() not in EPSILON_ALIASES and sym != EPSILON:
                    alpha_set.add(sym)

    augmented_alphabet = sorted(alpha_set)

    # Normalize type matching
    epsilon_types = {
        "EPSILON_NFA",
        "EPSILON-NFA",
        "E-NFA",
        "ENFA",
        "EPSILON_NONDETERMINISTIC",
        "Ε-NFA",
        "Ε_NFA",
        "ΕNFA",
        "ε-NFA",
        "ε_NFA",
        "εNFA",
    }

    if auto_type in {"DFA", "DETERMINISTIC"}:
        return DFA(
            states=states,
            alphabet=augmented_alphabet,
            start_state=start_state,
            accepting_states=accepting_states,
            transitions=transitions,
        )
    elif auto_type in {"NFA", "NONDETERMINISTIC"}:
        return NFA(
            states=states,
            alphabet=augmented_alphabet,
            start_state=start_state,
            accepting_states=accepting_states,
            transitions=transitions,
        )
    elif auto_type in epsilon_types or raw_type in epsilon_types:
        return EpsilonNFA(
            states=states,
            alphabet=augmented_alphabet,
            start_state=start_state,
            accepting_states=accepting_states,
            transitions=transitions,
        )
    else:
        raise AutomataValidationError(
            f"Unknown or unsupported automaton type: '{raw_type}'. "
            "Must be one of: 'DFA', 'NFA', 'EPSILON_NFA'."
        )


def automaton_from_json(json_str: str) -> BaseAutomaton:
    """Deserialize a JSON string into an automaton instance."""
    try:
        data = json.loads(json_str)
    except Exception as exc:
        raise AutomataValidationError(f"Invalid JSON string: {exc}") from exc
    return deserialize_automaton(data)

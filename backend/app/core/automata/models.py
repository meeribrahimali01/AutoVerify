"""Core automata data models (DFA, NFA, EpsilonNFA).

This module provides immutable, mathematically validated finite automata models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Final, Mapping, Sequence, Set

EPSILON: Final[str] = "ε"
EPSILON_ALIASES: Final[frozenset[str]] = frozenset({EPSILON, "eps", "epsilon", "lambda", "λ", ""})


class AutomataValidationError(ValueError):
    """Raised when an automaton fails mathematical validation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


@dataclass(frozen=True)
class BaseAutomaton(ABC):
    """Abstract base class for all finite automata.

    Attributes:
        states: Finite set of state identifiers (non-empty).
        alphabet: Finite set of input symbols (must not contain epsilon).
        start_state: The initial state (must belong to states).
        accepting_states: Subset of states that are accepting/final.
    """

    states: frozenset[str]
    alphabet: frozenset[str]
    start_state: str
    accepting_states: frozenset[str]

    def __post_init__(self) -> None:
        # Base validation common to all finite automata
        if not self.states:
            raise AutomataValidationError("States set cannot be empty.")

        if not isinstance(self.start_state, str):
            raise AutomataValidationError(
                f"Start state must be a string, got {type(self.start_state).__name__}."
            )

        if self.start_state not in self.states:
            raise AutomataValidationError(
                f"Start state '{self.start_state}' is not in states: {sorted(self.states)}."
            )

        invalid_accepting = self.accepting_states - self.states
        if invalid_accepting:
            raise AutomataValidationError(
                f"Accepting states must be a subset of states. Invalid: {sorted(invalid_accepting)}."
            )

        # Alphabet must not contain epsilon representations
        if EPSILON in self.alphabet:
            raise AutomataValidationError(
                f"Alphabet must not contain epsilon symbol '{EPSILON}'."
            )

        for sym in self.alphabet:
            if not isinstance(sym, str) or len(sym) == 0:
                raise AutomataValidationError(
                    "Alphabet symbols must be non-empty strings."
                )
            if sym.lower() in {"eps", "epsilon", "lambda", "λ"}:
                raise AutomataValidationError(
                    f"Alphabet symbol '{sym}' is a reserved epsilon alias."
                )

        self._validate_transitions()

    @abstractmethod
    def _validate_transitions(self) -> None:
        """Validate automaton-specific transitions."""
        pass

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize automaton to a standard dictionary format."""
        pass

    def to_json(self, indent: int | None = None) -> str:
        """Serialize automaton to a JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseAutomaton:
        """Deserialize from dictionary."""
        from app.core.automata.serialization import deserialize_automaton
        return deserialize_automaton(data)

    @classmethod
    def from_json(cls, json_str: str) -> BaseAutomaton:
        """Deserialize from JSON string."""
        import json
        return cls.from_dict(json.loads(json_str))

    def __eq__(self, other: object) -> bool:
        """Structural equality comparison.

        IMPORTANT NOTE:
        Structural equality checks if two automata have identical state names,
        alphabets, start states, accepting states, and exact transition mappings.
        Structural equality is NOT language equivalence (L(A1) == L(A2)).
        Formal language equivalence will be evaluated via the verification engine.
        """
        if not isinstance(other, self.__class__):
            return False
        return (
            self.states == other.states
            and self.alphabet == other.alphabet
            and self.start_state == other.start_state
            and self.accepting_states == other.accepting_states
            and getattr(self, "transitions", None) == getattr(other, "transitions", None)
        )


@dataclass(frozen=True)
class DFA(BaseAutomaton):
    """Deterministic Finite Automaton (DFA).

    In a DFA:
    - Transitions are deterministic: delta(state, symbol) -> next_state
    - Exactly zero or one destination state per (state, symbol) pair.
    - No epsilon transitions are permitted.
    """

    transitions: Mapping[tuple[str, str], str] = field(default_factory=dict)

    def __init__(
        self,
        states: Set[str] | Sequence[str],
        alphabet: Set[str] | Sequence[str],
        start_state: str,
        accepting_states: Set[str] | Sequence[str],
        transitions: Mapping[tuple[str, str], str] | Mapping[str, Mapping[str, str]] | Sequence[Mapping[str, str]],
    ):
        norm_states = frozenset(states)
        norm_alphabet = frozenset(alphabet)
        norm_accepting = frozenset(accepting_states)
        norm_transitions = self._normalize_transitions_input(transitions)

        object.__setattr__(self, "states", norm_states)
        object.__setattr__(self, "alphabet", norm_alphabet)
        object.__setattr__(self, "start_state", start_state)
        object.__setattr__(self, "accepting_states", norm_accepting)
        object.__setattr__(self, "transitions", norm_transitions)
        self.__post_init__()

    @staticmethod
    def _normalize_transitions_input(
        transitions: Mapping[tuple[str, str], str] | Mapping[str, Mapping[str, str]] | Sequence[Mapping[str, str]]
    ) -> dict[tuple[str, str], str]:
        normalized: dict[tuple[str, str], str] = {}
        if isinstance(transitions, Mapping):
            for key, val in transitions.items():
                if isinstance(key, tuple) and len(key) == 2:
                    src, sym = key
                    if not isinstance(val, str):
                        raise AutomataValidationError(
                            f"DFA transition destination for ({src}, {sym}) must be a single state string, got {val}."
                        )
                    normalized[(str(src), str(sym))] = str(val)
                elif isinstance(key, str) and isinstance(val, Mapping):
                    src = key
                    for sym, dst in val.items():
                        if not isinstance(dst, str):
                            raise AutomataValidationError(
                                f"DFA transition destination for ({src}, {sym}) must be a single state string, got {dst}."
                            )
                        normalized[(str(src), str(sym))] = str(dst)
                else:
                    raise AutomataValidationError(f"Invalid transition mapping format: {key} -> {val}")
        elif isinstance(transitions, (list, tuple)):
            for item in transitions:
                if not isinstance(item, Mapping) or "from_state" not in item or "symbol" not in item or "to_state" not in item:
                    raise AutomataValidationError(
                        f"DFA transition items must have 'from_state', 'symbol', and 'to_state', got {item}."
                    )
                src = str(item["from_state"])
                sym = str(item["symbol"])
                dst = str(item["to_state"])
                if (src, sym) in normalized and normalized[(src, sym)] != dst:
                    raise AutomataValidationError(
                        f"Nondeterministic transition detected in DFA for ({src}, '{sym}'): destinations '{normalized[(src, sym)]}' and '{dst}'."
                    )
                normalized[(src, sym)] = dst
        else:
            raise AutomataValidationError(f"Unsupported transitions type: {type(transitions).__name__}")
        return normalized

    def _validate_transitions(self) -> None:
        for (src, sym), dst in self.transitions.items():
            if src not in self.states:
                raise AutomataValidationError(
                    f"Transition source state '{src}' not in states: {sorted(self.states)}."
                )
            if sym not in self.alphabet:
                raise AutomataValidationError(
                    f"Transition symbol '{sym}' for state '{src}' not in alphabet: {sorted(self.alphabet)}."
                )
            if dst not in self.states:
                raise AutomataValidationError(
                    f"Transition destination state '{dst}' for ({src}, '{sym}') not in states: {sorted(self.states)}."
                )

    def get_transition(self, state: str, symbol: str) -> str | None:
        """Return destination state for delta(state, symbol), or None if undefined."""
        return self.transitions.get((state, symbol))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to standard JSON-compatible dictionary."""
        sorted_transitions = [
            {"from_state": src, "symbol": sym, "to_state": dst}
            for (src, sym), dst in sorted(self.transitions.items())
        ]
        return {
            "type": "DFA",
            "states": sorted(self.states),
            "alphabet": sorted(self.alphabet),
            "start_state": self.start_state,
            "accepting_states": sorted(self.accepting_states),
            "transitions": sorted_transitions,
        }


@dataclass(frozen=True)
class NFA(BaseAutomaton):
    """Nondeterministic Finite Automaton (NFA without epsilon transitions).

    In an NFA:
    - Transitions map (state, symbol) -> set of destination states.
    - Zero, one, or multiple destinations are permitted.
    - Epsilon transitions are not permitted (use EpsilonNFA for epsilon transitions).
    """

    transitions: Mapping[tuple[str, str], frozenset[str]] = field(default_factory=dict)

    def __init__(
        self,
        states: Set[str] | Sequence[str],
        alphabet: Set[str] | Sequence[str],
        start_state: str,
        accepting_states: Set[str] | Sequence[str],
        transitions: Mapping[tuple[str, str], Set[str] | Sequence[str] | str]
        | Mapping[str, Mapping[str, Set[str] | Sequence[str] | str]]
        | Sequence[Mapping[str, Any]],
    ):
        norm_states = frozenset(states)
        norm_alphabet = frozenset(alphabet)
        norm_accepting = frozenset(accepting_states)
        norm_transitions = self._normalize_transitions_input(transitions)

        object.__setattr__(self, "states", norm_states)
        object.__setattr__(self, "alphabet", norm_alphabet)
        object.__setattr__(self, "start_state", start_state)
        object.__setattr__(self, "accepting_states", norm_accepting)
        object.__setattr__(self, "transitions", norm_transitions)
        self.__post_init__()

    @staticmethod
    def _normalize_transitions_input(
        transitions: Mapping[tuple[str, str], Set[str] | Sequence[str] | str]
        | Mapping[str, Mapping[str, Set[str] | Sequence[str] | str]]
        | Sequence[Mapping[str, Any]]
    ) -> dict[tuple[str, str], frozenset[str]]:
        raw_map: dict[tuple[str, str], set[str]] = {}

        if isinstance(transitions, Mapping):
            for key, val in transitions.items():
                if isinstance(key, tuple) and len(key) == 2:
                    src, sym = str(key[0]), str(key[1])
                    if isinstance(val, str):
                        dsts = {val}
                    else:
                        dsts = {str(d) for d in val}
                    raw_map.setdefault((src, sym), set()).update(dsts)
                elif isinstance(key, str) and isinstance(val, Mapping):
                    src = key
                    for sym, dst_val in val.items():
                        sym_str = str(sym)
                        if isinstance(dst_val, str):
                            dsts = {dst_val}
                        else:
                            dsts = {str(d) for d in dst_val}
                        raw_map.setdefault((src, sym_str), set()).update(dsts)
                else:
                    raise AutomataValidationError(f"Invalid transition mapping format: {key} -> {val}")
        elif isinstance(transitions, (list, tuple)):
            for item in transitions:
                if not isinstance(item, Mapping) or "from_state" not in item or "symbol" not in item:
                    raise AutomataValidationError(
                        f"NFA transition items must have 'from_state' and 'symbol', got {item}."
                    )
                src = str(item["from_state"])
                sym = str(item["symbol"])
                if "to_state" in item:
                    raw_map.setdefault((src, sym), set()).add(str(item["to_state"]))
                elif "to_states" in item:
                    val = item["to_states"]
                    dsts = {val} if isinstance(val, str) else {str(d) for d in val}
                    raw_map.setdefault((src, sym), set()).update(dsts)
                else:
                    raise AutomataValidationError(
                        f"NFA transition item missing 'to_state' or 'to_states': {item}"
                    )
        else:
            raise AutomataValidationError(f"Unsupported transitions type: {type(transitions).__name__}")

        # Filter out empty destination sets
        return {k: frozenset(v) for k, v in raw_map.items() if v}

    def _validate_transitions(self) -> None:
        for (src, sym), dsts in self.transitions.items():
            if src not in self.states:
                raise AutomataValidationError(
                    f"Transition source state '{src}' not in states: {sorted(self.states)}."
                )
            if sym not in self.alphabet:
                raise AutomataValidationError(
                    f"Transition symbol '{sym}' for state '{src}' not in alphabet: {sorted(self.alphabet)}."
                )
            invalid_dsts = dsts - self.states
            if invalid_dsts:
                raise AutomataValidationError(
                    f"Transition destination states {sorted(invalid_dsts)} for ({src}, '{sym}') not in states: {sorted(self.states)}."
                )

    def get_transitions(self, state: str, symbol: str) -> frozenset[str]:
        """Return set of destination states for delta(state, symbol)."""
        return self.transitions.get((state, symbol), frozenset())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to standard JSON-compatible dictionary."""
        sorted_transitions = []
        for (src, sym), dsts in sorted(self.transitions.items()):
            for dst in sorted(dsts):
                sorted_transitions.append({"from_state": src, "symbol": sym, "to_state": dst})
        return {
            "type": "NFA",
            "states": sorted(self.states),
            "alphabet": sorted(self.alphabet),
            "start_state": self.start_state,
            "accepting_states": sorted(self.accepting_states),
            "transitions": sorted_transitions,
        }


@dataclass(frozen=True)
class EpsilonNFA(BaseAutomaton):
    """Nondeterministic Finite Automaton with Epsilon Transitions (ε-NFA).

    In an ε-NFA:
    - Transitions map (state, symbol) -> set of destination states, where
      symbol in alphabet OR symbol == EPSILON ('ε').
    - Multiple epsilon destinations, epsilon cycles, and epsilon chains are fully supported.
    """

    transitions: Mapping[tuple[str, str], frozenset[str]] = field(default_factory=dict)

    def __init__(
        self,
        states: Set[str] | Sequence[str],
        alphabet: Set[str] | Sequence[str],
        start_state: str,
        accepting_states: Set[str] | Sequence[str],
        transitions: Mapping[tuple[str, str], Set[str] | Sequence[str] | str]
        | Mapping[str, Mapping[str, Set[str] | Sequence[str] | str]]
        | Sequence[Mapping[str, Any]],
    ):
        norm_states = frozenset(states)
        norm_alphabet = frozenset(alphabet)
        norm_accepting = frozenset(accepting_states)
        norm_transitions = self._normalize_transitions_input(transitions)

        object.__setattr__(self, "states", norm_states)
        object.__setattr__(self, "alphabet", norm_alphabet)
        object.__setattr__(self, "start_state", start_state)
        object.__setattr__(self, "accepting_states", norm_accepting)
        object.__setattr__(self, "transitions", norm_transitions)
        self.__post_init__()

    @staticmethod
    def _normalize_symbol(sym: str) -> str:
        s = str(sym)
        if s.lower() in EPSILON_ALIASES:
            return EPSILON
        return s

    @classmethod
    def _normalize_transitions_input(
        cls,
        transitions: Mapping[tuple[str, str], Set[str] | Sequence[str] | str]
        | Mapping[str, Mapping[str, Set[str] | Sequence[str] | str]]
        | Sequence[Mapping[str, Any]]
    ) -> dict[tuple[str, str], frozenset[str]]:
        raw_map: dict[tuple[str, str], set[str]] = {}

        if isinstance(transitions, Mapping):
            for key, val in transitions.items():
                if isinstance(key, tuple) and len(key) == 2:
                    src = str(key[0])
                    sym = cls._normalize_symbol(str(key[1]))
                    if isinstance(val, str):
                        dsts = {val}
                    else:
                        dsts = {str(d) for d in val}
                    raw_map.setdefault((src, sym), set()).update(dsts)
                elif isinstance(key, str) and isinstance(val, Mapping):
                    src = key
                    for sym_raw, dst_val in val.items():
                        sym = cls._normalize_symbol(str(sym_raw))
                        if isinstance(dst_val, str):
                            dsts = {dst_val}
                        else:
                            dsts = {str(d) for d in dst_val}
                        raw_map.setdefault((src, sym), set()).update(dsts)
                else:
                    raise AutomataValidationError(f"Invalid transition mapping format: {key} -> {val}")
        elif isinstance(transitions, (list, tuple)):
            for item in transitions:
                if not isinstance(item, Mapping) or "from_state" not in item or "symbol" not in item:
                    raise AutomataValidationError(
                        f"EpsilonNFA transition items must have 'from_state' and 'symbol', got {item}."
                    )
                src = str(item["from_state"])
                sym = cls._normalize_symbol(str(item["symbol"]))
                if "to_state" in item:
                    raw_map.setdefault((src, sym), set()).add(str(item["to_state"]))
                elif "to_states" in item:
                    val = item["to_states"]
                    dsts = {val} if isinstance(val, str) else {str(d) for d in val}
                    raw_map.setdefault((src, sym), set()).update(dsts)
                else:
                    raise AutomataValidationError(
                        f"EpsilonNFA transition item missing 'to_state' or 'to_states': {item}"
                    )
        else:
            raise AutomataValidationError(f"Unsupported transitions type: {type(transitions).__name__}")

        return {k: frozenset(v) for k, v in raw_map.items() if v}

    def _validate_transitions(self) -> None:
        valid_symbols = self.alphabet | {EPSILON}
        for (src, sym), dsts in self.transitions.items():
            if src not in self.states:
                raise AutomataValidationError(
                    f"Transition source state '{src}' not in states: {sorted(self.states)}."
                )
            if sym not in valid_symbols:
                raise AutomataValidationError(
                    f"Transition symbol '{sym}' for state '{src}' is neither in alphabet {sorted(self.alphabet)} nor epsilon ('{EPSILON}')."
                )
            invalid_dsts = dsts - self.states
            if invalid_dsts:
                raise AutomataValidationError(
                    f"Transition destination states {sorted(invalid_dsts)} for ({src}, '{sym}') not in states: {sorted(self.states)}."
                )

    def get_transitions(self, state: str, symbol: str) -> frozenset[str]:
        """Return set of destination states for delta(state, symbol)."""
        norm_sym = self._normalize_symbol(symbol)
        return self.transitions.get((state, norm_sym), frozenset())

    def get_epsilon_transitions(self, state: str) -> frozenset[str]:
        """Return set of destination states reachable via epsilon from state."""
        return self.get_transitions(state, EPSILON)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to standard JSON-compatible dictionary."""
        sorted_transitions = []
        for (src, sym), dsts in sorted(self.transitions.items()):
            for dst in sorted(dsts):
                sorted_transitions.append({"from_state": src, "symbol": sym, "to_state": dst})
        return {
            "type": "EPSILON_NFA",
            "states": sorted(self.states),
            "alphabet": sorted(self.alphabet),
            "start_state": self.start_state,
            "accepting_states": sorted(self.accepting_states),
            "transitions": sorted_transitions,
        }

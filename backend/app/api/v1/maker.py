"""Automata Maker API endpoints."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.algorithms.closure import epsilon_closure
from app.core.algorithms.simulation import (
    simulate_dfa,
    simulate_epsilon_nfa,
    simulate_nfa,
    tokenize_input_string,
)
from app.core.automata.models import (
    DFA,
    EPSILON,
    NFA,
    AutomataValidationError,
    BaseAutomaton,
    EpsilonNFA,
)
from app.core.automata.serialization import (
    deserialize_automaton,
    serialize_automaton,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maker", tags=["Automata Maker"])


# ============================================================================
# REQUEST & RESPONSE SCHEMAS
# ============================================================================


class TransitionSchema(BaseModel):
    from_state: str
    symbol: str
    to_state: str


class AutomatonPayload(BaseModel):
    type: str = Field(..., description="DFA, NFA, or EPSILON_NFA")
    states: List[str]
    alphabet: List[str]
    start_state: str
    accepting_states: List[str]
    transitions: List[TransitionSchema]


class ValidationResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    automaton: Optional[Dict[str, Any]] = None


class SimulateRequest(BaseModel):
    automaton: AutomatonPayload
    input_string: str = Field("", description="Input string to test")


class SimulationStep(BaseModel):
    step_index: int
    current_states: List[str]
    symbol: Optional[str] = None
    next_states: List[str]


class SimulateResponse(BaseModel):
    accepted: bool
    input_string: str
    steps: List[SimulationStep] = Field(default_factory=list)
    final_states: List[str] = Field(default_factory=list)
    error: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/health")
def maker_health():
    """Health check for maker service."""
    return {"status": "ok", "module": "maker"}


@router.get("/presets")
def get_presets() -> Dict[str, Dict[str, Any]]:
    """Return standard educational preset automata."""
    return {
        "dfa_even_zeros": {
            "name": "DFA: Even number of 0s",
            "data": {
                "type": "DFA",
                "states": ["q_even", "q_odd"],
                "alphabet": ["0", "1"],
                "start_state": "q_even",
                "accepting_states": ["q_even"],
                "transitions": [
                    {"from_state": "q_even", "symbol": "0", "to_state": "q_odd"},
                    {"from_state": "q_even", "symbol": "1", "to_state": "q_even"},
                    {"from_state": "q_odd", "symbol": "0", "to_state": "q_even"},
                    {"from_state": "q_odd", "symbol": "1", "to_state": "q_odd"},
                ],
            },
        },
        "nfa_ends_with_01": {
            "name": "NFA: Strings ending in 01",
            "data": {
                "type": "NFA",
                "states": ["q0", "q1", "q2"],
                "alphabet": ["0", "1"],
                "start_state": "q0",
                "accepting_states": ["q2"],
                "transitions": [
                    {"from_state": "q0", "symbol": "0", "to_state": "q0"},
                    {"from_state": "q0", "symbol": "1", "to_state": "q0"},
                    {"from_state": "q0", "symbol": "0", "to_state": "q1"},
                    {"from_state": "q1", "symbol": "1", "to_state": "q2"},
                ],
            },
        },
        "enfa_pattern_0star_1star": {
            "name": "ε-NFA: Language 0* 1*",
            "data": {
                "type": "EPSILON_NFA",
                "states": ["q0", "q1"],
                "alphabet": ["0", "1"],
                "start_state": "q0",
                "accepting_states": ["q1"],
                "transitions": [
                    {"from_state": "q0", "symbol": "0", "to_state": "q0"},
                    {"from_state": "q0", "symbol": EPSILON, "to_state": "q1"},
                    {"from_state": "q1", "symbol": "1", "to_state": "q1"},
                ],
            },
        },
    }


@router.post("/validate")
def validate_automaton_endpoint(payload: AutomatonPayload) -> ValidationResponse:
    """Validate an automaton payload against mathematical domain rules."""
    try:
        dict_data = payload.model_dump()
        automaton = deserialize_automaton(dict_data)
        return ValidationResponse(
            valid=True,
            errors=[],
            automaton=serialize_automaton(automaton),
        )
    except AutomataValidationError as exc:
        return ValidationResponse(valid=False, errors=[exc.message])
    except Exception as exc:
        return ValidationResponse(valid=False, errors=[str(exc)])


@router.post("/simulate", response_model=SimulateResponse)
def simulate_automaton_endpoint(req: SimulateRequest) -> SimulateResponse:
    """Simulate a test string on the provided automaton and return step trace."""
    # 1. Deserialize automaton
    try:
        dict_data = req.automaton.model_dump()
        automaton = deserialize_automaton(dict_data)
    except AutomataValidationError as exc:
        return SimulateResponse(
            accepted=False,
            input_string=req.input_string,
            error=f"Automaton validation error: {exc.message}",
        )
    except Exception as exc:
        logger.exception("Failed to deserialize automaton for simulation")
        return SimulateResponse(
            accepted=False,
            input_string=req.input_string,
            error=f"Invalid automaton configuration: {str(exc)}",
        )

    # 2. Tokenize input string against automaton alphabet
    inp = req.input_string
    tokens = tokenize_input_string(automaton.alphabet, inp)

    # Check for symbols outside alphabet
    for sym in tokens:
        if sym not in automaton.alphabet:
            return SimulateResponse(
                accepted=False,
                input_string=inp,
                error=f"Input contains symbol '{sym}', which is not in the automaton alphabet {sorted(automaton.alphabet)}.",
            )

    steps: List[SimulationStep] = []

    try:
        if isinstance(automaton, DFA):
            curr = automaton.start_state
            for idx, sym in enumerate(tokens):
                nxt = automaton.get_transition(curr, sym)
                next_list = [nxt] if nxt else []
                steps.append(
                    SimulationStep(
                        step_index=idx,
                        current_states=[curr],
                        symbol=sym,
                        next_states=next_list,
                    )
                )
                if nxt is None:
                    return SimulateResponse(
                        accepted=False,
                        input_string=inp,
                        steps=steps,
                        final_states=[],
                    )
                curr = nxt

            accepted = curr in automaton.accepting_states
            return SimulateResponse(
                accepted=accepted,
                input_string=inp,
                steps=steps,
                final_states=[curr],
            )

        elif isinstance(automaton, (NFA, EpsilonNFA)):
            if isinstance(automaton, EpsilonNFA):
                current_set = epsilon_closure(automaton, {automaton.start_state})
            else:
                current_set = frozenset({automaton.start_state})

            for idx, sym in enumerate(tokens):
                if isinstance(automaton, EpsilonNFA):
                    direct_dests: set[str] = set()
                    for st in current_set:
                        direct_dests.update(automaton.get_transitions(st, sym))
                    next_set = epsilon_closure(automaton, direct_dests) if direct_dests else frozenset()
                else:
                    next_dests: set[str] = set()
                    for st in current_set:
                        next_dests.update(automaton.get_transitions(st, sym))
                    next_set = frozenset(next_dests)

                steps.append(
                    SimulationStep(
                        step_index=idx,
                        current_states=sorted(current_set),
                        symbol=sym,
                        next_states=sorted(next_set),
                    )
                )
                current_set = next_set
                if not current_set:
                    break

            accepted = bool(current_set & automaton.accepting_states)
            return SimulateResponse(
                accepted=accepted,
                input_string=inp,
                steps=steps,
                final_states=sorted(current_set),
            )

        return SimulateResponse(
            accepted=False,
            input_string=inp,
            error=f"Unsupported automaton type: {type(automaton).__name__}",
        )

    except Exception as exc:
        logger.exception("Simulation execution error")
        return SimulateResponse(
            accepted=False,
            input_string=inp,
            error=f"Simulation error: {str(exc)}",
        )

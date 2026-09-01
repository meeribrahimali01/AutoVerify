"""Automata Converter API endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.maker import AutomatonPayload
from app.core.automata.models import (
    DFA,
    EPSILON,
    EpsilonNFA,
    NFA,
    AutomataValidationError,
)
from app.core.automata.serialization import deserialize_automaton, serialize_automaton
from app.core.transformations.subset_construction import epsilon_nfa_to_dfa_with_trace
from app.core.verification.equivalence import verify_epsilon_nfa_against_dfa

router = APIRouter(prefix="/converter", tags=["Automata Converter"])


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class ConverterStatistics(BaseModel):
    input_states_count: int
    input_transitions_count: int
    input_epsilon_transitions_count: int
    dfa_states_count: int
    dfa_transitions_count: int
    dfa_accepting_states_count: int


class ConverterResponse(BaseModel):
    success: bool
    dfa: Optional[Dict[str, Any]] = None
    statistics: Optional[ConverterStatistics] = None
    trace: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/health")
def converter_health():
    """Health check endpoint for Converter module."""
    return {"status": "ok", "module": "converter"}


@router.post("/epsilon-nfa-to-dfa", response_model=ConverterResponse)
def convert_epsilon_nfa_to_dfa(payload: AutomatonPayload) -> ConverterResponse:
    """Convert an ε-NFA into an equivalent DFA using Subset Construction with Trace.

    Args:
        payload: Canonical automaton representation (ε-NFA or NFA).

    Returns:
        ConverterResponse: Resulting DFA, execution trace, conversion statistics,
                           and formal equivalence verification status.
    """
    try:
        dict_data = payload.model_dump()
        automaton = deserialize_automaton(dict_data)
    except AutomataValidationError as exc:
        return ConverterResponse(
            success=False,
            error=f"Automaton validation failed: {exc.message}",
        )
    except Exception as exc:
        return ConverterResponse(
            success=False,
            error=f"Failed to parse input automaton: {str(exc)}",
        )

    if not isinstance(automaton, (EpsilonNFA, NFA)):
        return ConverterResponse(
            success=False,
            error=f"Converter expects ε-NFA or NFA input, received {automaton.__class__.__name__}.",
        )

    try:
        # Run trusted Subset Construction with step trace
        conversion_result = epsilon_nfa_to_dfa_with_trace(automaton)
        dfa = conversion_result.dfa
        trace_dict = conversion_result.trace.to_dict()

        # Compute conversion statistics
        input_states_cnt = len(automaton.states)
        input_trans_cnt = sum(len(dsts) for dsts in automaton.transitions.values())
        if isinstance(automaton, EpsilonNFA):
            input_eps_cnt = sum(
                len(dsts)
                for (src, sym), dsts in automaton.transitions.items()
                if sym == EPSILON
            )
        else:
            input_eps_cnt = 0

        stats = ConverterStatistics(
            input_states_count=input_states_cnt,
            input_transitions_count=input_trans_cnt,
            input_epsilon_transitions_count=input_eps_cnt,
            dfa_states_count=len(dfa.states),
            dfa_transitions_count=len(dfa.transitions),
            dfa_accepting_states_count=len(dfa.accepting_states),
        )

        # Run internal formal verification sanity check
        if isinstance(automaton, EpsilonNFA):
            verif_res = verify_epsilon_nfa_against_dfa(automaton, dfa)
        else:
            # Wrap NFA as EpsilonNFA for verification check
            wrapped_enfa = EpsilonNFA(
                states=automaton.states,
                alphabet=automaton.alphabet,
                start_state=automaton.start_state,
                accepting_states=automaton.accepting_states,
                transitions=automaton.to_dict()["transitions"],
            )
            verif_res = verify_epsilon_nfa_against_dfa(wrapped_enfa, dfa)

        return ConverterResponse(
            success=True,
            dfa=serialize_automaton(dfa),
            statistics=stats,
            trace=trace_dict,
            verification=verif_res.to_dict(),
        )

    except Exception as exc:
        return ConverterResponse(
            success=False,
            error=f"Conversion error: {str(exc)}",
        )

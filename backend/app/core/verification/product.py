"""Product automaton construction and state transition stepper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple

from app.core.automata.models import DFA

TRAP_STATE: str = "⊥_TRAP"


@dataclass(frozen=True)
class ProductState:
    """Represents a state in the product automaton of two DFAs."""

    state_a: str
    state_b: str

    def is_mismatch(self, dfa_a: DFA, dfa_b: DFA) -> bool:
        """A product state is a mismatch if exactly one automaton is in an accepting state.

        Language difference condition:
            (qA in F_A and qB not in F_B) OR (qA not in F_A and qB in F_B)
        """
        a_accepts = (self.state_a != TRAP_STATE) and (self.state_a in dfa_a.accepting_states)
        b_accepts = (self.state_b != TRAP_STATE) and (self.state_b in dfa_b.accepting_states)
        return a_accepts != b_accepts

    def acceptance_pair(self, dfa_a: DFA, dfa_b: DFA) -> Tuple[bool, bool]:
        """Return (a_accepts, b_accepts) boolean pair."""
        a_accepts = (self.state_a != TRAP_STATE) and (self.state_a in dfa_a.accepting_states)
        b_accepts = (self.state_b != TRAP_STATE) and (self.state_b in dfa_b.accepting_states)
        return a_accepts, b_accepts


def step_product_state(
    current: ProductState,
    symbol: str,
    dfa_a: DFA,
    dfa_b: DFA,
) -> ProductState:
    """Compute the next product state for input symbol on DFA A and DFA B.

    Handles partial DFAs smoothly by mapping missing transitions to a virtual trap state ⊥_TRAP.
    """
    # Step DFA A
    if current.state_a == TRAP_STATE:
        next_a = TRAP_STATE
    else:
        next_a = dfa_a.get_transition(current.state_a, symbol) or TRAP_STATE

    # Step DFA B
    if current.state_b == TRAP_STATE:
        next_b = TRAP_STATE
    else:
        next_b = dfa_b.get_transition(current.state_b, symbol) or TRAP_STATE

    return ProductState(state_a=next_a, state_b=next_b)

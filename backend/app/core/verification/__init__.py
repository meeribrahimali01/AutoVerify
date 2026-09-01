"""Formal verification package."""

from app.core.verification.counterexample import reconstruct_counterexample
from app.core.verification.equivalence import (
    VerificationResult,
    verify_dfa_equivalence,
    verify_epsilon_nfa_against_dfa,
)
from app.core.verification.product import (
    TRAP_STATE,
    ProductState,
    step_product_state,
)

__all__ = [
    "VerificationResult",
    "verify_dfa_equivalence",
    "verify_epsilon_nfa_against_dfa",
    "ProductState",
    "TRAP_STATE",
    "step_product_state",
    "reconstruct_counterexample",
]

"""Formal DFA and ε-NFA language equivalence verifier.

Uses on-demand Product Automaton construction and Breadth-First Search (BFS)
to formally verify language equivalence and extract the shortest counterexample string.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.core.automata.models import DFA, AutomataValidationError, EpsilonNFA
from app.core.transformations.subset_construction import epsilon_nfa_to_dfa
from app.core.verification.counterexample import reconstruct_counterexample
from app.core.verification.product import ProductState, step_product_state


@dataclass(frozen=True)
class VerificationResult:
    """Structured result of formal language equivalence verification."""

    equivalent: bool
    counterexample: Optional[str] = None
    automaton_a_accepts: Optional[bool] = None
    automaton_b_accepts: Optional[bool] = None
    states_explored: int = 0
    trace: Optional[List[dict]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize verification result to standard dictionary."""
        return {
            "equivalent": self.equivalent,
            "counterexample": self.counterexample,
            "automaton_a_accepts": self.automaton_a_accepts,
            "automaton_b_accepts": self.automaton_b_accepts,
            "states_explored": self.states_explored,
            "trace": self.trace,
            "error": self.error,
        }


def verify_dfa_equivalence(
    dfa_a: DFA,
    dfa_b: DFA,
    include_trace: bool = False,
) -> VerificationResult:
    """Formally verify if two DFAs recognize the exact same regular language (L(A) == L(B)).

    Algorithm:
    1. Validate input alphabets: Sigma_A must match Sigma_B.
    2. Start BFS on product automaton from (A.start_state, B.start_state).
    3. Explore product states (qA, qB) across all input symbols.
    4. If a state is discovered where (qA in F_A) != (qB in F_B), a language mismatch exists.
    5. Reconstruct the shortest distinguishing counterexample string from the BFS predecessor tree.
    6. If BFS terminates without reaching any mismatch state, the two DFAs are formally EQUIVALENT.

    Args:
        dfa_a: First DFA (e.g. Trusted Reference DFA).
        dfa_b: Second DFA (e.g. Student Generated DFA).
        include_trace: Whether to include the counterexample step trace in the result.

    Returns:
        VerificationResult: Detailed verification outcome and counterexample if not equivalent.
    """
    # 1. Alphabet compatibility verification
    if dfa_a.alphabet != dfa_b.alphabet:
        missing_in_b = dfa_a.alphabet - dfa_b.alphabet
        extra_in_b = dfa_b.alphabet - dfa_a.alphabet
        error_msg = "Alphabet mismatch between automata."
        if missing_in_b:
            error_msg += f" Missing in second DFA: {sorted(missing_in_b)}."
        if extra_in_b:
            error_msg += f" Extra in second DFA: {sorted(extra_in_b)}."
        return VerificationResult(
            equivalent=False,
            counterexample=None,
            states_explored=0,
            error=error_msg,
        )

    alphabet = sorted(dfa_a.alphabet)
    start_prod = ProductState(state_a=dfa_a.start_state, state_b=dfa_b.start_state)

    # 2. Check if the initial state is already a mismatch (e.g., empty string "")
    if start_prod.is_mismatch(dfa_a, dfa_b):
        a_acc, b_acc = start_prod.acceptance_pair(dfa_a, dfa_b)
        return VerificationResult(
            equivalent=False,
            counterexample="",
            automaton_a_accepts=a_acc,
            automaton_b_accepts=b_acc,
            states_explored=1,
            trace=[] if include_trace else None,
        )

    # 3. BFS exploration
    visited: set[ProductState] = {start_prod}
    queue: deque[ProductState] = deque([start_prod])
    predecessors: dict[ProductState, tuple[ProductState, str]] = {}

    while queue:
        current = queue.popleft()

        for symbol in alphabet:
            next_prod = step_product_state(current, symbol, dfa_a, dfa_b)

            if next_prod not in visited:
                visited.add(next_prod)
                predecessors[next_prod] = (current, symbol)

                # Check for language mismatch
                if next_prod.is_mismatch(dfa_a, dfa_b):
                    counterexample_str, path = reconstruct_counterexample(
                        mismatch_state=next_prod,
                        start_state=start_prod,
                        predecessors=predecessors,
                    )
                    a_acc, b_acc = next_prod.acceptance_pair(dfa_a, dfa_b)
                    return VerificationResult(
                        equivalent=False,
                        counterexample=counterexample_str,
                        automaton_a_accepts=a_acc,
                        automaton_b_accepts=b_acc,
                        states_explored=len(visited),
                        trace=path if include_trace else None,
                    )

                queue.append(next_prod)

    # 4. No mismatch reachable in product graph -> Languages are identical
    return VerificationResult(
        equivalent=True,
        counterexample=None,
        states_explored=len(visited),
        trace=None,
    )


def verify_epsilon_nfa_against_dfa(
    enfa: EpsilonNFA,
    generated_dfa: DFA,
    include_trace: bool = False,
) -> VerificationResult:
    """Formally verify whether a candidate/generated DFA correctly implements an ε-NFA.

    Converts the ε-NFA into a ground-truth Reference DFA using our trusted Subset Construction,
    then executes formal Product Automaton equivalence verification.

    Args:
        enfa: The ground-truth input ε-NFA.
        generated_dfa: The candidate DFA produced by a student or third-party converter.
        include_trace: Whether to include the counterexample step trace if not equivalent.

    Returns:
        VerificationResult: Formally proven equivalence or shortest counterexample string.
    """
    if not isinstance(enfa, EpsilonNFA):
        raise AutomataValidationError(
            f"Expected EpsilonNFA instance, got {type(enfa).__name__}."
        )
    if not isinstance(generated_dfa, DFA):
        raise AutomataValidationError(
            f"Expected DFA instance for generated_dfa, got {type(generated_dfa).__name__}."
        )

    # 1. Construct trusted reference DFA
    reference_dfa = epsilon_nfa_to_dfa(enfa)

    # 2. Formally verify equivalence
    return verify_dfa_equivalence(
        dfa_a=reference_dfa,
        dfa_b=generated_dfa,
        include_trace=include_trace,
    )

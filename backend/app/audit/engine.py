"""Core audit orchestration engine for finite automata transformation programs."""

from __future__ import annotations

import concurrent.futures
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence, Union

from app.audit.metrics import AuditStatus, CategoryStatistics
from app.audit.report import AuditReport, AuditResult
from app.core.automata.models import (
    DFA,
    AutomataValidationError,
    BaseAutomaton,
    EpsilonNFA,
)
from app.core.automata.serialization import deserialize_automaton
from app.core.generators.edge_cases import GeneratedTestCase
from app.core.transformations.subset_construction import epsilon_nfa_to_dfa
from app.core.verification.equivalence import verify_epsilon_nfa_against_dfa


class AutomataConverter(Protocol):
    """Protocol for an automata transformation program."""

    def convert(self, enfa: EpsilonNFA) -> Any:
        """Convert an ε-NFA into a target automaton representation."""
        ...


@dataclass
class AuditConfig:
    """Configuration options for an audit run."""

    timeout_seconds: float = 3.0
    stop_on_failure: bool = False
    include_verification_trace: bool = False
    include_generated_dfa: bool = True


# ============================================================================
# AUDIT ENGINE RUNNER
# ============================================================================


def _execute_with_timeout(
    executor: concurrent.futures.Executor,
    converter_fn: Callable[[EpsilonNFA], Any],
    enfa: EpsilonNFA,
    timeout_seconds: float,
) -> tuple[Any, Optional[AuditStatus], Optional[str]]:
    """Execute converter with strict per-test timeout monitoring."""
    future = executor.submit(converter_fn, enfa)
    try:
        result = future.result(timeout=timeout_seconds)
        return result, None, None
    except concurrent.futures.TimeoutError:
        return None, AuditStatus.TIMEOUT, f"Execution timed out after {timeout_seconds}s"
    except Exception as exc:
        return None, AuditStatus.EXECUTION_ERROR, f"{type(exc).__name__}: {str(exc)}"


def _parse_and_validate_dfa(raw_output: Any) -> tuple[Optional[DFA], Optional[str]]:
    """Ensure converter output is a valid DFA instance or serializable dictionary."""
    if raw_output is None:
        return None, "Converter returned None"

    if isinstance(raw_output, DFA):
        return raw_output, None

    if isinstance(raw_output, dict):
        try:
            automaton = deserialize_automaton(raw_output)
            if not isinstance(automaton, DFA):
                return None, f"Expected DFA output, got {automaton.__class__.__name__}"
            return automaton, None
        except Exception as exc:
            return None, f"Failed to parse DFA from dictionary: {exc}"

    return None, f"Unsupported converter output type: {type(raw_output).__name__}"


def run_audit(
    converter: Union[AutomataConverter, Callable[[EpsilonNFA], Any]],
    test_suite: Sequence[GeneratedTestCase],
    transformation: str = "epsilon_nfa_to_dfa",
    config: Optional[AuditConfig] = None,
    audit_id: Optional[str] = None,
    seed: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, str, str, Dict[str, int]], None]] = None,
) -> AuditReport:
    """Audit an ε-NFA -> DFA converter implementation across an automated test suite.

    Args:
        converter: Converter object with a `convert` method, or a callable function.
        test_suite: Sequence of GeneratedTestCase items to evaluate.
        transformation: Name of the audited transformation.
        config: Audit execution configuration.
        audit_id: Optional unique identifier for this audit run.
        seed: Optional test generator seed for report tracking.
        progress_callback: Optional callback(current, total, category, status_text, counts_dict)

    Returns:
        AuditReport: Comprehensive audit metrics, Verified Conversion Rate, and failure records.
    """
    cfg = config or AuditConfig()
    assigned_audit_id = audit_id or f"audit_{uuid.uuid4().hex[:10]}"

    # Resolve callable function from object or function
    if hasattr(converter, "convert") and callable(getattr(converter, "convert")):
        converter_fn = converter.convert
    elif callable(converter):
        converter_fn = converter
    else:
        raise TypeError("Converter must have a 'convert' method or be callable.")

    results: List[AuditResult] = []
    category_stats: Dict[str, CategoryStatistics] = {}

    verified_count = 0
    not_equiv_count = 0
    invalid_output_count = 0
    exec_error_count = 0
    timeout_count = 0

    total_start_time = time.perf_counter()
    total_test_count = len(test_suite)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        for idx, case in enumerate(test_suite, start=1):
            category = case.metadata.category
            if category not in category_stats:
                category_stats[category] = CategoryStatistics(category=category)

            if progress_callback:
                progress_callback(
                    idx,
                    total_test_count,
                    category,
                    "EXECUTING",
                    {
                        "verified": verified_count,
                        "failed": not_equiv_count,
                        "invalid_output": invalid_output_count,
                        "crashes": exec_error_count,
                        "timeouts": timeout_count,
                    },
                )

            t0 = time.perf_counter()
            raw_output, op_status, err_msg = _execute_with_timeout(
                executor, converter_fn, case.automaton, cfg.timeout_seconds
            )
            t1 = time.perf_counter()
            exec_time = t1 - t0

            if op_status is not None:
                # Operational failure (TIMEOUT or EXECUTION_ERROR)
                if op_status == AuditStatus.TIMEOUT:
                    timeout_count += 1
                else:
                    exec_error_count += 1

                category_stats[category].record(op_status)
                res = AuditResult(
                    test_id=case.metadata.test_id,
                    category=category,
                    status=op_status,
                    execution_time_seconds=exec_time,
                    original_enfa=case.automaton.to_dict(),
                    error_message=err_msg,
                    metadata=case.metadata,
                )
                results.append(res)

            else:
                # Output was produced -> Validate as DFA
                dfa, parse_err = _parse_and_validate_dfa(raw_output)
                if dfa is None:
                    invalid_output_count += 1
                    category_stats[category].record(AuditStatus.INVALID_OUTPUT)
                    res = AuditResult(
                        test_id=case.metadata.test_id,
                        category=category,
                        status=AuditStatus.INVALID_OUTPUT,
                        execution_time_seconds=exec_time,
                        original_enfa=case.automaton.to_dict(),
                        error_message=parse_err,
                        metadata=case.metadata,
                    )
                    results.append(res)

                else:
                    # Valid DFA produced -> Formally verify equivalence against trusted reference
                    verif_res = verify_epsilon_nfa_against_dfa(
                        enfa=case.automaton,
                        generated_dfa=dfa,
                        include_trace=cfg.include_verification_trace,
                    )

                    if verif_res.error:
                        # e.g., Alphabet mismatch
                        invalid_output_count += 1
                        category_stats[category].record(AuditStatus.INVALID_OUTPUT)
                        res = AuditResult(
                            test_id=case.metadata.test_id,
                            category=category,
                            status=AuditStatus.INVALID_OUTPUT,
                            execution_time_seconds=exec_time,
                            original_enfa=case.automaton.to_dict(),
                            generated_dfa=dfa.to_dict() if cfg.include_generated_dfa else None,
                            error_message=verif_res.error,
                            metadata=case.metadata,
                        )
                        results.append(res)

                    elif verif_res.equivalent:
                        verified_count += 1
                        category_stats[category].record(AuditStatus.VERIFIED)
                        res = AuditResult(
                            test_id=case.metadata.test_id,
                            category=category,
                            status=AuditStatus.VERIFIED,
                            execution_time_seconds=exec_time,
                            original_enfa=case.automaton.to_dict(),
                            generated_dfa=dfa.to_dict() if cfg.include_generated_dfa else None,
                            states_explored=verif_res.states_explored,
                            metadata=case.metadata,
                        )
                        results.append(res)

                    else:
                        # Mathematical mismatch (NOT_EQUIVALENT)
                        not_equiv_count += 1
                        category_stats[category].record(AuditStatus.NOT_EQUIVALENT)
                        res = AuditResult(
                            test_id=case.metadata.test_id,
                            category=category,
                            status=AuditStatus.NOT_EQUIVALENT,
                            execution_time_seconds=exec_time,
                            original_enfa=case.automaton.to_dict(),
                            generated_dfa=dfa.to_dict() if cfg.include_generated_dfa else None,
                            counterexample=verif_res.counterexample,
                            expected_acceptance=verif_res.automaton_a_accepts,
                            generated_acceptance=verif_res.automaton_b_accepts,
                            states_explored=verif_res.states_explored,
                            trace=verif_res.trace,
                            metadata=case.metadata,
                        )
                        results.append(res)

            # Check early stopping if requested
            if cfg.stop_on_failure and results[-1].status != AuditStatus.VERIFIED:
                break

    total_exec_time = time.perf_counter() - total_start_time

    return AuditReport(
        audit_id=assigned_audit_id,
        transformation=transformation,
        total_tests=len(results),
        verified_count=verified_count,
        failed_count=not_equiv_count,
        invalid_output_count=invalid_output_count,
        execution_error_count=exec_error_count,
        timeout_count=timeout_count,
        total_execution_time_seconds=total_exec_time,
        results=results,
        category_statistics=category_stats,
        seed=seed,
    )


# ============================================================================
# DEVELOPMENT REFERENCE AND TEST CONVERTERS
# ============================================================================


class CorrectConverter:
    """Reference converter utilizing trusted Subset Construction."""

    def convert(self, enfa: EpsilonNFA) -> DFA:
        return epsilon_nfa_to_dfa(enfa)


class BuggyConverter:
    """Deliberately flawed converter for verification testing.

    Bug: Omits epsilon-closure on the start state and ignores epsilon paths,
    causing it to fail on epsilon-heavy and acceptance-sensitive automata.
    """

    def convert(self, enfa: EpsilonNFA) -> DFA:
        # Intentionally ignore epsilon transitions entirely (treat as plain NFA without eps)
        plain_transitions: dict[tuple[str, str], set[str]] = {}
        for (src, sym), dsts in enfa.transitions.items():
            if sym in enfa.alphabet:
                plain_transitions[(src, sym)] = set(dsts)

        from app.core.automata.models import NFA
        nfa = NFA(
            states=enfa.states,
            alphabet=enfa.alphabet,
            start_state=enfa.start_state,
            accepting_states=enfa.accepting_states,
            transitions=plain_transitions,
        )
        return epsilon_nfa_to_dfa(nfa)


class InvalidOutputConverter:
    """Converter producing malformed/unparseable outputs."""

    def convert(self, enfa: EpsilonNFA) -> dict:
        return {"type": "DFA", "broken": True}


class ErrorRaisingConverter:
    """Converter that throws runtime exceptions."""

    def convert(self, enfa: EpsilonNFA) -> DFA:
        raise RuntimeError("Simulated converter crash")


class TimeoutConverter:
    """Converter simulating an infinite loop / timeout."""

    def __init__(self, delay_seconds: float = 10.0):
        self.delay_seconds = delay_seconds

    def convert(self, enfa: EpsilonNFA) -> DFA:
        time.sleep(self.delay_seconds)
        return epsilon_nfa_to_dfa(enfa)

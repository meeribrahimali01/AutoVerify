"""Student project audit orchestration adapter."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.ai.models import ProjectAnalysis
from app.audit.engine import AuditConfig, run_audit
from app.audit.report import AuditReport
from app.core.automata.models import EpsilonNFA
from app.core.generators.edge_cases import GeneratedTestCase
from app.core.generators.random_nfa import GeneratorConfig, generate_test_suite
from app.execution.models import ExecutionStatus
from app.execution.runner import StudentProgramRunner

logger = logging.getLogger(__name__)


class StudentProjectConverter:
    """Adapts StudentProgramRunner to the AutomataConverter protocol expected by run_audit."""

    def __init__(
        self,
        runner: StudentProgramRunner,
        project_id: str,
        project_dir: Path,
        analysis: ProjectAnalysis,
    ):
        self.runner = runner
        self.project_id = project_id
        self.project_dir = project_dir
        self.analysis = analysis

    def convert(self, enfa: EpsilonNFA) -> Any:
        enfa_dict = enfa.to_dict()
        res = self.runner.execute_single_test(
            project_id=self.project_id,
            project_dir=self.project_dir,
            analysis=self.analysis,
            test_enfa=enfa_dict,
        )

        if res.status == ExecutionStatus.SUCCESS:
            return res.generated_dfa
        elif res.status == ExecutionStatus.INVALID_OUTPUT:
            return res.stdout or "INVALID_OUTPUT"
        elif res.status == ExecutionStatus.TIMEOUT:
            raise TimeoutError(res.error_message or "Execution timed out")
        elif res.status == ExecutionStatus.CRASH:
            raise RuntimeError(res.error_message or "Process crashed")
        else:
            raise RuntimeError(res.error_message or f"Execution failed: {res.status}")


def execute_student_project_audit(
    project_id: str,
    project_dir: Path,
    analysis: ProjectAnalysis,
    test_count: int = 100,
    seed: int = 42,
    categories: Optional[List[str]] = None,
    timeout_seconds: float = 3.0,
    progress_callback: Optional[Callable[[int, int, str, str, Dict[str, int]], None]] = None,
    runner: Optional[StudentProgramRunner] = None,
) -> AuditReport:
    """Generate deterministic test suite and audit student project in sandbox."""
    # 1. Generate deterministic test suite
    gen_config = GeneratorConfig(count=test_count)
    suite: List[GeneratedTestCase] = generate_test_suite(
        config=gen_config,
        seed=seed,
        include_edge_cases=False,
    )

    # Filter categories if requested
    if categories and len(categories) > 0:
        allowed = set(categories)
        suite = [c for c in suite if c.metadata.category in allowed]

    actual_runner = runner or StudentProgramRunner(timeout_seconds=timeout_seconds)
    converter = StudentProjectConverter(
        runner=actual_runner,
        project_id=project_id,
        project_dir=project_dir,
        analysis=analysis,
    )

    cfg = AuditConfig(
        timeout_seconds=timeout_seconds,
        include_verification_trace=False,
        include_generated_dfa=True,
    )

    return run_audit(
        converter=converter,
        test_suite=suite,
        transformation="epsilon_nfa_to_dfa",
        config=cfg,
        audit_id=f"audit_proj_{project_id[:8]}_{seed}",
        seed=seed,
        progress_callback=progress_callback,
    )

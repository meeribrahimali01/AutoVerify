"""StudentProgramRunner orchestration for secure automata execution."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app.ai.models import ProjectAnalysis
from app.execution.adapter import (
    build_command_line,
    parse_and_normalize_student_output,
    prepare_student_input,
)
from app.execution.models import (
    ExecuteSingleTestResponse,
    ExecutionStatus,
    RawExecutionResult,
)
from app.execution.sandbox import (
    DEFAULT_TIMEOUT_SECONDS,
    IsolatedProcessSandbox,
    Sandbox,
)

logger = logging.getLogger(__name__)

SUPPORTED_RUNTIMES = {"python", "java", "cpp", "c"}


class StudentProgramRunner:
    """Orchestrates secure sandboxed execution of student automata converters."""

    def __init__(self, sandbox: Optional[Sandbox] = None, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS):
        self.sandbox = sandbox or IsolatedProcessSandbox()
        self.timeout_seconds = timeout_seconds

    def execute_single_test(
        self,
        project_id: str,
        project_dir: Path,
        analysis: ProjectAnalysis,
        test_enfa: Dict[str, Any],
    ) -> ExecuteSingleTestResponse:
        """Safely execute one test case and parse the returned DFA."""
        # 1. Validate project directory
        if not project_dir.exists() or not project_dir.is_dir():
            return ExecuteSingleTestResponse(
                status=ExecutionStatus.SANDBOX_ERROR,
                project_id=project_id,
                execution_time_ms=0.0,
                error_message=f"Project directory '{project_id}' does not exist or has expired.",
                original_enfa=test_enfa,
            )

        # 2. Validate language support
        lang = (analysis.language or "").lower()
        if lang not in SUPPORTED_RUNTIMES:
            return ExecuteSingleTestResponse(
                status=ExecutionStatus.NEEDS_CONFIGURATION,
                project_id=project_id,
                execution_time_ms=0.0,
                error_message=f"Language '{lang}' is not yet supported for automated sandbox execution.",
                original_enfa=test_enfa,
            )

        # 3. Validate entry point
        if not analysis.entry_point:
            return ExecuteSingleTestResponse(
                status=ExecutionStatus.NEEDS_CONFIGURATION,
                project_id=project_id,
                execution_time_ms=0.0,
                error_message="No entry point specified. Please configure the project entry point.",
                original_enfa=test_enfa,
            )

        # 4. Prepare isolated temporary execution directory
        scratch_dir = Path(tempfile.mkdtemp(prefix="autoverify_exec_"))

        try:
            # Copy student project files into isolated scratch space
            for item in project_dir.iterdir():
                dest = scratch_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)

            # 5. Prepare input data
            input_file, stdin_data = prepare_student_input(
                test_automaton=test_enfa,
                input_format=analysis.input_format,
                scratch_dir=scratch_dir,
            )

            # 6. Build command line
            try:
                cmd = build_command_line(
                    analysis=analysis,
                    project_dir=scratch_dir,
                    input_file=input_file,
                    scratch_dir=scratch_dir,
                )
            except Exception as exc:
                return ExecuteSingleTestResponse(
                    status=ExecutionStatus.NEEDS_CONFIGURATION,
                    project_id=project_id,
                    execution_time_ms=0.0,
                    error_message=f"Failed to build invocation command: {str(exc)}",
                    original_enfa=test_enfa,
                )

            # 7. Execute in sandbox
            raw_res = self.sandbox.run_command(
                command=cmd,
                work_dir=scratch_dir,
                stdin_data=stdin_data,
                timeout_seconds=self.timeout_seconds,
            )

            exec_time_ms = raw_res.execution_time_seconds * 1000.0

            # 8. Handle Timeout
            if raw_res.timed_out:
                return ExecuteSingleTestResponse(
                    status=ExecutionStatus.TIMEOUT,
                    project_id=project_id,
                    execution_time_ms=exec_time_ms,
                    exit_code=raw_res.exit_code,
                    stdout=raw_res.stdout,
                    stderr=raw_res.stderr,
                    error_message=raw_res.error or "Execution timed out.",
                    original_enfa=test_enfa,
                )

            # 9. Handle Crash (Non-zero exit code)
            if raw_res.exit_code != 0:
                return ExecuteSingleTestResponse(
                    status=ExecutionStatus.CRASH,
                    project_id=project_id,
                    execution_time_ms=exec_time_ms,
                    exit_code=raw_res.exit_code,
                    stdout=raw_res.stdout,
                    stderr=raw_res.stderr,
                    error_message=f"Process exited with non-zero exit code {raw_res.exit_code}.\nStderr: {raw_res.stderr.strip()}",
                    original_enfa=test_enfa,
                )

            # 10. Parse and normalize output DFA
            success, canonical_dfa, parse_err = parse_and_normalize_student_output(
                stdout_text=raw_res.stdout,
                scratch_dir=scratch_dir,
                output_format=analysis.output_format,
            )

            if not success or not canonical_dfa:
                return ExecuteSingleTestResponse(
                    status=ExecutionStatus.INVALID_OUTPUT,
                    project_id=project_id,
                    execution_time_ms=exec_time_ms,
                    exit_code=raw_res.exit_code,
                    stdout=raw_res.stdout,
                    stderr=raw_res.stderr,
                    error_message=parse_err or "Invalid or unparseable automaton output.",
                    original_enfa=test_enfa,
                )

            # 11. Success!
            return ExecuteSingleTestResponse(
                status=ExecutionStatus.SUCCESS,
                project_id=project_id,
                execution_time_ms=exec_time_ms,
                exit_code=raw_res.exit_code,
                stdout=raw_res.stdout,
                stderr=raw_res.stderr,
                original_enfa=test_enfa,
                generated_dfa=canonical_dfa,
            )

        except Exception as exc:
            logger.error("Sandbox execution error: %s", exc)
            return ExecuteSingleTestResponse(
                status=ExecutionStatus.SANDBOX_ERROR,
                project_id=project_id,
                execution_time_ms=0.0,
                error_message=f"Sandbox execution error: {str(exc)}",
                original_enfa=test_enfa,
            )

        finally:
            # 12. Clean up temporary scratch directory
            try:
                if scratch_dir.exists():
                    shutil.rmtree(scratch_dir, ignore_errors=True)
            except Exception:
                pass

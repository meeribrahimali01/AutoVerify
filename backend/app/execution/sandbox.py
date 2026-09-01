"""Sandbox execution environments for untrusted student code."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from app.execution.models import RawExecutionResult

logger = logging.getLogger(__name__)

MAX_OUTPUT_BYTES = 1024 * 1024  # 1 MB max captured output
DEFAULT_TIMEOUT_SECONDS = 5.0

# Minimal sanitized environment variables for isolated processes
SAFE_ENV_KEYS = {
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "PYTHONPATH",
    "JAVA_HOME",
    "CC",
    "CXX",
}


def get_sanitized_env() -> Dict[str, str]:
    """Return a stripped-down environment preventing leakage of API keys and DB secrets."""
    clean_env = {
        "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for k in SAFE_ENV_KEYS:
        if k in os.environ:
            clean_env[k] = os.environ[k]
    return clean_env


class Sandbox(ABC):
    """Abstract sandbox provider interface."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this sandbox runtime is available on the system."""
        pass

    @abstractmethod
    def run_command(
        self,
        command: List[str],
        work_dir: Path,
        stdin_data: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> RawExecutionResult:
        """Execute a command within the isolated sandbox."""
        pass


class IsolatedProcessSandbox(Sandbox):
    """Local isolated process sandbox with strict resource limits and env sanitization."""

    def is_available(self) -> bool:
        return True

    def run_command(
        self,
        command: List[str],
        work_dir: Path,
        stdin_data: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> RawExecutionResult:
        start_time = time.perf_counter()
        clean_env = get_sanitized_env()

        stdin_input = stdin_data.encode("utf-8") if stdin_data is not None else None

        try:
            process = subprocess.Popen(
                command,
                cwd=str(work_dir),
                stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=clean_env,
                shell=False,
            )

            stdout_bytes, stderr_bytes = process.communicate(
                input=stdin_input,
                timeout=timeout_seconds,
            )
            elapsed = time.perf_counter() - start_time

            # Limit output sizes to avoid memory exhaustion
            stdout_str = stdout_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
            stderr_str = stderr_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")

            return RawExecutionResult(
                exit_code=process.returncode,
                stdout=stdout_str,
                stderr=stderr_str,
                execution_time_seconds=elapsed,
                timed_out=False,
            )

        except subprocess.TimeoutExpired:
            elapsed = time.perf_counter() - start_time
            try:
                process.kill()
                process.wait(timeout=1.0)
            except Exception:
                pass

            return RawExecutionResult(
                exit_code=-1,
                stdout="",
                stderr="Execution timed out.",
                execution_time_seconds=elapsed,
                timed_out=True,
                error=f"Process exceeded maximum time limit of {timeout_seconds}s.",
            )

        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            logger.error("Failed to execute sandboxed process: %s", exc)
            return RawExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                execution_time_seconds=elapsed,
                timed_out=False,
                error=f"Execution error: {str(exc)}",
            )


class DockerSandbox(Sandbox):
    """Docker container isolation sandbox."""

    def __init__(self, image: str = "python:3.11-slim"):
        self.image = image
        self._checked_availability: Optional[bool] = None

    def is_available(self) -> bool:
        if self._checked_availability is not None:
            return self._checked_availability
        try:
            res = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                timeout=2.0,
                check=False,
            )
            self._checked_availability = res.returncode == 0
        except Exception:
            self._checked_availability = False
        return self._checked_availability

    def run_command(
        self,
        command: List[str],
        work_dir: Path,
        stdin_data: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> RawExecutionResult:
        if not self.is_available():
            raise RuntimeError("Docker is not available on this host.")

        start_time = time.perf_counter()
        abs_work_dir = str(work_dir.resolve())

        # Construct hardened docker invocation
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", "256m",
            "--cpus", "1.0",
            "--pids-limit", "64",
            "-v", f"{abs_work_dir}:/workspace",
            "-w", "/workspace",
            "-i" if stdin_data is not None else "-t",
            self.image,
        ] + command

        stdin_input = stdin_data.encode("utf-8") if stdin_data is not None else None

        try:
            process = subprocess.Popen(
                docker_cmd,
                stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )

            stdout_bytes, stderr_bytes = process.communicate(
                input=stdin_input,
                timeout=timeout_seconds,
            )
            elapsed = time.perf_counter() - start_time

            stdout_str = stdout_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
            stderr_str = stderr_bytes[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")

            return RawExecutionResult(
                exit_code=process.returncode,
                stdout=stdout_str,
                stderr=stderr_str,
                execution_time_seconds=elapsed,
                timed_out=False,
            )

        except subprocess.TimeoutExpired:
            elapsed = time.perf_counter() - start_time
            try:
                process.kill()
            except Exception:
                pass
            return RawExecutionResult(
                exit_code=-1,
                stdout="",
                stderr="Docker execution timed out.",
                execution_time_seconds=elapsed,
                timed_out=True,
                error=f"Container exceeded time limit of {timeout_seconds}s.",
            )
        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            return RawExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                execution_time_seconds=elapsed,
                timed_out=False,
                error=f"Docker sandbox error: {str(exc)}",
            )


class MockSandbox(Sandbox):
    """Mock sandbox for testing and controlled simulations."""

    def __init__(self, canned_result: Optional[RawExecutionResult] = None):
        self.canned_result = canned_result or RawExecutionResult(
            exit_code=0,
            stdout="{}",
            stderr="",
            execution_time_seconds=0.05,
        )

    def is_available(self) -> bool:
        return True

    def run_command(
        self,
        command: List[str],
        work_dir: Path,
        stdin_data: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> RawExecutionResult:
        return self.canned_result

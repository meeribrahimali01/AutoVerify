"""Models and schemas for secure student program execution."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.ai.models import ProjectAnalysis


class ExecutionStatus(str, Enum):
    """Execution status outcomes."""
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    CRASH = "CRASH"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    NEEDS_CONFIGURATION = "NEEDS_CONFIGURATION"
    SANDBOX_ERROR = "SANDBOX_ERROR"


class RawExecutionResult(BaseModel):
    """Raw process result from sandbox."""
    exit_code: int
    stdout: str
    stderr: str
    execution_time_seconds: float
    timed_out: bool = False
    error: Optional[str] = None


class ExecuteSingleTestRequest(BaseModel):
    """Request to execute one test case on an analyzed project."""
    project_id: str = Field(..., description="ID of extracted project")
    analysis: ProjectAnalysis = Field(..., description="AI or teacher-confirmed analysis")
    test_case: Optional[Dict[str, Any]] = Field(None, description="Optional custom test automaton. If omitted, a sample ε-NFA is generated.")


class ExecuteSingleTestResponse(BaseModel):
    """Response containing execution status, raw logs, and parsed canonical DFA."""
    status: ExecutionStatus
    project_id: str
    execution_time_ms: float
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    original_enfa: Optional[Dict[str, Any]] = None
    generated_dfa: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

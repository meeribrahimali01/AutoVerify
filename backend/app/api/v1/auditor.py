"""Automata Auditor API endpoints and in-memory execution store."""

from __future__ import annotations

import concurrent.futures
import threading
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.audit.engine import (
    AuditConfig,
    BuggyConverter,
    CorrectConverter,
    run_audit,
)
from app.audit.inspector import (
    FileCountLimitError,
    InvalidZipError,
    PathTraversalError,
    ProjectInspectionResponse,
    SizeLimitExceededError,
    ZipExtractionError,
    inspect_and_extract_project_zip,
)
from app.ai.models import (
    ProjectAnalysis,
    ProjectAnalysisRequest,
    ProjectAnalysisResponse,
)
from app.execution.models import ExecuteSingleTestRequest, ExecuteSingleTestResponse
from app.audit.report import AuditReport
from app.core.generators.edge_cases import GeneratedTestCase
from app.core.generators.random_nfa import GeneratorConfig, generate_test_suite

router = APIRouter(prefix="/auditor", tags=["Auditor"])


# ============================================================================
# IN-MEMORY AUDIT JOB STORE
# ============================================================================


class AuditJob:
    """Represents a background or synchronous audit job."""

    def __init__(self, audit_id: str, total_tests: int, seed: int, converter_name: str):
        self.audit_id = audit_id
        self.total_tests = total_tests
        self.seed = seed
        self.converter_name = converter_name
        self.status = "running"  # "running" | "completed" | "failed"
        self.current_test_index = 0
        self.current_category = "INITIALIZING"
        self.current_status_text = "GENERATING_TESTS"
        self.verified_count = 0
        self.failed_count = 0
        self.crash_count = 0
        self.timeout_count = 0
        self.invalid_output_count = 0
        self.report: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None


# Global in-memory audit job registry (most recent 50 runs)
_AUDIT_JOBS: Dict[str, AuditJob] = {}
_JOB_LOCK = threading.Lock()


# ============================================================================
# REQUEST & RESPONSE SCHEMAS
# ============================================================================


class AuditRunRequest(BaseModel):
    converter: str = Field(
        "correct",
        description="Converter identifier: 'correct' (reference) or 'buggy' (demo)",
    )
    test_count: int = Field(100, ge=1, le=1000, description="Number of tests to evaluate")
    seed: int = Field(42, description="Deterministic generator seed")
    categories: Optional[List[str]] = Field(
        None, description="Optional list of specific categories to include"
    )


class ProjectAuditRunRequest(BaseModel):
    project_id: str = Field(..., description="ID of extracted project")
    analysis: ProjectAnalysis = Field(..., description="AI or teacher-confirmed analysis")
    test_count: int = Field(100, ge=1, le=1000, description="Number of tests to evaluate")
    seed: int = Field(42, description="Deterministic generator seed")
    categories: Optional[List[str]] = Field(
        None, description="Optional list of specific categories to include"
    )
    timeout_seconds: float = Field(3.0, ge=0.5, le=30.0, description="Per-test timeout in seconds")


class ConverterInfo(BaseModel):
    id: str
    name: str
    description: str
    expected_vcr: Optional[float] = None


class AuditProgress(BaseModel):
    current: int
    total: int
    current_category: str
    current_status: str
    verified_count: int = 0
    failed_count: int = 0
    crash_count: int = 0
    timeout_count: int = 0
    invalid_output_count: int = 0


class AuditStatusResponse(BaseModel):
    audit_id: str
    status: str
    converter: str
    seed: int
    progress: AuditProgress
    report: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# BACKGROUND AUDIT RUNNERS
# ============================================================================


def _execute_audit_job(job: AuditJob, config_req: AuditRunRequest) -> None:
    """Execute reference audit asynchronously in background thread and update job status."""
    try:
        # Select converter
        if config_req.converter.lower() == "buggy":
            converter = BuggyConverter()
        else:
            converter = CorrectConverter()

        job.current_status_text = "GENERATING_SUITE"
        job.current_category = "ALL"

        # Generate test suite
        gen_config = GeneratorConfig(count=config_req.test_count)
        suite: List[GeneratedTestCase] = generate_test_suite(
            config=gen_config,
            seed=config_req.seed,
            include_edge_cases=False,
        )

        # Filter by categories if specified
        if config_req.categories and len(config_req.categories) > 0:
            allowed = set(config_req.categories)
            suite = [c for c in suite if c.metadata.category in allowed]

        job.total_tests = len(suite)
        job.current_status_text = "AUDITING"

        def on_prog(curr, tot, cat, stat, counts):
            job.current_test_index = curr
            job.total_tests = tot
            job.current_category = cat
            job.current_status_text = stat
            job.verified_count = counts.get("verified", 0)
            job.failed_count = counts.get("failed", 0)
            job.invalid_output_count = counts.get("invalid_output", 0)
            job.crash_count = counts.get("crashes", 0)
            job.timeout_count = counts.get("timeouts", 0)

        # Run audit engine
        report: AuditReport = run_audit(
            converter=converter,
            test_suite=suite,
            transformation="epsilon_nfa_to_dfa",
            config=AuditConfig(include_verification_trace=True),
            audit_id=job.audit_id,
            seed=config_req.seed,
            progress_callback=on_prog,
        )

        job.current_test_index = len(suite)
        job.current_category = "COMPLETED"
        job.current_status_text = "VERIFIED"
        job.report = report.to_dict()
        job.status = "completed"

    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.current_status_text = "ERROR"


def _execute_project_audit_job(
    job: AuditJob,
    req: ProjectAuditRunRequest,
    project_dir: Any,
) -> None:
    """Execute sandboxed student project audit asynchronously in background thread."""
    from app.audit.student_audit import execute_student_project_audit

    try:
        job.current_status_text = "GENERATING_SUITE"
        job.current_category = "ALL"

        def on_prog(curr, tot, cat, stat, counts):
            job.current_test_index = curr
            job.total_tests = tot
            job.current_category = cat
            job.current_status_text = stat
            job.verified_count = counts.get("verified", 0)
            job.failed_count = counts.get("failed", 0)
            job.invalid_output_count = counts.get("invalid_output", 0)
            job.crash_count = counts.get("crashes", 0)
            job.timeout_count = counts.get("timeouts", 0)

        report = execute_student_project_audit(
            project_id=req.project_id,
            project_dir=project_dir,
            analysis=req.analysis,
            test_count=req.test_count,
            seed=req.seed,
            categories=req.categories,
            timeout_seconds=req.timeout_seconds,
            progress_callback=on_prog,
        )

        job.current_test_index = req.test_count
        job.current_category = "COMPLETED"
        job.current_status_text = "VERIFIED"
        job.report = report.to_dict()
        job.status = "completed"

    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.current_status_text = "ERROR"


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/health")
def auditor_health():
    """Health check for Auditor API."""
    return {"status": "ok", "module": "auditor"}


@router.post("/upload-project", response_model=ProjectInspectionResponse)
async def upload_project(file: UploadFile = File(...)) -> ProjectInspectionResponse:
    """Accept and securely extract a student project ZIP archive, inspecting its files passively."""
    # 1. Basic filename validation
    filename = file.filename or "project.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .zip project archives are accepted.",
        )

    # 2. Read file contents into memory safely
    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(exc)}",
        )

    # 3. Secure extraction & inspection
    try:
        response, _extracted_dir = inspect_and_extract_project_zip(
            zip_bytes=content,
            original_filename=filename,
        )
        return response
    except SizeLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Size limit exceeded: {str(exc)}",
        )
    except PathTraversalError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security error: {str(exc)}",
        )
    except InvalidZipError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ZIP: {str(exc)}",
        )
    except FileCountLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project inspection error: {str(exc)}",
        )


@router.post("/analyze-project", response_model=ProjectAnalysisResponse)
def analyze_project(req: ProjectAnalysisRequest) -> ProjectAnalysisResponse:
    """Statically analyze extracted student project code with AI to infer invocation interface."""
    import tempfile
    from pathlib import Path
    from app.ai.analyzer import analyze_student_project

    base_dir = Path(tempfile.gettempdir()) / "autoverify_projects"
    project_dir = base_dir / req.project_id

    if not project_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{req.project_id}' not found or session expired. Please re-upload.",
        )

    # Normalize single wrapper folder if present
    items = [p for p in project_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]
    effective_dir = project_dir
    if len(items) == 1 and len(list(project_dir.glob("*"))) == 1:
        effective_dir = items[0]

    return analyze_student_project(
        project_id=req.project_id,
        project_dir=effective_dir,
        manual_entry_point=req.manual_entry_point,
    )


@router.post("/execute-test", response_model=ExecuteSingleTestResponse)
def execute_single_test(req: ExecuteSingleTestRequest) -> ExecuteSingleTestResponse:
    """Safely execute one generated automaton test case against student's project."""
    import tempfile
    from pathlib import Path
    from app.execution.runner import StudentProgramRunner
    from app.core.generators.random_nfa import GeneratorConfig, generate_test_suite
    from app.core.automata.serialization import serialize_automaton

    base_dir = Path(tempfile.gettempdir()) / "autoverify_projects"
    project_dir = base_dir / req.project_id

    if not project_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{req.project_id}' not found or session expired. Please re-upload.",
        )

    items = [p for p in project_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]
    effective_dir = project_dir
    if len(items) == 1 and len(list(project_dir.glob("*"))) == 1:
        effective_dir = items[0]

    # Prepare test ε-NFA
    if req.test_case:
        test_enfa = req.test_case
    else:
        # Generate a deterministic benchmark sample ε-NFA
        suite = generate_test_suite(
            config=GeneratorConfig(min_states=3, max_states=4, alphabet=["0", "1"], epsilon_probability=0.4),
            count=1,
            seed=42,
        )
        test_enfa = serialize_automaton(suite[0].automaton)

    runner = StudentProgramRunner()
    return runner.execute_single_test(
        project_id=req.project_id,
        project_dir=effective_dir,
        analysis=req.analysis,
        test_enfa=test_enfa,
    )


@router.get("/converters", response_model=List[ConverterInfo])
def list_demo_converters():
    """List available demo & reference converters."""
    return [
        ConverterInfo(
            id="correct",
            name="Correct Reference Converter",
            description="Trusted subset construction implementation. Formally verified 100% equivalence rate.",
            expected_vcr=1.0,
        ),
        ConverterInfo(
            id="buggy",
            name="Buggy Demo Converter",
            description="Deliberately flawed converter that omits multi-hop epsilon transitions. Demonstrates counterexample detection.",
            expected_vcr=0.23,
        ),
    ]


@router.post("/run", response_model=AuditStatusResponse)
def trigger_audit_run(req: AuditRunRequest, background_tasks: BackgroundTasks):
    """Trigger a new automated audit run."""
    assigned_id = f"audit_{uuid.uuid4().hex[:10]}"
    job = AuditJob(
        audit_id=assigned_id,
        total_tests=req.test_count,
        seed=req.seed,
        converter_name=req.converter,
    )

    with _JOB_LOCK:
        _AUDIT_JOBS[assigned_id] = job

    # Launch in background thread
    background_tasks.add_task(_execute_audit_job, job, req)

    return AuditStatusResponse(
        audit_id=job.audit_id,
        status=job.status,
        converter=job.converter_name,
        seed=job.seed,
        progress=AuditProgress(
            current=job.current_test_index,
            total=job.total_tests,
            current_category=job.current_category,
            current_status=job.current_status_text,
            verified_count=job.verified_count,
            failed_count=job.failed_count,
            crash_count=job.crash_count,
            timeout_count=job.timeout_count,
            invalid_output_count=job.invalid_output_count,
        ),
        report=None,
        error=None,
    )


@router.post("/run-project-audit", response_model=AuditStatusResponse)
def trigger_project_audit_run(req: ProjectAuditRunRequest, background_tasks: BackgroundTasks):
    """Trigger an automated sandboxed audit run on an uploaded student project."""
    import tempfile
    from pathlib import Path

    base_dir = Path(tempfile.gettempdir()) / "autoverify_projects"
    project_dir = base_dir / req.project_id

    if not project_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{req.project_id}' not found or session expired. Please re-upload.",
        )

    items = [p for p in project_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]
    effective_dir = project_dir
    if len(items) == 1 and len(list(project_dir.glob("*"))) == 1:
        effective_dir = items[0]

    assigned_id = f"audit_proj_{req.project_id[:6]}_{uuid.uuid4().hex[:6]}"
    job = AuditJob(
        audit_id=assigned_id,
        total_tests=req.test_count,
        seed=req.seed,
        converter_name=f"Student ({req.analysis.language})",
    )

    with _JOB_LOCK:
        _AUDIT_JOBS[assigned_id] = job

    # Execute asynchronously in background thread
    background_tasks.add_task(_execute_project_audit_job, job, req, effective_dir)

    return AuditStatusResponse(
        audit_id=job.audit_id,
        status=job.status,
        converter=job.converter_name,
        seed=job.seed,
        progress=AuditProgress(
            current=0,
            total=req.test_count,
            current_category="INITIALIZING",
            current_status="LAUNCHING",
        ),
        report=None,
        error=None,
    )


@router.get("/status/{audit_id}", response_model=AuditStatusResponse)
@router.get("/{audit_id}", response_model=AuditStatusResponse)
def get_audit_status(audit_id: str):
    """Query current status or retrieve final report of an audit run."""
    with _JOB_LOCK:
        job = _AUDIT_JOBS.get(audit_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Audit job '{audit_id}' not found.")

    return AuditStatusResponse(
        audit_id=job.audit_id,
        status=job.status,
        converter=job.converter_name,
        seed=job.seed,
        progress=AuditProgress(
            current=job.current_test_index,
            total=job.total_tests,
            current_category=job.current_category,
            current_status=job.current_status_text,
            verified_count=job.verified_count,
            failed_count=job.failed_count,
            crash_count=job.crash_count,
            timeout_count=job.timeout_count,
            invalid_output_count=job.invalid_output_count,
        ),
        report=job.report,
        error=job.error,
    )


@router.get("/history/recent", response_model=List[Dict[str, Any]])
def get_recent_audits():
    """Return summary list of recent audit runs."""
    with _JOB_LOCK:
        jobs = list(_AUDIT_JOBS.values())[-20:]

    history = []
    for j in reversed(jobs):
        item: Dict[str, Any] = {
            "audit_id": j.audit_id,
            "status": j.status,
            "converter": j.converter_name,
            "total_tests": j.total_tests,
            "seed": j.seed,
        }
        if j.report and "summary" in j.report:
            item["vcr"] = j.report["summary"].get("verified_conversion_rate")
            item["verified"] = j.report["summary"].get("verified_count")
            item["failed"] = j.report["summary"].get("failed_count")
        history.append(item)
    return history

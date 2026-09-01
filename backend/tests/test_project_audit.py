"""Tests for Auditor Step 4: Full Automated Student Project Audit."""

import io
import json
import time
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ai.models import ProjectAnalysis
from app.audit.report import AuditReport
from app.audit.student_audit import execute_student_project_audit
from app.core.automata.models import EpsilonNFA
from app.core.transformations.subset_construction import epsilon_nfa_to_dfa
from app.execution.models import ExecutionStatus, RawExecutionResult
from app.execution.runner import StudentProgramRunner
from app.execution.sandbox import MockSandbox

client = TestClient(app)


def create_zip_bytes(files: dict[str, str]) -> bytes:
    """Helper to create an in-memory zip file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(path, content.encode("utf-8"))
    return buf.getvalue()


class MockDynamicStudentRunner(StudentProgramRunner):
    """Dynamic mock runner that converts inputs using a given python logic without disk I/O."""

    def __init__(self, mode: str = "correct", timeout_seconds: float = 3.0):
        super().__init__(sandbox=MockSandbox(), timeout_seconds=timeout_seconds)
        self.mode = mode

    def execute_single_test(self, project_id, project_dir, analysis, test_enfa):
        from app.core.automata.serialization import deserialize_automaton, serialize_automaton

        if self.mode == "timeout":
            return type("Res", (), {
                "status": ExecutionStatus.TIMEOUT,
                "error_message": "Execution timed out",
                "execution_time_ms": 3000.0,
                "exit_code": -1,
                "stdout": "",
                "stderr": "",
                "generated_dfa": None,
            })()

        if self.mode == "crash":
            return type("Res", (), {
                "status": ExecutionStatus.CRASH,
                "error_message": "Process crashed with exit code 1",
                "execution_time_ms": 10.0,
                "exit_code": 1,
                "stdout": "",
                "stderr": "RuntimeError",
                "generated_dfa": None,
            })()

        if self.mode == "invalid_dfa":
            return type("Res", (), {
                "status": ExecutionStatus.INVALID_OUTPUT,
                "error_message": "Invalid DFA structure",
                "execution_time_ms": 10.0,
                "exit_code": 0,
                "stdout": "NOT_A_VALID_DFA",
                "stderr": "",
                "generated_dfa": None,
            })()

        # Normal conversion
        enfa = deserialize_automaton(test_enfa) if isinstance(test_enfa, dict) else test_enfa
        if self.mode == "buggy":
            # Buggy: corrupt DFA by emptying accepting states
            dfa = epsilon_nfa_to_dfa(enfa)
            dfa_dict = serialize_automaton(dfa)
            dfa_dict["accepting_states"] = []
            return type("Res", (), {
                "status": ExecutionStatus.SUCCESS,
                "execution_time_ms": 5.0,
                "exit_code": 0,
                "stdout": json.dumps(dfa_dict),
                "stderr": "",
                "generated_dfa": dfa_dict,
                "error_message": None,
            })()

        # Correct reference
        dfa = epsilon_nfa_to_dfa(enfa)
        dfa_dict = serialize_automaton(dfa)
        return type("Res", (), {
            "status": ExecutionStatus.SUCCESS,
            "execution_time_ms": 2.0,
            "exit_code": 0,
            "stdout": json.dumps(dfa_dict),
            "stderr": "",
            "generated_dfa": dfa_dict,
            "error_message": None,
        })()


# ============================================================================
# TEST CASES
# ============================================================================


def test_1_ten_test_successful_audit(tmp_path):
    """1. 10-test audit of correct student project achieves 100% VCR."""
    runner = MockDynamicStudentRunner(mode="correct")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    report: AuditReport = execute_student_project_audit(
        project_id="test_10",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=10,
        seed=42,
        runner=runner,
    )

    assert report.total_tests == 10
    assert report.verified_count == 10
    assert report.failed_count == 0
    assert report.verified_conversion_rate == 1.0


def test_2_hundred_test_successful_audit(tmp_path):
    """2. 100-test audit of correct student project achieves 100% VCR across all categories."""
    runner = MockDynamicStudentRunner(mode="correct")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    report: AuditReport = execute_student_project_audit(
        project_id="test_100",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=100,
        seed=42,
        runner=runner,
    )

    assert report.total_tests == 100
    assert report.verified_count == 100
    assert report.verified_conversion_rate == 1.0


def test_3_reproducibility_with_same_seed(tmp_path):
    """3. Auditing with identical seed produces identical test cases and results."""
    runner = MockDynamicStudentRunner(mode="correct")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    rep1 = execute_student_project_audit("p1", tmp_path, analysis, test_count=20, seed=12345, runner=runner)
    rep2 = execute_student_project_audit("p2", tmp_path, analysis, test_count=20, seed=12345, runner=runner)

    assert [r.test_id for r in rep1.results] == [r.test_id for r in rep2.results]
    assert rep1.verified_count == rep2.verified_count


def test_4_different_seed_produces_different_suite(tmp_path):
    """4. Different seeds generate different test suite automata."""
    runner = MockDynamicStudentRunner(mode="correct")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    rep1 = execute_student_project_audit("p1", tmp_path, analysis, test_count=20, seed=111, runner=runner)
    rep2 = execute_student_project_audit("p2", tmp_path, analysis, test_count=20, seed=999, runner=runner)

    assert [r.original_enfa for r in rep1.results] != [r.original_enfa for r in rep2.results]


def test_5_mathematically_incorrect_converter_detection(tmp_path):
    """5. Buggy converter is detected by formal equivalence checker."""
    runner = MockDynamicStudentRunner(mode="buggy")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    report = execute_student_project_audit(
        project_id="buggy_p",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=20,
        seed=42,
        runner=runner,
    )

    assert report.failed_count > 0
    assert report.verified_conversion_rate is not None
    assert report.verified_conversion_rate < 1.0


def test_6_counterexample_preservation(tmp_path):
    """6. For mathematically incorrect cases, shortest distinguishing string is captured."""
    runner = MockDynamicStudentRunner(mode="buggy")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    report = execute_student_project_audit(
        project_id="buggy_p",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=20,
        seed=42,
        runner=runner,
    )

    assert len(report.failures) > 0
    for failure in report.failures:
        if failure.status.value == "NOT_EQUIVALENT":
            assert failure.counterexample is not None


def test_7_crash_handling(tmp_path):
    """7. Crash is recorded as operational error, not counted as mathematical non-equivalence."""
    runner = MockDynamicStudentRunner(mode="crash")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    report = execute_student_project_audit(
        project_id="crash_p",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=10,
        seed=42,
        runner=runner,
    )

    assert report.execution_error_count == 10
    assert report.verified_count == 0
    assert report.failed_count == 0  # Not equivalent count is 0


def test_8_timeout_handling(tmp_path):
    """8. Timeout is recorded as operational error."""
    runner = MockDynamicStudentRunner(mode="timeout")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    report = execute_student_project_audit(
        project_id="timeout_p",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=10,
        seed=42,
        runner=runner,
    )

    assert report.timeout_count == 10
    assert report.verified_count == 0


def test_9_invalid_dfa_handling(tmp_path):
    """9. Invalid output is recorded under invalid_output_count."""
    runner = MockDynamicStudentRunner(mode="invalid_dfa")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    report = execute_student_project_audit(
        project_id="inv_p",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=10,
        seed=42,
        runner=runner,
    )

    assert report.invalid_output_count == 10


def test_10_category_statistics(tmp_path):
    """10. Per-category statistics are calculated accurately."""
    runner = MockDynamicStudentRunner(mode="correct")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    report = execute_student_project_audit(
        project_id="cat_p",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=50,
        seed=42,
        runner=runner,
    )

    assert len(report.category_statistics) > 0
    for cat_name, stats in report.category_statistics.items():
        assert stats.total > 0
        assert stats.verified_conversion_rate == 1.0


def test_11_vcr_calculation(tmp_path):
    """11. Verified Conversion Rate is verified / (verified + not_equivalent)."""
    runner = MockDynamicStudentRunner(mode="buggy")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    report = execute_student_project_audit(
        project_id="vcr_p",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=30,
        seed=42,
        runner=runner,
    )

    denom = report.verified_count + report.failed_count
    if denom > 0:
        expected_vcr = report.verified_count / denom
        assert abs(report.verified_conversion_rate - expected_vcr) < 1e-6


def test_12_audit_progress_callback(tmp_path):
    """12. Progress callback receives increasing index and accurate counts."""
    runner = MockDynamicStudentRunner(mode="correct")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    progress_ticks = []

    def on_prog(curr, tot, cat, stat, counts):
        progress_ticks.append((curr, tot, cat))

    execute_student_project_audit(
        project_id="prog_p",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=10,
        seed=42,
        progress_callback=on_prog,
        runner=runner,
    )

    assert len(progress_ticks) == 10
    assert progress_ticks[-1][0] == 10


def test_13_final_report_generation(tmp_path):
    """13. Final report dict contains all required summary and category fields."""
    runner = MockDynamicStudentRunner(mode="correct")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    report = execute_student_project_audit(
        project_id="rep_p",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=10,
        seed=42,
        runner=runner,
    )

    report_dict = report.to_dict()
    assert "summary" in report_dict
    assert "category_statistics" in report_dict
    assert "failures" in report_dict
    assert report_dict["summary"]["verified_count"] == 10


def test_14_project_execution_failure_handling(tmp_path):
    """14. Execution error in runner throws exception and is recorded."""
    runner = MockDynamicStudentRunner(mode="crash")
    analysis = ProjectAnalysis(language="python", entry_point="main.py")

    report = execute_student_project_audit(
        project_id="fail_p",
        project_dir=tmp_path,
        analysis=analysis,
        test_count=5,
        seed=42,
        runner=runner,
    )

    assert report.execution_error_count == 5


def test_15_api_run_project_audit_isolation():
    """15. API run-project-audit launches and can be queried via /status/{id} and /{id}."""
    zip_bytes = create_zip_bytes({
        "main.py": """
import sys, json
# Return dummy DFA
print(json.dumps({
    "type": "DFA",
    "states": ["q0"],
    "alphabet": ["0", "1"],
    "start_state": "q0",
    "accepting_states": ["q0"],
    "transitions": [
        {"from_state": "q0", "symbol": "0", "to_state": "q0"},
        {"from_state": "q0", "symbol": "1", "to_state": "q0"}
    ]
}))
""",
    })

    upload_res = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("project.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 200
    project_id = upload_res.json()["project_id"]

    run_req = {
        "project_id": project_id,
        "analysis": {
            "language": "python",
            "entry_point": "main.py",
            "relevant_files": ["main.py"],
            "input_format": "json",
            "output_format": "stdout_json",
            "invocation": "python main.py <input.json>",
            "conversion_type": "epsilon_nfa_to_dfa",
            "is_supported_language": True,
            "confidence": 0.95,
            "ambiguities": [],
            "reasoning_summary": "",
        },
        "test_count": 5,
        "seed": 42,
    }

    start_res = client.post("/api/v1/auditor/run-project-audit", json=run_req)
    assert start_res.status_code == 200
    audit_id = start_res.json()["audit_id"]

    # Poll status
    time.sleep(0.5)
    status_res = client.get(f"/api/v1/auditor/status/{audit_id}")
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["audit_id"] == audit_id
    assert data["status"] in {"running", "completed"}

    # Also check GET /{audit_id} alias
    alias_res = client.get(f"/api/v1/auditor/{audit_id}")
    assert alias_res.status_code == 200

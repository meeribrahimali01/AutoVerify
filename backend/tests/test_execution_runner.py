"""Tests for Auditor Step 3: Secure Student Project Execution."""

import io
import json
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ai.models import ProjectAnalysis
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


@pytest.fixture
def sample_enfa_dict():
    return {
        "type": "EpsilonNFA",
        "states": ["q0", "q1", "q2"],
        "alphabet": ["0", "1"],
        "start_state": "q0",
        "accepting_states": ["q2"],
        "transitions": [
            {"from_state": "q0", "symbol": "0", "to_state": "q1"},
            {"from_state": "q1", "symbol": "ε", "to_state": "q2"},
        ],
    }


@pytest.fixture
def valid_dfa_dict():
    return {
        "type": "DFA",
        "states": ["q0", "q1"],
        "alphabet": ["0", "1"],
        "start_state": "q0",
        "accepting_states": ["q1"],
        "transitions": [
            {"from_state": "q0", "symbol": "0", "to_state": "q1"},
            {"from_state": "q0", "symbol": "1", "to_state": "q0"},
            {"from_state": "q1", "symbol": "0", "to_state": "q1"},
            {"from_state": "q1", "symbol": "1", "to_state": "q1"},
        ],
    }


# ============================================================================
# UNIT TESTS FOR RUNNER AND EXECUTION ENDPOINT
# ============================================================================


def test_1_successful_python_project_execution(sample_enfa_dict, valid_dfa_dict, tmp_path):
    """1. End-to-end execution of a real Python script outputting valid DFA JSON."""
    proj_dir = tmp_path / "proj1"
    proj_dir.mkdir()
    script = proj_dir / "main.py"
    script.write_text(f"""
import sys, json
data = json.loads(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].startswith('{{') else None
dfa = {json.dumps(valid_dfa_dict)}
print(json.dumps(dfa))
""", encoding="utf-8")

    analysis = ProjectAnalysis(
        language="python",
        entry_point="main.py",
        input_format="json",
        output_format="stdout_json",
        invocation="python main.py <input.json>",
        conversion_type="epsilon_nfa_to_dfa",
        is_supported_language=True,
        confidence=0.95,
    )

    runner = StudentProgramRunner()
    resp = runner.execute_single_test(
        project_id="test_p1",
        project_dir=proj_dir,
        analysis=analysis,
        test_enfa=sample_enfa_dict,
    )

    assert resp.status == ExecutionStatus.SUCCESS
    assert resp.exit_code == 0
    assert resp.generated_dfa is not None
    assert resp.generated_dfa["type"] == "DFA"
    assert resp.generated_dfa["states"] == ["q0", "q1"]


def test_2_successful_java_project_mock_execution(sample_enfa_dict, valid_dfa_dict, tmp_path):
    """2. Execution of Java project with MockSandbox returning valid DFA."""
    proj_dir = tmp_path / "proj_java"
    proj_dir.mkdir()
    (proj_dir / "Main.java").write_text("public class Main {}", encoding="utf-8")

    mock_sb = MockSandbox(
        canned_result=RawExecutionResult(
            exit_code=0,
            stdout=json.dumps(valid_dfa_dict),
            stderr="",
            execution_time_seconds=0.08,
        )
    )

    analysis = ProjectAnalysis(
        language="java",
        entry_point="Main.java",
        input_format="json",
        output_format="stdout_json",
        invocation="java Main.java <input.json>",
        conversion_type="epsilon_nfa_to_dfa",
        is_supported_language=True,
        confidence=0.9,
    )

    runner = StudentProgramRunner(sandbox=mock_sb)
    resp = runner.execute_single_test(
        project_id="test_java",
        project_dir=proj_dir,
        analysis=analysis,
        test_enfa=sample_enfa_dict,
    )

    assert resp.status == ExecutionStatus.SUCCESS
    assert resp.generated_dfa["states"] == ["q0", "q1"]


def test_3_successful_cpp_project_mock_execution(sample_enfa_dict, valid_dfa_dict, tmp_path):
    """3. Execution of C++ project with MockSandbox returning valid DFA."""
    proj_dir = tmp_path / "proj_cpp"
    proj_dir.mkdir()
    (proj_dir / "converter.cpp").write_text("int main() {}", encoding="utf-8")

    mock_sb = MockSandbox(
        canned_result=RawExecutionResult(
            exit_code=0,
            stdout=f"Log: starting conversion...\n{json.dumps(valid_dfa_dict)}\nLog: complete.",
            stderr="",
            execution_time_seconds=0.04,
        )
    )

    analysis = ProjectAnalysis(
        language="cpp",
        entry_point="converter",
        input_format="json",
        output_format="stdout_json",
        invocation="./converter <input.json>",
        conversion_type="epsilon_nfa_to_dfa",
        is_supported_language=True,
        confidence=0.9,
    )

    runner = StudentProgramRunner(sandbox=mock_sb)
    resp = runner.execute_single_test(
        project_id="test_cpp",
        project_dir=proj_dir,
        analysis=analysis,
        test_enfa=sample_enfa_dict,
    )

    assert resp.status == ExecutionStatus.SUCCESS
    assert resp.generated_dfa is not None


def test_4_execution_timeout(sample_enfa_dict, tmp_path):
    """4. Program that times out triggers TIMEOUT status."""
    proj_dir = tmp_path / "proj_timeout"
    proj_dir.mkdir()
    (proj_dir / "main.py").write_text("import time; time.sleep(10)", encoding="utf-8")

    analysis = ProjectAnalysis(
        language="python",
        entry_point="main.py",
        input_format="json",
        output_format="stdout_json",
    )

    runner = StudentProgramRunner(timeout_seconds=0.5)
    resp = runner.execute_single_test(
        project_id="test_timeout",
        project_dir=proj_dir,
        analysis=analysis,
        test_enfa=sample_enfa_dict,
    )

    assert resp.status == ExecutionStatus.TIMEOUT
    assert "time limit" in resp.error_message.lower() or "timed out" in resp.error_message.lower()


def test_5_execution_crash_non_zero_exit(sample_enfa_dict, tmp_path):
    """5. Program throwing runtime error triggers CRASH status."""
    proj_dir = tmp_path / "proj_crash"
    proj_dir.mkdir()
    (proj_dir / "main.py").write_text("raise RuntimeError('Fatal syntax/algorithm crash!')", encoding="utf-8")

    analysis = ProjectAnalysis(
        language="python",
        entry_point="main.py",
        input_format="json",
        output_format="stdout_json",
    )

    runner = StudentProgramRunner()
    resp = runner.execute_single_test(
        project_id="test_crash",
        project_dir=proj_dir,
        analysis=analysis,
        test_enfa=sample_enfa_dict,
    )

    assert resp.status == ExecutionStatus.CRASH
    assert resp.exit_code != 0
    assert "Fatal syntax/algorithm crash" in resp.stderr or "RuntimeError" in resp.stderr


def test_6_malformed_output_dfa(sample_enfa_dict, tmp_path):
    """6. Output is not valid JSON or violates DFA definition (e.g. missing transitions) -> INVALID_OUTPUT."""
    proj_dir = tmp_path / "proj_invalid"
    proj_dir.mkdir()
    (proj_dir / "main.py").write_text("print('NOT A JSON AT ALL')", encoding="utf-8")

    analysis = ProjectAnalysis(
        language="python",
        entry_point="main.py",
        input_format="json",
        output_format="stdout_json",
    )

    runner = StudentProgramRunner()
    resp = runner.execute_single_test(
        project_id="test_inv",
        project_dir=proj_dir,
        analysis=analysis,
        test_enfa=sample_enfa_dict,
    )

    assert resp.status == ExecutionStatus.INVALID_OUTPUT
    assert resp.generated_dfa is None


def test_7_missing_entry_point(sample_enfa_dict, tmp_path):
    """7. Missing entry point returns NEEDS_CONFIGURATION."""
    proj_dir = tmp_path / "proj_no_entry"
    proj_dir.mkdir()

    analysis = ProjectAnalysis(
        language="python",
        entry_point=None,
    )

    runner = StudentProgramRunner()
    resp = runner.execute_single_test(
        project_id="test_no_entry",
        project_dir=proj_dir,
        analysis=analysis,
        test_enfa=sample_enfa_dict,
    )

    assert resp.status == ExecutionStatus.NEEDS_CONFIGURATION


def test_8_unsupported_language(sample_enfa_dict, tmp_path):
    """8. Unsupported language returns NEEDS_CONFIGURATION."""
    proj_dir = tmp_path / "proj_haskell"
    proj_dir.mkdir()

    analysis = ProjectAnalysis(
        language="haskell",
        entry_point="Main.hs",
        is_supported_language=False,
    )

    runner = StudentProgramRunner()
    resp = runner.execute_single_test(
        project_id="test_hs",
        project_dir=proj_dir,
        analysis=analysis,
        test_enfa=sample_enfa_dict,
    )

    assert resp.status == ExecutionStatus.NEEDS_CONFIGURATION
    assert "not yet supported" in resp.error_message.lower()


def test_9_oversized_output_is_truncated(sample_enfa_dict, tmp_path):
    """9. Output larger than limit is safely truncated without crashing."""
    proj_dir = tmp_path / "proj_spam"
    proj_dir.mkdir()
    (proj_dir / "main.py").write_text("print('A' * 2_000_000)", encoding="utf-8")

    analysis = ProjectAnalysis(
        language="python",
        entry_point="main.py",
        input_format="json",
        output_format="stdout_json",
    )

    runner = StudentProgramRunner()
    resp = runner.execute_single_test(
        project_id="test_spam",
        project_dir=proj_dir,
        analysis=analysis,
        test_enfa=sample_enfa_dict,
    )

    assert resp.status == ExecutionStatus.INVALID_OUTPUT
    assert len(resp.stdout.encode("utf-8")) <= 1024 * 1024 + 100


def test_10_sandbox_error_non_existent_project(sample_enfa_dict, tmp_path):
    """10. Non-existent project path returns SANDBOX_ERROR."""
    analysis = ProjectAnalysis(
        language="python",
        entry_point="main.py",
    )

    runner = StudentProgramRunner()
    resp = runner.execute_single_test(
        project_id="non_existent",
        project_dir=tmp_path / "does_not_exist",
        analysis=analysis,
        test_enfa=sample_enfa_dict,
    )

    assert resp.status == ExecutionStatus.SANDBOX_ERROR


def test_11_api_execute_test_endpoint_end_to_end(sample_enfa_dict, valid_dfa_dict):
    """11. Test the full /api/v1/auditor/execute-test HTTP endpoint."""
    zip_bytes = create_zip_bytes({
        "main.py": f"""
import sys, json
dfa = {json.dumps(valid_dfa_dict)}
print(json.dumps(dfa))
""",
    })

    upload_res = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("p.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 200
    project_id = upload_res.json()["project_id"]

    exec_req = {
        "project_id": project_id,
        "analysis": {
            "language": "python",
            "entry_point": "main.py",
            "input_format": "json",
            "output_format": "stdout_json",
            "invocation": "python main.py <input.json>",
            "conversion_type": "epsilon_nfa_to_dfa",
            "is_supported_language": True,
            "confidence": 0.95,
        },
        "test_case": sample_enfa_dict,
    }

    res = client.post("/api/v1/auditor/execute-test", json=exec_req)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["generated_dfa"] is not None
    assert data["generated_dfa"]["type"] == "DFA"
    assert data["execution_time_ms"] >= 0.0

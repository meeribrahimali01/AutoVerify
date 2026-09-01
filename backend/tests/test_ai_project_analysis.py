"""Tests for Auditor Step 2: AI-Assisted Project Analysis."""

import io
import json
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ai.models import ProjectAnalysis
from app.ai.provider import MockAIProvider, set_ai_provider

client = TestClient(app)


def create_zip_bytes(files: dict[str, str]) -> bytes:
    """Helper to create an in-memory zip file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(path, content.encode("utf-8"))
    return buf.getvalue()


@pytest.fixture(autouse=True)
def reset_provider():
    """Ensure active provider is reset after each test."""
    yield
    set_ai_provider(None)


# ============================================================================
# TEST CASES
# ============================================================================


def test_1_simple_python_cli_converter():
    """1. Simple Python CLI converter analysis."""
    zip_bytes = create_zip_bytes({
        "main.py": """
import sys, json

def convert(enfa_dict):
    # conversion code
    return {"type": "DFA", "states": ["q0"], "alphabet": ["0", "1"], "start_state": "q0", "accepting_states": [], "transitions": []}

if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        data = json.load(f)
    res = convert(data)
    print(json.dumps(res))
""",
    })

    upload_res = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("project.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 200
    project_id = upload_res.json()["project_id"]

    mock_analysis = {
        "language": "python",
        "entry_point": "main.py",
        "relevant_files": ["main.py"],
        "converter_file": "main.py",
        "converter_function": "convert",
        "input_format": "json",
        "output_format": "stdout_json",
        "invocation": "python main.py <input.json>",
        "conversion_type": "epsilon_nfa_to_dfa",
        "is_supported_language": True,
        "confidence": 0.95,
        "ambiguities": [],
        "reasoning_summary": "CLI script reading JSON from file argument and printing DFA JSON to stdout.",
    }
    set_ai_provider(MockAIProvider(canned_response=mock_analysis))

    analysis_res = client.post(
        "/api/v1/auditor/analyze-project",
        json={"project_id": project_id},
    )
    assert analysis_res.status_code == 200
    data = analysis_res.json()
    assert data["status"] == "SUCCESS"
    assert data["analysis"]["language"] == "python"
    assert data["analysis"]["entry_point"] == "main.py"
    assert data["analysis"]["confidence"] == 0.95


def test_2_python_converter_with_function():
    """2. Python project structured as module with dedicated converter function."""
    zip_bytes = create_zip_bytes({
        "converter.py": "def epsilon_nfa_to_dfa(enfa): return {}",
        "models.py": "class Automaton: pass",
        "run.py": "from converter import epsilon_nfa_to_dfa",
    })
    upload_res = client.post("/api/v1/auditor/upload-project", files={"file": ("p.zip", zip_bytes, "application/zip")})
    project_id = upload_res.json()["project_id"]

    set_ai_provider(MockAIProvider({
        "language": "python",
        "entry_point": "run.py",
        "relevant_files": ["converter.py", "run.py"],
        "converter_file": "converter.py",
        "converter_function": "epsilon_nfa_to_dfa",
        "input_format": "json",
        "output_format": "json",
        "invocation": "python run.py <input.json>",
        "conversion_type": "epsilon_nfa_to_dfa",
        "is_supported_language": True,
        "confidence": 0.92,
        "ambiguities": [],
        "reasoning_summary": "Dedicated conversion function in converter.py called from run.py.",
    }))

    res = client.post("/api/v1/auditor/analyze-project", json={"project_id": project_id})
    assert res.status_code == 200
    assert res.json()["analysis"]["converter_function"] == "epsilon_nfa_to_dfa"


def test_3_python_project_with_nested_directories():
    """3. Python project with nested source directory structure."""
    zip_bytes = create_zip_bytes({
        "src/main.py": "import sys; print('run')",
        "src/core/subset.py": "class SubsetEngine: pass",
        "requirements.txt": "pydantic",
    })
    upload_res = client.post("/api/v1/auditor/upload-project", files={"file": ("nested.zip", zip_bytes, "application/zip")})
    project_id = upload_res.json()["project_id"]

    set_ai_provider(MockAIProvider({
        "language": "python",
        "entry_point": "src/main.py",
        "relevant_files": ["src/main.py", "src/core/subset.py"],
        "converter_file": "src/core/subset.py",
        "converter_class": "SubsetEngine",
        "input_format": "json",
        "output_format": "stdout_json",
        "invocation": "python src/main.py <input.json>",
        "conversion_type": "epsilon_nfa_to_dfa",
        "is_supported_language": True,
        "confidence": 0.88,
        "ambiguities": [],
        "reasoning_summary": "Modular project located in src directory with subset.py engine.",
    }))

    res = client.post("/api/v1/auditor/analyze-project", json={"project_id": project_id})
    assert res.status_code == 200
    assert res.json()["analysis"]["entry_point"] == "src/main.py"


def test_4_project_with_misleading_filenames():
    """4. Project with misleading filenames (e.g. test.py, fake.py, real_entry.py)."""
    zip_bytes = create_zip_bytes({
        "test.py": "# Unit test runner",
        "fake.py": "# Deprecated code",
        "app.py": "if __name__ == '__main__': pass",
    })
    upload_res = client.post("/api/v1/auditor/upload-project", files={"file": ("p.zip", zip_bytes, "application/zip")})
    project_id = upload_res.json()["project_id"]

    set_ai_provider(MockAIProvider({
        "language": "python",
        "entry_point": "app.py",
        "relevant_files": ["app.py"],
        "input_format": "json",
        "output_format": "json",
        "invocation": "python app.py <input.json>",
        "conversion_type": "epsilon_nfa_to_dfa",
        "is_supported_language": True,
        "confidence": 0.82,
        "ambiguities": ["test.py could be alternative entry point"],
        "reasoning_summary": "app.py is the primary entry point, while test.py is a test runner.",
    }))

    res = client.post("/api/v1/auditor/analyze-project", json={"project_id": project_id})
    assert res.status_code == 200
    assert res.json()["analysis"]["entry_point"] == "app.py"


def test_5_multiple_possible_entry_points_triggers_low_confidence():
    """5. Multiple ambiguous entry points triggers LOW_CONFIDENCE status."""
    zip_bytes = create_zip_bytes({
        "cli.py": "if __name__ == '__main__': pass",
        "main.py": "if __name__ == '__main__': pass",
        "converter_standalone.py": "if __name__ == '__main__': pass",
    })
    upload_res = client.post("/api/v1/auditor/upload-project", files={"file": ("p.zip", zip_bytes, "application/zip")})
    project_id = upload_res.json()["project_id"]

    set_ai_provider(MockAIProvider({
        "language": "python",
        "entry_point": "main.py",
        "relevant_files": ["cli.py", "main.py", "converter_standalone.py"],
        "input_format": "json",
        "output_format": "json",
        "invocation": "python main.py <input.json>",
        "conversion_type": "epsilon_nfa_to_dfa",
        "is_supported_language": True,
        "confidence": 0.48,
        "ambiguities": ["cli.py", "converter_standalone.py"],
        "reasoning_summary": "Multiple standalone CLI scripts detected with identical main blocks.",
    }))

    res = client.post("/api/v1/auditor/analyze-project", json={"project_id": project_id})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "LOW_CONFIDENCE"
    assert len(data["analysis"]["ambiguities"]) > 0


def test_6_java_project():
    """6. Java project analysis identification."""
    zip_bytes = create_zip_bytes({
        "src/Main.java": "public class Main { public static void main(String[] args) {} }",
        "src/SubsetConverter.java": "public class SubsetConverter {}",
        "pom.xml": "<project></project>",
    })
    upload_res = client.post("/api/v1/auditor/upload-project", files={"file": ("java.zip", zip_bytes, "application/zip")})
    project_id = upload_res.json()["project_id"]

    set_ai_provider(MockAIProvider({
        "language": "java",
        "entry_point": "src/Main.java",
        "relevant_files": ["src/Main.java", "src/SubsetConverter.java"],
        "converter_class": "SubsetConverter",
        "input_format": "json",
        "output_format": "stdout_json",
        "invocation": "java -cp bin Main <input.json>",
        "conversion_type": "epsilon_nfa_to_dfa",
        "is_supported_language": True,
        "confidence": 0.91,
        "ambiguities": [],
        "reasoning_summary": "Standard Java project with Main.java containing main method.",
    }))

    res = client.post("/api/v1/auditor/analyze-project", json={"project_id": project_id})
    assert res.status_code == 200
    assert res.json()["analysis"]["language"] == "java"
    assert res.json()["analysis"]["is_supported_language"] is True


def test_7_cpp_project():
    """7. C++ project analysis identification."""
    zip_bytes = create_zip_bytes({
        "main.cpp": "int main(int argc, char** argv) { return 0; }",
        "converter.h": "class AutomataConverter {};",
        "Makefile": "all: g++ main.cpp -o converter",
    })
    upload_res = client.post("/api/v1/auditor/upload-project", files={"file": ("cpp.zip", zip_bytes, "application/zip")})
    project_id = upload_res.json()["project_id"]

    set_ai_provider(MockAIProvider({
        "language": "cpp",
        "entry_point": "main.cpp",
        "relevant_files": ["main.cpp", "converter.h"],
        "converter_class": "AutomataConverter",
        "input_format": "json",
        "output_format": "stdout_json",
        "invocation": "./converter <input.json>",
        "conversion_type": "epsilon_nfa_to_dfa",
        "is_supported_language": True,
        "confidence": 0.93,
        "ambiguities": [],
        "reasoning_summary": "C++ project with Makefile building converter executable from main.cpp.",
    }))

    res = client.post("/api/v1/auditor/analyze-project", json={"project_id": project_id})
    assert res.status_code == 200
    assert res.json()["analysis"]["language"] == "cpp"


def test_8_project_with_readme_explaining_usage():
    """8. Project with README explaining specific CLI invocation."""
    zip_bytes = create_zip_bytes({
        "README.md": "Run using: python transform.py --spec input.json --out out.json",
        "transform.py": "import argparse",
    })
    upload_res = client.post("/api/v1/auditor/upload-project", files={"file": ("readme.zip", zip_bytes, "application/zip")})
    project_id = upload_res.json()["project_id"]

    set_ai_provider(MockAIProvider({
        "language": "python",
        "entry_point": "transform.py",
        "relevant_files": ["README.md", "transform.py"],
        "input_format": "json",
        "output_format": "json",
        "invocation": "python transform.py --spec <input.json>",
        "conversion_type": "epsilon_nfa_to_dfa",
        "is_supported_language": True,
        "confidence": 0.96,
        "ambiguities": [],
        "reasoning_summary": "Explicit invocation instructions identified in README.md.",
    }))

    res = client.post("/api/v1/auditor/analyze-project", json={"project_id": project_id})
    assert res.status_code == 200
    assert "transform.py" in res.json()["analysis"]["invocation"]


def test_9_project_with_no_obvious_converter():
    """9. Project with no obvious converter returns low confidence or error."""
    zip_bytes = create_zip_bytes({
        "random.txt": "Not an automata project",
    })
    upload_res = client.post("/api/v1/auditor/upload-project", files={"file": ("empty.zip", zip_bytes, "application/zip")})
    project_id = upload_res.json()["project_id"]

    set_ai_provider(MockAIProvider({
        "language": "unknown",
        "entry_point": None,
        "relevant_files": [],
        "input_format": "unknown",
        "output_format": "unknown",
        "conversion_type": "unknown",
        "is_supported_language": False,
        "confidence": 0.1,
        "ambiguities": ["No recognized automata converter logic found"],
        "reasoning_summary": "Archive contains no source files implementing automata subset construction.",
    }))

    res = client.post("/api/v1/auditor/analyze-project", json={"project_id": project_id})
    assert res.status_code == 200
    assert res.json()["status"] == "LOW_CONFIDENCE"


def test_10_ai_unavailable_missing_api_key():
    """10. Unconfigured AI provider returns AI_NOT_CONFIGURED status gracefully without crashing."""
    zip_bytes = create_zip_bytes({"main.py": "print(1)"})
    upload_res = client.post("/api/v1/auditor/upload-project", files={"file": ("p.zip", zip_bytes, "application/zip")})
    project_id = upload_res.json()["project_id"]

    set_ai_provider(MockAIProvider(configured=False))

    res = client.post("/api/v1/auditor/analyze-project", json={"project_id": project_id})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "AI_NOT_CONFIGURED"
    assert "API key" in data["message"] or "not configured" in data["message"].lower()


def test_11_malformed_ai_response_handled_safely():
    """11. Malformed or invalid AI response is caught and reported as ERROR."""
    zip_bytes = create_zip_bytes({"main.py": "print(1)"})
    upload_res = client.post("/api/v1/auditor/upload-project", files={"file": ("p.zip", zip_bytes, "application/zip")})
    project_id = upload_res.json()["project_id"]

    # Provider returning non-dict or invalid confidence
    set_ai_provider(MockAIProvider(canned_response={"confidence": "invalid_not_a_float"}))

    res = client.post("/api/v1/auditor/analyze-project", json={"project_id": project_id})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ERROR"
    assert "Malformed" in data["error"] or "failed" in data["error"].lower()


def test_12_low_confidence_analysis():
    """12. Low confidence (< 0.65) sets status to LOW_CONFIDENCE."""
    zip_bytes = create_zip_bytes({"script.py": "x = 1"})
    upload_res = client.post("/api/v1/auditor/upload-project", files={"file": ("p.zip", zip_bytes, "application/zip")})
    project_id = upload_res.json()["project_id"]

    set_ai_provider(MockAIProvider({
        "language": "python",
        "entry_point": "script.py",
        "confidence": 0.45,
        "ambiguities": ["Uncertain whether script.py performs subset construction"],
    }))

    res = client.post("/api/v1/auditor/analyze-project", json={"project_id": project_id})
    assert res.status_code == 200
    assert res.json()["status"] == "LOW_CONFIDENCE"

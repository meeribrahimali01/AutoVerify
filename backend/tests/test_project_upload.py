"""Tests for Auditor ZIP project upload, secure extraction, and passive inspection."""

import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def create_zip_bytes(files: dict[str, str | bytes]) -> bytes:
    """Helper to create an in-memory zip file from a dictionary of path -> content."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            if isinstance(content, str):
                zf.writestr(path, content.encode("utf-8"))
            else:
                zf.writestr(path, content)
    return buf.getvalue()


# ============================================================================
# TEST CASES
# ============================================================================


def test_1_valid_zip_upload():
    """1. Valid ZIP upload returns 200 and expected metadata."""
    zip_data = create_zip_bytes({
        "README.md": "# Student Project",
        "converter.py": "def convert(enfa): pass\n",
    })

    response = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("student_submission.zip", zip_data, "application/zip")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "student_submission.zip"
    assert data["file_count"] == 2
    assert "python" in data["languages"]
    assert "converter.py" in data["likely_source_files"]


def test_2_zip_containing_python_files():
    """2. ZIP containing Python files correctly identifies .py and python language."""
    zip_data = create_zip_bytes({
        "main.py": "print('hello')",
        "submodule/utils.py": "def helper(): pass",
    })

    response = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("py_project.zip", zip_data, "application/zip")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["languages"] == ["python"]
    assert sorted(data["likely_source_files"]) == ["main.py", "submodule/utils.py"]


def test_3_zip_containing_multiple_languages():
    """3. ZIP containing multiple languages identifies all distinct languages."""
    zip_data = create_zip_bytes({
        "src/App.java": "public class App {}",
        "src/native.cpp": "int main() { return 0; }",
        "scripts/run.py": "import sys",
        "web/index.ts": "const x: number = 10;",
        "docs/spec.txt": "Automata specification",
    })

    response = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("polyglot.zip", zip_data, "application/zip")},
    )
    assert response.status_code == 200
    data = response.json()
    assert sorted(data["languages"]) == ["cpp", "java", "python", "typescript"]
    assert len(data["likely_source_files"]) == 4
    assert "docs/spec.txt" not in data["likely_source_files"]


def test_4_empty_zip():
    """4. Empty ZIP file returns 400."""
    response = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("empty.zip", b"", "application/zip")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_5_invalid_non_zip_upload():
    """5. Invalid non-ZIP file or non-.zip extension returns 400."""
    # Text file named .zip
    response = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("fake.zip", b"This is plain text, not a zip archive", "application/zip")},
    )
    assert response.status_code == 400
    assert "invalid zip" in response.json()["detail"].lower()

    # File without .zip extension
    response_ext = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("project.tar.gz", b"binary", "application/gzip")},
    )
    assert response_ext.status_code == 400
    assert "only .zip" in response_ext.json()["detail"].lower()


def test_6_zip_exceeding_size_limit():
    """6. ZIP exceeding 50 MB size limit returns 400."""
    # We can test the inspector boundary check directly
    from app.audit.inspector import MAX_ZIP_SIZE, SizeLimitExceededError, inspect_and_extract_project_zip

    oversized_bytes = b"0" * (MAX_ZIP_SIZE + 10)
    with pytest.raises(SizeLimitExceededError):
        inspect_and_extract_project_zip(oversized_bytes, "oversized.zip")


def test_7_path_traversal_zip_entry():
    """7. Path traversal entry (e.g. ../evil.py) is rejected with 400 security error."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../evil.py", b"import os; os.system('echo hacked')")
        zf.writestr("safe.py", b"print('safe')")

    response = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("traversal.zip", buf.getvalue(), "application/zip")},
    )
    assert response.status_code == 400
    assert "security error" in response.json()["detail"].lower() or "traversal" in response.json()["detail"].lower()


def test_8_absolute_path_zip_entry():
    """8. Absolute path entries (/evil.py or C:\\evil.py) are rejected."""
    # Unix absolute path
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("/root/evil.py", b"print('root')")

    response = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("abs_unix.zip", buf.getvalue(), "application/zip")},
    )
    assert response.status_code == 400
    assert "security error" in response.json()["detail"].lower()

    # Windows absolute drive path
    buf_win = io.BytesIO()
    with zipfile.ZipFile(buf_win, "w") as zf:
        zf.writestr("C:/Windows/evil.py", b"print('win')")

    response_win = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("abs_win.zip", buf_win.getvalue(), "application/zip")},
    )
    assert response_win.status_code == 400


def test_9_excessive_extracted_size(monkeypatch):
    """9. Zip bomb / excessive uncompressed size (> 200 MB) is rejected."""
    from app.audit.inspector import MAX_EXTRACTED_SIZE, SizeLimitExceededError, inspect_and_extract_project_zip

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.bin", b"hello")

    # Mock infolist entry to declare uncompressed size > MAX_EXTRACTED_SIZE
    fake_info = zipfile.ZipInfo("large_data.bin")
    fake_info.file_size = MAX_EXTRACTED_SIZE + 1024
    monkeypatch.setattr(zipfile.ZipFile, "infolist", lambda self: [fake_info])

    with pytest.raises(SizeLimitExceededError):
        inspect_and_extract_project_zip(buf.getvalue(), "zipbomb.zip")


def test_10_excessive_file_count():
    """10. ZIP with > 10,000 files is rejected."""
    from app.audit.inspector import MAX_FILE_COUNT, FileCountLimitError, inspect_and_extract_project_zip

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(MAX_FILE_COUNT + 5):
            zf.writestr(f"file_{i}.txt", b"x")

    with pytest.raises(FileCountLimitError):
        inspect_and_extract_project_zip(buf.getvalue(), "many_files.zip")


def test_11_nested_project_directory():
    """11. Nested project directory (single wrapper folder) is normalized."""
    zip_data = create_zip_bytes({
        "my_project/src/main.py": "def run(): pass",
        "my_project/src/converter.py": "def convert(): pass",
        "my_project/README.md": "Documentation",
    })

    response = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("nested.zip", zip_data, "application/zip")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["file_count"] == 3
    # Effective root was unwrapped
    paths = [f["path"] for f in data["files"]]
    assert "src/main.py" in paths
    assert "src/converter.py" in paths
    assert "README.md" in paths


def test_12_normal_project_root():
    """12. Normal project root without wrapper folder is preserved."""
    zip_data = create_zip_bytes({
        "main.py": "print(1)",
        "converter.py": "print(2)",
    })

    response = client.post(
        "/api/v1/auditor/upload-project",
        files={"file": ("normal.zip", zip_data, "application/zip")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["file_count"] == 2
    paths = [f["path"] for f in data["files"]]
    assert paths == ["converter.py", "main.py"]

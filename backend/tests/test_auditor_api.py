"""Tests for Auditor API endpoints."""

import time
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_auditor_health():
    """Health check for Auditor API."""
    response = client.get("/api/v1/auditor/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_demo_converters():
    """List available demo converters."""
    response = client.get("/api/v1/auditor/converters")
    assert response.status_code == 200
    converters = response.json()
    assert len(converters) >= 2
    ids = [c["id"] for c in converters]
    assert "correct" in ids
    assert "buggy" in ids


def test_run_audit_correct_converter():
    """Run audit with Correct Reference Converter and assert 100% VCR."""
    req = {
        "converter": "correct",
        "test_count": 15,
        "seed": 42,
    }

    # Trigger audit run
    response = client.post("/api/v1/auditor/run", json=req)
    assert response.status_code == 200
    data = response.json()
    audit_id = data["audit_id"]

    # Poll until completed
    max_wait = 10
    start = time.time()
    report = None
    while time.time() - start < max_wait:
        res = client.get(f"/api/v1/auditor/{audit_id}")
        assert res.status_code == 200
        poll_data = res.json()
        if poll_data["status"] == "completed":
            report = poll_data["report"]
            break
        time.sleep(0.1)

    assert report is not None
    assert report["summary"]["total_tests"] == 15
    assert report["summary"]["verified_count"] == 15
    assert report["summary"]["failed_count"] == 0
    assert report["summary"]["verified_conversion_rate"] == 1.0
    assert len(report["failures"]) == 0


def test_run_audit_buggy_converter():
    """Run audit with Buggy Demo Converter and assert failure detection + counterexamples."""
    req = {
        "converter": "buggy",
        "test_count": 25,
        "seed": 99,
    }

    response = client.post("/api/v1/auditor/run", json=req)
    assert response.status_code == 200
    audit_id = response.json()["audit_id"]

    max_wait = 10
    start = time.time()
    report = None
    while time.time() - start < max_wait:
        res = client.get(f"/api/v1/auditor/{audit_id}")
        assert res.status_code == 200
        poll_data = res.json()
        if poll_data["status"] == "completed":
            report = poll_data["report"]
            break
        time.sleep(0.1)

    assert report is not None
    assert report["summary"]["failed_count"] > 0
    assert report["summary"]["verified_conversion_rate"] < 1.0

    # Ensure counterexamples exist for every failure
    failures = report["failures"]
    assert len(failures) == report["summary"]["failed_count"]
    for fail in failures:
        assert fail["status"] == "NOT_EQUIVALENT"
        assert fail["counterexample"] is not None
        assert "expected_acceptance" in fail
        assert "generated_acceptance" in fail
        assert fail["expected_acceptance"] != fail["generated_acceptance"]


def test_run_audit_category_filter():
    """Run audit filtered to specific categories."""
    req = {
        "converter": "correct",
        "test_count": 20,
        "seed": 77,
        "categories": ["A_BASIC"],
    }

    response = client.post("/api/v1/auditor/run", json=req)
    assert response.status_code == 200
    audit_id = response.json()["audit_id"]

    # Poll until completed
    max_wait = 10
    start = time.time()
    report = None
    while time.time() - start < max_wait:
        res = client.get(f"/api/v1/auditor/{audit_id}")
        poll_data = res.json()
        if poll_data["status"] == "completed":
            report = poll_data["report"]
            break
        time.sleep(0.1)

    assert report is not None
    for r in report["results"]:
        assert r["category"] == "A_BASIC"


def test_invalid_audit_id():
    """Querying non-existent audit ID returns 404."""
    response = client.get("/api/v1/auditor/audit_nonexistent_12345")
    assert response.status_code == 404


def test_invalid_test_count_validation():
    """Test count out of bounds rejected by schema."""
    response = client.post("/api/v1/auditor/run", json={"test_count": 0})
    assert response.status_code == 422

    response = client.post("/api/v1/auditor/run", json={"test_count": 2000})
    assert response.status_code == 422

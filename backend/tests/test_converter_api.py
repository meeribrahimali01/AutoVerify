"""Tests for Converter API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_converter_health():
    """Verify converter health check endpoint."""
    response = client.get("/api/v1/converter/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "converter"


def test_convert_simple_epsilon_nfa():
    """Convert simple ε-NFA: q0 --ε--> q1 --a--> q2."""
    payload = {
        "type": "EPSILON_NFA",
        "states": ["q0", "q1", "q2"],
        "alphabet": ["a"],
        "start_state": "q0",
        "accepting_states": ["q2"],
        "transitions": [
            {"from_state": "q0", "symbol": "ε", "to_state": "q1"},
            {"from_state": "q1", "symbol": "a", "to_state": "q2"},
        ],
    }

    response = client.post("/api/v1/converter/epsilon-nfa-to-dfa", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["dfa"] is not None
    assert data["dfa"]["type"] == "DFA"
    assert data["statistics"]["input_states_count"] == 3
    assert data["statistics"]["input_epsilon_transitions_count"] == 1
    assert data["trace"] is not None
    assert "steps" in data["trace"]
    assert data["verification"]["equivalent"] is True


def test_convert_epsilon_chains():
    """Convert ε-NFA with an epsilon chain: q0 --ε--> q1 --ε--> q2 --a--> q3."""
    payload = {
        "type": "EPSILON_NFA",
        "states": ["q0", "q1", "q2", "q3"],
        "alphabet": ["a", "b"],
        "start_state": "q0",
        "accepting_states": ["q3"],
        "transitions": [
            {"from_state": "q0", "symbol": "ε", "to_state": "q1"},
            {"from_state": "q1", "symbol": "ε", "to_state": "q2"},
            {"from_state": "q2", "symbol": "a", "to_state": "q3"},
            {"from_state": "q3", "symbol": "b", "to_state": "q3"},
        ],
    }

    response = client.post("/api/v1/converter/epsilon-nfa-to-dfa", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["dfa"] is not None
    assert data["statistics"]["input_epsilon_transitions_count"] == 2
    assert data["verification"]["equivalent"] is True


def test_convert_epsilon_cycles():
    """Convert ε-NFA with epsilon cycles: q0 <---> q1."""
    payload = {
        "type": "EPSILON_NFA",
        "states": ["q0", "q1", "q2"],
        "alphabet": ["0", "1"],
        "start_state": "q0",
        "accepting_states": ["q2"],
        "transitions": [
            {"from_state": "q0", "symbol": "ε", "to_state": "q1"},
            {"from_state": "q1", "symbol": "ε", "to_state": "q0"},
            {"from_state": "q1", "symbol": "0", "to_state": "q2"},
        ],
    }

    response = client.post("/api/v1/converter/epsilon-nfa-to-dfa", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["verification"]["equivalent"] is True


def test_convert_multiple_accepting_states():
    """Convert ε-NFA with multiple accepting states."""
    payload = {
        "type": "EPSILON_NFA",
        "states": ["q0", "q1", "q2", "q3"],
        "alphabet": ["0", "1"],
        "start_state": "q0",
        "accepting_states": ["q1", "q3"],
        "transitions": [
            {"from_state": "q0", "symbol": "0", "to_state": "q1"},
            {"from_state": "q0", "symbol": "ε", "to_state": "q2"},
            {"from_state": "q2", "symbol": "1", "to_state": "q3"},
        ],
    }

    response = client.post("/api/v1/converter/epsilon-nfa-to-dfa", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["dfa"] is not None
    assert data["statistics"]["dfa_accepting_states_count"] >= 1
    assert data["verification"]["equivalent"] is True


def test_convert_invalid_input():
    """Handle invalid automaton payload gracefully."""
    # Start state not in states list
    payload = {
        "type": "EPSILON_NFA",
        "states": ["q0", "q1"],
        "alphabet": ["0"],
        "start_state": "q_invalid",
        "accepting_states": ["q1"],
        "transitions": [],
    }

    response = client.post("/api/v1/converter/epsilon-nfa-to-dfa", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is False
    assert "validation failed" in data["error"].lower()

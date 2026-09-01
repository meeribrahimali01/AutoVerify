"""Tests for Automata Maker Simulation API endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ============================================================================
# 1 & 2. DFA Tests (Accepted, Rejected, Empty string)
# ============================================================================


def test_simulate_dfa_accepted():
    """DFA: Even number of 0s on input '00' -> accepted = True."""
    payload = {
        "automaton": {
            "type": "DFA",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "accepting_states": ["q0"],
            "transitions": [
                {"from_state": "q0", "symbol": "0", "to_state": "q1"},
                {"from_state": "q0", "symbol": "1", "to_state": "q0"},
                {"from_state": "q1", "symbol": "0", "to_state": "q0"},
                {"from_state": "q1", "symbol": "1", "to_state": "q1"},
            ],
        },
        "input_string": "00",
    }
    response = client.post("/api/v1/maker/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["error"] is None
    assert data["final_states"] == ["q0"]


def test_simulate_dfa_rejected():
    """DFA: Even number of 0s on input '0' -> accepted = False."""
    payload = {
        "automaton": {
            "type": "DFA",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "accepting_states": ["q0"],
            "transitions": [
                {"from_state": "q0", "symbol": "0", "to_state": "q1"},
                {"from_state": "q0", "symbol": "1", "to_state": "q0"},
                {"from_state": "q1", "symbol": "0", "to_state": "q0"},
                {"from_state": "q1", "symbol": "1", "to_state": "q1"},
            ],
        },
        "input_string": "0",
    }
    response = client.post("/api/v1/maker/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert data["error"] is None
    assert data["final_states"] == ["q1"]


def test_simulate_dfa_empty_string():
    """DFA: Even number of 0s on empty input '' -> accepted = True (start is accepting)."""
    payload = {
        "automaton": {
            "type": "DFA",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "accepting_states": ["q0"],
            "transitions": [
                {"from_state": "q0", "symbol": "0", "to_state": "q1"},
                {"from_state": "q0", "symbol": "1", "to_state": "q0"},
                {"from_state": "q1", "symbol": "0", "to_state": "q0"},
                {"from_state": "q1", "symbol": "1", "to_state": "q1"},
            ],
        },
        "input_string": "",
    }
    response = client.post("/api/v1/maker/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["final_states"] == ["q0"]


# ============================================================================
# 3 & 4. NFA Tests (Step 4 screenshot case: 101 accepted, 100 rejected)
# ============================================================================


def test_simulate_nfa_101_accepted():
    """NFA: q0 --1--> q1 --0--> q2 --1--> q3 on input '101' -> accepted = True."""
    payload = {
        "automaton": {
            "type": "NFA",
            "states": ["q0", "q1", "q2", "q3"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "accepting_states": ["q3"],
            "transitions": [
                {"from_state": "q0", "symbol": "1", "to_state": "q1"},
                {"from_state": "q1", "symbol": "0", "to_state": "q2"},
                {"from_state": "q2", "symbol": "1", "to_state": "q3"},
            ],
        },
        "input_string": "101",
    }
    response = client.post("/api/v1/maker/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["error"] is None
    assert data["final_states"] == ["q3"]
    assert len(data["steps"]) == 3


def test_simulate_nfa_100_rejected():
    """NFA: q0 --1--> q1 --0--> q2 --1--> q3 on input '100' -> accepted = False."""
    payload = {
        "automaton": {
            "type": "NFA",
            "states": ["q0", "q1", "q2", "q3"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "accepting_states": ["q3"],
            "transitions": [
                {"from_state": "q0", "symbol": "1", "to_state": "q1"},
                {"from_state": "q1", "symbol": "0", "to_state": "q2"},
                {"from_state": "q2", "symbol": "1", "to_state": "q3"},
            ],
        },
        "input_string": "100",
    }
    response = client.post("/api/v1/maker/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert data["error"] is None
    assert data["final_states"] == []


# ============================================================================
# 5 & 6. ε-NFA Tests (Accepted, Rejected, Empty string)
# ============================================================================


def test_simulate_exact_user_enfa_1234():
    """Verify ε-NFA q0 --1--> q1 --2--> q2 --3--> q3 --4--> q4 on input '1234' -> accepted = True."""
    payload = {
        "automaton": {
            "type": "EPSILON_NFA",
            "states": ["q0", "q1", "q2", "q3", "q4"],
            "alphabet": ["0", "1", "2", "3", "4", "6"],
            "start_state": "q0",
            "accepting_states": ["q4"],
            "transitions": [
                {"from_state": "q0", "symbol": "1", "to_state": "q1"},
                {"from_state": "q1", "symbol": "2", "to_state": "q2"},
                {"from_state": "q2", "symbol": "3", "to_state": "q3"},
                {"from_state": "q3", "symbol": "4", "to_state": "q4"},
            ],
        },
        "input_string": "1234",
    }
    response = client.post("/api/v1/maker/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["error"] is None
    assert len(data["steps"]) == 4
    assert data["final_states"] == ["q4"]


def test_simulate_enfa_partial_rejected():
    """ε-NFA on partial input '123' reaches q3 -> accepted = False."""
    payload = {
        "automaton": {
            "type": "EPSILON_NFA",
            "states": ["q0", "q1", "q2", "q3", "q4"],
            "alphabet": ["1", "2", "3", "4"],
            "start_state": "q0",
            "accepting_states": ["q4"],
            "transitions": [
                {"from_state": "q0", "symbol": "1", "to_state": "q1"},
                {"from_state": "q1", "symbol": "2", "to_state": "q2"},
                {"from_state": "q2", "symbol": "3", "to_state": "q3"},
                {"from_state": "q3", "symbol": "4", "to_state": "q4"},
            ],
        },
        "input_string": "123",
    }
    response = client.post("/api/v1/maker/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert data["final_states"] == ["q3"]


def test_simulate_epsilon_transitions():
    """Simulate ε-transitions: q0 --ε--> q1 --a--> q2 --ε--> q3 on input 'a' -> accepted = True."""
    payload = {
        "automaton": {
            "type": "EPSILON_NFA",
            "states": ["q0", "q1", "q2", "q3"],
            "alphabet": ["a"],
            "start_state": "q0",
            "accepting_states": ["q3"],
            "transitions": [
                {"from_state": "q0", "symbol": "ε", "to_state": "q1"},
                {"from_state": "q1", "symbol": "a", "to_state": "q2"},
                {"from_state": "q2", "symbol": "ε", "to_state": "q3"},
            ],
        },
        "input_string": "a",
    }
    response = client.post("/api/v1/maker/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert "q3" in data["final_states"]


def test_simulate_empty_string_epsilon_acceptance():
    """Empty string on ε-NFA with start state reaching accepting state via ε."""
    payload = {
        "automaton": {
            "type": "EPSILON_NFA",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "accepting_states": ["q1"],
            "transitions": [
                {"from_state": "q0", "symbol": "ε", "to_state": "q1"},
            ],
        },
        "input_string": "",
    }
    response = client.post("/api/v1/maker/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert set(data["final_states"]) == {"q0", "q1"}


# ============================================================================
# 7 & 8. Error Handling & Unknown Symbols
# ============================================================================


def test_simulate_symbol_outside_alphabet():
    """Input containing unknown symbol returns clear 200 with error field without 500."""
    payload = {
        "automaton": {
            "type": "EPSILON_NFA",
            "states": ["q0", "q1"],
            "alphabet": ["0", "1"],
            "start_state": "q0",
            "accepting_states": ["q1"],
            "transitions": [
                {"from_state": "q0", "symbol": "0", "to_state": "q1"},
            ],
        },
        "input_string": "0x1",
    }
    response = client.post("/api/v1/maker/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is False
    assert data["error"] is not None
    assert "symbol 'x'" in data["error"]

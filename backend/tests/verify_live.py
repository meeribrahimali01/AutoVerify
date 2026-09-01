import sys
import urllib.request
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def test_endpoint(name, payload):
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/maker/simulate',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            acc = data.get('accepted')
            err = data.get('error')
            fin = data.get('final_states')
            print(f'[{resp.status}] {name} -> accepted: {acc}, error: {err}, final: {fin}')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f'[{e.code}] {name} -> HTTP ERROR: {body}')
    except Exception as e:
        print(f'[ERR] {name} -> {e}')

nfa_payload_101 = {
    'automaton': {
        'type': 'NFA',
        'states': ['q0', 'q1', 'q2', 'q3'],
        'alphabet': ['0', '1'],
        'start_state': 'q0',
        'accepting_states': ['q3'],
        'transitions': [
            {'from_state': 'q0', 'symbol': '1', 'to_state': 'q1'},
            {'from_state': 'q1', 'symbol': '0', 'to_state': 'q2'},
            {'from_state': 'q2', 'symbol': '1', 'to_state': 'q3'}
        ]
    },
    'input_string': '101'
}

nfa_payload_100 = {
    'automaton': {
        'type': 'NFA',
        'states': ['q0', 'q1', 'q2', 'q3'],
        'alphabet': ['0', '1'],
        'start_state': 'q0',
        'accepting_states': ['q3'],
        'transitions': [
            {'from_state': 'q0', 'symbol': '1', 'to_state': 'q1'},
            {'from_state': 'q1', 'symbol': '0', 'to_state': 'q2'},
            {'from_state': 'q2', 'symbol': '1', 'to_state': 'q3'}
        ]
    },
    'input_string': '100'
}

dfa_payload_acc = {
    'automaton': {
        'type': 'DFA',
        'states': ['q0', 'q1'],
        'alphabet': ['0', '1'],
        'start_state': 'q0',
        'accepting_states': ['q0'],
        'transitions': [
            {'from_state': 'q0', 'symbol': '0', 'to_state': 'q1'},
            {'from_state': 'q0', 'symbol': '1', 'to_state': 'q0'},
            {'from_state': 'q1', 'symbol': '0', 'to_state': 'q0'},
            {'from_state': 'q1', 'symbol': '1', 'to_state': 'q1'}
        ]
    },
    'input_string': '00'
}
dfa_payload_rej = {
    'automaton': {
        'type': 'DFA',
        'states': ['q0', 'q1'],
        'alphabet': ['0', '1'],
        'start_state': 'q0',
        'accepting_states': ['q0'],
        'transitions': [
            {'from_state': 'q0', 'symbol': '0', 'to_state': 'q1'},
            {'from_state': 'q0', 'symbol': '1', 'to_state': 'q0'},
            {'from_state': 'q1', 'symbol': '0', 'to_state': 'q0'},
            {'from_state': 'q1', 'symbol': '1', 'to_state': 'q1'}
        ]
    },
    'input_string': '0'
}
dfa_payload_empty = {
    'automaton': {
        'type': 'DFA',
        'states': ['q0', 'q1'],
        'alphabet': ['0', '1'],
        'start_state': 'q0',
        'accepting_states': ['q0'],
        'transitions': [
            {'from_state': 'q0', 'symbol': '0', 'to_state': 'q1'},
            {'from_state': 'q0', 'symbol': '1', 'to_state': 'q0'},
            {'from_state': 'q1', 'symbol': '0', 'to_state': 'q0'},
            {'from_state': 'q1', 'symbol': '1', 'to_state': 'q1'}
        ]
    },
    'input_string': ''
}

enfa_payload_acc = {
    'automaton': {
        'type': 'EPSILON_NFA',
        'states': ['q0', 'q1', 'q2', 'q3', 'q4'],
        'alphabet': ['1', '2', '3', '4'],
        'start_state': 'q0',
        'accepting_states': ['q4'],
        'transitions': [
            {'from_state': 'q0', 'symbol': '1', 'to_state': 'q1'},
            {'from_state': 'q1', 'symbol': '2', 'to_state': 'q2'},
            {'from_state': 'q2', 'symbol': '3', 'to_state': 'q3'},
            {'from_state': 'q3', 'symbol': '4', 'to_state': 'q4'}
        ]
    },
    'input_string': '1234'
}
enfa_payload_rej = {
    'automaton': {
        'type': 'EPSILON_NFA',
        'states': ['q0', 'q1', 'q2', 'q3', 'q4'],
        'alphabet': ['1', '2', '3', '4'],
        'start_state': 'q0',
        'accepting_states': ['q4'],
        'transitions': [
            {'from_state': 'q0', 'symbol': '1', 'to_state': 'q1'},
            {'from_state': 'q1', 'symbol': '2', 'to_state': 'q2'},
            {'from_state': 'q2', 'symbol': '3', 'to_state': 'q3'},
            {'from_state': 'q3', 'symbol': '4', 'to_state': 'q4'}
        ]
    },
    'input_string': '123'
}
enfa_payload_empty = {
    'automaton': {
        'type': 'EPSILON_NFA',
        'states': ['q0', 'q1'],
        'alphabet': ['0', '1'],
        'start_state': 'q0',
        'accepting_states': ['q1'],
        'transitions': [
            {'from_state': 'q0', 'symbol': 'ε', 'to_state': 'q1'}
        ]
    },
    'input_string': ''
}
enfa_payload_unknown = {
    'automaton': {
        'type': 'EPSILON_NFA',
        'states': ['q0', 'q1'],
        'alphabet': ['0', '1'],
        'start_state': 'q0',
        'accepting_states': ['q1'],
        'transitions': [
            {'from_state': 'q0', 'symbol': '0', 'to_state': 'q1'}
        ]
    },
    'input_string': '0x1'
}

test_endpoint('NFA 101 (accepted)', nfa_payload_101)
test_endpoint('NFA 100 (rejected)', nfa_payload_100)
test_endpoint('DFA 00 (accepted)', dfa_payload_acc)
test_endpoint('DFA 0 (rejected)', dfa_payload_rej)
test_endpoint('DFA empty string (accepted)', dfa_payload_empty)
test_endpoint('ε-NFA 1234 (accepted)', enfa_payload_acc)
test_endpoint('ε-NFA 123 (rejected)', enfa_payload_rej)
test_endpoint('ε-NFA empty string (accepted)', enfa_payload_empty)
test_endpoint('ε-NFA unknown symbol (rejected with error)', enfa_payload_unknown)

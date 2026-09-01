import {
  AuditStatusResponse,
  AutomatonData,
  ConverterInfo,
  ConverterResponse,
  ExecuteSingleTestResponse,
  PresetItem,
  ProjectAnalysis,
  ProjectAnalysisResponse,
  ProjectInspectionResponse,
  SimulateResponse,
  ValidationResponse,
} from '../types';

const rawEnvUrl = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
const API_BASE = rawEnvUrl
  ? (rawEnvUrl.endsWith('/api/v1') ? rawEnvUrl : `${rawEnvUrl.replace(/\/+$/, '')}/api/v1`)
  : '/api/v1';

export async function validateAutomaton(automaton: AutomatonData): Promise<ValidationResponse> {
  try {
    const res = await fetch(`${API_BASE}/maker/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(automaton),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { valid: false, errors: [err.detail || `Server error ${res.status}`] };
    }
    return await res.json();
  } catch {
    // Client-side fallback validation if server unavailable
    return clientSideValidate(automaton);
  }
}

export async function simulateAutomaton(
  automaton: AutomatonData,
  inputString: string
): Promise<SimulateResponse> {
  try {
    const res = await fetch(`${API_BASE}/maker/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ automaton, input_string: inputString }),
    });
    if (!res.ok) {
      // Fallback to pure client-side mathematical simulation if endpoint is unreachable/405
      return clientSideSimulate(automaton, inputString);
    }
    return await res.json();
  } catch {
    // Network fallback
    return clientSideSimulate(automaton, inputString);
  }
}

export async function getPresets(): Promise<Record<string, PresetItem>> {
  try {
    const res = await fetch(`${API_BASE}/maker/presets`);
    if (!res.ok) throw new Error('Failed to load presets');
    return await res.json();
  } catch {
    return {
      dfa_even_zeros: {
        name: 'DFA: Even number of 0s',
        data: {
          type: 'DFA',
          states: ['q_even', 'q_odd'],
          alphabet: ['0', '1'],
          start_state: 'q_even',
          accepting_states: ['q_even'],
          transitions: [
            { from_state: 'q_even', symbol: '0', to_state: 'q_odd' },
            { from_state: 'q_even', symbol: '1', to_state: 'q_even' },
            { from_state: 'q_odd', symbol: '0', to_state: 'q_even' },
            { from_state: 'q_odd', symbol: '1', to_state: 'q_odd' },
          ],
        },
      },
      nfa_ends_with_01: {
        name: 'NFA: Strings ending in 01',
        data: {
          type: 'NFA',
          states: ['q0', 'q1', 'q2'],
          alphabet: ['0', '1'],
          start_state: 'q0',
          accepting_states: ['q2'],
          transitions: [
            { from_state: 'q0', symbol: '0', to_state: 'q0' },
            { from_state: 'q0', symbol: '1', to_state: 'q0' },
            { from_state: 'q0', symbol: '0', to_state: 'q1' },
            { from_state: 'q1', symbol: '1', to_state: 'q2' },
          ],
        },
      },
      enfa_pattern_0star_1star: {
        name: 'ε-NFA: Language 0* 1*',
        data: {
          type: 'EPSILON_NFA',
          states: ['q0', 'q1'],
          alphabet: ['0', '1'],
          start_state: 'q0',
          accepting_states: ['q1'],
          transitions: [
            { from_state: 'q0', symbol: '0', to_state: 'q0' },
            { from_state: 'q0', symbol: 'ε', to_state: 'q1' },
            { from_state: 'q1', symbol: '1', to_state: 'q1' },
          ],
        },
      },
    };
  }
}

export async function convertEpsilonNfaToDfa(
  automaton: AutomatonData
): Promise<ConverterResponse> {
  try {
    const res = await fetch(`${API_BASE}/converter/epsilon-nfa-to-dfa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(automaton),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return {
        success: false,
        error: err.detail || `Server returned error ${res.status}`,
      };
    }
    return await res.json();
  } catch (err: any) {
    return {
      success: false,
      error: `Network error: ${err.message || 'Cannot reach converter server'}`,
    };
  }
}

export async function getAuditConverters(): Promise<ConverterInfo[]> {
  try {
    const res = await fetch(`${API_BASE}/auditor/converters`);
    if (!res.ok) throw new Error('Failed to load converters');
    return await res.json();
  } catch {
    return [
      {
        id: 'trusted_subset_construction',
        name: 'Trusted ε-NFA → DFA (Gold Standard)',
        description: 'Mathematical textbook subset construction reference implementation.',
        expected_vcr: 1.0,
      },
      {
        id: 'buggy_no_epsilon_closure',
        name: 'Buggy: Epsilon Closure Ignored',
        description: 'Skips initial and post-move epsilon closures. Fails on epsilon chains/cycles.',
        expected_vcr: 0.1,
      },
      {
        id: 'buggy_accepting_states',
        name: 'Buggy: Flawed Final State Detection',
        description: 'Marks DFA state as accepting only if ALL subset states are accepting.',
        expected_vcr: 0.45,
      },
      {
        id: 'buggy_missing_dead_state',
        name: 'Buggy: Incomplete Transition Table',
        description: 'Omits transitions to empty set (dead state) in output DFA.',
        expected_vcr: 0.75,
      },
    ];
  }
}

export async function startAudit(
  payloadOrConverterId:
    | {
        converter_id: string;
        test_count: number;
        seed?: number;
        categories?: string[];
      }
    | string,
  test_count?: number,
  seed?: number,
  categories?: string[]
): Promise<AuditStatusResponse> {
  const payload =
    typeof payloadOrConverterId === 'string'
      ? {
          converter_id: payloadOrConverterId,
          test_count: test_count || 10,
          seed: seed !== undefined ? seed : 42,
          categories,
        }
      : payloadOrConverterId;

  try {
    const res = await fetch(`${API_BASE}/auditor/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Audit failed with code ${res.status}`);
    }
    return await res.json();
  } catch (err: any) {
    return {
      audit_id: 'error',
      status: 'failed',
      converter: payload.converter_id,
      seed: payload.seed || 42,
      progress: { current: 0, total: payload.test_count, current_category: 'error', current_status: 'failed' },
      error: err.message || 'Network error during audit execution',
    };
  }
}

export const getAuditorConverters = getAuditConverters;
export const triggerAuditRun = startAudit;

export async function uploadProjectZip(file: File): Promise<ProjectInspectionResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/auditor/upload-project`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed with status ${res.status}`);
  }

  return await res.json();
}

export async function analyzeProject(
  projectId: string,
  manualEntryPoint?: string
): Promise<ProjectAnalysisResponse> {
  const res = await fetch(`${API_BASE}/auditor/analyze-project`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      manual_entry_point: manualEntryPoint,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Analysis failed with status ${res.status}`);
  }

  return await res.json();
}

export async function executeSingleTest(
  projectId: string,
  analysis: ProjectAnalysis,
  testCase?: AutomatonData
): Promise<ExecuteSingleTestResponse> {
  const res = await fetch(`${API_BASE}/auditor/execute-test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      analysis,
      test_case: testCase || null,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Test execution failed with status ${res.status}`);
  }

  return await res.json();
}

export async function triggerProjectAuditRun(
  projectId: string,
  analysis: ProjectAnalysis,
  testCount: number = 100,
  seed: number = 42,
  categories?: string[],
  timeoutSeconds: number = 3.0
): Promise<AuditStatusResponse> {
  const res = await fetch(`${API_BASE}/auditor/run-project-audit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      analysis,
      test_count: testCount,
      seed,
      categories: categories || null,
      timeout_seconds: timeoutSeconds,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Audit run failed with status ${res.status}`);
  }

  return await res.json();
}

export async function getAuditStatus(auditId: string): Promise<AuditStatusResponse> {
  try {
    const res = await fetch(`${API_BASE}/auditor/status/${auditId}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Status check failed with code ${res.status}`);
    }
    return await res.json();
  } catch (err: any) {
    return {
      audit_id: auditId,
      status: 'failed',
      converter: '',
      seed: 42,
      progress: { current: 0, total: 0, current_category: 'error', current_status: 'failed' },
      error: err.message || 'Network error fetching audit report',
    };
  }
}

function clientSideValidate(a: AutomatonData): ValidationResponse {
  const errors: string[] = [];
  if (a.states.length === 0) return { valid: true, errors: [] };

  if (a.start_state && !a.states.includes(a.start_state)) {
    errors.push(`Start state '${a.start_state}' is not in states list.`);
  }

  for (const acc of a.accepting_states) {
    if (!a.states.includes(acc)) {
      errors.push(`Accepting state '${acc}' is not in states list.`);
    }
  }

  const stateSet = new Set(a.states);
  for (const t of a.transitions) {
    if (!stateSet.has(t.from_state)) {
      errors.push(`Transition source '${t.from_state}' is not in states list.`);
    }
    if (!stateSet.has(t.to_state)) {
      errors.push(`Transition destination '${t.to_state}' is not in states list.`);
    }
  }

  if (a.type === 'DFA') {
    const seen = new Map<string, string>();
    for (const t of a.transitions) {
      const key = `${t.from_state}|${t.symbol}`;
      if (seen.has(key)) {
        errors.push(`DFA has multiple transitions from '${t.from_state}' on symbol '${t.symbol}'.`);
      }
      seen.set(key, t.to_state);
      if (t.symbol === 'ε') {
        errors.push('DFA cannot have epsilon (ε) transitions.');
      }
    }
  }

  return { valid: errors.length === 0, errors };
}

function computeEpsilonClosure(
  states: string[],
  transitions: { from_state: string; symbol: string; to_state: string }[]
): string[] {
  const closure = new Set<string>(states);
  const queue = [...states];
  while (queue.length > 0) {
    const curr = queue.shift()!;
    for (const t of transitions) {
      if (t.from_state === curr && (t.symbol === 'ε' || t.symbol === 'e' || t.symbol === '')) {
        if (!closure.has(t.to_state)) {
          closure.add(t.to_state);
          queue.push(t.to_state);
        }
      }
    }
  }
  return Array.from(closure).sort();
}

function clientSideSimulate(a: AutomatonData, inputString: string): SimulateResponse {
  if (!a.start_state || !a.states.includes(a.start_state)) {
    return {
      accepted: false,
      input_string: inputString,
      steps: [],
      final_states: [],
      error: 'Invalid or missing start state in automaton.',
    };
  }

  const tokens = inputString ? inputString.split('') : [];
  const steps: any[] = [];

  if (a.type === 'DFA') {
    let curr = a.start_state;
    for (let i = 0; i < tokens.length; i++) {
      const sym = tokens[i];
      const match = a.transitions.find((t) => t.from_state === curr && t.symbol === sym);
      const nxt = match ? match.to_state : null;
      steps.push({
        step_index: i,
        current_states: [curr],
        symbol: sym,
        next_states: nxt ? [nxt] : [],
      });
      if (!nxt) {
        return {
          accepted: false,
          input_string: inputString,
          steps,
          final_states: [],
        };
      }
      curr = nxt;
    }
    const accepted = a.accepting_states.includes(curr);
    return {
      accepted,
      input_string: inputString,
      steps,
      final_states: [curr],
    };
  }

  // NFA / EPSILON_NFA
  const isEnfa = a.type === 'EPSILON_NFA';
  let currentStates = isEnfa
    ? computeEpsilonClosure([a.start_state], a.transitions)
    : [a.start_state];

  for (let i = 0; i < tokens.length; i++) {
    const sym = tokens[i];
    const nextSet = new Set<string>();
    for (const st of currentStates) {
      for (const t of a.transitions) {
        if (t.from_state === st && t.symbol === sym) {
          nextSet.add(t.to_state);
        }
      }
    }
    const rawNext = Array.from(nextSet);
    const closedNext = isEnfa ? computeEpsilonClosure(rawNext, a.transitions) : rawNext.sort();

    steps.push({
      step_index: i,
      current_states: currentStates,
      symbol: sym,
      next_states: closedNext,
    });

    currentStates = closedNext;
    if (currentStates.length === 0) {
      break;
    }
  }

  const accepted = currentStates.some((st) => a.accepting_states.includes(st));
  return {
    accepted,
    input_string: inputString,
    steps,
    final_states: currentStates,
  };
}


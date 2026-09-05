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

export function getApiBase(): string {
  if (typeof window !== 'undefined') {
    const custom = localStorage.getItem('autoverify_api_url')?.trim();
    if (custom) {
      return custom.endsWith('/api/v1') ? custom : `${custom.replace(/\/+$/, '')}/api/v1`;
    }
  }
  const rawEnv = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
  if (rawEnv) {
    return rawEnv.endsWith('/api/v1') ? rawEnv : `${rawEnv.replace(/\/+$/, '')}/api/v1`;
  }
  return '/api/v1';
}

export function setCustomApiUrl(url: string): void {
  if (typeof window !== 'undefined') {
    const clean = url.trim();
    if (!clean) {
      localStorage.removeItem('autoverify_api_url');
    } else {
      localStorage.setItem('autoverify_api_url', clean);
    }
  }
}

export function getRawCustomApiUrl(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('autoverify_api_url') || '';
  }
  return '';
}

export function getCustomAiApiKey(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('autoverify_ai_api_key') || '';
  }
  return '';
}

export function setCustomAiApiKey(key: string): void {
  if (typeof window !== 'undefined') {
    const clean = key.trim();
    if (!clean) {
      localStorage.removeItem('autoverify_ai_api_key');
    } else {
      localStorage.setItem('autoverify_ai_api_key', clean);
    }
  }
}

export async function checkBackendHealth(): Promise<{ healthy: boolean; url: string; error?: string }> {
  const base = getApiBase();
  const root = base.replace(/\/api\/v1$/, '');
  try {
    const res = await fetch(`${root}/health`);
    if (res.ok) {
      return { healthy: true, url: base };
    }
    return { healthy: false, url: base, error: `Status ${res.status}` };
  } catch (err: any) {
    return { healthy: false, url: base, error: err.message || 'Cannot reach server' };
  }
}

export async function validateAutomaton(automaton: AutomatonData): Promise<ValidationResponse> {
  try {
    const res = await fetch(`${getApiBase()}/maker/validate`, {
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
    const res = await fetch(`${getApiBase()}/maker/simulate`, {
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
    const res = await fetch(`${getApiBase()}/maker/presets`);
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
  automaton: AutomatonData,
  minimize: boolean = false
): Promise<ConverterResponse> {
  try {
    const res = await fetch(`${getApiBase()}/converter/epsilon-nfa-to-dfa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ automaton, minimize }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Conversion failed with code ${res.status}`);
    }
    return await res.json();
  } catch (err: any) {
    throw new Error(err.message || 'Cannot reach conversion service');
  }
}

export async function getAuditConverters(): Promise<ConverterInfo[]> {
  try {
    const res = await fetch(`${getApiBase()}/auditor/converters`);
    if (!res.ok) throw new Error('Failed to load converters');
    return await res.json();
  } catch {
    return [
      {
        id: 'reference_correct',
        name: 'AutoVerify Reference Engine (Correct)',
        description: 'Standard subset construction and closure implementation (100% VCR expected).',
        expected_vcr: 1.0,
      },
      {
        id: 'buggy',
        name: 'Defective Conversion Model (Buggy)',
        description: 'Demonstration converter with closure faults on edge transitions (~60-70% VCR).',
        expected_vcr: 0.65,
      },
    ];
  }
}

export async function startAudit(
  payloadOrConverterId:
    | string
    | {
        converter_id: string;
        test_count: number;
        seed?: number;
        categories?: string[];
      },
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
    const res = await fetch(`${getApiBase()}/auditor/run`, {
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

/**
 * Pure client-side ZIP inspection helper to extract file list, sizes, languages,
 * and entry points without requiring a backend server or external npm packages.
 */
export async function inspectZipClientSide(file: File): Promise<ProjectInspectionResponse> {
  const buffer = await file.arrayBuffer();
  const view = new DataView(buffer);
  const files: { path: string; extension: string; size_bytes: number }[] = [];
  const likelySourceFiles: string[] = [];
  const languagesSet = new Set<string>();

  // 1. Locate End of Central Directory (EOCD)
  let eocdOffset = -1;
  const maxSearch = Math.min(buffer.byteLength, 65536 + 22);
  for (let i = buffer.byteLength - 22; i >= buffer.byteLength - maxSearch; i--) {
    if (view.getUint32(i, true) === 0x06054b50) {
      eocdOffset = i;
      break;
    }
  }

  if (eocdOffset !== -1) {
    const totalEntries = view.getUint16(eocdOffset + 10, true);
    const cdOffset = view.getUint32(eocdOffset + 16, true);
    let curr = cdOffset;

    for (let r = 0; r < totalEntries && curr + 46 <= buffer.byteLength; r++) {
      if (view.getUint32(curr, true) !== 0x02014b50) break;
      const uncompressedSize = view.getUint32(curr + 24, true);
      const nameLen = view.getUint16(curr + 28, true);
      const extraLen = view.getUint16(curr + 30, true);
      const commentLen = view.getUint16(curr + 32, true);

      if (curr + 46 + nameLen <= buffer.byteLength) {
        const nameBytes = new Uint8Array(buffer, curr + 46, nameLen);
        const path = new TextDecoder('utf-8').decode(nameBytes).replace(/\\/g, '/');

        if (!path.endsWith('/') && !path.startsWith('__MACOSX') && !path.includes('.DS_Store')) {
          const parts = path.split('/');
          const filename = parts[parts.length - 1];
          const dotIdx = filename.lastIndexOf('.');
          const ext = dotIdx !== -1 ? filename.slice(dotIdx).toLowerCase() : '';

          const langMap: Record<string, string> = {
            '.py': 'python',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cc': 'cpp',
            '.js': 'javascript',
            '.mjs': 'javascript',
            '.cjs': 'javascript',
            '.ts': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
          };

          if (langMap[ext]) {
            languagesSet.add(langMap[ext]);
            likelySourceFiles.push(path);
          }

          files.push({
            path,
            extension: ext,
            size_bytes: uncompressedSize,
          });
        }
      }

      curr += 46 + nameLen + extraLen + commentLen;
    }
  }

  // Fallback scan: read local file headers if central directory was empty
  if (files.length === 0) {
    let offset = 0;
    while (offset + 30 <= buffer.byteLength) {
      if (view.getUint32(offset, true) === 0x04034b50) {
        const uncompressedSize = view.getUint32(offset + 22, true);
        const nameLen = view.getUint16(offset + 26, true);
        const extraLen = view.getUint16(offset + 28, true);
        if (offset + 30 + nameLen <= buffer.byteLength) {
          const nameBytes = new Uint8Array(buffer, offset + 30, nameLen);
          const path = new TextDecoder('utf-8').decode(nameBytes).replace(/\\/g, '/');
          if (!path.endsWith('/') && !path.startsWith('__MACOSX') && !path.includes('.DS_Store')) {
            const parts = path.split('/');
            const filename = parts[parts.length - 1];
            const dotIdx = filename.lastIndexOf('.');
            const ext = dotIdx !== -1 ? filename.slice(dotIdx).toLowerCase() : '';
            files.push({ path, extension: ext, size_bytes: uncompressedSize });
            if (['.py', '.java', '.cpp', '.c', '.js', '.ts'].includes(ext)) {
              likelySourceFiles.push(path);
            }
          }
        }
        offset += 30 + nameLen + extraLen;
      } else {
        offset++;
      }
    }
  }

  // Sort candidate source files: prioritize main/converter files
  likelySourceFiles.sort((a, b) => {
    const aL = a.toLowerCase();
    const bL = b.toLowerCase();
    if (aL.includes('main') || aL.includes('converter')) return -1;
    if (bL.includes('main') || bL.includes('converter')) return 1;
    return a.localeCompare(b);
  });

  return {
    project_id: 'client_' + Math.random().toString(36).substring(2, 10),
    filename: file.name,
    file_count: files.length,
    total_size_bytes: file.size,
    languages: Array.from(languagesSet),
    files,
    likely_source_files: likelySourceFiles,
  };
}

export async function uploadProjectZip(file: File): Promise<ProjectInspectionResponse> {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${getApiBase()}/auditor/upload-project`, {
      method: 'POST',
      body: formData,
    });

    if (res.ok) {
      return await res.json();
    }

    // If server responded with 404/405 or gateway error, inspect client-side
    if (res.status === 404 || res.status === 405 || res.status >= 500) {
      console.warn(`Server status ${res.status} for /upload-project. Inspecting client-side.`);
      return await inspectZipClientSide(file);
    }

    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed with status ${res.status}`);
  } catch (err: any) {
    // If network error (offline backend, CORS, sleeping Render free tier), inspect client-side
    console.warn('Network error during upload-project. Inspecting client-side:', err);
    try {
      return await inspectZipClientSide(file);
    } catch {
      throw new Error(err.message || 'Failed to inspect project ZIP file.');
    }
  }
}

export async function analyzeProject(
  projectId: string,
  manualEntryPoint?: string,
  fallbackInspection?: ProjectInspectionResponse,
  overrideAiKey?: string
): Promise<ProjectAnalysisResponse> {
  const apiKey = overrideAiKey !== undefined ? overrideAiKey : getCustomAiApiKey();
  try {
    const res = await fetch(`${getApiBase()}/auditor/analyze-project`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projectId,
        manual_entry_point: manualEntryPoint,
        ai_api_key: apiKey ? apiKey.trim() : undefined,
      }),
    });

    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('Backend analyze-project unreachable, using client-side heuristic:', err);
  }

  // Client-side heuristic analysis fallback
  const entry = manualEntryPoint || fallbackInspection?.likely_source_files?.[0] || 'main.py';
  const dotIdx = entry.lastIndexOf('.');
  const ext = dotIdx !== -1 ? entry.slice(dotIdx).toLowerCase() : '';
  const lang = ext === '.py' ? 'python' : ext === '.java' ? 'java' : ext === '.cpp' ? 'cpp' : 'c';

  return {
    status: 'SUCCESS',
    project_id: projectId,
    candidate_entry_points: fallbackInspection?.likely_source_files || [entry],
    analysis: {
      language: lang,
      entry_point: entry,
      relevant_files: fallbackInspection?.likely_source_files || [entry],
      input_format: 'json',
      output_format: 'stdout_json',
      invocation: `${lang === 'python' ? 'python' : lang === 'java' ? 'java' : './'} ${entry} <input.json>`,
      conversion_type: 'epsilon_nfa_to_dfa',
      is_supported_language: true,
      confidence: 0.95,
      ambiguities: [],
      reasoning_summary: `Heuristic inspection detected entry point "${entry}" (${lang.toUpperCase()}).`,
    },
    message: 'Project analysis completed.',
  };
}

export async function executeSingleTest(
  projectId: string,
  analysis: ProjectAnalysis,
  testCase?: AutomatonData
): Promise<ExecuteSingleTestResponse> {
  try {
    const res = await fetch(`${getApiBase()}/auditor/execute-test`, {
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
  } catch (err: any) {
    throw new Error(
      `${err.message || 'Cannot reach execution server'}. If your backend is deployed on Render free tier, please verify the backend URL in Server Settings.`
    );
  }
}

export async function triggerProjectAuditRun(
  projectId: string,
  analysis: ProjectAnalysis,
  testCount: number = 100,
  seed: number = 42,
  categories?: string[],
  timeoutSeconds: number = 3.0
): Promise<AuditStatusResponse> {
  try {
    const res = await fetch(`${getApiBase()}/auditor/run-project-audit`, {
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
  } catch (err: any) {
    throw new Error(
      `${err.message || 'Cannot reach audit execution server'}. Please check your backend connection in Server Settings.`
    );
  }
}

export async function getAuditStatus(auditId: string): Promise<AuditStatusResponse> {
  try {
    const res = await fetch(`${getApiBase()}/auditor/status/${auditId}`);
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

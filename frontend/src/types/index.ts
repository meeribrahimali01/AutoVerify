export type AutomatonType = 'DFA' | 'NFA' | 'EPSILON_NFA';

export const EPSILON_SYMBOL = 'ε';

export interface Transition {
  from_state: string;
  symbol: string;
  to_state: string;
}

export interface AutomatonData {
  type: AutomatonType;
  states: string[];
  alphabet: string[];
  start_state: string;
  accepting_states: string[];
  transitions: Transition[];
}

export interface SimulationStep {
  step_index: number;
  current_states: string[];
  symbol?: string;
  next_states: string[];
}

export interface SimulateResponse {
  accepted: boolean;
  input_string: string;
  steps: SimulationStep[];
  final_states: string[];
  error?: string;
}

export interface ValidationResponse {
  valid: boolean;
  errors: string[];
  automaton?: AutomatonData;
}

export interface PresetItem {
  name: string;
  data: AutomatonData;
}

// ============================================================================
// CONVERTER TYPES
// ============================================================================

export interface ConverterStatistics {
  input_states_count: number;
  input_transitions_count: number;
  input_epsilon_transitions_count: number;
  dfa_states_count: number;
  dfa_transitions_count: number;
  dfa_accepting_states_count: number;
}

export interface SubsetStep {
  source_name: string;
  source_subset: string[];
  symbol: string;
  move_result: string[];
  closure_result: string[];
  target_name: string;
  is_new_subset: boolean;
}

export interface SubsetTrace {
  start_closure: string[];
  start_state_name: string;
  discovered_subsets: { name: string; states: string[] }[];
  steps: SubsetStep[];
  accepting_subsets: { name: string; states: string[] }[];
}

export interface VerificationStatus {
  equivalent: boolean;
  counterexample?: string | null;
  automaton_a_accepts?: boolean | null;
  automaton_b_accepts?: boolean | null;
  states_explored?: number;
  error?: string | null;
}

export interface ConverterResponse {
  success: boolean;
  dfa?: AutomatonData;
  statistics?: ConverterStatistics;
  trace?: SubsetTrace;
  verification?: VerificationStatus;
  error?: string;
}

// ============================================================================
// AUDITOR TYPES
// ============================================================================

export interface ConverterInfo {
  id: string;
  name: string;
  description: string;
  expected_vcr?: number;
}

export interface AuditProgress {
  current: number;
  total: number;
  current_category: string;
  current_status: string;
  verified_count?: number;
  failed_count?: number;
  crash_count?: number;
  timeout_count?: number;
  invalid_output_count?: number;
}

export interface AuditSummary {
  total_tests: number;
  verified_count: number;
  failed_count: number;
  invalid_output_count: number;
  execution_error_count: number;
  timeout_count: number;
  verified_conversion_rate: number | null;
  total_execution_time_seconds: number;
  average_execution_time_seconds: number;
}

export interface CategoryStatsItem {
  category: string;
  total_tests: number;
  verified_count: number;
  failed_count: number;
  invalid_output_count: number;
  execution_error_count: number;
  timeout_count: number;
  verified_conversion_rate: number | null;
}

export interface AuditResultItem {
  test_id: string;
  category: string;
  status: string;
  execution_time_seconds: number;
  generated_dfa?: AutomatonData | null;
  original_enfa?: AutomatonData | null;
  counterexample?: string | null;
  expected_acceptance?: boolean | null;
  generated_acceptance?: boolean | null;
  states_explored?: number;
  error_message?: string | null;
  metadata?: any;
  trace?: any;
}

export interface AuditReport {
  audit_id: string;
  transformation: string;
  timestamp: string;
  seed: number;
  summary: AuditSummary;
  category_statistics: Record<string, CategoryStatsItem>;
  failures: AuditResultItem[];
  results: AuditResultItem[];
}

export interface AuditStatusResponse {
  audit_id: string;
  status: 'running' | 'completed' | 'failed';
  converter: string;
  seed: number;
  progress: AuditProgress;
  report?: AuditReport | null;
  error?: string | null;
}

export interface FileInfo {
  path: string;
  extension: string;
  size_bytes: number;
}

export interface ProjectInspectionResponse {
  project_id: string;
  filename: string;
  file_count: number;
  total_size_bytes: number;
  languages: string[];
  files: FileInfo[];
  likely_source_files: string[];
}

export interface ProjectAnalysis {
  language: string;
  entry_point?: string | null;
  relevant_files: string[];
  converter_file?: string | null;
  converter_function?: string | null;
  converter_class?: string | null;
  input_format: string;
  output_format: string;
  invocation?: string | null;
  conversion_type: string;
  is_supported_language: boolean;
  confidence: number;
  ambiguities: string[];
  reasoning_summary: string;
}

export interface ProjectAnalysisResponse {
  status: 'SUCCESS' | 'AI_NOT_CONFIGURED' | 'LOW_CONFIDENCE' | 'ERROR';
  project_id: string;
  analysis?: ProjectAnalysis | null;
  candidate_entry_points: string[];
  message?: string | null;
  error?: string | null;
}

export type ExecutionStatus =
  | 'READY'
  | 'RUNNING'
  | 'SUCCESS'
  | 'TIMEOUT'
  | 'CRASH'
  | 'INVALID_OUTPUT'
  | 'NEEDS_CONFIGURATION'
  | 'SANDBOX_ERROR';

export interface ExecuteSingleTestResponse {
  status: ExecutionStatus;
  project_id: string;
  execution_time_ms: number;
  exit_code?: number | null;
  stdout: string;
  stderr: string;
  original_enfa?: AutomatonData | null;
  generated_dfa?: AutomatonData | null;
  error_message?: string | null;
}

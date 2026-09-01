import React, { useState, useEffect, useRef, useCallback } from 'react';
import './AutomataConverter.css';
import {
  AutomatonData,
  ConverterResponse,
  ConverterStatistics,
  PresetItem,
  SubsetStep,
  SubsetTrace,
  VerificationStatus,
} from '../../types';
import { convertEpsilonNfaToDfa, getPresets } from '../../api/client';
import { GraphCanvas } from '../graph/GraphCanvas';
import { ImportExportModal } from '../maker/ImportExportModal';

const DEFAULT_INPUT_ENFA: AutomatonData = {
  type: 'EPSILON_NFA',
  states: ['q0', 'q1', 'q2'],
  alphabet: ['0', '1'],
  start_state: 'q0',
  accepting_states: ['q2'],
  transitions: [
    { from_state: 'q0', symbol: '0', to_state: 'q0' },
    { from_state: 'q0', symbol: 'ε', to_state: 'q1' },
    { from_state: 'q1', symbol: '1', to_state: 'q1' },
    { from_state: 'q1', symbol: 'ε', to_state: 'q2' },
    { from_state: 'q2', symbol: '0', to_state: 'q2' },
  ],
};

export const AutomataConverter: React.FC = () => {
  const [inputAutomaton, setInputAutomaton] = useState<AutomatonData>(DEFAULT_INPUT_ENFA);
  const [resultDfa, setResultDfa] = useState<AutomatonData | null>(null);
  const [statistics, setStatistics] = useState<ConverterStatistics | null>(null);
  const [trace, setTrace] = useState<SubsetTrace | null>(null);
  const [verification, setVerification] = useState<VerificationStatus | null>(null);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [presets, setPresets] = useState<Record<string, PresetItem>>({});
  const [isImportOpen, setIsImportOpen] = useState<boolean>(false);
  const [isExportDfaOpen, setIsExportDfaOpen] = useState<boolean>(false);
  const [copiedDfa, setCopiedDfa] = useState<boolean>(false);

  // Active highlights on canvases
  const [inputHighlights, setInputHighlights] = useState<string[]>([]);
  const [dfaHighlights, setDfaHighlights] = useState<string[]>([]);

  const playTimerRef = useRef<number | null>(null);

  // Load Presets on Mount
  useEffect(() => {
    getPresets().then((res) => setPresets(res));
  }, []);

  // Perform Conversion
  const handleConvert = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const resp: ConverterResponse = await convertEpsilonNfaToDfa(inputAutomaton);
      if (!resp.success || !resp.dfa) {
        setErrorMessage(resp.error || 'Conversion failed.');
        return;
      }

      setResultDfa(resp.dfa);
      setStatistics(resp.statistics || null);
      setTrace(resp.trace || null);
      setVerification(resp.verification || null);
      setCurrentStepIndex(0);
      setIsPlaying(false);

      // Highlight initial subset
      if (resp.trace && resp.trace.steps.length > 0) {
        const firstStep = resp.trace.steps[0];
        setInputHighlights(firstStep.source_subset);
        setDfaHighlights([firstStep.source_name]);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'An unexpected error occurred during conversion.');
    } finally {
      setLoading(false);
    }
  };

  // Run initial conversion once on load
  useEffect(() => {
    handleConvert();
  }, []);

  // Step Navigation
  const goToStep = useCallback(
    (index: number) => {
      if (!trace || trace.steps.length === 0) return;
      const clampedIndex = Math.max(0, Math.min(index, trace.steps.length - 1));
      setCurrentStepIndex(clampedIndex);

      const step = trace.steps[clampedIndex];
      setInputHighlights(step.closure_result.length > 0 ? step.closure_result : step.source_subset);
      setDfaHighlights([step.target_name]);
    },
    [trace]
  );

  const handlePrevStep = () => {
    goToStep(currentStepIndex - 1);
  };

  const handleNextStep = () => {
    goToStep(currentStepIndex + 1);
  };

  // Play / Pause Auto Stepper
  useEffect(() => {
    if (isPlaying && trace && trace.steps.length > 0) {
      playTimerRef.current = window.setInterval(() => {
        setCurrentStepIndex((prev) => {
          if (prev >= trace.steps.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          const next = prev + 1;
          const step = trace.steps[next];
          setInputHighlights(step.closure_result.length > 0 ? step.closure_result : step.source_subset);
          setDfaHighlights([step.target_name]);
          return next;
        });
      }, 1200);
    } else if (playTimerRef.current) {
      clearInterval(playTimerRef.current);
      playTimerRef.current = null;
    }

    return () => {
      if (playTimerRef.current) {
        clearInterval(playTimerRef.current);
        playTimerRef.current = null;
      }
    };
  }, [isPlaying, trace]);

  // Load Preset
  const handleSelectPreset = (presetKey: string) => {
    if (presets[presetKey]) {
      setInputAutomaton(presets[presetKey].data);
      setResultDfa(null);
      setTrace(null);
      setStatistics(null);
      setVerification(null);
    }
  };

  // Copy DFA JSON
  const handleCopyDfaJson = () => {
    if (!resultDfa) return;
    navigator.clipboard.writeText(JSON.stringify(resultDfa, null, 2));
    setCopiedDfa(true);
    setTimeout(() => setCopiedDfa(false), 2000);
  };

  const currentStep: SubsetStep | null =
    trace && trace.steps.length > 0 ? trace.steps[currentStepIndex] : null;

  return (
    <div className="converter-workspace">
      {/* Top Header Control Bar */}
      <div className="converter-header-bar">
        <div className="converter-title-group">
          <div>
            <div className="converter-title">Automata Converter</div>
            <div className="converter-subtitle">
              ε-NFA → DFA Subset Construction with Execution Trace
            </div>
          </div>
        </div>

        <div className="converter-controls-group">
          {/* Preset Selector */}
          <select
            className="inspector-input"
            style={{ width: '200px' }}
            onChange={(e) => handleSelectPreset(e.target.value)}
            defaultValue=""
          >
            <option value="" disabled>
              Load Preset ε-NFA...
            </option>
            {Object.entries(presets).map(([key, item]) => (
              <option key={key} value={key}>
                {item.name}
              </option>
            ))}
          </select>

          {/* Import JSON */}
          <button className="tool-btn icon-only" onClick={() => setIsImportOpen(true)} title="Import ε-NFA JSON">
            📥 Import
          </button>

          {/* Convert Action Button */}
          <button
            className="btn-convert-action"
            onClick={handleConvert}
            disabled={loading || inputAutomaton.states.length === 0}
          >
            {loading ? 'Converting...' : '⚡ Convert ε-NFA → DFA'}
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="av-toast error" style={{ position: 'relative', bottom: 'auto', left: 'auto', transform: 'none' }}>
          {errorMessage}
        </div>
      )}

      {/* Dual Canvas Display */}
      <div className="converter-grid">
        {/* LEFT CANVAS: Input ε-NFA */}
        <div className="canvas-card">
          <div className="canvas-card-header">
            <div className="canvas-card-title">
              <span>Input Automaton</span>
              <span className="badge-tag enfa">{inputAutomaton.type === 'EPSILON_NFA' ? 'ε-NFA' : inputAutomaton.type}</span>
            </div>
            <span className="hint-text">{inputAutomaton.states.length} states</span>
          </div>
          <div className="canvas-card-body">
            <GraphCanvas
              automaton={inputAutomaton}
              activeStates={inputHighlights}
              activeTool="select"
            />
          </div>
        </div>

        {/* RIGHT CANVAS: Resulting DFA */}
        <div className="canvas-card">
          <div className="canvas-card-header">
            <div className="canvas-card-title">
              <span>Generated Reference DFA</span>
              <span className="badge-tag dfa">DFA</span>
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              {resultDfa && (
                <>
                  <button className="tool-btn icon-only" onClick={handleCopyDfaJson} title="Copy DFA JSON">
                    {copiedDfa ? '✓ Copied' : '📋 Copy'}
                  </button>
                  <button className="tool-btn icon-only" onClick={() => setIsExportDfaOpen(true)} title="Export DFA JSON">
                    📤 Export
                  </button>
                </>
              )}
            </div>
          </div>
          <div className="canvas-card-body">
            {resultDfa ? (
              <GraphCanvas
                automaton={resultDfa}
                activeStates={dfaHighlights}
                activeTool="select"
              />
            ) : (
              <div className="canvas-empty">
                <div className="canvas-empty-content">
                  <span className="canvas-empty-icon">⚙</span>
                  <h3>DFA Result Pending</h3>
                  <p>Click "Convert ε-NFA → DFA" to generate the equivalent deterministic automaton.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Statistics & Sanity Verification Bar */}
      {statistics && (
        <div className="stats-banner">
          <div className="stat-item">
            <span className="stat-label">Input States</span>
            <span className="stat-value">{statistics.input_states_count}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Input Transitions</span>
            <span className="stat-value">{statistics.input_transitions_count}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">ε-Transitions</span>
            <span className="stat-value">{statistics.input_epsilon_transitions_count}</span>
          </div>

          <div className="stat-divider" />

          <div className="stat-item">
            <span className="stat-label">DFA States</span>
            <span className="stat-value">{statistics.dfa_states_count}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">DFA Transitions</span>
            <span className="stat-value">{statistics.dfa_transitions_count}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">DFA Accepting</span>
            <span className="stat-value">{statistics.dfa_accepting_states_count}</span>
          </div>

          <div className="stat-divider" />

          {/* Formal Verification Sanity Check */}
          {verification && (
            <div
              className={`verification-badge-container ${
                verification.equivalent ? 'verified' : 'failed'
              }`}
            >
              {verification.equivalent ? (
                <span>✓ Conversion Verified (Languages Equivalent)</span>
              ) : (
                <span>
                  ⚠ Verification Mismatch! Counterexample: "
                  {verification.counterexample || 'ε'}"
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Conversion Trace Section */}
      {trace && trace.steps.length > 0 && (
        <div className="trace-card">
          <div className="trace-header">
            <div className="trace-title">
              Subset Construction Trace ({trace.steps.length} Steps)
            </div>

            <div className="trace-nav-controls">
              <button
                className="tool-btn icon-only"
                onClick={handlePrevStep}
                disabled={currentStepIndex === 0}
                title="Previous Step"
              >
                ◀
              </button>
              <span className="trace-step-indicator">
                Step {currentStepIndex + 1} of {trace.steps.length}
              </span>
              <button
                className="tool-btn icon-only"
                onClick={handleNextStep}
                disabled={currentStepIndex === trace.steps.length - 1}
                title="Next Step"
              >
                ▶
              </button>
              <button
                className="tool-btn icon-only"
                onClick={() => setIsPlaying(!isPlaying)}
                title={isPlaying ? 'Pause' : 'Play Trace'}
              >
                {isPlaying ? '⏸ Pause' : '▶ Play'}
              </button>
            </div>
          </div>

          {/* Current Step Detailed Breakdown */}
          {currentStep && (
            <div className="trace-step-details">
              <div className="trace-step-grid">
                <div className="trace-cell">
                  <span className="trace-cell-label">Current DFA Subset</span>
                  <span className="trace-cell-value">
                    {`{ ${currentStep.source_subset.join(', ') || '∅'} }`}
                  </span>
                </div>

                <div className="trace-cell">
                  <span className="trace-cell-label">Input Symbol</span>
                  <span className="trace-cell-value highlight">
                    {currentStep.symbol}
                  </span>
                </div>

                <div className="trace-cell">
                  <span className="trace-cell-label">move(Subset, {currentStep.symbol})</span>
                  <span className="trace-cell-value">
                    {`{ ${currentStep.move_result.join(', ') || '∅'} }`}
                  </span>
                </div>

                <div className="trace-cell">
                  <span className="trace-cell-label">ε-closure(move)</span>
                  <span className="trace-cell-value">
                    {`{ ${currentStep.closure_result.join(', ') || '∅'} }`}
                  </span>
                </div>

                <div className="trace-cell">
                  <span className="trace-cell-label">Target DFA State</span>
                  <span className="trace-cell-value highlight">
                    {currentStep.target_name}
                  </span>
                </div>

                <div className="trace-cell">
                  <span className="trace-cell-label">New Subset Discovered?</span>
                  <span className="trace-cell-value">
                    {currentStep.is_new_subset ? '✓ Yes' : 'No (Already Seen)'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Complete Step Table */}
          <div className="trace-table-wrapper">
            <table className="trace-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Source Subset</th>
                  <th>Symbol</th>
                  <th>move(S, a)</th>
                  <th>ε-closure</th>
                  <th>Target DFA State</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {trace.steps.map((st, i) => (
                  <tr
                    key={`step_row_${i}`}
                    className={`trace-row ${i === currentStepIndex ? 'active' : ''}`}
                    onClick={() => goToStep(i)}
                  >
                    <td>{i + 1}</td>
                    <td>{st.source_name}</td>
                    <td><strong>{st.symbol}</strong></td>
                    <td>{`{ ${st.move_result.join(', ') || '∅'} }`}</td>
                    <td>{`{ ${st.closure_result.join(', ') || '∅'} }`}</td>
                    <td><strong>{st.target_name}</strong></td>
                    <td>
                      {st.is_new_subset && (
                        <span className="badge-tag dfa">New</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Import Modal for ε-NFA */}
      <ImportExportModal
        automaton={inputAutomaton}
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onImport={(imported) => {
          setInputAutomaton(imported);
          setResultDfa(null);
          setTrace(null);
          setStatistics(null);
          setVerification(null);
        }}
      />

      {/* Export Modal for Resulting DFA */}
      {resultDfa && (
        <ImportExportModal
          automaton={resultDfa}
          isOpen={isExportDfaOpen}
          onClose={() => setIsExportDfaOpen(false)}
          onImport={() => {}}
        />
      )}
    </div>
  );
};

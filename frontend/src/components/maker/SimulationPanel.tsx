import React, { useState } from 'react';
import { AutomatonData, SimulateResponse } from '../../types';
import { simulateAutomaton } from '../../api/client';

export interface SimulationPanelProps {
  automaton: AutomatonData;
  onHighlightStates: (states: string[]) => void;
}

export const SimulationPanel: React.FC<SimulationPanelProps> = ({
  automaton,
  onHighlightStates,
}) => {
  const [inputString, setInputString] = useState<string>('0101');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<SimulateResponse | null>(null);

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const resp = await simulateAutomaton(automaton, inputString);
      setResult(resp);
      onHighlightStates(resp.final_states);
    } finally {
      setLoading(false);
    }
  };

  const handleStepClick = (states: string[]) => {
    onHighlightStates(states);
  };

  return (
    <div className="simulation-card">
      <h3 className="section-title">String Simulation</h3>

      <form onSubmit={handleSimulate} className="sim-form">
        <div className="input-group">
          <input
            type="text"
            placeholder="Input string (e.g. 101001 or empty)"
            value={inputString}
            onChange={(e) => setInputString(e.target.value)}
            className="text-input font-mono"
          />
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Testing...' : 'Test String'}
          </button>
        </div>
      </form>

      {/* Result Display */}
      {result && (
        <div className="sim-result-box">
          <div className="sim-result-header">
            <span>
              Input: <code>"{result.input_string}"</code>
            </span>
            <span className={`badge-verdict ${result.accepted ? 'badge-accept-verdict' : 'badge-reject-verdict'}`}>
              {result.accepted ? 'ACCEPTED' : 'REJECTED'}
            </span>
          </div>

          {result.error && <p className="error-text mt-1">{result.error}</p>}

          {result.steps.length > 0 && (
            <div className="sim-steps-wrapper mt-2">
              <span className="steps-title">Execution Path:</span>
              <div className="sim-steps-timeline">
                {result.steps.map((st, i) => (
                  <div
                    key={`step_${i}`}
                    className="step-item"
                    onClick={() => handleStepClick(st.next_states.length ? st.next_states : st.current_states)}
                    title="Click to highlight on graph"
                  >
                    <span className="step-badge">Step {st.step_index + 1}</span>
                    <span className="step-states">{`{ ${st.current_states.join(', ')} }`}</span>
                    {st.symbol && <span className="step-arrow">--({st.symbol})--&gt;</span>}
                    <span className="step-next">{`{ ${st.next_states.join(', ') || '∅'} }`}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

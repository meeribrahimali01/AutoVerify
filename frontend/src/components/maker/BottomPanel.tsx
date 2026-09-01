import React, { useState } from 'react';
import { AutomatonData, EPSILON_SYMBOL, SimulateResponse } from '../../types';
import { simulateAutomaton } from '../../api/client';

interface BottomPanelProps {
  automaton: AutomatonData;
  isOpen: boolean;
  activeTab: 'simulate' | 'table';
  onTabChange: (tab: 'simulate' | 'table') => void;
  onHighlightStates: (states: string[]) => void;
  onClose: () => void;
}

export const BottomPanel: React.FC<BottomPanelProps> = ({
  automaton,
  isOpen,
  activeTab,
  onTabChange,
  onHighlightStates,
  onClose,
}) => {
  const [inputStr, setInputStr] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulateResponse | null>(null);

  if (!isOpen) return null;

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const resp = await simulateAutomaton(automaton, inputStr);
      setResult(resp);
      if (!resp.error && resp.final_states) {
        onHighlightStates(resp.final_states);
      }
    } finally {
      setLoading(false);
    }
  };

  // Build transition table columns: alphabet symbols sorted, plus ε if ε-NFA
  const symbols = [...new Set([...automaton.alphabet])].filter((s) => s !== EPSILON_SYMBOL).sort();
  if (automaton.type === 'EPSILON_NFA') {
    symbols.push(EPSILON_SYMBOL);
  }

  // Map: state -> symbol -> destinations[]
  const transitionMatrix: Record<string, Record<string, string[]>> = {};
  automaton.states.forEach((st) => {
    transitionMatrix[st] = {};
    symbols.forEach((sym) => {
      transitionMatrix[st][sym] = [];
    });
  });

  automaton.transitions.forEach((tr) => {
    if (transitionMatrix[tr.from_state]?.[tr.symbol]) {
      if (!transitionMatrix[tr.from_state][tr.symbol].includes(tr.to_state)) {
        transitionMatrix[tr.from_state][tr.symbol].push(tr.to_state);
      }
    }
  });

  const isDFA = automaton.type === 'DFA';

  return (
    <div className="bottom-panel" style={{ maxHeight: '260px' }}>
      <div className="bottom-tabs">
        <button
          className={`bottom-tab ${activeTab === 'table' ? 'active' : ''}`}
          onClick={() => onTabChange('table')}
        >
          📊 Transition Table (δ)
        </button>
        <button
          className={`bottom-tab ${activeTab === 'simulate' ? 'active' : ''}`}
          onClick={() => onTabChange('simulate')}
        >
          ▶ String Simulation
        </button>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
          <button
            className="tool-btn icon-only"
            onClick={onClose}
            title="Close Panel"
            style={{ fontSize: '14px', padding: '2px 8px' }}
          >
            ✕
          </button>
        </div>
      </div>

      <div className="bottom-content">
        {activeTab === 'table' && (
          <div className="table-panel">
            {automaton.states.length === 0 ? (
              <div style={{ padding: '12px', color: 'var(--text-tertiary)', fontSize: '13px' }}>
                No states created yet. Select the State tool (<kbd>S</kbd>) and click on the canvas to add states.
              </div>
            ) : (
              <table className="delta-table" style={{ fontSize: '13px' }}>
                <thead>
                  <tr>
                    <th className="th-state" style={{ minWidth: '130px' }}>
                      State
                    </th>
                    {symbols.map((sym) => (
                      <th
                        key={sym}
                        className={sym === EPSILON_SYMBOL ? 'th-eps' : ''}
                        style={{ minWidth: '100px', textAlign: 'center' }}
                      >
                        Input: <strong>{sym}</strong>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {automaton.states.map((st) => {
                    const isStart = st === automaton.start_state;
                    const isAcc = automaton.accepting_states.includes(st);
                    return (
                      <tr key={st}>
                        <td className="td-state">
                          {isStart && (
                            <span className="td-badge start" title="Start State">
                              ▶
                            </span>
                          )}
                          {isAcc && (
                            <span className="td-badge accept" title="Accepting State">
                              ◎
                            </span>
                          )}
                          <span style={{ fontWeight: 700 }}>{st}</span>
                        </td>
                        {symbols.map((sym) => {
                          const dests = transitionMatrix[st]?.[sym] || [];
                          let cellText = '—';
                          let isEmpty = false;

                          if (isDFA) {
                            if (dests.length > 0) {
                              cellText = dests[0];
                            } else {
                              cellText = '—';
                              isEmpty = true;
                            }
                          } else {
                            if (dests.length > 0) {
                              cellText = `{ ${dests.sort().join(', ')} }`;
                            } else {
                              cellText = '∅';
                              isEmpty = true;
                            }
                          }

                          return (
                            <td
                              key={sym}
                              className={isEmpty ? 'td-empty' : ''}
                              style={{
                                textAlign: 'center',
                                fontFamily: 'ui-monospace, monospace',
                                fontWeight: isEmpty ? 400 : 700,
                              }}
                            >
                              {cellText}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'simulate' && (
          <div className="sim-panel">
            <form onSubmit={handleSimulate} className="sim-form">
              <span className="sim-label">Test string:</span>
              <input
                type="text"
                className="sim-input"
                placeholder='e.g. 1234, 101001, or empty string ""'
                value={inputStr}
                onChange={(e) => setInputStr(e.target.value)}
              />
              <button type="submit" className="sim-btn" disabled={loading}>
                {loading ? '...' : 'Test String'}
              </button>
            </form>

            {result && (
              <>
                {result.error ? (
                  <div className="sim-result">
                    <span className="sim-verdict error">
                      ⚠ Simulation Error
                    </span>
                    <span className="sim-error">{result.error}</span>
                  </div>
                ) : (
                  <div className="sim-result">
                    <span
                      className={`sim-verdict ${result.accepted ? 'accept' : 'reject'}`}
                    >
                      {result.accepted ? '✓ ACCEPTED' : '✗ REJECTED'}
                    </span>
                    <span className="sim-input-echo">
                      Input: <code>"{result.input_string}"</code>
                    </span>
                    {result.steps.length > 0 && (
                      <div className="sim-path">
                        {result.steps.map((step, i) => (
                          <span
                            key={i}
                            className="sim-step"
                            onClick={() =>
                              onHighlightStates(
                                step.next_states.length ? step.next_states : step.current_states
                              )
                            }
                            title="Click to highlight in graph"
                          >
                            {'{' + step.current_states.join(',') + '}'}
                            {step.symbol && (
                              <span className="sim-step-sym">─({step.symbol})→</span>
                            )}
                          </span>
                        ))}
                        <span className="sim-step final">
                          {'{' + (result.final_states.join(',') || '∅') + '}'}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

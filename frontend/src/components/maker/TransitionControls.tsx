import React, { useState } from 'react';
import { AutomatonData, EPSILON_SYMBOL } from '../../types';

export interface TransitionControlsProps {
  automaton: AutomatonData;
  selectedState: string | null;
  selectedTransitionIndex: number | null;
  onAddTransition: (from: string, symbol: string, to: string) => void;
  onDeleteTransition: (index: number) => void;
}

export const TransitionControls: React.FC<TransitionControlsProps> = ({
  automaton,
  selectedState,
  selectedTransitionIndex,
  onAddTransition,
  onDeleteTransition,
}) => {
  const [fromState, setFromState] = useState<string>(selectedState || automaton.start_state || '');
  const [toState, setToState] = useState<string>(automaton.states[0] || '');
  const [symbol, setSymbol] = useState<string>('0');

  // Sync fromState with canvas selection
  React.useEffect(() => {
    if (selectedState && automaton.states.includes(selectedState)) {
      setFromState(selectedState);
    }
  }, [selectedState, automaton.states]);

  // Keep toState valid
  React.useEffect(() => {
    if (!automaton.states.includes(toState) && automaton.states.length > 0) {
      setToState(automaton.states[0]);
    }
  }, [automaton.states, toState]);

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    const sym = symbol.trim();
    if (!fromState || !toState || !sym) return;

    // Check DFA non-determinism constraint
    if (automaton.type === 'DFA') {
      const existing = automaton.transitions.find(
        (t) => t.from_state === fromState && t.symbol === sym
      );
      if (existing) {
        alert(
          `DFA Error: Transition from '${fromState}' on symbol '${sym}' already exists to '${existing.to_state}'.`
        );
        return;
      }
    }

    onAddTransition(fromState, sym, toState);
  };

  const handleSetEpsilon = () => {
    setSymbol(EPSILON_SYMBOL);
  };

  const isEpsilonAllowed = automaton.type === 'EPSILON_NFA';

  return (
    <div className="control-section">
      <h3 className="section-title">Transitions</h3>

      {automaton.states.length < 1 ? (
        <p className="hint-text">Add at least one state before creating transitions.</p>
      ) : (
        <form onSubmit={handleAdd} className="transition-form">
          <div className="transition-row">
            <div className="field-group">
              <label>Source (From):</label>
              <select
                value={fromState}
                onChange={(e) => setFromState(e.target.value)}
                className="select-input"
              >
                {automaton.states.map((s) => (
                  <option key={`from_${s}`} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div className="field-group">
              <label>Symbol:</label>
              <div className="symbol-input-wrapper">
                <input
                  type="text"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  placeholder="e.g. 0"
                  maxLength={5}
                  className="text-input text-center"
                />
                {isEpsilonAllowed && (
                  <button
                    type="button"
                    className="btn btn-xs btn-purple"
                    onClick={handleSetEpsilon}
                    title="Insert Epsilon Symbol"
                  >
                    ε
                  </button>
                )}
              </div>
            </div>

            <div className="field-group">
              <label>Target (To):</label>
              <select
                value={toState}
                onChange={(e) => setToState(e.target.value)}
                className="select-input"
              >
                {automaton.states.map((s) => (
                  <option key={`to_${s}`} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button type="submit" className="btn btn-primary w-full mt-2">
            + Add Transition ({fromState} --{symbol}--&gt; {toState})
          </button>
        </form>
      )}

      {/* Selected Transition Deletion */}
      {selectedTransitionIndex !== null && automaton.transitions[selectedTransitionIndex] && (
        <div className="selected-box mt-3">
          <div className="selected-header">
            <span>
              Selected Transition #{selectedTransitionIndex + 1}:
              <strong>
                {' '}
                {automaton.transitions[selectedTransitionIndex].from_state} --
                {automaton.transitions[selectedTransitionIndex].symbol}--&gt;{' '}
                {automaton.transitions[selectedTransitionIndex].to_state}
              </strong>
            </span>
          </div>
          <button
            className="btn btn-sm btn-danger w-full mt-2"
            onClick={() => onDeleteTransition(selectedTransitionIndex)}
          >
            🗑 Delete Selected Transition
          </button>
        </div>
      )}
    </div>
  );
};

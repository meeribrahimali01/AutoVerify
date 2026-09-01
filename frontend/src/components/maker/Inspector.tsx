import React, { useState } from 'react';
import { AutomatonData, EPSILON_SYMBOL } from '../../types';

interface InspectorProps {
  automaton: AutomatonData;
  selectedState: string | null;
  selectedTransitionIndex: number | null;
  validationErrors: string[];
  onRenameState: (oldName: string, newName: string) => void;
  onDeleteState: (name: string) => void;
  onSetStartState: (name: string) => void;
  onToggleAccepting: (name: string) => void;
  onDeleteTransition: (index: number) => void;
  onEditTransitionSymbol: (index: number, newSymbol: string) => string | null;
}

export const Inspector: React.FC<InspectorProps> = ({
  automaton, selectedState, selectedTransitionIndex, validationErrors,
  onRenameState, onDeleteState, onSetStartState, onToggleAccepting,
  onDeleteTransition, onEditTransitionSymbol,
}) => {
  const [renameValue, setRenameValue] = useState('');
  const [editSymbol, setEditSymbol] = useState('');
  const [editError, setEditError] = useState<string | null>(null);

  // State inspector
  if (selectedState) {
    const isStart = selectedState === automaton.start_state;
    const isAccepting = automaton.accepting_states.includes(selectedState);
    const stateTransitions = automaton.transitions.filter(
      t => t.from_state === selectedState || t.to_state === selectedState
    );

    return (
      <div className="inspector-panel">
        <div className="inspector-header">
          <span className="inspector-label">State</span>
          <span className="inspector-title">{selectedState}</span>
        </div>

        <div className="inspector-section">
          <div className="inspector-row">
            <span className="inspector-key">Name</span>
            <div className="inspector-inline-edit">
              <input
                type="text"
                className="inspector-input"
                placeholder={selectedState}
                value={renameValue}
                onChange={e => setRenameValue(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && renameValue.trim()) {
                    onRenameState(selectedState, renameValue.trim());
                    setRenameValue('');
                  }
                }}
              />
              {renameValue.trim() && (
                <button className="inspector-btn-sm" onClick={() => {
                  onRenameState(selectedState, renameValue.trim());
                  setRenameValue('');
                }}>✓</button>
              )}
            </div>
          </div>

          <div className="inspector-row">
            <span className="inspector-key">Start</span>
            <button
              className={`inspector-toggle ${isStart ? 'on' : ''}`}
              onClick={() => onSetStartState(selectedState)}
              disabled={isStart}
            >
              {isStart ? '▶ Start State' : 'Set as Start'}
            </button>
          </div>

          <div className="inspector-row">
            <span className="inspector-key">Accepting</span>
            <button
              className={`inspector-toggle ${isAccepting ? 'on accept' : ''}`}
              onClick={() => onToggleAccepting(selectedState)}
            >
              {isAccepting ? '◎ Accepting' : 'Not Accepting'}
            </button>
          </div>
        </div>

        {stateTransitions.length > 0 && (
          <div className="inspector-section">
            <span className="inspector-section-title">Transitions ({stateTransitions.length})</span>
            <div className="inspector-transition-list">
              {stateTransitions.map((t, _i) => {
                const idx = automaton.transitions.indexOf(t);
                return (
                  <div key={idx} className="inspector-tr-item">
                    <span>{t.from_state} <span className="tr-arrow">→</span> {t.to_state}</span>
                    <span className={`tr-symbol ${t.symbol === EPSILON_SYMBOL ? 'epsilon' : ''}`}>{t.symbol}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="inspector-actions">
          <button className="inspector-btn danger" onClick={() => onDeleteState(selectedState)}>
            Delete State
          </button>
        </div>
      </div>
    );
  }

  // Transition inspector
  if (selectedTransitionIndex !== null && automaton.transitions[selectedTransitionIndex]) {
    const t = automaton.transitions[selectedTransitionIndex];
    return (
      <div className="inspector-panel">
        <div className="inspector-header">
          <span className="inspector-label">Transition</span>
          <span className="inspector-title">{t.from_state} → {t.to_state}</span>
        </div>

        <div className="inspector-section">
          <div className="inspector-row">
            <span className="inspector-key">From</span>
            <span className="inspector-value">{t.from_state}</span>
          </div>
          <div className="inspector-row">
            <span className="inspector-key">To</span>
            <span className="inspector-value">{t.to_state}</span>
          </div>
          <div className="inspector-row">
            <span className="inspector-key">Symbol</span>
            <div className="inspector-inline-edit">
              <input
                type="text"
                className="inspector-input symbol-input"
                placeholder={t.symbol}
                value={editSymbol}
                onChange={e => { setEditSymbol(e.target.value); setEditError(null); }}
                onKeyDown={e => {
                  if (e.key === 'Enter' && editSymbol.trim()) {
                    const err = onEditTransitionSymbol(selectedTransitionIndex, editSymbol.trim());
                    if (err) setEditError(err); else { setEditSymbol(''); setEditError(null); }
                  }
                }}
              />
              {automaton.type === 'EPSILON_NFA' && (
                <button className="inspector-btn-sm epsilon" onClick={() => setEditSymbol(EPSILON_SYMBOL)}>ε</button>
              )}
            </div>
            {editError && <span className="inspector-error">{editError}</span>}
          </div>
        </div>

        <div className="inspector-actions">
          <button className="inspector-btn danger" onClick={() => onDeleteTransition(selectedTransitionIndex)}>
            Delete Transition
          </button>
        </div>
      </div>
    );
  }

  // Default: automaton overview
  const uniqueAlpha = new Set(automaton.alphabet);
  automaton.transitions.forEach(t => { if (t.symbol !== EPSILON_SYMBOL) uniqueAlpha.add(t.symbol); });
  const epsCount = automaton.transitions.filter(t => t.symbol === EPSILON_SYMBOL).length;

  return (
    <div className="inspector-panel">
      <div className="inspector-header">
        <span className="inspector-label">Automaton</span>
        <span className="inspector-title">{automaton.type === 'EPSILON_NFA' ? 'ε-NFA' : automaton.type}</span>
      </div>

      <div className="inspector-section">
        <div className="inspector-row">
          <span className="inspector-key">States</span>
          <span className="inspector-value">{automaton.states.length}</span>
        </div>
        <div className="inspector-row">
          <span className="inspector-key">Alphabet</span>
          <span className="inspector-value mono">{'{ ' + Array.from(uniqueAlpha).sort().join(', ') + ' }'}</span>
        </div>
        <div className="inspector-row">
          <span className="inspector-key">Transitions</span>
          <span className="inspector-value">{automaton.transitions.length}{epsCount > 0 ? ` (${epsCount} ε)` : ''}</span>
        </div>
        <div className="inspector-row">
          <span className="inspector-key">Start</span>
          <span className="inspector-value">{automaton.start_state || '—'}</span>
        </div>
        <div className="inspector-row">
          <span className="inspector-key">Accepting</span>
          <span className="inspector-value">{automaton.accepting_states.length > 0 ? automaton.accepting_states.join(', ') : '—'}</span>
        </div>
      </div>

      {validationErrors.length > 0 && (
        <div className="inspector-section">
          <span className="inspector-section-title error-title">Issues ({validationErrors.length})</span>
          <ul className="inspector-errors">
            {validationErrors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {automaton.states.length > 0 && validationErrors.length === 0 && (
        <div className="inspector-status valid">✓ Valid {automaton.type === 'EPSILON_NFA' ? 'ε-NFA' : automaton.type}</div>
      )}
    </div>
  );
};

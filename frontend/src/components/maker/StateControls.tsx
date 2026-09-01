import React, { useState } from 'react';
import { AutomatonData } from '../../types';

export interface StateControlsProps {
  automaton: AutomatonData;
  selectedState: string | null;
  onAddState: (name: string) => void;
  onDeleteState: (name: string) => void;
  onSetStartState: (name: string) => void;
  onToggleAccepting: (name: string) => void;
  onRenameState: (oldName: string, newName: string) => void;
}

export const StateControls: React.FC<StateControlsProps> = ({
  automaton,
  selectedState,
  onAddState,
  onDeleteState,
  onSetStartState,
  onToggleAccepting,
  onRenameState,
}) => {
  const [newStateName, setNewStateName] = useState('');
  const [renameValue, setRenameValue] = useState('');

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    const name = newStateName.trim();
    if (!name) return;
    if (automaton.states.includes(name)) {
      alert(`State '${name}' already exists.`);
      return;
    }
    onAddState(name);
    setNewStateName('');
  };

  const handleRename = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedState) return;
    const newName = renameValue.trim();
    if (!newName || newName === selectedState) return;
    if (automaton.states.includes(newName)) {
      alert(`State '${newName}' already exists.`);
      return;
    }
    onRenameState(selectedState, newName);
    setRenameValue('');
  };

  const isSelectedStart = selectedState === automaton.start_state;
  const isSelectedAccepting = selectedState ? automaton.accepting_states.includes(selectedState) : false;

  return (
    <div className="control-section">
      <h3 className="section-title">States Management</h3>

      {/* Add State Form */}
      <form onSubmit={handleAdd} className="input-group">
        <input
          type="text"
          placeholder="New state name (e.g. q3)"
          value={newStateName}
          onChange={(e) => setNewStateName(e.target.value)}
          className="text-input"
        />
        <button type="submit" className="btn btn-primary" disabled={!newStateName.trim()}>
          + Add State
        </button>
      </form>

      {/* Selected State Actions */}
      {selectedState ? (
        <div className="selected-box">
          <div className="selected-header">
            <span>
              Selected State: <strong>{selectedState}</strong>
            </span>
          </div>

          <div className="action-buttons-grid">
            <button
              className={`btn btn-sm ${isSelectedStart ? 'btn-active' : 'btn-outline'}`}
              onClick={() => onSetStartState(selectedState)}
              disabled={isSelectedStart}
            >
              {isSelectedStart ? '✓ Is Start State' : '▶ Set as Start'}
            </button>

            <button
              className={`btn btn-sm ${isSelectedAccepting ? 'btn-success' : 'btn-outline'}`}
              onClick={() => onToggleAccepting(selectedState)}
            >
              {isSelectedAccepting ? '✓ Accepting (Final)' : '◎ Set Accepting'}
            </button>
          </div>

          {/* Rename State */}
          <form onSubmit={handleRename} className="input-group mt-2">
            <input
              type="text"
              placeholder={`Rename '${selectedState}'`}
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              className="text-input text-input-sm"
            />
            <button type="submit" className="btn btn-sm btn-outline" disabled={!renameValue.trim()}>
              Rename
            </button>
          </form>

          <button
            className="btn btn-sm btn-danger mt-2 w-full"
            onClick={() => onDeleteState(selectedState)}
          >
            🗑 Delete State '{selectedState}'
          </button>
        </div>
      ) : (
        <p className="hint-text">Click a state on the canvas to edit or configure it.</p>
      )}
    </div>
  );
};

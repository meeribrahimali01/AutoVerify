import React from 'react';
import { useTheme } from '../../context/ThemeContext';
import { ToolMode } from '../../hooks/useAutomaton';

export interface ToolbarProps {
  activeTool: ToolMode;
  onToolChange: (tool: ToolMode) => void;
  automatonType: string;
  onTypeChange: (type: 'DFA' | 'NFA' | 'EPSILON_NFA') => void;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onFit: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onClear: () => void;
  onImportExport: () => void;
  onExportImage: () => void;
  validationStatus: 'valid' | 'error' | 'empty';
  onOpenTable: () => void;
  onOpenSimulate: () => void;
  bottomPanelOpen: boolean;
  activeBottomTab: 'simulate' | 'table';
}

const TOOLS: { mode: ToolMode; icon: string; label: string; shortcut: string }[] = [
  { mode: 'select',     icon: '⊹',  label: 'Select',     shortcut: 'V' },
  { mode: 'state',      icon: '◯',  label: 'State',      shortcut: 'S' },
  { mode: 'transition', icon: '→',  label: 'Transition', shortcut: 'T' },
  { mode: 'delete',     icon: '✕',  label: 'Delete',     shortcut: 'D' },
  { mode: 'start',      icon: '▶',  label: 'Start',      shortcut: '' },
  { mode: 'accepting',  icon: '◎',  label: 'Accepting',  shortcut: '' },
];

export const Toolbar: React.FC<ToolbarProps> = ({
  activeTool,
  onToolChange,
  automatonType,
  onTypeChange,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onFit,
  onZoomIn,
  onZoomOut,
  onClear,
  onImportExport,
  onExportImage,
  validationStatus,
  onOpenTable,
  onOpenSimulate,
  bottomPanelOpen,
  activeBottomTab,
}) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="av-toolbar">
      {/* Left: Type selector */}
      <div className="toolbar-section">
        <div className="type-switcher">
          {(['DFA', 'NFA', 'EPSILON_NFA'] as const).map((t) => (
            <button
              key={t}
              className={`type-btn ${automatonType === t ? 'active' : ''}`}
              onClick={() => onTypeChange(t)}
              title={t === 'EPSILON_NFA' ? 'Epsilon NFA' : t}
            >
              {t === 'EPSILON_NFA' ? 'ε-NFA' : t}
            </button>
          ))}
        </div>
        <div className="toolbar-divider" />
      </div>

      {/* Center: Tool buttons */}
      <div className="toolbar-section toolbar-tools">
        {TOOLS.map((t) => (
          <button
            key={t.mode}
            className={`tool-btn ${activeTool === t.mode ? 'active' : ''}`}
            onClick={() => onToolChange(t.mode)}
            title={`${t.label}${t.shortcut ? ` (${t.shortcut})` : ''}`}
          >
            <span className="tool-icon">{t.icon}</span>
            <span className="tool-label">{t.label}</span>
          </button>
        ))}

        <div className="toolbar-divider" />

        {/* Undo / Redo */}
        <button
          className="tool-btn icon-only"
          onClick={onUndo}
          disabled={!canUndo}
          title="Undo (Ctrl+Z)"
        >
          ↩
        </button>
        <button
          className="tool-btn icon-only"
          onClick={onRedo}
          disabled={!canRedo}
          title="Redo (Ctrl+Shift+Z)"
        >
          ↪
        </button>

        <div className="toolbar-divider" />

        {/* View */}
        <button className="tool-btn icon-only" onClick={onZoomIn} title="Zoom In">
          +
        </button>
        <button className="tool-btn icon-only" onClick={onZoomOut} title="Zoom Out">
          −
        </button>
        <button className="tool-btn icon-only" onClick={onFit} title="Fit to Content">
          ⊞
        </button>
      </div>

      {/* Right: Panels & Actions */}
      <div className="toolbar-section toolbar-actions">
        {/* Transition Table Button */}
        <button
          className={`tool-btn ${bottomPanelOpen && activeBottomTab === 'table' ? 'active' : ''}`}
          onClick={onOpenTable}
          title="Open Transition Table (δ)"
        >
          <span className="tool-icon">📊</span>
          <span className="tool-label">Transition Table</span>
        </button>

        {/* Simulation Button */}
        <button
          className={`tool-btn ${bottomPanelOpen && activeBottomTab === 'simulate' ? 'active' : ''}`}
          onClick={onOpenSimulate}
          title="Test / Simulate String"
        >
          <span className="tool-icon">▶</span>
          <span className="tool-label">Simulate</span>
        </button>

        <div className="toolbar-divider" />

        {/* Export Image Button */}
        <button
          className="tool-btn"
          onClick={onExportImage}
          title="Export Automaton Diagram as PNG / SVG"
        >
          <span className="tool-icon">🖼</span>
          <span className="tool-label">Export Image</span>
        </button>

        {/* Import / Export JSON */}
        <button
          className="tool-btn icon-only"
          onClick={onImportExport}
          title="Import / Export JSON"
        >
          ⇄
        </button>

        {/* Clear All */}
        <button className="tool-btn icon-only" onClick={onClear} title="Clear All">
          🗑
        </button>

        <div className="toolbar-divider" />

        {/* Validation badge */}
        <span
          className={`validation-badge ${validationStatus}`}
          title={
            validationStatus === 'valid'
              ? 'Valid automaton'
              : validationStatus === 'empty'
              ? 'No states'
              : 'Has issues'
          }
        >
          {validationStatus === 'valid'
            ? '✓'
            : validationStatus === 'empty'
            ? '○'
            : '⚠'}
        </span>

        {/* Theme toggle */}
        <button
          className="tool-btn icon-only theme-toggle"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
        >
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
      </div>
    </div>
  );
};

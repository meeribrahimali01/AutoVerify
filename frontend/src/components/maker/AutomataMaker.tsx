import React, { useCallback, useEffect, useRef, useState } from 'react';
import './AutomataMaker.css';
import { AutomatonData, AutomatonType, EPSILON_SYMBOL } from '../../types';
import { useAutomaton, ToolMode } from '../../hooks/useAutomaton';

import { GraphCanvas, GraphCanvasHandle, ExportOptions } from '../graph/GraphCanvas';
import { Toolbar } from './Toolbar';
import { Inspector } from './Inspector';
import { BottomPanel } from './BottomPanel';
import { ContextMenu, ContextMenuAction } from './ContextMenu';
import { TransitionPopover } from './TransitionPopover';
import { ImportExportModal } from './ImportExportModal';
import { ExportImageModal } from './ExportImageModal';

const INITIAL: AutomatonData = {
  type: 'DFA',
  states: [],
  alphabet: ['0', '1'],
  start_state: '',
  accepting_states: [],
  transitions: [],
};

export const AutomataMaker: React.FC = () => {
  const {
    automaton,
    history,
    addState,
    deleteState,
    renameState,
    setStartState,
    toggleAccepting,
    addTransition,
    deleteTransition,
    editTransitionSymbol,
    setType,
    clearAll,
    loadAutomaton,
    nextStateName,
    validationErrors,
  } = useAutomaton(INITIAL);

  const [activeTool, setActiveTool] = useState<ToolMode>('select');
  const [selectedState, setSelectedState] = useState<string | null>(null);
  const [selectedTransitionIndex, setSelectedTransitionIndex] = useState<number | null>(null);
  const [activeStates, setActiveStates] = useState<string[]>([]);
  const [bottomPanelOpen, setBottomPanelOpen] = useState(false);
  const [activeBottomTab, setActiveBottomTab] = useState<'simulate' | 'table'>('table');
  const [importExportOpen, setImportExportOpen] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'error' | 'info' } | null>(null);

  // GraphCanvas imperative handle
  const graphRef = useRef<GraphCanvasHandle>(null);

  // Context menu state
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; actions: ContextMenuAction[] } | null>(null);

  // Transition popover state
  const [trPopover, setTrPopover] = useState<{ x: number; y: number; from: string; to: string } | null>(null);

  // Show toast
  const showToast = useCallback((message: string, type: 'error' | 'info' = 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  }, []);

  // Canvas click → create state at exact model position
  const handleCanvasClickCreate = useCallback(
    (x: number, y: number) => {
      const name = nextStateName();
      console.log('[AutoVerify] creating state', {
        name,
        position: { x, y },
      });
      // Record position in authoritative graph handle first
      graphRef.current?.setNodePosition(name, x, y);
      addState(name);
      setSelectedState(name);
      setSelectedTransitionIndex(null);
    },
    [nextStateName, addState]
  );

  // Transition draw complete → show popover
  const handleTransitionDraw = useCallback(
    (from: string, to: string, screenX: number, screenY: number) => {
      setTrPopover({ x: screenX, y: screenY, from, to });
    },
    []
  );

  // Transition popover confirm
  const handleTransitionConfirm = useCallback(
    (symbol: string) => {
      if (!trPopover) return;
      const err = addTransition(trPopover.from, symbol, trPopover.to);
      if (err) {
        showToast(err);
      }
      setTrPopover(null);
    },
    [trPopover, addTransition, showToast]
  );

  // Export handler
  const handleExport = useCallback(
    async (options: ExportOptions) => {
      if (!graphRef.current) {
        showToast('⚠ Graph canvas not ready', 'error');
        return;
      }
      const res = await graphRef.current.exportImage(options);
      if (res.success) {
        showToast(`✓ Automaton exported as ${options.format?.toUpperCase() || 'PNG'}`, 'info');
      } else {
        showToast(res.error || '⚠ Could not export automaton', 'error');
      }
    },
    [showToast]
  );

  // Context menu for state
  const handleContextMenuState = useCallback(
    (name: string, x: number, y: number) => {
      const isStart = name === automaton.start_state;
      const isAcc = automaton.accepting_states.includes(name);
      setCtxMenu({
        x,
        y,
        actions: [
          {
            label: 'Rename...',
            icon: '✏',
            onClick: () => {
              const newName = prompt(`Rename state '${name}':`, name);
              if (newName && newName !== name) {
                if (automaton.states.includes(newName)) {
                  showToast(`State '${newName}' already exists.`);
                  return;
                }
                graphRef.current?.renameNodePosition(name, newName);
                renameState(name, newName);
              }
            },
          },
          {
            label: isStart ? 'Start State ✓' : 'Set as Start',
            icon: '▶',
            disabled: isStart,
            onClick: () => setStartState(name),
          },
          {
            label: isAcc ? 'Unmark Accepting' : 'Make Accepting',
            icon: '◎',
            onClick: () => toggleAccepting(name),
          },
          {
            label: 'Delete',
            icon: '🗑',
            danger: true,
            onClick: () => {
              graphRef.current?.removeNodePosition(name);
              deleteState(name);
              if (selectedState === name) setSelectedState(null);
            },
          },
        ],
      });
    },
    [automaton, selectedState, renameState, setStartState, toggleAccepting, deleteState, showToast]
  );

  // Context menu for edge
  const handleContextMenuEdge = useCallback(
    (index: number, x: number, y: number) => {
      const t = automaton.transitions[index];
      if (!t) return;
      setCtxMenu({
        x,
        y,
        actions: [
          {
            label: `Edit Symbol (${t.symbol})`,
            icon: '✏',
            onClick: () => {
              const newSym = prompt(`New symbol for ${t.from_state} → ${t.to_state}:`, t.symbol);
              if (newSym !== null && newSym.trim()) {
                const err = editTransitionSymbol(index, newSym.trim());
                if (err) showToast(err);
              }
            },
          },
          {
            label: 'Delete',
            icon: '🗑',
            danger: true,
            onClick: () => {
              deleteTransition(index);
              if (selectedTransitionIndex === index) setSelectedTransitionIndex(null);
            },
          },
        ],
      });
    },
    [automaton.transitions, editTransitionSymbol, deleteTransition, selectedTransitionIndex, showToast]
  );

  // Start/Accepting tool handlers
  const handleStartTool = useCallback(
    (name: string) => {
      setStartState(name);
      setActiveTool('select');
    },
    [setStartState]
  );

  const handleAcceptingTool = useCallback(
    (name: string) => {
      toggleAccepting(name);
    },
    [toggleAccepting]
  );

  // Type change
  const handleTypeChange = useCallback(
    (type: AutomatonType) => {
      if (type === automaton.type) return;
      const hasEps = automaton.transitions.some((t) => t.symbol === EPSILON_SYMBOL);
      const hasNondet = (() => {
        const seen = new Set<string>();
        return automaton.transitions.some((t) => {
          const key = `${t.from_state}|${t.symbol}`;
          if (seen.has(key)) return true;
          seen.add(key);
          return false;
        });
      })();

      if (type === 'DFA' && (hasEps || hasNondet)) {
        if (
          !confirm(
            'Switching to DFA will remove epsilon transitions and non-deterministic transitions. Continue?'
          )
        )
          return;
      } else if (type === 'NFA' && hasEps) {
        if (!confirm('Switching to NFA will remove epsilon transitions. Continue?')) return;
      }
      setType(type);
    },
    [automaton, setType]
  );

  // Clear all
  const handleClear = useCallback(() => {
    if (automaton.states.length === 0) return;
    if (!confirm('Clear all states and transitions?')) return;
    graphRef.current?.clearNodePositions();
    clearAll();
    setSelectedState(null);
    setSelectedTransitionIndex(null);
    setActiveStates([]);
  }, [automaton.states.length, clearAll]);

  // Load imported or preset automaton with clean circle layout
  const handleImportAutomaton = useCallback(
    (data: AutomatonData) => {
      graphRef.current?.clearNodePositions();
      if (data.states.length > 1) {
        const radius = Math.max(120, data.states.length * 35);
        const centerX = 350;
        const centerY = 250;
        data.states.forEach((st, idx) => {
          const angle = (2 * Math.PI * idx) / data.states.length;
          const x = centerX + radius * Math.cos(angle);
          const y = centerY + radius * Math.sin(angle);
          graphRef.current?.setNodePosition(st, x, y);
        });
      }
      loadAutomaton(data);
      setSelectedState(data.start_state || null);
      setSelectedTransitionIndex(null);
      setActiveStates([]);
    },
    [loadAutomaton]
  );

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const inInput =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable;
      if (inInput) return;

      // Undo/Redo
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        history.undo();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === 'Z' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        history.redo();
        return;
      }

      // Tool shortcuts
      switch (e.key.toLowerCase()) {
        case 'v':
          setActiveTool('select');
          break;
        case 's':
          e.preventDefault();
          setActiveTool('state');
          break;
        case 't':
          setActiveTool('transition');
          break;
        case 'd':
          setActiveTool('delete');
          break;
        case 'delete':
          if (selectedState) {
            graphRef.current?.removeNodePosition(selectedState);
            deleteState(selectedState);
            setSelectedState(null);
          } else if (selectedTransitionIndex !== null) {
            deleteTransition(selectedTransitionIndex);
            setSelectedTransitionIndex(null);
          }
          break;
        case 'escape':
          setSelectedState(null);
          setSelectedTransitionIndex(null);
          setCtxMenu(null);
          setTrPopover(null);
          setActiveTool('select');
          break;
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [history, selectedState, selectedTransitionIndex, deleteState, deleteTransition]);

  // Validation status
  const validationStatus =
    automaton.states.length === 0
      ? ('empty' as const)
      : validationErrors.length === 0
      ? ('valid' as const)
      : ('error' as const);

  // Zoom controls
  const handleZoomIn = () => {
    const container = document.querySelector('.graph-canvas > div');
    if (container) {
      const cy = (container as any)._cyreg?.cy;
      if (cy) cy.zoom(cy.zoom() * 1.25);
    }
  };
  const handleZoomOut = () => {
    const container = document.querySelector('.graph-canvas > div');
    if (container) {
      const cy = (container as any)._cyreg?.cy;
      if (cy) cy.zoom(cy.zoom() * 0.8);
    }
  };
  const handleFit = () => {
    const container = document.querySelector('.graph-canvas > div');
    if (container) {
      const cy = (container as any)._cyreg?.cy;
      if (cy) cy.fit(undefined, 40);
    }
  };

  // Open Transition Table
  const handleOpenTable = () => {
    if (bottomPanelOpen && activeBottomTab === 'table') {
      setBottomPanelOpen(false);
    } else {
      setActiveBottomTab('table');
      setBottomPanelOpen(true);
    }
  };

  // Open Simulation
  const handleOpenSimulate = () => {
    if (bottomPanelOpen && activeBottomTab === 'simulate') {
      setBottomPanelOpen(false);
    } else {
      setActiveBottomTab('simulate');
      setBottomPanelOpen(true);
    }
  };

  return (
    <div className="maker-workspace">
      {/* Toolbar */}
      <Toolbar
        activeTool={activeTool}
        onToolChange={setActiveTool}
        automatonType={automaton.type}
        onTypeChange={handleTypeChange}
        canUndo={history.canUndo}
        canRedo={history.canRedo}
        onUndo={history.undo}
        onRedo={history.redo}
        onFit={handleFit}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onClear={handleClear}
        onImportExport={() => setImportExportOpen(true)}
        onExportImage={() => setExportModalOpen(true)}
        validationStatus={validationStatus}
        onOpenTable={handleOpenTable}
        onOpenSimulate={handleOpenSimulate}
        bottomPanelOpen={bottomPanelOpen}
        activeBottomTab={activeBottomTab}
      />

      {/* Main workspace area */}
      <div className="maker-body">
        {/* Canvas — fills available space */}
        <div className="maker-canvas-area">
          <GraphCanvas
            ref={graphRef}
            automaton={automaton}
            activeTool={activeTool}
            selectedState={selectedState}
            selectedTransitionIndex={selectedTransitionIndex}
            activeStates={activeStates}
            onSelectState={(st) => {
              setSelectedState(st);
              setSelectedTransitionIndex(null);
            }}
            onSelectTransition={(idx) => {
              setSelectedTransitionIndex(idx);
              setSelectedState(null);
            }}
            onCanvasClickCreate={handleCanvasClickCreate}
            onTransitionDraw={handleTransitionDraw}
            onDeleteState={(name) => {
              graphRef.current?.removeNodePosition(name);
              deleteState(name);
              if (selectedState === name) setSelectedState(null);
            }}
            onDeleteTransition={(idx) => {
              deleteTransition(idx);
              if (selectedTransitionIndex === idx) setSelectedTransitionIndex(null);
            }}
            onContextMenuState={handleContextMenuState}
            onContextMenuEdge={handleContextMenuEdge}
            onStartTool={handleStartTool}
            onAcceptingTool={handleAcceptingTool}
          />
        </div>

        {/* Inspector panel — right side */}
        <div className="maker-inspector">
          <Inspector
            automaton={automaton}
            selectedState={selectedState}
            selectedTransitionIndex={selectedTransitionIndex}
            validationErrors={validationErrors}
            onRenameState={(old, nw) => {
              graphRef.current?.renameNodePosition(old, nw);
              renameState(old, nw);
              if (selectedState === old) setSelectedState(nw);
            }}
            onDeleteState={(name) => {
              graphRef.current?.removeNodePosition(name);
              deleteState(name);
              setSelectedState(null);
            }}
            onSetStartState={setStartState}
            onToggleAccepting={toggleAccepting}
            onDeleteTransition={(idx) => {
              deleteTransition(idx);
              setSelectedTransitionIndex(null);
            }}
            onEditTransitionSymbol={editTransitionSymbol}
          />
        </div>
      </div>

      {/* Bottom panel */}
      <BottomPanel
        automaton={automaton}
        isOpen={bottomPanelOpen}
        activeTab={activeBottomTab}
        onTabChange={setActiveBottomTab}
        onHighlightStates={setActiveStates}
        onClose={() => setBottomPanelOpen(false)}
      />

      {/* Context menu */}
      {ctxMenu && (
        <ContextMenu
          x={ctxMenu.x}
          y={ctxMenu.y}
          actions={ctxMenu.actions}
          onClose={() => setCtxMenu(null)}
        />
      )}

      {/* Transition popover */}
      {trPopover && (
        <TransitionPopover
          x={trPopover.x}
          y={trPopover.y}
          fromState={trPopover.from}
          toState={trPopover.to}
          isEpsilonNFA={automaton.type === 'EPSILON_NFA'}
          onConfirm={handleTransitionConfirm}
          onCancel={() => setTrPopover(null)}
        />
      )}

      {/* Import/Export JSON modal */}
      <ImportExportModal
        automaton={automaton}
        isOpen={importExportOpen}
        onClose={() => setImportExportOpen(false)}
        onImport={handleImportAutomaton}
      />

      {/* Export Image modal */}
      <ExportImageModal
        isOpen={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
        automatonType={automaton.type}
        onExport={handleExport}
      />

      {/* Toast notification */}
      {toast && <div className={`av-toast ${toast.type}`}>{toast.message}</div>}
    </div>
  );
};

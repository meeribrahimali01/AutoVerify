import React, { useEffect, useImperativeHandle, useRef } from 'react';
import cytoscape, { Core, EventObject, NodeSingular, EdgeSingular } from 'cytoscape';
import { AutomatonData, EPSILON_SYMBOL } from '../../types';
import { ToolMode } from '../../hooks/useAutomaton';
import { useTheme } from '../../context/ThemeContext';

export interface ExportOptions {
  format?: 'png' | 'svg';
  background?: 'white' | 'theme' | 'transparent';
  scale?: number;
  filename?: string;
}

export interface GraphCanvasHandle {
  setNodePosition: (name: string, x: number, y: number) => void;
  removeNodePosition: (name: string) => void;
  renameNodePosition: (oldName: string, newName: string) => void;
  clearNodePositions: () => void;
  exportImage: (options?: ExportOptions) => Promise<{ success: boolean; error?: string }>;
  getCytoscape: () => Core | null;
}

export interface GraphCanvasProps {
  automaton?: AutomatonData;
  activeTool?: ToolMode;
  selectedState?: string | null;
  selectedTransitionIndex?: number | null;
  activeStates?: string[];
  onSelectState?: (name: string | null) => void;
  onSelectTransition?: (index: number | null) => void;
  onCanvasClickCreate?: (x: number, y: number) => void;
  onTransitionDraw?: (from: string, to: string, screenX: number, screenY: number) => void;
  onDeleteState?: (name: string) => void;
  onDeleteTransition?: (index: number) => void;
  onContextMenuState?: (name: string, screenX: number, screenY: number) => void;
  onContextMenuEdge?: (index: number, screenX: number, screenY: number) => void;
  onStartTool?: (name: string) => void;
  onAcceptingTool?: (name: string) => void;
  className?: string;
}

const DEFAULT_AUTOMATON: AutomatonData = {
  type: 'DFA',
  states: [],
  alphabet: ['0', '1'],
  start_state: '',
  accepting_states: [],
  transitions: [],
};

// Helper to get Cytoscape style props from theme
function makeStyles(isDark: boolean): any[] {
  return [
    {
      selector: 'node',
      style: {
        label: 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'font-size': '13px',
        'font-weight': 'bold',
        'font-family': 'Inter, system-ui, sans-serif',
        color: isDark ? '#e2e8f0' : '#1e293b',
        'background-color': isDark ? '#22252f' : '#ffffff',
        'border-width': 2,
        'border-color': isDark ? '#64748b' : '#64748b',
        width: 50,
        height: 50,
        'overlay-opacity': 0,
      },
    },
    {
      selector: 'node.start',
      style: {
        'border-color': isDark ? '#3b82f6' : '#2563eb',
        'border-width': 3,
        'background-color': isDark ? '#1e3a5f' : '#eff6ff',
      },
    },
    {
      selector: 'node.accepting',
      style: {
        'border-width': 6,
        'border-style': 'double',
        'border-color': isDark ? '#34d399' : '#059669',
      },
    },
    {
      selector: 'node.selected-node',
      style: {
        'border-color': isDark ? '#fbbf24' : '#f59e0b',
        'border-width': 4,
        'background-color': isDark ? '#422006' : '#fef3c7',
      },
    },
    {
      selector: 'node.active-sim',
      style: {
        'background-color': isDark ? '#059669' : '#10b981',
        color: '#ffffff',
        'border-color': isDark ? '#34d399' : '#047857',
        'border-width': 4,
      },
    },
    {
      selector: 'node.drawing-source',
      style: {
        'border-color': isDark ? '#a78bfa' : '#7c3aed',
        'border-width': 4,
        'border-style': 'dashed',
      },
    },
    {
      selector: 'edge',
      style: {
        label: 'data(symbol)',
        'font-size': '12px',
        'font-weight': 'bold',
        'font-family': 'Inter, system-ui, sans-serif',
        color: isDark ? '#e2e8f0' : '#0f172a',
        'text-background-color': isDark ? '#1a1d27' : '#ffffff',
        'text-background-opacity': 0.88,
        'text-background-padding': '3px',
        'text-background-shape': 'roundrectangle',
        'curve-style': 'bezier',
        'control-point-step-size': 40,
        'target-arrow-shape': 'triangle',
        'target-arrow-color': isDark ? '#64748b' : '#64748b',
        'line-color': isDark ? '#64748b' : '#64748b',
        width: 2,
        'arrow-scale': 1.15,
        'loop-direction': '0deg',
        'loop-sweep': '-60deg',
      },
    },
    {
      selector: 'edge.epsilon',
      style: {
        'line-color': isDark ? '#a78bfa' : '#8b5cf6',
        'target-arrow-color': isDark ? '#a78bfa' : '#8b5cf6',
        color: isDark ? '#c4b5fd' : '#7c3aed',
        'line-style': 'dashed',
      },
    },
    {
      selector: 'edge.selected-edge',
      style: {
        'line-color': isDark ? '#fbbf24' : '#f59e0b',
        'target-arrow-color': isDark ? '#fbbf24' : '#f59e0b',
        width: 3.5,
        color: isDark ? '#fbbf24' : '#b45309',
      },
    },
    // Start arrow indicator (hidden pseudo-node + edge)
    {
      selector: 'node.start-arrow',
      style: {
        width: 1,
        height: 1,
        'background-opacity': 0,
        'border-opacity': 0,
        label: '',
        events: 'no',
        'overlay-opacity': 0,
      },
    },
    {
      selector: 'edge.start-arrow-edge',
      style: {
        'line-color': isDark ? '#3b82f6' : '#2563eb',
        'target-arrow-color': isDark ? '#3b82f6' : '#2563eb',
        'target-arrow-shape': 'triangle',
        width: 2.5,
        'arrow-scale': 1.3,
        'curve-style': 'straight',
        label: '',
      },
    },
  ];
}

export const GraphCanvas = React.forwardRef<GraphCanvasHandle, GraphCanvasProps>(
  (
    {
      automaton = DEFAULT_AUTOMATON,
      activeTool = 'select',
      selectedState = null,
      selectedTransitionIndex = null,
      activeStates = [],
      onSelectState,
      onSelectTransition,
      onCanvasClickCreate,
      onTransitionDraw,
      onDeleteState,
      onDeleteTransition,
      onContextMenuState,
      onContextMenuEdge,
      onStartTool,
      onAcceptingTool,
      className = '',
    },
    ref
  ) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const cyRef = useRef<Core | null>(null);
    const { theme } = useTheme();
    const isDark = theme === 'dark';

    // Refs for transition drawing
    const drawingRef = useRef<{ from: string } | null>(null);

    // Persistent Authoritative Position Map
    const posMapRef = useRef<Record<string, { x: number; y: number }>>({});

    // Ref container for callbacks to avoid stale closures in Cytoscape handlers
    const callbacksRef = useRef({
      activeTool,
      onSelectState,
      onSelectTransition,
      onCanvasClickCreate,
      onTransitionDraw,
      onDeleteState,
      onDeleteTransition,
      onContextMenuState,
      onContextMenuEdge,
      onStartTool,
      onAcceptingTool,
    });

    // Update callbacksRef synchronously on every render
    callbacksRef.current = {
      activeTool,
      onSelectState,
      onSelectTransition,
      onCanvasClickCreate,
      onTransitionDraw,
      onDeleteState,
      onDeleteTransition,
      onContextMenuState,
      onContextMenuEdge,
      onStartTool,
      onAcceptingTool,
    };

    // Expose imperative handle
    useImperativeHandle(ref, () => ({
      getCytoscape: () => cyRef.current,
      setNodePosition: (name: string, x: number, y: number) => {
        posMapRef.current[name] = { x, y };
      },
      removeNodePosition: (name: string) => {
        delete posMapRef.current[name];
      },
      renameNodePosition: (oldName: string, newName: string) => {
        if (posMapRef.current[oldName]) {
          posMapRef.current[newName] = posMapRef.current[oldName];
          delete posMapRef.current[oldName];
        }
      },
      clearNodePositions: () => {
        posMapRef.current = {};
      },
      exportImage: async (options: ExportOptions = {}) => {
        const cy = cyRef.current;
        if (!cy || cy.nodes(':not(.start-arrow)').length === 0) {
          return {
            success: false,
            error: 'Canvas is empty. Add states to your automaton before exporting.',
          };
        }

        const format = options.format || 'png';
        const bgChoice = options.background || 'white';
        let bgValue: string | undefined = '#ffffff';
        if (bgChoice === 'theme') {
          bgValue = isDark ? '#12141a' : '#f8fafc';
        } else if (bgChoice === 'transparent') {
          bgValue = undefined;
        }

        const filename =
          options.filename ||
          `AutoVerify-${automaton.type === 'EPSILON_NFA' ? 'eNFA' : automaton.type}.${format}`;

        try {
          if (format === 'png') {
            // If exporting on white background in dark mode, temporarily apply clean light styles for high contrast
            if (bgChoice === 'white' && isDark) {
              cy.style(makeStyles(false)).update();
            }

            const blob = cy.png({
              output: 'blob',
              full: true,
              scale: options.scale || 3,
              bg: bgValue,
            }) as Blob;

            // Restore dark styles if changed
            if (bgChoice === 'white' && isDark) {
              cy.style(makeStyles(true)).update();
            }

            const blobUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);

            return { success: true };
          } else if (format === 'svg') {
            const elements = cy.elements();
            const bb = elements.boundingBox({});
            const padding = 50;
            const minX = bb.x1 - padding;
            const minY = bb.y1 - padding;
            const width = Math.max(200, bb.w + padding * 2);
            const height = Math.max(200, bb.h + padding * 2);

            const isLightBg = bgChoice === 'white' || (!isDark && bgChoice === 'theme');
            const strokeColor = isLightBg ? '#475569' : '#94a3b8';
            const nodeFill = isLightBg ? '#ffffff' : '#1e293b';
            const textColor = isLightBg ? '#0f172a' : '#f8fafc';
            const startColor = '#2563eb';
            const accColor = isLightBg ? '#059669' : '#10b981';

            let svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${minX} ${minY} ${width} ${height}" width="${width}" height="${height}">\n`;

            if (bgValue) {
              svgContent += `  <rect x="${minX}" y="${minY}" width="${width}" height="${height}" fill="${bgValue}"/>\n`;
            }

            svgContent += `  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="${strokeColor}"/>
    </marker>
    <marker id="start-arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="${startColor}"/>
    </marker>
  </defs>\n`;

            // Draw edges
            cy.edges().forEach((edge) => {
              const src = edge.source();
              const tgt = edge.target();
              const isStartArrow = edge.hasClass('start-arrow-edge');
              const isEps = edge.hasClass('epsilon');

              if (src.length && tgt.length) {
                const sp = src.position();
                const tp = tgt.position();
                const sym = edge.data('symbol') || '';

                if (isStartArrow) {
                  svgContent += `  <line x1="${sp.x}" y1="${sp.y}" x2="${tp.x}" y2="${tp.y}" stroke="${startColor}" stroke-width="2.5" marker-end="url(#start-arrow)"/>\n`;
                } else if (src.id() === tgt.id()) {
                  // Self-loop
                  const r = 25;
                  const loopPath = `M ${sp.x - 10} ${sp.y - r} C ${sp.x - 30} ${sp.y - 75}, ${sp.x + 30} ${sp.y - 75}, ${sp.x + 10} ${sp.y - r}`;
                  svgContent += `  <path d="${loopPath}" fill="none" stroke="${isEps ? '#8b5cf6' : strokeColor}" stroke-width="2" ${isEps ? 'stroke-dasharray="4 4"' : ''} marker-end="url(#arrow)"/>\n`;
                  svgContent += `  <rect x="${sp.x - 12}" y="${sp.y - 82}" width="24" height="18" rx="4" fill="${bgValue || '#ffffff'}" opacity="0.9"/>\n`;
                  svgContent += `  <text x="${sp.x}" y="${sp.y - 68}" text-anchor="middle" font-family="Inter, sans-serif" font-size="13" font-weight="bold" fill="${isEps ? '#8b5cf6' : textColor}">${sym}</text>\n`;
                } else {
                  svgContent += `  <line x1="${sp.x}" y1="${sp.y}" x2="${tp.x}" y2="${tp.y}" stroke="${isEps ? '#8b5cf6' : strokeColor}" stroke-width="2" ${isEps ? 'stroke-dasharray="4 4"' : ''} marker-end="url(#arrow)"/>\n`;
                  const mx = (sp.x + tp.x) / 2;
                  const my = (sp.y + tp.y) / 2;
                  svgContent += `  <rect x="${mx - 14}" y="${my - 12}" width="28" height="18" rx="4" fill="${bgValue || '#ffffff'}" opacity="0.9"/>\n`;
                  svgContent += `  <text x="${mx}" y="${my + 2}" text-anchor="middle" font-family="Inter, sans-serif" font-size="13" font-weight="bold" fill="${isEps ? '#8b5cf6' : textColor}">${sym}</text>\n`;
                }
              }
            });

            // Draw nodes
            cy.nodes(':not(.start-arrow)').forEach((node) => {
              const pos = node.position();
              const name = node.data('label') || node.id();
              const isStart = node.hasClass('start');
              const isAcc = node.hasClass('accepting');

              const nodeStroke = isStart ? startColor : isAcc ? accColor : strokeColor;
              const nodeStrokeWidth = isStart ? 3 : 2;

              svgContent += `  <circle cx="${pos.x}" cy="${pos.y}" r="25" fill="${nodeFill}" stroke="${nodeStroke}" stroke-width="${nodeStrokeWidth}"/>\n`;

              if (isAcc) {
                svgContent += `  <circle cx="${pos.x}" cy="${pos.y}" r="20" fill="none" stroke="${accColor}" stroke-width="2"/>\n`;
              }

              svgContent += `  <text x="${pos.x}" y="${pos.y + 4}" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" font-weight="bold" fill="${textColor}">${name}</text>\n`;
            });

            svgContent += `</svg>`;

            const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
            const blobUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);

            return { success: true };
          }
          return { success: false, error: `Unsupported format: ${format}` };
        } catch (err: any) {
          return {
            success: false,
            error: err.message || 'Error occurred during image export.',
          };
        }
      },
    }));

    // Create cy instance once
    useEffect(() => {
      if (!containerRef.current) return;
      const cy = cytoscape({
        container: containerRef.current,
        boxSelectionEnabled: false,
        autounselectify: true,
        style: makeStyles(isDark),
        elements: [],
        minZoom: 0.25,
        maxZoom: 4,
        wheelSensitivity: 0.3,
      });

      cyRef.current = cy;

      if (containerRef.current) {
        (containerRef.current as any)._cyreg = { cy };
      }

      // --- Node events ---
      cy.on('tap', 'node', (evt: EventObject) => {
        const node = evt.target as NodeSingular;
        if (node.hasClass('start-arrow')) return;
        const stateName = node.id();
        const curTool = callbacksRef.current.activeTool;

        if (curTool === 'select') {
          callbacksRef.current.onSelectState?.(stateName);
          callbacksRef.current.onSelectTransition?.(null);
        } else if (curTool === 'delete') {
          callbacksRef.current.onDeleteState?.(stateName);
        } else if (curTool === 'start') {
          callbacksRef.current.onStartTool?.(stateName);
        } else if (curTool === 'accepting') {
          callbacksRef.current.onAcceptingTool?.(stateName);
        } else if (curTool === 'transition') {
          if (!drawingRef.current) {
            drawingRef.current = { from: stateName };
            node.addClass('drawing-source');
          } else {
            const from = drawingRef.current.from;
            const to = stateName;
            const fromNode = cy.getElementById(from);
            fromNode.removeClass('drawing-source');
            drawingRef.current = null;

            const renderedPos = node.renderedPosition();
            const rect = containerRef.current?.getBoundingClientRect();
            const screenX = (rect?.left || 0) + renderedPos.x;
            const screenY = (rect?.top || 0) + renderedPos.y;
            callbacksRef.current.onTransitionDraw?.(from, to, screenX, screenY);
          }
        }
      });

      // --- Edge events ---
      cy.on('tap', 'edge', (evt: EventObject) => {
        const edge = evt.target as EdgeSingular;
        if (edge.hasClass('start-arrow-edge')) return;
        const trIdx = edge.data('transitionIndex');
        if (trIdx === undefined) return;
        const curTool = callbacksRef.current.activeTool;

        if (curTool === 'select') {
          callbacksRef.current.onSelectTransition?.(trIdx);
          callbacksRef.current.onSelectState?.(null);
        } else if (curTool === 'delete') {
          callbacksRef.current.onDeleteTransition?.(trIdx);
        }
      });

      // --- Background tap ---
      cy.on('tap', (evt: EventObject) => {
        const isBackground = evt.target === cy;
        const curTool = callbacksRef.current.activeTool;

        console.log('[AutoVerify] canvas tap', {
          targetIsCy: isBackground,
          tool: curTool,
          position: evt.position,
        });

        if (!isBackground) return;

        if (drawingRef.current) {
          const fromNode = cy.getElementById(drawingRef.current.from);
          fromNode.removeClass('drawing-source');
          drawingRef.current = null;
        }

        if (curTool === 'select') {
          callbacksRef.current.onSelectState?.(null);
          callbacksRef.current.onSelectTransition?.(null);
        } else if (curTool === 'state') {
          const pos = evt.position;
          console.log('[AutoVerify] background tap in state mode at', pos);
          callbacksRef.current.onCanvasClickCreate?.(pos.x, pos.y);
        }
      });

      // --- Context menu on node ---
      cy.on('cxttap', 'node', (evt: EventObject) => {
        const node = evt.target as NodeSingular;
        if (node.hasClass('start-arrow')) return;
        evt.originalEvent?.preventDefault();
        const oe = evt.originalEvent as MouseEvent;
        callbacksRef.current.onContextMenuState?.(node.id(), oe.clientX, oe.clientY);
      });

      // --- Context menu on edge ---
      cy.on('cxttap', 'edge', (evt: EventObject) => {
        const edge = evt.target as EdgeSingular;
        if (edge.hasClass('start-arrow-edge')) return;
        evt.originalEvent?.preventDefault();
        const trIdx = edge.data('transitionIndex');
        if (trIdx === undefined) return;
        const oe = evt.originalEvent as MouseEvent;
        callbacksRef.current.onContextMenuEdge?.(trIdx, oe.clientX, oe.clientY);
      });

      // --- Drag: record position ---
      cy.on('dragfree', 'node', (evt: EventObject) => {
        const node = evt.target as NodeSingular;
        if (node.hasClass('start-arrow')) return;
        posMapRef.current[node.id()] = { x: node.position().x, y: node.position().y };

        // Update start arrow indicator position
        const startArrowSrc = cy.getElementById('__start_arrow_src');
        if (startArrowSrc.length && node.hasClass('start')) {
          const npos = node.position();
          startArrowSrc.position({ x: npos.x - 70, y: npos.y });
        }
      });

      return () => {
        cy.destroy();
        cyRef.current = null;
      };
    }, []);

    // Theme changes → update styles
    useEffect(() => {
      const cy = cyRef.current;
      if (!cy) return;
      cy.style(makeStyles(isDark)).update();
    }, [isDark]);

    // Automaton / state changes → sync graph elements
    useEffect(() => {
      const cy = cyRef.current;
      if (!cy) return;

      cy.batch(() => {
        // Collect existing positions for all nodes in graph
        cy.nodes(':not(.start-arrow)').forEach((n) => {
          posMapRef.current[n.id()] = { x: n.position().x, y: n.position().y };
        });

        cy.elements().remove();

        // Add state nodes using authoritative posMapRef
        automaton.states.forEach((name, idx) => {
          const isStart = name === automaton.start_state;
          const isAcc = automaton.accepting_states.includes(name);
          const isSel = name === selectedState;
          const isActive = activeStates.includes(name);

          const classes = [
            isStart ? 'start' : '',
            isAcc ? 'accepting' : '',
            isSel ? 'selected-node' : '',
            isActive ? 'active-sim' : '',
          ]
            .filter(Boolean)
            .join(' ');

          let pos = posMapRef.current[name];
          if (!pos) {
            pos = { x: 180 + idx * 140, y: 220 };
            posMapRef.current[name] = pos;
          }

          cy.add({
            group: 'nodes',
            data: { id: name, label: name },
            position: { x: pos.x, y: pos.y },
            classes,
          });
        });

        // Add transition edges
        automaton.transitions.forEach((tr, index) => {
          if (
            !automaton.states.includes(tr.from_state) ||
            !automaton.states.includes(tr.to_state)
          )
            return;
          const isEps = tr.symbol === EPSILON_SYMBOL;
          const isSel = index === selectedTransitionIndex;
          const classes = [
            isEps ? 'epsilon' : '',
            isSel ? 'selected-edge' : '',
          ]
            .filter(Boolean)
            .join(' ');

          cy.add({
            group: 'edges',
            data: {
              id: `e_${index}`,
              source: tr.from_state,
              target: tr.to_state,
              symbol: tr.symbol,
              transitionIndex: index,
            },
            classes,
          });
        });

        // Start arrow: add indicator pointing to start state
        if (automaton.start_state && automaton.states.includes(automaton.start_state)) {
          const startNode = cy.getElementById(automaton.start_state);
          if (startNode.length) {
            const spos = startNode.position();
            cy.add({
              group: 'nodes',
              data: { id: '__start_arrow_src' },
              classes: 'start-arrow',
              position: { x: spos.x - 70, y: spos.y },
              grabbable: false,
              selectable: false,
            });
            cy.add({
              group: 'edges',
              data: {
                id: '__start_arrow_e',
                source: '__start_arrow_src',
                target: automaton.start_state,
              },
              classes: 'start-arrow-edge',
              selectable: false,
            });
          }
        }
      });
    }, [automaton, selectedState, selectedTransitionIndex, activeStates]);

    // Cursor based on tool
    useEffect(() => {
      const el = containerRef.current;
      if (!el) return;
      const cursors: Record<ToolMode, string> = {
        select: 'default',
        state: 'crosshair',
        transition: 'cell',
        delete: 'not-allowed',
        start: 'pointer',
        accepting: 'pointer',
      };
      el.style.cursor = cursors[activeTool] || 'default';
    }, [activeTool]);

    return (
      <div
        className={`graph-canvas ${className}`}
        style={{ width: '100%', height: '100%', position: 'relative' }}
      >
        <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

        {/* Empty state overlay */}
        {automaton.states.length === 0 && (
          <div
            className="canvas-empty"
            style={{ pointerEvents: 'none' }}
          >
            <div className="canvas-empty-content">
              <span className="canvas-empty-icon">◯</span>
              <h3>Build your automaton</h3>
              <p>
                Select the <strong>State</strong> tool (<kbd>S</kbd>) and click anywhere on the canvas to place a state.
              </p>
            </div>
          </div>
        )}
      </div>
    );
  }
);

GraphCanvas.displayName = 'GraphCanvas';

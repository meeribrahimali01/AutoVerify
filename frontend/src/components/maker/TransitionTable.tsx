import React from 'react';
import { AutomatonData, EPSILON_SYMBOL } from '../../types';

export interface TransitionTableProps {
  automaton: AutomatonData;
}

export const TransitionTable: React.FC<TransitionTableProps> = ({ automaton }) => {
  // Columns: all alphabet symbols, plus epsilon if EpsilonNFA
  const columns = [...automaton.alphabet];
  if (automaton.type === 'EPSILON_NFA' && !columns.includes(EPSILON_SYMBOL)) {
    columns.push(EPSILON_SYMBOL);
  }

  // Pre-calculate transition cells: cellMap[state][symbol] = string[]
  const cellMap: Record<string, Record<string, string[]>> = {};
  automaton.states.forEach((st) => {
    cellMap[st] = {};
    columns.forEach((sym) => {
      cellMap[st][sym] = [];
    });
  });

  automaton.transitions.forEach((tr) => {
    if (cellMap[tr.from_state] && cellMap[tr.from_state][tr.symbol]) {
      cellMap[tr.from_state][tr.symbol].push(tr.to_state);
    }
  });

  return (
    <div className="table-card">
      <h3 className="section-title">Transition Table $\delta(q, a)$</h3>
      {automaton.states.length === 0 ? (
        <p className="hint-text">No states defined.</p>
      ) : (
        <div className="table-responsive">
          <table className="automata-table">
            <thead>
              <tr>
                <th className="th-state">State</th>
                {columns.map((sym) => (
                  <th key={`col_${sym}`} className={sym === EPSILON_SYMBOL ? 'th-epsilon' : ''}>
                    {sym}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {automaton.states.map((st) => {
                const isStart = st === automaton.start_state;
                const isAccepting = automaton.accepting_states.includes(st);

                return (
                  <tr key={`row_${st}`}>
                    <td className="td-state">
                      {isStart && <span className="badge-start">▶</span>}
                      {isAccepting && <span className="badge-accept">◎</span>}
                      <strong>{st}</strong>
                    </td>
                    {columns.map((sym) => {
                      const dests = cellMap[st]?.[sym] || [];
                      let cellText = '—';
                      if (automaton.type === 'DFA') {
                        cellText = dests.length > 0 ? dests[0] : '—';
                      } else {
                        cellText = dests.length > 0 ? `{ ${dests.join(', ')} }` : '∅';
                      }

                      return (
                        <td key={`cell_${st}_${sym}`} className={dests.length === 0 ? 'td-empty' : 'td-active'}>
                          {cellText}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

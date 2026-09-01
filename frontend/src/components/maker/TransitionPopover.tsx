import React, { useEffect, useRef, useState } from 'react';
import { EPSILON_SYMBOL } from '../../types';

interface TransitionPopoverProps {
  x: number;
  y: number;
  fromState: string;
  toState: string;
  isEpsilonNFA: boolean;
  onConfirm: (symbol: string) => void;
  onCancel: () => void;
}

export const TransitionPopover: React.FC<TransitionPopoverProps> = ({
  x, y, fromState, toState, isEpsilonNFA, onConfirm, onCancel,
}) => {
  const [symbol, setSymbol] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const popRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    const handleClick = (e: MouseEvent) => {
      if (popRef.current && !popRef.current.contains(e.target as Node)) onCancel();
    };
    document.addEventListener('keydown', handleKey);
    document.addEventListener('mousedown', handleClick);
    return () => {
      document.removeEventListener('keydown', handleKey);
      document.removeEventListener('mousedown', handleClick);
    };
  }, [onCancel]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (symbol.trim()) onConfirm(symbol.trim());
  };

  const style: React.CSSProperties = {
    position: 'fixed',
    left: Math.min(x, window.innerWidth - 240),
    top: Math.min(y, window.innerHeight - 120),
    zIndex: 1000,
  };

  return (
    <div className="tr-popover" ref={popRef} style={style}>
      <div className="tr-popover-header">
        {fromState} → {toState}
      </div>
      <form onSubmit={handleSubmit} className="tr-popover-body">
        <div className="tr-popover-input-row">
          <input
            ref={inputRef}
            type="text"
            className="tr-popover-input"
            placeholder="Symbol"
            value={symbol}
            onChange={e => setSymbol(e.target.value)}
            maxLength={10}
          />
          {isEpsilonNFA && (
            <button type="button" className="tr-popover-eps" onClick={() => setSymbol(EPSILON_SYMBOL)} title="Epsilon">
              ε
            </button>
          )}
        </div>
        <div className="tr-popover-actions">
          <button type="button" className="tr-popover-cancel" onClick={onCancel}>Cancel</button>
          <button type="submit" className="tr-popover-add" disabled={!symbol.trim()}>Add</button>
        </div>
      </form>
    </div>
  );
};

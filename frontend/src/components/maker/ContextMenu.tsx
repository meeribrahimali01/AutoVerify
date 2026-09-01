import React, { useEffect, useRef } from 'react';

export interface ContextMenuAction {
  label: string;
  icon?: string;
  danger?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

interface ContextMenuProps {
  x: number;
  y: number;
  actions: ContextMenuAction[];
  onClose: () => void;
}

export const ContextMenu: React.FC<ContextMenuProps> = ({ x, y, actions, onClose }) => {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [onClose]);

  // Clamp to viewport
  const style: React.CSSProperties = {
    position: 'fixed',
    left: Math.min(x, window.innerWidth - 200),
    top: Math.min(y, window.innerHeight - actions.length * 36 - 16),
    zIndex: 1000,
  };

  return (
    <div className="ctx-menu" ref={menuRef} style={style}>
      {actions.map((a, i) => (
        <button
          key={i}
          className={`ctx-item ${a.danger ? 'danger' : ''} ${a.disabled ? 'disabled' : ''}`}
          onClick={() => { a.onClick(); onClose(); }}
          disabled={a.disabled}
        >
          {a.icon && <span className="ctx-icon">{a.icon}</span>}
          {a.label}
        </button>
      ))}
    </div>
  );
};

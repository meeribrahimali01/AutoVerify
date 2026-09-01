import { useState, useCallback, useRef } from 'react';

const MAX_HISTORY = 80;

export interface UseHistoryReturn<T> {
  state: T;
  set: (newState: T) => void;
  replace: (newState: T) => void; // replace current without pushing to undo
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  reset: (initial: T) => void;
}

export function useHistory<T>(initial: T): UseHistoryReturn<T> {
  const [state, setState] = useState<T>(initial);
  const pastRef = useRef<T[]>([]);
  const futureRef = useRef<T[]>([]);

  const set = useCallback((newState: T) => {
    setState((prev) => {
      pastRef.current = [...pastRef.current.slice(-(MAX_HISTORY - 1)), prev];
      futureRef.current = [];
      return newState;
    });
  }, []);

  const replace = useCallback((newState: T) => {
    setState(newState);
  }, []);

  const undo = useCallback(() => {
    setState((prev) => {
      if (pastRef.current.length === 0) return prev;
      const previous = pastRef.current[pastRef.current.length - 1];
      pastRef.current = pastRef.current.slice(0, -1);
      futureRef.current = [prev, ...futureRef.current];
      return previous;
    });
  }, []);

  const redo = useCallback(() => {
    setState((prev) => {
      if (futureRef.current.length === 0) return prev;
      const next = futureRef.current[0];
      futureRef.current = futureRef.current.slice(1);
      pastRef.current = [...pastRef.current, prev];
      return next;
    });
  }, []);

  const reset = useCallback((initial: T) => {
    pastRef.current = [];
    futureRef.current = [];
    setState(initial);
  }, []);

  return {
    state,
    set,
    replace,
    undo,
    redo,
    canUndo: pastRef.current.length > 0,
    canRedo: futureRef.current.length > 0,
    reset,
  };
}

import { useCallback, useMemo } from 'react';
import { AutomatonData, AutomatonType, EPSILON_SYMBOL } from '../types';
import { useHistory, UseHistoryReturn } from './useHistory';

const EMPTY_AUTOMATON: AutomatonData = {
  type: 'DFA',
  states: [],
  alphabet: ['0', '1'],
  start_state: '',
  accepting_states: [],
  transitions: [],
};

export type ToolMode = 'select' | 'state' | 'transition' | 'delete' | 'start' | 'accepting';

export interface UseAutomatonReturn {
  automaton: AutomatonData;
  history: UseHistoryReturn<AutomatonData>;

  // State ops
  addState: (name: string, x?: number, y?: number) => void;
  deleteState: (name: string) => void;
  renameState: (oldName: string, newName: string) => void;
  setStartState: (name: string) => void;
  toggleAccepting: (name: string) => void;

  // Transition ops
  addTransition: (from: string, symbol: string, to: string) => string | null; // returns error or null
  deleteTransition: (index: number) => void;
  editTransitionSymbol: (index: number, newSymbol: string) => string | null;

  // Bulk ops
  setType: (type: AutomatonType) => void;
  clearAll: () => void;
  loadAutomaton: (data: AutomatonData) => void;

  // Derived
  nextStateName: () => string;
  alphabetSymbols: string[];
  validationErrors: string[];
}

function getNextStateName(states: string[]): string {
  let i = 0;
  while (states.includes(`q${i}`)) i++;
  return `q${i}`;
}



function validate(a: AutomatonData): string[] {
  const errors: string[] = [];
  if (a.states.length === 0) return errors; // empty is valid (just empty)
  if (a.start_state && !a.states.includes(a.start_state)) {
    errors.push(`Start state '${a.start_state}' is not in states.`);
  }
  for (const acc of a.accepting_states) {
    if (!a.states.includes(acc)) errors.push(`Accepting state '${acc}' is not in states.`);
  }
  const stateSet = new Set(a.states);
  for (const t of a.transitions) {
    if (!stateSet.has(t.from_state)) errors.push(`Transition source '${t.from_state}' not in states.`);
    if (!stateSet.has(t.to_state)) errors.push(`Transition target '${t.to_state}' not in states.`);
  }
  if (a.type === 'DFA') {
    // Check determinism
    const seen = new Map<string, string>();
    for (const t of a.transitions) {
      const key = `${t.from_state}|${t.symbol}`;
      if (seen.has(key)) {
        errors.push(`DFA: '${t.from_state}' has multiple transitions on '${t.symbol}'.`);
      }
      seen.set(key, t.to_state);
      if (t.symbol === EPSILON_SYMBOL) {
        errors.push(`DFA: epsilon transitions are not allowed.`);
      }
    }
  }
  if (a.type === 'NFA') {
    for (const t of a.transitions) {
      if (t.symbol === EPSILON_SYMBOL) {
        errors.push(`NFA: epsilon transitions are not allowed. Switch to ε-NFA.`);
      }
    }
  }
  return errors;
}

export function useAutomaton(initial?: AutomatonData): UseAutomatonReturn {
  const history = useHistory<AutomatonData>(initial || EMPTY_AUTOMATON);
  const automaton = history.state;

  const addState = useCallback((name: string) => {
    history.set({
      ...automaton,
      states: [...automaton.states, name],
      start_state: automaton.start_state || name,
    });
  }, [automaton, history]);

  const deleteState = useCallback((name: string) => {
    history.set({
      ...automaton,
      states: automaton.states.filter(s => s !== name),
      start_state: automaton.start_state === name ? (automaton.states.filter(s => s !== name)[0] || '') : automaton.start_state,
      accepting_states: automaton.accepting_states.filter(s => s !== name),
      transitions: automaton.transitions.filter(t => t.from_state !== name && t.to_state !== name),
    });
  }, [automaton, history]);

  const renameState = useCallback((oldName: string, newName: string) => {
    if (automaton.states.includes(newName)) return;
    history.set({
      ...automaton,
      states: automaton.states.map(s => s === oldName ? newName : s),
      start_state: automaton.start_state === oldName ? newName : automaton.start_state,
      accepting_states: automaton.accepting_states.map(s => s === oldName ? newName : s),
      transitions: automaton.transitions.map(t => ({
        ...t,
        from_state: t.from_state === oldName ? newName : t.from_state,
        to_state: t.to_state === oldName ? newName : t.to_state,
      })),
    });
  }, [automaton, history]);

  const setStartState = useCallback((name: string) => {
    history.set({ ...automaton, start_state: name });
  }, [automaton, history]);

  const toggleAccepting = useCallback((name: string) => {
    const isAcc = automaton.accepting_states.includes(name);
    history.set({
      ...automaton,
      accepting_states: isAcc
        ? automaton.accepting_states.filter(s => s !== name)
        : [...automaton.accepting_states, name],
    });
  }, [automaton, history]);

  const addTransition = useCallback((from: string, symbol: string, to: string): string | null => {
    // DFA constraint
    if (automaton.type === 'DFA') {
      if (symbol === EPSILON_SYMBOL) return 'DFA does not allow epsilon transitions.';
      const existing = automaton.transitions.find(t => t.from_state === from && t.symbol === symbol);
      if (existing) return `Invalid DFA transition: '${from}' already has a transition on '${symbol}' → '${existing.to_state}'.`;
    }
    if (automaton.type === 'NFA' && symbol === EPSILON_SYMBOL) {
      return 'NFA does not allow epsilon transitions. Switch to ε-NFA.';
    }
    // Update alphabet
    const newAlphabet = symbol !== EPSILON_SYMBOL && !automaton.alphabet.includes(symbol)
      ? [...automaton.alphabet, symbol].sort()
      : [...automaton.alphabet];

    history.set({
      ...automaton,
      alphabet: newAlphabet,
      transitions: [...automaton.transitions, { from_state: from, symbol, to_state: to }],
    });
    return null;
  }, [automaton, history]);

  const deleteTransition = useCallback((index: number) => {
    history.set({
      ...automaton,
      transitions: automaton.transitions.filter((_, i) => i !== index),
    });
  }, [automaton, history]);

  const editTransitionSymbol = useCallback((index: number, newSymbol: string): string | null => {
    const t = automaton.transitions[index];
    if (!t) return 'Transition not found.';
    if (automaton.type === 'DFA') {
      if (newSymbol === EPSILON_SYMBOL) return 'DFA does not allow epsilon transitions.';
      const existing = automaton.transitions.find((tr, i) => i !== index && tr.from_state === t.from_state && tr.symbol === newSymbol);
      if (existing) return `Invalid DFA: '${t.from_state}' already transitions on '${newSymbol}'.`;
    }
    if (automaton.type === 'NFA' && newSymbol === EPSILON_SYMBOL) {
      return 'NFA does not allow epsilon transitions.';
    }
    const newTransitions = automaton.transitions.map((tr, i) =>
      i === index ? { ...tr, symbol: newSymbol } : tr
    );
    const newAlphabet = newSymbol !== EPSILON_SYMBOL && !automaton.alphabet.includes(newSymbol)
      ? [...automaton.alphabet, newSymbol].sort()
      : [...automaton.alphabet];
    history.set({ ...automaton, transitions: newTransitions, alphabet: newAlphabet });
    return null;
  }, [automaton, history]);

  const setType = useCallback((type: AutomatonType) => {
    if (type === automaton.type) return;
    // Filter invalid transitions
    let newTransitions = automaton.transitions;
    if (type === 'DFA') {
      // Remove epsilon transitions and keep only first per (state, symbol)
      const seen = new Set<string>();
      newTransitions = automaton.transitions.filter(t => {
        if (t.symbol === EPSILON_SYMBOL) return false;
        const key = `${t.from_state}|${t.symbol}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    } else if (type === 'NFA') {
      newTransitions = automaton.transitions.filter(t => t.symbol !== EPSILON_SYMBOL);
    }
    history.set({ ...automaton, type, transitions: newTransitions });
  }, [automaton, history]);

  const clearAll = useCallback(() => {
    history.set({
      type: automaton.type,
      states: [],
      alphabet: ['0', '1'],
      start_state: '',
      accepting_states: [],
      transitions: [],
    });
  }, [automaton.type, history]);

  const loadAutomaton = useCallback((data: AutomatonData) => {
    history.set(data);
  }, [history]);

  const nextStateName = useCallback(() => getNextStateName(automaton.states), [automaton.states]);

  const alphabetSymbols = useMemo(() => {
    const syms = new Set(automaton.alphabet);
    for (const t of automaton.transitions) {
      if (t.symbol !== EPSILON_SYMBOL) syms.add(t.symbol);
    }
    return Array.from(syms).sort();
  }, [automaton.alphabet, automaton.transitions]);

  const validationErrors = useMemo(() => validate(automaton), [automaton]);

  return {
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
    alphabetSymbols,
    validationErrors,
  };
}

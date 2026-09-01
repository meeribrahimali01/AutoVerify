# AutoVerify

**AutoVerify** is an automated auditing and formal verification platform for finite-automata transformation programs (starting with $\varepsilon$-NFA $\to$ DFA).

## Project Overview

- **Automata Maker**: Visual graph creation, editing, string testing, and serialization for DFA, NFA, and $\varepsilon$-NFA.
- **Automata Converter**: Interactive reference transformations ($\varepsilon$-NFA $\to$ DFA, NFA $\to$ DFA, DFA Minimization).
- **Auditor**: Automated test harness and formal verification engine for student converter programs using Product Automata, Language Equivalence, and Shortest Counterexample Reconstruction.

## Architecture

- **Backend**: Python (FastAPI, Pydantic, SQLite)
- **Frontend**: React + TypeScript + Vite + Cytoscape.js
- **Execution Sandbox**: Docker
- **Formal Verification Engine**: Exact Product Automaton + BFS (Zero AI dependency for formal equivalence)

## Directory Structure

- `backend/`: FastAPI application, core automata data structures, algorithms, verification engine, and audit runner.
- `frontend/`: React SPA with visual graph canvas and audit dashboards.
- `docker/`: Isolation images and sandboxing for submitted user programs.

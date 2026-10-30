# AutoVerify

[![Live App](https://img.shields.io/badge/Live%20Demo-auto--verify--smoky.vercel.app-brightgreen?style=for-the-badge&logo=vercel)](https://auto-verify-smoky.vercel.app)
[![API Status](https://img.shields.io/badge/Render%20Backend-Live-blue?style=for-the-badge&logo=render)](https://autoverify-backend-kh5o.onrender.com/health)
[![API Docs](https://img.shields.io/badge/API-Swagger%20Docs-informational?style=for-the-badge&logo=fastapi)](https://autoverify-backend-kh5o.onrender.com/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **AutoVerify** is an automated auditing and formal verification platform for finite-automata transformation programs (starting with $\varepsilon$-NFA $\to$ DFA).

---

## 🌐 Live Deployments & Links

| Service | Link | Status | Description |
| :--- | :--- | :--- | :--- |
| **Frontend Web App** | [auto-verify-smoky.vercel.app](https://auto-verify-smoky.vercel.app) | ![Vercel](https://img.shields.io/badge/Vercel-Deployed-success?style=flat-square&logo=vercel) | Interactive web interface (Automata Maker & Auditor) |
| **Production API** | [autoverify-backend-kh5o.onrender.com](https://autoverify-backend-kh5o.onrender.com) | ![Render](https://img.shields.io/badge/Render-Active-blue?style=flat-square&logo=render) | FastAPI backend formal verification engine |
| **API Documentation** | [Swagger / OpenAPI Docs](https://autoverify-backend-kh5o.onrender.com/docs) | ![Swagger](https://img.shields.io/badge/Docs-Swagger%20UI-green?style=flat-square) | Interactive API exploration and endpoint schemas |
| **Health Check** | [API Health Endpoint](https://autoverify-backend-kh5o.onrender.com/health) | ![Health](https://img.shields.io/badge/Health-200%20OK-brightgreen?style=flat-square) | Real-time backend health monitor |

> **Note on Render Free Tier**: If the backend has been inactive for >15 minutes, Render spins down the free-tier service. The very first request may take ~30–40 seconds to cold start; all subsequent requests respond immediately.

---

## Project Overview

- **Automata Maker**: Visual graph creation, editing, string testing, and serialization for DFA, NFA, and $\varepsilon$-NFA with an interactive Cytoscape canvas.
- **Auditor**: Automated test harness and formal verification engine for student converter programs using Product Automata, Language Equivalence, and Shortest Counterexample Reconstruction.
- **Deterministic Formal Equivalence**: Zero AI dependency for mathematical verification. Exact product automaton construction and BFS state-space search guarantee 100% sound counterexample extraction.
- **Optional AI Analysis**: Integrated Gemini AI assistance for project source code structural analysis, hints, and feedback.

## Architecture

- **Backend**: Python (FastAPI, Pydantic v2, NetworkX, Pytest)
- **Frontend**: React + TypeScript + Vite + TailwindCSS + Lucide Icons
- **Verification Engine**: Exact Cartesian Product Automaton + BFS (Zero-hallucination formal verification)
- **Deployment**:
  - Frontend hosted on **Vercel**
  - Backend API hosted on **Render**

## Directory Structure

- `backend/`: FastAPI application, core automata data structures, algorithms, verification engine, and audit runner.
- `frontend/`: React SPA with visual graph canvas and audit dashboards.
- `docker/`: Isolation images and sandboxing for submitted user programs.

---

## Quick Start (Local Development)

### 1. Backend Setup
```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

# Agentic Delivery Control Tower

A governed multi-agent enterprise workflow system for delivery risk analysis and workflow automation.

## Architecture

```
User Query
    ↓
Pre-Orchestration Validation Layer   ← security before graph
    ↓
Orchestrator (LangGraph)             ← conditional routing
    ↓
[Intake] → [Retrieval] → [Risk Analysis] → [Planning] → [Critic] → [Security/Policy] → [Workflow Action]
                                                                              ↑
                                                              Human Approval Gate (write path only)
```

All agents share a single typed LangGraph state object. Every agent emits a validated Pydantic model. No agent can execute write actions without passing the Critic, Security, and human approval gates.

## Stack

| Layer | Tech |
|---|---|
| Orchestration | LangGraph |
| Backend | FastAPI + Python 3.11 |
| LLM | Groq (primary) / OpenAI (fallback) |
| Vector store | FAISS |
| Validation | Pydantic v2 |
| Frontend | React + Vite |
| Deployment | Railway (API) + Vercel (frontend) |

## Phases

- **Phase 1** — Project skeleton, schemas, synthetic data, FAISS index ✅
- **Phase 2** — Agent implementations, LangGraph wiring, FastAPI endpoints
- **Phase 3** — Frontend, explainability UI, human approval gate
- **Phase 4** — Deployment, CI/CD, live demo link

## Quick Start

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your API keys
python -m data.seed    # generate synthetic dataset + FAISS index
uvicorn api.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
delivery-control-tower/
├── backend/
│   ├── agents/         # one file per agent
│   ├── core/           # state schema, orchestrator, config, validation layer
│   ├── api/            # FastAPI routes
│   ├── data/           # synthetic dataset + FAISS index builder
│   └── tests/          # pytest test suite
├── frontend/
│   └── src/            # React + Vite
├── docs/               # architecture notes, agent contracts
└── .github/workflows/  # CI pipeline
```

## Security Model

- Pre-orchestration input validation before any agent fires
- Pydantic schemas enforce typed outputs at every agent boundary
- Confidence thresholds gate downstream agent behavior
- Critic Agent blocks unsupported recommendations
- Security/Policy Agent masks PII and enforces role constraints
- Human approval required for all write actions
- Full audit log written to SQLite on every run

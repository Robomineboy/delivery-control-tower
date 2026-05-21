---
title: Delivery Control Tower
emoji: 🗼
colorFrom: gray
colorTo: gray
sdk: docker
pinned: false
---


# Agentic Delivery Control Tower

A governed multi-agent enterprise workflow system for delivery risk analysis and workflow automation — built for the Wipro Junior FDE pre-screening assignment.

**Live Demo:** https://huggingface.co/spaces/sidjain204/dct-prod

---

## What it does

Connects to a live Jira board via OAuth2 and runs a multi-agent pipeline that:

- Identifies project risks, blockers, SLA violations, and overloaded assignees
- Produces evidence-backed findings with severity ratings and confidence scores
- Generates prioritized recommended actions
- Executes approved Jira mutations (create ticket, reassign, set due date, add comment) under human oversight

Natural language input. Structured, auditable output.

---

## Architecture

```
User query
    ↓
Pre-orchestration validation layer      ← injection detection, sanitization, role check
    ↓
Intake Agent (LLM)                      ← intent, filters, urgency, action type
    ↓
Retrieval Agent                         ← FAISS semantic search + structured filters
    ↓
Orchestrator ── routes by intent ───────────────────────────────────────┐
    │                                                                    │
    ├── WRITE PATH                   ── RISK PATH           ── SUMMARY PATH
    │   Planning Agent (LLM)             Risk Analysis (LLM)    Summary Agent (LLM)
    │   Security Agent (rule-based)      Critic (rule-based)
    │   Human Approval Gate              Planning Agent (LLM)
    │   Writer Agent
    │
    └── Structured API response → Frontend UI
```

All agents share a single typed `PipelineState` object (Pydantic v2). Every agent reads full context and appends its typed output before passing control downstream.

---

## Agent responsibilities

| Agent | Type | Responsibility |
|---|---|---|
| Intake | LLM | Parses natural language into structured intent: project, action type (read/write), urgency, filters |
| Retrieval | Hybrid | FAISS semantic search over live Jira tickets with structured field filters on status, assignee, priority |
| Risk Analysis | LLM | Cross-ticket pattern detection: blockers, SLA violations, overloaded assignees, unowned criticals. Returns findings with severity (CRITICAL → LOW) and confidence (0.0–1.0) |
| Critic | Rule-based | Validates each finding against retrieved ticket IDs. Removes unsupported claims, caps confidence on single-ticket evidence |
| Planning | LLM | Converts findings into prioritized recommendations (IMMEDIATE / THIS_WEEK / BACKLOG). On write path, generates exact Jira operations matching the user's request only |
| Security | Rule-based | Validates write actions before approval gate: ticket ID format, valid team member names, date format, comment length |
| Writer | Typed tools | Executes approved Jira actions via REST API. Restricted to four typed functions: `create_ticket`, `update_assignee`, `set_due_date`, `add_comment` |

---

## Security and guardrails

- **Pre-orchestration validation** — prompt injection detection, input sanitization, role validation before any agent fires
- **Confidence thresholds** — externalized in config (`MIN_RETRIEVAL_CONFIDENCE`, `MIN_PLANNING_CONFIDENCE`, `MIN_CRITIC_CONFIDENCE`). Pipeline halts gracefully if confidence falls below threshold
- **Critic Agent** — every recommendation must be traceable to a specific ticket ID in the retrieved evidence
- **Security Agent** — validates all write actions before they reach the human approval gate
- **Human-in-the-loop approval** — no Jira mutation occurs without explicit user approval. Write actions presented as a per-action review card
- **Typed tool access only** — Writer Agent cannot issue arbitrary API calls. Four typed functions is the complete write surface area
- **Token visibility** — per-agent input/output token counts and estimated cost surfaced in the UI on every query

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.10) |
| LLM | Groq `llama-3.1-8b-instant` (primary) · OpenAI GPT-4o (fallback) |
| Vector store | FAISS + `sentence-transformers` (all-MiniLM-L6-v2) |
| Jira integration | REST API v3 · OAuth2 three-legged flow · silent refresh token rotation |
| Schemas | Pydantic v2 — typed at every agent boundary |
| Frontend | Vanilla HTML/CSS/JS — agent trace timeline, dev console, token panel |
| Deployment | HuggingFace Spaces (Docker) |

---

## Project structure

```
delivery-control-tower/
├── agents/
│   ├── intake_agent.py          # LLM intent parser
│   ├── retrieval_agent.py       # FAISS semantic search
│   ├── risk_agent.py            # LLM risk analysis
│   ├── critic_agent.py          # Rule-based validation
│   ├── planning_agent.py        # LLM action generation + write action generator
│   ├── security_agent.py        # Rule-based write action validator
│   ├── writer_agent.py          # Typed Jira API write tools
│   ├── summary_agent.py         # LLM direct answer
│   └── token_logger.py          # Per-agent token tracking
├── data/
│   ├── tickets.py               # Jira OAuth2 loader + fallback dataset
│   ├── build_index.py           # FAISS index builder
│   ├── tickets.faiss            # Vector index (generated)
│   └── tickets.pkl              # Ticket map (generated)
├── docs/                        # Architecture decisions + planning log
├── tests/                       # Jira auth testing utilities
├── api.py                       # FastAPI app — /api/query, /api/approve, /api/refresh
├── pipeline.py                  # Orchestrator + routing logic
├── index.html                   # Frontend UI
├── Dockerfile                   # HuggingFace Spaces deployment
└── requirements.txt
```

---

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/Robomineboy/delivery-control-tower
cd delivery-control-tower
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Add: GROQ_API_KEY, JIRA_CLIENT_ID, JIRA_CLIENT_SECRET

# 3. Authorize Jira (opens browser once, saves refresh token)
python data/tickets.py

# 4. Build FAISS index
python data/build_index.py

# 5. Start backend
python api.py

# 6. Open frontend
# Open index.html in Chrome — points to localhost:8000
```

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/query` | Run the full agent pipeline. Body: `{"query": "..."}` |
| `POST` | `/api/approve` | Execute approved write actions. Body: `{"run_id": "...", "approved_indices": [...]}` |
| `POST` | `/api/refresh` | Re-fetch Jira tickets and rebuild FAISS index |
| `GET` | `/api/health` | Health check |
| `GET` | `/` | Serves the frontend UI |

---

## Gold label evaluation

Five queries used to validate end-to-end system behavior:

| Query | Expected intent | Expected path | Verification |
|---|---|---|---|
| "Show me blocked tickets" | `blocker_analysis` | Risk | SS-15 surfaces as top result; Risk Agent flags blocker with evidence; Critic validates ticket ID |
| "What is Aryan working on?" | `person_query` | Summary | `assignee_contains` filter applied; 3 Aryan tickets retrieved; direct answer without risk analysis |
| "What are the biggest risks this sprint?" | `risk_analysis` | Risk | 2–4 findings with severity and confidence; all backed by ticket IDs; Critic passes or flags |
| "Assign SS-10 to Aryan Ghosh" | `write_action` | Write | Exactly one `update_assignee` generated; Security clears it; HITL card shown; Jira updates on approval |
| "Overall project health?" | `project_summary` | Summary | All tickets fetched; honest assessment referencing specific IDs and statuses |

---

## Key design decisions

**Shared typed state over message passing** — every agent has full context, enabling the Critic to cross-check Planning output against original Retrieval evidence. Message passing would require each agent to know its upstream neighbor's schema.

**Pre-orchestration security boundary** — if injection detection happened inside the Security Agent (position 6 of 7), adversarial input would have already been processed by five agents. The trust boundary must be at the system edge.

**Confidence thresholds as externalized config** — a client deploying this for risk-averse financial services will need different thresholds than a startup. Externalizing them makes the system tunable per deployment without code changes.

**Rule-based Critic and Security Agents** — deterministic validation is more auditable than LLM validation. The LLM agents reason; the rule-based agents enforce.

**Human-in-the-loop as architecture, not feature** — no enterprise client will deploy a system that autonomously modifies project data. HITL is a prerequisite, not an add-on.

---

## Built by

**Sidharth Jain** — sidjain.co  
UMass Amherst B.S. Computer Science + Mathematics, May 2026  
Creator of GATTII (patented wearable gait analysis system, 100+ clinical deployments)

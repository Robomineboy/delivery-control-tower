# Architecture Decision Log

## ADR-001 — Single shared Pydantic state object (not message passing)

**Decision:** All agents share one `PipelineState` object threaded through every LangGraph node. Each agent reads the full state and appends its typed output.

**Rationale:** Message passing between agents requires each agent to know the message schema of its upstream neighbor — tight coupling. A shared state object means every agent has full context, enabling the Critic to cross-check Planning output against Retrieval evidence without explicit message routing.

**Trade-off:** State object grows with pipeline depth. Acceptable at current scale; would move to event sourcing for >20 agents.

---

## ADR-002 — Pre-orchestration validation layer

**Decision:** Input sanitization, injection detection, and role validation run before LangGraph initializes. Nothing enters the agent graph without passing these checks.

**Rationale:** If injection detection happens inside the Security Agent (position 6 of 7), adversarial input has already been processed by 5 agents. The trust boundary must be at the system edge.

---

## ADR-003 — Confidence thresholds as externalized config

**Decision:** `MIN_RETRIEVAL_CONFIDENCE`, `MIN_PLANNING_CONFIDENCE`, `MIN_CRITIC_CONFIDENCE` live in `.env` / config, not hardcoded in agent logic.

**Rationale:** A Wipro client deploying this for a risk-averse financial services firm will need lower thresholds than a startup. Externalizing thresholds makes the system tunable per deployment without code changes.

---

## ADR-004 — Retrieval Agent graceful degradation

**Decision:** If FAISS index is unavailable, Retrieval Agent falls back to keyword search rather than failing.

**Rationale:** During demo, the index may not be pre-built. Keyword fallback keeps the pipeline demonstrable while returning lower confidence scores that honestly reflect reduced retrieval quality.

---

## ADR-005 — Workflow Action Agent limited to 3 typed tools

**Decision:** The final agent can only call `create_draft_ticket()`, `draft_summary()`, `draft_escalation_note()`. No general tool access.

**Rationale:** Unrestricted tool access is the primary risk in autonomous agent systems. Typed tools with explicit signatures are auditable, testable, and explainable to enterprise clients.

---

## ADR-006 — Human-in-the-loop as a first-class architectural gate

**Decision:** Write actions set `approval_status = PENDING` and return to the caller. The Workflow Action Agent checks this gate and blocks until approval arrives via `POST /api/approve/{run_id}`.

**Rationale:** Enterprise clients will not deploy systems that autonomously create or modify tickets. HITL is not a feature — it is a prerequisite for enterprise adoption.

---

## ADR-007 — Planning + Risk kept as separate agents

**Decision:** Risk Analysis Agent detects problems. Planning Agent proposes responses. They are separate nodes.

**Rationale:** Separation of detection from recommendation mirrors how enterprise delivery teams actually work (incident detection vs incident response). It also means the Critic can validate that recommendations map to detected risks — not possible if detection and recommendation happen in one step.

---

## Phase changelog

### Phase 1 (current)
- Project skeleton, Pydantic schemas, config, validation layer
- Synthetic 32-ticket dataset (Phoenix + Atlas)
- Rule-based agent stubs (no LLM required)
- LangGraph graph wired end-to-end
- FastAPI skeleton with all routes
- Audit logger
- Full test suite passing

### Phase 2 (next)
- Replace stub agent logic with Groq LLM calls
- Structured JSON output with confidence scoring
- FAISS semantic search live
- Error handling: timeouts, retries, partial completion

### Phase 3
- React frontend + explainability UI (agent execution timeline)
- Human approval gate UI
- Full integration tests

### Phase 4
- Railway + Vercel deployment
- Live demo link
- Written report

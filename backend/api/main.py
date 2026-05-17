"""
api/main.py

FastAPI application entry point.
Routes:
  POST /api/query          — run the full agent pipeline
  GET  /api/health         — health check
  GET  /api/audit          — recent audit log entries
  POST /api/approve/{run_id} — human approval gate for write actions
"""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.audit import get_recent_runs, log_run
from core.config import get_settings
from core.orchestrator import run_pipeline
from core.schemas import ApprovalStatus, PipelineState
from core.validation import validate_request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Agentic Delivery Control Tower",
    description="Governed multi-agent enterprise workflow system",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for pending approvals (Phase 3: move to Redis/DB)
_pending_approvals: dict[str, PipelineState] = {}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    user_role: str = "analyst"


class ApprovalRequest(BaseModel):
    approved: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "environment": settings.environment}


@app.post("/api/query")
async def query(req: QueryRequest):
    # Pre-orchestration validation — security before graph
    validation = validate_request(req.query, req.user_role)
    if not validation.valid:
        raise HTTPException(status_code=400, detail={"errors": validation.errors})

    # Run pipeline with sanitized query
    state = await run_pipeline(
        query=validation.sanitized_query,
        user_role=req.user_role,
    )

    # Store for approval if needed
    if state.approval_status == ApprovalStatus.PENDING:
        _pending_approvals[state.run_id] = state

    # Audit log
    outcome = "blocked" if state.blocked_reason else "success"
    await log_run(
        run_id=state.run_id,
        user_role=req.user_role,
        query=req.query,
        outcome=outcome,
        agents_fired=[t.agent for t in state.trace],
        trace=[t.model_dump() for t in state.trace],
        blocked_reason=state.blocked_reason,
    )

    return state.model_dump()


@app.post("/api/approve/{run_id}")
async def approve(run_id: str, req: ApprovalRequest):
    """Human approval gate — approves or rejects pending write actions."""
    if run_id not in _pending_approvals:
        raise HTTPException(status_code=404, detail="No pending approval found for this run_id.")

    state = _pending_approvals.pop(run_id)

    if req.approved:
        state.approval_status = ApprovalStatus.APPROVED
        # Re-run workflow action agent with approval
        from agents.workflow_action import WorkflowActionAgent
        agent = WorkflowActionAgent()
        state = await agent(state)

        await log_run(
            run_id=state.run_id,
            user_role=state.user_role,
            query=state.user_query,
            outcome="approved_and_executed",
            agents_fired=[t.agent for t in state.trace],
            trace=[t.model_dump() for t in state.trace],
        )
    else:
        state.approval_status = ApprovalStatus.REJECTED

    return state.model_dump()


@app.get("/api/audit")
async def audit(limit: int = 20):
    runs = await get_recent_runs(limit=limit)
    return {"runs": runs}

"""
core/schemas.py

Typed contracts for every agent boundary in the system.
Every agent receives a typed input and emits a typed output.
The LangGraph state object is itself a Pydantic model.

These schemas are the single source of truth for inter-agent communication.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionType(str, Enum):
    READ = "read"       # summary, report, analysis — no write actions
    WRITE = "write"     # draft ticket, escalation, update


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NOT_REQUIRED = "not_required"


class AgentStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"       # blocked by confidence threshold or policy


# ---------------------------------------------------------------------------
# Ticket model (synthetic Jira-style data)
# ---------------------------------------------------------------------------

class Ticket(BaseModel):
    id: str
    title: str
    status: str                         # Open, Blocked, In Progress, Done
    priority: str                       # Critical, High, Medium, Low
    assignee: str | None = None
    project: str
    sprint: str | None = None
    created_at: str
    updated_at: str
    comments: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)   # ticket IDs
    sla_deadline: str | None = None
    customer_impacting: bool = False


# ---------------------------------------------------------------------------
# Agent output models (one per agent)
# ---------------------------------------------------------------------------

class IntakeOutput(BaseModel):
    project: str
    timeframe: str
    action_type: ActionType
    urgency: Severity
    raw_intent: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 3)


class RetrievalOutput(BaseModel):
    tickets: list[Ticket]
    query_used: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_count: int

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 3)


class RiskFinding(BaseModel):
    title: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ticket_ids: list[str]
    description: str

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 3)


class RiskAnalysisOutput(BaseModel):
    findings: list[RiskFinding]
    overall_health: Severity          # worst-case severity across all findings
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 3)


class RecommendedAction(BaseModel):
    title: str
    action_type: ActionType
    priority: Severity
    linked_risk: str                  # RiskFinding.title this addresses
    draft_content: str | None = None  # populated by Workflow Action Agent


class PlanningOutput(BaseModel):
    recommendations: list[RecommendedAction]
    executive_summary: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 3)


class CriticOutput(BaseModel):
    approved: bool
    flags: list[str]                  # unsupported claims removed or flagged
    revised_recommendations: list[RecommendedAction]
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 3)


class SecurityOutput(BaseModel):
    cleared: bool
    pii_masked: bool
    injection_detected: bool
    policy_flags: list[str]
    sanitized_summary: str


class WorkflowActionOutput(BaseModel):
    actions_taken: list[str]
    draft_tickets: list[dict[str, Any]] = Field(default_factory=list)
    draft_summaries: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Shared LangGraph state — passed through every node
# ---------------------------------------------------------------------------

class AgentTrace(BaseModel):
    """One entry per agent in the execution timeline."""
    agent: str
    status: AgentStatus
    confidence: float | None = None
    notes: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PipelineState(BaseModel):
    """
    The single shared state object threaded through every LangGraph node.
    Each agent reads the full state and appends its typed output.
    """

    # --- Request metadata ---
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    user_query: str
    user_role: str = "analyst"        # analyst | manager | executive
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # --- Agent outputs (None until that agent fires) ---
    intake: IntakeOutput | None = None
    retrieval: RetrievalOutput | None = None
    risk_analysis: RiskAnalysisOutput | None = None
    planning: PlanningOutput | None = None
    critic: CriticOutput | None = None
    security: SecurityOutput | None = None
    workflow_action: WorkflowActionOutput | None = None

    # --- Orchestration control ---
    routing_path: list[str] = Field(default_factory=list)  # which agents will fire
    current_agent: str = "intake"
    blocked_reason: str | None = None  # set if pipeline halted early

    # --- Human approval gate ---
    approval_status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    approval_required_for: list[str] = Field(default_factory=list)

    # --- Execution trace (for explainability UI) ---
    trace: list[AgentTrace] = Field(default_factory=list)

    def add_trace(
        self,
        agent: str,
        status: AgentStatus,
        confidence: float | None = None,
        notes: str = "",
    ) -> None:
        self.trace.append(
            AgentTrace(agent=agent, status=status, confidence=confidence, notes=notes)
        )

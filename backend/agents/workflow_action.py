"""
agents/workflow_action.py

Workflow Action Agent (formerly "Execution Agent").
Only fires after human approval on write-path queries.
Has access to ONLY three typed tool calls — no unrestricted autonomy.

Typed tools:
  - create_draft_ticket()
  - draft_summary()
  - draft_escalation_note()

Phase 1: Returns stub drafts.
Phase 2: LLM-generated draft content for each action.
"""

from core.schemas import (
    ActionType,
    AgentStatus,
    ApprovalStatus,
    PipelineState,
    WorkflowActionOutput,
)
from agents.base import BaseAgent


class WorkflowActionAgent(BaseAgent):
    name = "workflow_action"

    async def run(self, state: PipelineState) -> PipelineState:
        # Gate 1: security must have cleared
        if state.security is None or not state.security.cleared:
            state.add_trace(self.name, AgentStatus.BLOCKED, notes="Security policy not cleared")
            return state

        # Gate 2: write actions need human approval
        if state.approval_status == ApprovalStatus.PENDING:
            state.add_trace(
                agent=self.name,
                status=AgentStatus.BLOCKED,
                notes="Awaiting human approval for write actions.",
            )
            return state

        if not state.critic or not state.critic.revised_recommendations:
            state.add_trace(self.name, AgentStatus.SKIPPED, notes="No recommendations to action")
            return state

        actions_taken: list[str] = []
        draft_tickets: list[dict] = []
        draft_summaries: list[str] = []

        for rec in state.critic.revised_recommendations:
            if rec.action_type == ActionType.WRITE and state.approval_status == ApprovalStatus.APPROVED:
                draft = self._create_draft_ticket(rec.title, rec.priority.value, rec.linked_risk)
                draft_tickets.append(draft)
                actions_taken.append(f"Draft ticket created: {rec.title}")

            elif rec.action_type == ActionType.READ:
                summary = self._draft_summary(rec, state)
                draft_summaries.append(summary)
                actions_taken.append(f"Summary drafted: {rec.title}")

        state.workflow_action = WorkflowActionOutput(
            actions_taken=actions_taken,
            draft_tickets=draft_tickets,
            draft_summaries=draft_summaries,
        )
        state.add_trace(
            agent=self.name,
            status=AgentStatus.SUCCESS,
            notes=f"{len(actions_taken)} actions taken",
        )
        return state

    # ---------------------------------------------------------------------------
    # Typed tool calls — the only write operations the agent can perform
    # ---------------------------------------------------------------------------

    def _create_draft_ticket(self, title: str, priority: str, linked_risk: str) -> dict:
        """Typed tool: create a draft ticket (not submitted — human reviews first)."""
        return {
            "type": "draft_ticket",
            "title": f"[AUTO-DRAFT] {title}",
            "priority": priority,
            "description": f"Auto-generated based on risk finding: {linked_risk}. Requires human review before submission.",
            "status": "Draft",
            "labels": ["auto-generated", "review-required"],
        }

    def _draft_summary(self, rec, state: PipelineState) -> str:
        """Typed tool: generate a structured text summary for a recommendation."""
        # Phase 2: LLM-generated with ticket context
        project = state.intake.project if state.intake else "project"
        return (
            f"[{rec.priority.value}] {rec.title}\n"
            f"Linked risk: {rec.linked_risk}\n"
            f"Project: {project}\n"
            f"Recommended action: Review and assign to relevant team lead."
        )

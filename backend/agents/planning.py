"""
agents/planning.py

Planning Agent — converts risk findings into recommended actions
and generates an executive summary.

Phase 1: Template-based stub.
Phase 2: LLM-generated recommendations with structured output.
"""

from core.config import get_settings
from core.schemas import (
    ActionType,
    AgentStatus,
    PipelineState,
    PlanningOutput,
    RecommendedAction,
    Severity,
)
from agents.base import BaseAgent

settings = get_settings()


class PlanningAgent(BaseAgent):
    name = "planning"

    async def run(self, state: PipelineState) -> PipelineState:
        if state.risk_analysis is None:
            state.add_trace(self.name, AgentStatus.BLOCKED, notes="No risk analysis available")
            return state

        confidence = state.risk_analysis.confidence

        if confidence < settings.min_planning_confidence:
            state.add_trace(
                agent=self.name,
                status=AgentStatus.BLOCKED,
                confidence=confidence,
                notes=f"Risk confidence {confidence:.2f} below planning threshold {settings.min_planning_confidence}",
            )
            state.blocked_reason = (
                f"Planning Agent blocked: risk analysis confidence ({confidence:.2f}) "
                f"below minimum threshold ({settings.min_planning_confidence})."
            )
            return state

        recommendations = self._generate_recommendations(state)
        summary = self._generate_summary(state)

        state.planning = PlanningOutput(
            recommendations=recommendations,
            executive_summary=summary,
            confidence=round(confidence - 0.03, 3),  # planning inherits slight uncertainty
        )
        state.add_trace(
            agent=self.name,
            status=AgentStatus.SUCCESS,
            confidence=state.planning.confidence,
            notes=f"{len(recommendations)} recommendations generated",
        )
        return state

    def _generate_recommendations(self, state: PipelineState) -> list[RecommendedAction]:
        recs = []
        findings = state.risk_analysis.findings
        intake = state.intake

        for finding in findings:
            if finding.severity in (Severity.CRITICAL, Severity.HIGH):
                action_type = (
                    ActionType.WRITE if intake and intake.action_type == ActionType.WRITE
                    else ActionType.READ
                )
                recs.append(RecommendedAction(
                    title=f"Address: {finding.title}",
                    action_type=action_type,
                    priority=finding.severity,
                    linked_risk=finding.title,
                    draft_content=None,  # Workflow Action Agent populates this
                ))

        return recs

    def _generate_summary(self, state: PipelineState) -> str:
        ra = state.risk_analysis
        intake = state.intake
        project = intake.project if intake else "the project"
        count = len(ra.findings)
        health = ra.overall_health.value

        # Phase 2: replace with LLM-generated narrative summary
        return (
            f"Project {project} — {count} risk finding(s) detected this {intake.timeframe if intake else 'sprint'}. "
            f"Overall health: {health}. "
            f"Immediate attention required on: "
            f"{', '.join(f.title for f in ra.findings if f.severity in (Severity.CRITICAL, Severity.HIGH))}."
        )

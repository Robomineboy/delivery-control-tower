"""
agents/critic.py

Critic Agent — validates that every recommendation is traceable
to evidence in the retrieved tickets. Removes unsupported claims.

Phase 1: Evidence ID cross-check stub.
Phase 2: LLM-powered reasoning quality check.
"""

from core.config import get_settings
from core.schemas import (
    AgentStatus,
    CriticOutput,
    PipelineState,
    RecommendedAction,
)
from agents.base import BaseAgent

settings = get_settings()


class CriticAgent(BaseAgent):
    name = "critic"

    async def run(self, state: PipelineState) -> PipelineState:
        if state.planning is None:
            state.add_trace(self.name, AgentStatus.BLOCKED, notes="No planning output to validate")
            return state

        flags: list[str] = []
        valid_recs: list[RecommendedAction] = []

        # Get all evidence ticket IDs from risk findings
        evidence_ids: set[str] = set()
        if state.risk_analysis:
            for finding in state.risk_analysis.findings:
                evidence_ids.update(finding.evidence_ticket_ids)

        for rec in state.planning.recommendations:
            # Phase 1: check that the linked risk maps to a real finding with evidence
            linked_finding = next(
                (f for f in state.risk_analysis.findings if f.title == rec.linked_risk),
                None,
            ) if state.risk_analysis else None

            if linked_finding is None:
                flags.append(f"Recommendation '{rec.title}' has no linked risk finding — removed.")
                continue

            if not linked_finding.evidence_ticket_ids:
                flags.append(f"Recommendation '{rec.title}' linked to finding with no evidence — removed.")
                continue

            valid_recs.append(rec)

        approved = len(flags) == 0
        confidence = settings.min_critic_confidence if approved else settings.min_critic_confidence - 0.1

        state.critic = CriticOutput(
            approved=approved,
            flags=flags,
            revised_recommendations=valid_recs,
            confidence=round(confidence, 3),
        )
        state.add_trace(
            agent=self.name,
            status=AgentStatus.SUCCESS,
            confidence=confidence,
            notes=f"approved={approved}, flags={len(flags)}, valid_recs={len(valid_recs)}",
        )
        return state

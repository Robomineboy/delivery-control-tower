"""
agents/risk_analysis.py

Risk Analysis Agent — scans retrieved tickets for blockers, SLA risks,
missing owners, dependency chains, and repeated failures.

Phase 1: Rule-based stub using ticket fields directly.
Phase 2: Replace with LLM-powered analysis returning RiskFinding list.
"""

from datetime import date

from core.schemas import (
    AgentStatus,
    PipelineState,
    RiskAnalysisOutput,
    RiskFinding,
    Severity,
    Ticket,
)
from agents.base import BaseAgent


class RiskAnalysisAgent(BaseAgent):
    name = "risk_analysis"

    async def run(self, state: PipelineState) -> PipelineState:
        if state.retrieval is None or not state.retrieval.tickets:
            state.add_trace(self.name, AgentStatus.BLOCKED, notes="No tickets to analyze")
            return state

        findings = self._analyze(state.retrieval.tickets)
        overall = self._worst_severity(findings)
        confidence = min(state.retrieval.confidence + 0.05, 1.0)  # Phase 2: LLM confidence

        state.risk_analysis = RiskAnalysisOutput(
            findings=findings,
            overall_health=overall,
            confidence=round(confidence, 3),
        )
        state.add_trace(
            agent=self.name,
            status=AgentStatus.SUCCESS,
            confidence=confidence,
            notes=f"{len(findings)} findings, overall={overall.value}",
        )
        return state

    def _analyze(self, tickets: list[Ticket]) -> list[RiskFinding]:
        findings: list[RiskFinding] = []
        today = date.today().isoformat()

        # Pattern 1: Blocked tickets
        blocked = [t for t in tickets if t.status == "Blocked"]
        if blocked:
            findings.append(RiskFinding(
                title="Active blockers detected",
                severity=Severity.HIGH,
                confidence=0.95,
                evidence_ticket_ids=[t.id for t in blocked],
                description=f"{len(blocked)} tickets are blocked: {', '.join(t.id for t in blocked)}.",
            ))

        # Pattern 2: SLA violations
        overdue = [t for t in tickets if t.sla_deadline and t.sla_deadline < today]
        if overdue:
            findings.append(RiskFinding(
                title="SLA deadline violations",
                severity=Severity.CRITICAL,
                confidence=0.99,
                evidence_ticket_ids=[t.id for t in overdue],
                description=f"{len(overdue)} tickets have passed their SLA deadline.",
            ))

        # Pattern 3: Missing owners on critical/high items
        unowned_critical = [
            t for t in tickets
            if t.assignee is None and t.priority in ("Critical", "High")
        ]
        if unowned_critical:
            findings.append(RiskFinding(
                title="High-priority tickets without an owner",
                severity=Severity.HIGH,
                confidence=0.98,
                evidence_ticket_ids=[t.id for t in unowned_critical],
                description=f"{len(unowned_critical)} critical/high tickets have no assignee.",
            ))

        # Pattern 4: Customer-impacting open items
        customer_open = [
            t for t in tickets
            if t.customer_impacting and t.status not in ("Done",)
        ]
        if customer_open:
            findings.append(RiskFinding(
                title="Customer-impacting issues unresolved",
                severity=Severity.CRITICAL,
                confidence=0.97,
                evidence_ticket_ids=[t.id for t in customer_open],
                description=f"{len(customer_open)} open items are flagged as customer-impacting.",
            ))

        # Pattern 5: Dependency chains (blocked_by non-empty)
        chained = [t for t in tickets if t.blocked_by]
        if len(chained) >= 2:
            findings.append(RiskFinding(
                title="Dependency chain risk",
                severity=Severity.HIGH,
                confidence=0.90,
                evidence_ticket_ids=[t.id for t in chained],
                description=f"Dependency chain detected: {len(chained)} tickets blocked by upstream items.",
            ))

        return findings

    def _worst_severity(self, findings: list[RiskFinding]) -> Severity:
        order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]
        for s in order:
            if any(f.severity == s for f in findings):
                return s
        return Severity.LOW

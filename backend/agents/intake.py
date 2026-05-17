"""
agents/intake.py

Intake Agent — parses user query into a structured task object.
Extracts: project, timeframe, action_type (read/write), urgency, confidence.

Phase 1: Returns a stub output for skeleton testing.
Phase 2: Replace _parse_with_llm() with real Groq call.
"""

from core.schemas import (
    ActionType,
    AgentStatus,
    IntakeOutput,
    PipelineState,
    Severity,
)
from agents.base import BaseAgent


class IntakeAgent(BaseAgent):
    name = "intake"

    async def run(self, state: PipelineState) -> PipelineState:
        try:
            output = await self._parse(state.user_query)
            state.intake = output
            state.add_trace(
                agent=self.name,
                status=AgentStatus.SUCCESS,
                confidence=output.confidence,
            )
        except Exception as exc:
            state.add_trace(
                agent=self.name,
                status=AgentStatus.FAILED,
                notes=str(exc),
            )
            state.blocked_reason = "Intake agent failed to parse query."

        return state

    async def _parse(self, query: str) -> IntakeOutput:
        """
        Phase 1: rule-based stub.
        Phase 2: replace with structured LLM call returning IntakeOutput JSON.
        """
        query_lower = query.lower()

        # Detect write intent
        write_keywords = ["draft", "create", "escalate", "assign", "update", "generate ticket"]
        action_type = (
            ActionType.WRITE
            if any(kw in query_lower for kw in write_keywords)
            else ActionType.READ
        )

        # Detect urgency
        if any(w in query_lower for w in ["critical", "urgent", "asap", "immediately"]):
            urgency = Severity.CRITICAL
        elif any(w in query_lower for w in ["high", "risk", "blocker", "blocked"]):
            urgency = Severity.HIGH
        else:
            urgency = Severity.MEDIUM

        # Extract project hint
        if "phoenix" in query_lower:
            project = "Phoenix"
        elif "atlas" in query_lower:
            project = "Atlas"
        else:
            project = "all"

        # Timeframe hint
        if "this week" in query_lower:
            timeframe = "this week"
        elif "today" in query_lower:
            timeframe = "today"
        else:
            timeframe = "current sprint"

        return IntakeOutput(
            project=project,
            timeframe=timeframe,
            action_type=action_type,
            urgency=urgency,
            raw_intent=query,
            confidence=0.80,  # Phase 2: real confidence from LLM logprobs or self-eval
        )

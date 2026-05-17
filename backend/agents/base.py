"""
agents/base.py

Abstract base class for all agents.
Enforces the contract: every agent receives PipelineState,
returns PipelineState, and handles its own errors gracefully.
"""

from abc import ABC, abstractmethod
import logging

from core.schemas import AgentStatus, PipelineState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str = "base"
    timeout_seconds: int = 30

    @abstractmethod
    async def run(self, state: PipelineState) -> PipelineState:
        """
        Execute this agent's logic.
        Must return the updated PipelineState with output appended.
        Must call state.add_trace() before returning.
        Must never raise — handle exceptions and return a FAILED trace.
        """
        ...

    async def __call__(self, state: PipelineState) -> PipelineState:
        logger.info(f"[{self.name}] starting — run_id={state.run_id}")
        try:
            result = await self.run(state)
            logger.info(f"[{self.name}] complete")
            return result
        except Exception as exc:
            logger.error(f"[{self.name}] unhandled error: {exc}", exc_info=True)
            state.add_trace(
                agent=self.name,
                status=AgentStatus.FAILED,
                notes=f"Unhandled error: {type(exc).__name__}: {exc}",
            )
            state.blocked_reason = f"{self.name} failed unexpectedly."
            return state

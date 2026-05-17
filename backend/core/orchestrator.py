"""
core/orchestrator.py

LangGraph orchestrator.
Defines the agent graph, conditional routing (read vs write path),
and the pipeline entry point.

All agents share a single PipelineState object threaded through every node.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from agents.critic import CriticAgent
from agents.intake import IntakeAgent
from agents.planning import PlanningAgent
from agents.retrieval import RetrievalAgent
from agents.risk_analysis import RiskAnalysisAgent
from agents.security_policy import SecurityPolicyAgent
from agents.workflow_action import WorkflowActionAgent
from core.schemas import ActionType, ApprovalStatus, PipelineState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Instantiate agents (singletons — FAISS loads once)
# ---------------------------------------------------------------------------
_intake = IntakeAgent()
_retrieval = RetrievalAgent()
_risk = RiskAnalysisAgent()
_planning = PlanningAgent()
_critic = CriticAgent()
_security = SecurityPolicyAgent()
_action = WorkflowActionAgent()


# ---------------------------------------------------------------------------
# Node wrappers (LangGraph nodes must be sync or async callables)
# ---------------------------------------------------------------------------
async def intake_node(state: dict) -> dict:
    ps = PipelineState(**state)
    ps = await _intake(ps)
    return ps.model_dump()

async def retrieval_node(state: dict) -> dict:
    ps = PipelineState(**state)
    ps = await _retrieval(ps)
    return ps.model_dump()

async def risk_node(state: dict) -> dict:
    ps = PipelineState(**state)
    ps = await _risk(ps)
    return ps.model_dump()

async def planning_node(state: dict) -> dict:
    ps = PipelineState(**state)
    ps = await _planning(ps)
    return ps.model_dump()

async def critic_node(state: dict) -> dict:
    ps = PipelineState(**state)
    ps = await _critic(ps)
    return ps.model_dump()

async def security_node(state: dict) -> dict:
    ps = PipelineState(**state)
    ps = await _security(ps)
    return ps.model_dump()

async def action_node(state: dict) -> dict:
    ps = PipelineState(**state)
    ps = await _action(ps)
    return ps.model_dump()


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------

def should_continue_after_retrieval(state: dict) -> str:
    """Block pipeline if retrieval confidence is too low."""
    ps = PipelineState(**state)
    if ps.blocked_reason:
        return "end"
    return "risk"


def should_continue_after_security(state: dict) -> str:
    """Route to action agent only if write path and cleared."""
    ps = PipelineState(**state)
    if ps.blocked_reason or not ps.security or not ps.security.cleared:
        return "end"
    if (
        ps.intake
        and ps.intake.action_type == ActionType.WRITE
        and ps.approval_status != ApprovalStatus.PENDING
    ):
        return "action"
    return "end"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    graph = StateGraph(dict)

    graph.add_node("intake", intake_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("risk", risk_node)
    graph.add_node("planning", planning_node)
    graph.add_node("critic", critic_node)
    graph.add_node("security", security_node)
    graph.add_node("action", action_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "retrieval")
    graph.add_conditional_edges("retrieval", should_continue_after_retrieval, {"risk": "risk", "end": END})
    graph.add_edge("risk", "planning")
    graph.add_edge("planning", "critic")
    graph.add_edge("critic", "security")
    graph.add_conditional_edges("security", should_continue_after_security, {"action": "action", "end": END})
    graph.add_edge("action", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

_compiled_graph = None

def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


async def run_pipeline(query: str, user_role: str = "analyst") -> PipelineState:
    """
    Entry point for the full agent pipeline.
    Returns the final PipelineState with all agent outputs and trace.
    """
    initial_state = PipelineState(user_query=query, user_role=user_role)
    graph = get_graph()

    logger.info(f"Pipeline starting — run_id={initial_state.run_id}")
    result = await graph.ainvoke(initial_state.model_dump())
    final_state = PipelineState(**result)
    logger.info(f"Pipeline complete — run_id={final_state.run_id}, agents={[t.agent for t in final_state.trace]}")

    return final_state

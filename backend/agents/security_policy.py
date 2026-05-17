"""
agents/security_policy.py

Security / Policy Agent — enforces:
  - PII masking in ticket data
  - Role-based action constraints
  - Output filtering
  - Audit flag generation

Phase 1: Pattern-based PII masking + role constraint stub.
Phase 2: Add LLM-assisted policy reasoning for edge cases.
"""

import re

from core.schemas import (
    AgentStatus,
    ApprovalStatus,
    PipelineState,
    SecurityOutput,
)
from agents.base import BaseAgent

# Simple PII patterns — extended in Phase 2
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE_RE = re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")
_CC_RE = re.compile(r"\b(?:\d[ -]?){13,16}\b")

# Role-based write permissions
_WRITE_ALLOWED_ROLES = {"manager", "executive"}


class SecurityPolicyAgent(BaseAgent):
    name = "security_policy"

    async def run(self, state: PipelineState) -> PipelineState:
        policy_flags: list[str] = []
        pii_masked = False

        # 1. PII masking in executive summary
        summary = ""
        if state.planning:
            summary = state.planning.executive_summary
            masked, was_masked = self._mask_pii(summary)
            if was_masked:
                pii_masked = True
                policy_flags.append("PII detected and masked in executive summary.")
                # Update the summary in-place
                state.planning.executive_summary = masked
            summary = state.planning.executive_summary

        # 2. Role-based write constraint
        has_write_actions = state.critic and any(
            r.action_type.value == "write"
            for r in state.critic.revised_recommendations
        )

        if has_write_actions and state.user_role not in _WRITE_ALLOWED_ROLES:
            policy_flags.append(
                f"Role '{state.user_role}' is not permitted to execute write actions. "
                f"Recommendations downgraded to read-only."
            )
            # Downgrade write recs to read
            if state.critic:
                for rec in state.critic.revised_recommendations:
                    from core.schemas import ActionType
                    rec.action_type = ActionType.READ

        # 3. Set approval gate for write actions
        if has_write_actions and state.user_role in _WRITE_ALLOWED_ROLES:
            state.approval_status = ApprovalStatus.PENDING
            state.approval_required_for = [
                r.title for r in (state.critic.revised_recommendations if state.critic else [])
                if r.action_type.value == "write"
            ]

        cleared = len([f for f in policy_flags if "not permitted" in f]) == 0

        state.security = SecurityOutput(
            cleared=cleared,
            pii_masked=pii_masked,
            injection_detected=False,  # already checked pre-orchestration
            policy_flags=policy_flags,
            sanitized_summary=summary,
        )
        state.add_trace(
            agent=self.name,
            status=AgentStatus.SUCCESS,
            notes=f"cleared={cleared}, pii_masked={pii_masked}, flags={len(policy_flags)}",
        )
        return state

    def _mask_pii(self, text: str) -> tuple[str, bool]:
        original = text
        text = _EMAIL_RE.sub("[EMAIL REDACTED]", text)
        text = _PHONE_RE.sub("[PHONE REDACTED]", text)
        text = _CC_RE.sub("[CARD REDACTED]", text)
        return text, text != original

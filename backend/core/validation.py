"""
core/validation.py

Pre-orchestration validation layer.
This runs BEFORE LangGraph initializes — nothing enters the agent
graph without passing these checks.

Covers:
  - Input size constraints
  - Basic prompt injection pattern detection
  - Role validation
  - Request sanitization
"""

import re

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Injection patterns — common adversarial prefixes
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"you are now",
    r"disregard (your )?(system|previous)",
    r"act as (a )?(different|new|unrestricted)",
    r"jailbreak",
    r"do anything now",
    r"pretend (you are|to be)",
    r"forget (your )?(instructions|guidelines|rules)",
    r"<\s*script",           # script tag injection
    r"system\s*:",           # fake system message
    r"assistant\s*:",        # fake assistant turn
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]

VALID_ROLES = {"analyst", "manager", "executive"}
MAX_QUERY_LENGTH = 2000


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    valid: bool
    sanitized_query: str
    injection_detected: bool = False
    errors: list[str] = []


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def validate_request(query: str, role: str) -> ValidationResult:
    """
    Run all pre-orchestration checks.
    Returns a ValidationResult — caller must check .valid before
    initializing the LangGraph pipeline.
    """
    errors: list[str] = []
    injection_detected = False

    # 1. Size constraint
    if not query or not query.strip():
        return ValidationResult(
            valid=False,
            sanitized_query="",
            errors=["Query cannot be empty."],
        )

    if len(query) > MAX_QUERY_LENGTH:
        errors.append(
            f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters."
        )

    # 2. Role validation
    if role not in VALID_ROLES:
        errors.append(f"Invalid role '{role}'. Must be one of: {VALID_ROLES}.")

    # 3. Injection detection
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(query):
            injection_detected = True
            errors.append("Potential prompt injection detected in query.")
            break

    # 4. Sanitize — strip null bytes and control characters
    sanitized = _sanitize(query)

    return ValidationResult(
        valid=len(errors) == 0,
        sanitized_query=sanitized,
        injection_detected=injection_detected,
        errors=errors,
    )


def _sanitize(text: str) -> str:
    """Remove null bytes and non-printable control characters."""
    # Keep newlines and tabs (legitimate in multi-line queries)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return cleaned.strip()

"""
Security Agent — validates write actions before execution.
Ensures no action bypasses guardrails.
"""

VALID_TEAM = {"Sidharth Jain", "Robo Mineboy", "Aryan Ghosh"}
VALID_PRIORITIES = {"Highest", "High", "Medium", "Low"}
VALID_ACTION_TYPES = {"create_ticket", "update_assignee", "set_due_date", "add_comment"}
MAX_SUMMARY_LENGTH = 200
MAX_COMMENT_LENGTH = 1000

def validate_write_action(action):
    """
    Validates a pending write action before it reaches the Writer Agent.
    Returns (approved: bool, reason: str)
    """
    action_type = action.get("action_type")
    
    # Check action type is valid
    if action_type not in VALID_ACTION_TYPES:
        return False, f"Unknown action type '{action_type}' — blocked"

    # Validate create_ticket
    if action_type == "create_ticket":
        summary = action.get("summary", "")
        priority = action.get("priority", "")
        assignee = action.get("assignee", "")

        if not summary or len(summary) < 5:
            return False, "Ticket summary too short or missing"
        if len(summary) > MAX_SUMMARY_LENGTH:
            return False, f"Ticket summary exceeds {MAX_SUMMARY_LENGTH} characters"
        if priority not in VALID_PRIORITIES:
            return False, f"Invalid priority '{priority}'"
        if assignee and assignee not in VALID_TEAM:
            return False, f"Assignee '{assignee}' is not a valid team member"

    # Validate update_assignee
    elif action_type == "update_assignee":
        ticket_id = action.get("ticket_id", "")
        assignee = action.get("assignee", "")

        if not ticket_id.startswith("SS-"):
            return False, f"Invalid ticket ID '{ticket_id}'"
        if assignee not in VALID_TEAM:
            return False, f"Assignee '{assignee}' is not a valid team member"

    # Validate set_due_date
    elif action_type == "set_due_date":
        import re
        ticket_id = action.get("ticket_id", "")
        due_date = action.get("due_date", "")

        if not ticket_id.startswith("SS-"):
            return False, f"Invalid ticket ID '{ticket_id}'"
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", due_date):
            return False, f"Invalid date format '{due_date}' — must be YYYY-MM-DD"

    # Validate add_comment
    elif action_type == "add_comment":
        ticket_id = action.get("ticket_id", "")
        comment = action.get("comment", "")

        if not ticket_id.startswith("SS-"):
            return False, f"Invalid ticket ID '{ticket_id}'"
        if not comment or len(comment) < 3:
            return False, "Comment too short or missing"
        if len(comment) > MAX_COMMENT_LENGTH:
            return False, f"Comment exceeds {MAX_COMMENT_LENGTH} characters"

    return True, "Action cleared by Security Agent"


def validate_all_actions(pending_actions):
    """Validate a list of pending actions. Returns cleared and blocked lists."""
    cleared = []
    blocked = []

    for action in pending_actions:
        approved, reason = validate_write_action(action)
        action["security_status"] = "cleared" if approved else "blocked"
        action["security_reason"] = reason

        if approved:
            cleared.append(action)
        else:
            blocked.append(action)

    return cleared, blocked
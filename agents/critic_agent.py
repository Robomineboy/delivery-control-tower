import os
import json
from datetime import date
from dotenv import load_dotenv

load_dotenv()

VALID_TEAM = {"Aryan Ghosh", "Sidharth Jain", "Robo Mineboy"}

# ─── Risk path ────────────────────────────────────────────────────────────────

def validate_findings(findings, tickets):
    ticket_map = {t["id"]: t for t in tickets}
    validated = []
    flagged = []

    for finding in findings:
        evidence_ids = finding.get("evidence", [])

        valid_evidence = [eid for eid in evidence_ids if eid in ticket_map]
        if not valid_evidence:
            flagged.append(f"Removed '{finding['risk']}' — evidence {evidence_ids} not in retrieved tickets")
            continue

        severity = finding["severity"]
        evidence_tickets = [ticket_map[eid] for eid in valid_evidence]

        if severity == "CRITICAL":
            has_critical = any(
                t["priority"] in ("Highest", "Critical") or
                t["status"] == "Blocked" or
                (t.get("due_date") and t["due_date"] < date.today().isoformat())
                for t in evidence_tickets
            )
            if not has_critical:
                finding["severity"] = "HIGH"
                finding["confidence"] = round(finding["confidence"] - 0.1, 2)
                flagged.append(f"Downgraded '{finding['risk']}' from CRITICAL to HIGH — evidence doesn't support it")

        if len(valid_evidence) == 1 and finding["confidence"] > 0.85:
            finding["confidence"] = 0.85
            flagged.append(f"Capped confidence for '{finding['risk']}' — single ticket evidence")

        validated.append(finding)

    return validated, flagged


# ─── Planning path ────────────────────────────────────────────────────────────

def validate_plan(plan, findings, tickets):
    ticket_ids = {t["id"] for t in tickets}
    finding_titles = {f["risk"] for f in findings}
    flagged = []
    validated = []

    for action in plan:
        # Check ticket IDs are real
        invalid_tickets = [tid for tid in action.get("ticket_ids", []) if tid not in ticket_ids]
        if invalid_tickets:
            flagged.append(f"Action '{action['action'][:40]}' references non-existent tickets: {invalid_tickets}")
            action["ticket_ids"] = [tid for tid in action["ticket_ids"] if tid in ticket_ids]

        # Check owner is a real team member
        owner = action.get("owner", "")
        if owner not in VALID_TEAM and owner not in ("Unassigned", "Team Lead", "unassigned"):
            flagged.append(f"Action '{action['action'][:40]}' has unrecognized owner '{owner}' — set to Team Lead")
            action["owner"] = "Team Lead"

        # Check priority is valid
        if action.get("priority") not in ("IMMEDIATE", "THIS_WEEK", "BACKLOG"):
            action["priority"] = "THIS_WEEK"
            flagged.append(f"Invalid priority on action — defaulted to THIS_WEEK")

        validated.append(action)

    return validated, flagged


# ─── Summary path ─────────────────────────────────────────────────────────────

def validate_summary(summary, tickets):
    ticket_ids = {t["id"] for t in tickets}
    flagged = []

    # Check for hallucinated ticket references
    import re
    mentioned = set(re.findall(r'SS-\d+', summary))
    hallucinated = mentioned - ticket_ids
    if hallucinated:
        flagged.append(f"Summary references tickets not in retrieved set: {hallucinated}")

    return summary, flagged
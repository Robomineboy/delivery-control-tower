import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def validate_findings(findings, tickets):
    """
    Validates each finding against the actual ticket evidence.
    Removes or downgrades findings that aren't supported by the data.
    """
    ticket_map = {t["id"]: t for t in tickets}
    validated = []
    flagged = []

    for finding in findings:
        evidence_ids = finding.get("evidence", [])

        # Check 1: evidence tickets actually exist
        valid_evidence = [eid for eid in evidence_ids if eid in ticket_map]
        if not valid_evidence:
            flagged.append(f"Removed '{finding['risk']}' — evidence {evidence_ids} not in retrieved tickets")
            continue

        # Check 2: severity matches actual ticket data
        severity = finding["severity"]
        evidence_tickets = [ticket_map[eid] for eid in valid_evidence]

        # CRITICAL findings need at least one critical/highest ticket or overdue
        if severity == "CRITICAL":
            has_critical = any(
                t["priority"] in ("Highest", "Critical") or
                t["status"] == "Blocked" or
                t.get("due_date") and t["due_date"] < __import__('datetime').date.today().isoformat()
                for t in evidence_tickets
            )
            if not has_critical:
                finding["severity"] = "HIGH"
                finding["confidence"] = round(finding["confidence"] - 0.1, 2)
                flagged.append(f"Downgraded '{finding['risk']}' from CRITICAL to HIGH — evidence doesn't support critical severity")

        # Check 3: confidence too high for weak evidence
        if len(valid_evidence) == 1 and finding["confidence"] > 0.85:
            finding["confidence"] = 0.85
            flagged.append(f"Capped confidence for '{finding['risk']}' — single ticket evidence")

        validated.append(finding)

    return validated, flagged

if __name__ == "__main__":
    import sys
    sys.path.append("../data")
    sys.path.append("../risk")
    from tickets import get_all_tickets
    from risk_agent import analyze_risks

    tickets = get_all_tickets()
    findings = analyze_risks(tickets)

    print("Raw findings from Risk Agent:")
    for f in findings:
        print(f"  [{f['severity']}] {f['risk']} (confidence: {f['confidence']})")

    print("\nRunning Critic validation...\n")
    validated, flagged = validate_findings(findings, tickets)

    if flagged:
        print("Flags raised:")
        for flag in flagged:
            print(f"  ⚠ {flag}")
        print()

    print(f"Validated findings ({len(validated)} of {len(findings)} passed):")
    for f in validated:
        print(f"  [{f['severity']}] {f['risk']} (confidence: {f['confidence']})")
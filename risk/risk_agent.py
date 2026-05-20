from datetime import date

def analyze_risks(tickets):
    findings = []
    today = date.today().isoformat()

    # Pattern 1: Blocked tickets
    blocked = [t for t in tickets if t["status"] == "Blocked"]
    if blocked:
        findings.append({
            "risk": "Active blockers detected",
            "severity": "HIGH",
            "confidence": 0.95,
            "evidence": [t["id"] for t in blocked],
            "detail": f"{len(blocked)} ticket(s) are blocked: " +
                     ", ".join(f"{t['id']} ({t['title']})" for t in blocked)
        })

    # Pattern 2: Overdue tickets (past due date)
    overdue = [t for t in tickets if t.get("due_date") and t["due_date"] < today]
    if overdue:
        findings.append({
            "risk": "SLA violations — tickets past due date",
            "severity": "CRITICAL",
            "confidence": 0.99,
            "evidence": [t["id"] for t in overdue],
            "detail": f"{len(overdue)} ticket(s) past their due date: " +
                     ", ".join(f"{t['id']} due {t['due_date']}" for t in overdue)
        })

    # Pattern 3: High priority with no owner
    unowned = [
        t for t in tickets
        if t["assignee"] is None and t["priority"] in ("Highest", "High")
    ]
    if unowned:
        findings.append({
            "risk": "High priority tickets with no owner",
            "severity": "HIGH",
            "confidence": 0.98,
            "evidence": [t["id"] for t in unowned],
            "detail": f"{len(unowned)} high priority ticket(s) unassigned: " +
                     ", ".join(f"{t['id']} ({t['title']})" for t in unowned)
        })

    # Pattern 4: Customer impacting open issues
    customer_issues = [
        t for t in tickets
        if t["customer_impacting"] and t["status"] != "Done"
    ]
    if customer_issues:
        findings.append({
            "risk": "Open customer-impacting issues",
            "severity": "CRITICAL",
            "confidence": 0.97,
            "evidence": [t["id"] for t in customer_issues],
            "detail": f"{len(customer_issues)} customer-impacting ticket(s) unresolved: " +
                     ", ".join(t["id"] for t in customer_issues)
        })

    # Pattern 5: Highest priority bugs
    critical_bugs = [
        t for t in tickets
        if t["type"] == "Bug" and t["priority"] == "Highest"
    ]
    if critical_bugs:
        findings.append({
            "risk": "Critical bugs unresolved",
            "severity": "CRITICAL",
            "confidence": 0.96,
            "evidence": [t["id"] for t in critical_bugs],
            "detail": f"{len(critical_bugs)} critical bug(s) open: " +
                     ", ".join(f"{t['id']} ({t['title']})" for t in critical_bugs)
        })

    return findings

def get_overall_severity(findings):
    if any(f["severity"] == "CRITICAL" for f in findings):
        return "CRITICAL"
    if any(f["severity"] == "HIGH" for f in findings):
        return "HIGH"
    if any(f["severity"] == "MEDIUM" for f in findings):
        return "MEDIUM"
    return "LOW"

if __name__ == "__main__":
    import sys
    sys.path.append("../data")
    from tickets import get_all_tickets

    tickets = get_all_tickets()

    print("Running Risk Analysis...\n")
    findings = analyze_risks(tickets)
    severity = get_overall_severity(findings)

    print(f"Overall project health: {severity}")
    print(f"Total findings: {len(findings)}\n")

    for f in findings:
        print(f"[{f['severity']}] {f['risk']}")
        print(f"  Confidence: {f['confidence']}")
        print(f"  Evidence:   {f['evidence']}")
        print(f"  Detail:     {f['detail']}")
        print()
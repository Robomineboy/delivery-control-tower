import sys
sys.path.append("data")
sys.path.append("intake")
sys.path.append("retrieval")
sys.path.append("risk")
sys.path.append("critic")

from tickets import get_all_tickets
from intake_agent import parse_query
from retrieval_agent import retrieve_filtered
from risk_agent import analyze_risks, get_overall_severity
from critic_agent import validate_findings

def run(user_query):
    print(f"Query: '{user_query}'")
    print("-" * 60)

    # Step 1: Intake
    parsed = parse_query(user_query)
    print(f"Intent:  {parsed['intent']} | Urgency: {parsed['urgency']}")
    print(f"Filters: {parsed['filters']}")
    print()

    # Step 2: Retrieval
    results = retrieve_filtered(parsed['query'], filters=parsed['filters'] or None)
    tickets = [r['ticket'] for r in results]
    print(f"Retrieved {len(tickets)} tickets")
    for r in results:
        t = r['ticket']
        print(f"  [{r['score']}] {t['id']} — {t['title']} [{t['status']}]")
    print()

    # Step 3: Risk Analysis
    print("Running LLM risk analysis...")
    findings = analyze_risks(tickets)
    print(f"Raw findings: {len(findings)}")
    print()

    # Step 4: Critic validation
    print("Running Critic validation...")
    validated, flagged = validate_findings(findings, tickets)
    if flagged:
        for flag in flagged:
            print(f"  ⚠ {flag}")
    print(f"Validated findings: {len(validated)} of {len(findings)} passed")
    print()

    severity = get_overall_severity(validated)
    print(f"Overall health: {severity}")
    print()

    for f in validated:
        print(f"  [{f['severity']}] {f['risk']}")
        print(f"    Confidence: {f['confidence']}")
        print(f"    Evidence:   {f['evidence']}")
        print(f"    Detail:     {f['detail']}")
        print()

    return {
        "query": user_query,
        "intent": parsed["intent"],
        "tickets": tickets,
        "findings": validated,
        "flagged": flagged,
        "overall_severity": severity
    }

if __name__ == "__main__":
    queries = [
        "What are the biggest risks this sprint?",
        "Show me blocked and unassigned tickets",
        "What is the overall project health?"
    ]

    for q in queries:
        run(q)
        print("=" * 60)
        print()
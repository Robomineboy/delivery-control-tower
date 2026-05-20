import sys
sys.path.append("data")
sys.path.append("intake")
sys.path.append("retrieval")
sys.path.append("risk")

from tickets import get_all_tickets
from intake_agent import parse_query
from retrieval_agent import retrieve_filtered
from risk_agent import analyze_risks, get_overall_severity

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
    severity = get_overall_severity(findings)

    print(f"\nOverall health: {severity}")
    print(f"Findings: {len(findings)}\n")
    for f in findings:
        print(f"  [{f['severity']}] {f['risk']}")
        print(f"    Confidence: {f['confidence']}")
        print(f"    Evidence:   {f['evidence']}")
        print(f"    Detail:     {f['detail']}")
        print()

    return {
        "query": user_query,
        "intent": parsed['intent'],
        "tickets": tickets,
        "findings": findings,
        "overall_severity": severity
    }

if __name__ == "__main__":
    queries = [
        "What are the biggest risks this sprint?",
        "Show me blocked and unassigned tickets",
    ]

    for q in queries:
        run(q)
        print("=" * 60)
        print()
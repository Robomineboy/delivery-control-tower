import sys
sys.path.append("data")

from agents.token_logger import reset_tokens, get_token_summary
from agents.intake_agent import parse_query
from agents.retrieval_agent import retrieve_filtered
from agents.risk_agent import analyze_risks, get_overall_severity
from agents.critic_agent import validate_findings, validate_plan
from agents.summary_agent import summarize
from agents.planning_agent import generate_plan

RISK_INTENTS = {"risk_analysis", "blocker_analysis", "ownership_gap", "planning"}
SUMMARY_INTENTS = {"person_query", "project_summary", "general", "timeline"}

def run(user_query):
    reset_tokens()
    print(f"\nQuery: '{user_query}'")
    print("-" * 60)

    # Step 1: Intake
    parsed = parse_query(user_query)
    intent = parsed["intent"]
    print(f"Intent: {intent} | Urgency: {parsed['urgency']}")
    print(f"Filters: {parsed['filters']}")
    print(f"Search: {parsed['search_query']}")

    # Step 2: Retrieval
    filters = parsed["filters"] if parsed["filters"] else None

    if intent == "project_summary":
        from tickets import get_all_tickets
        tickets = get_all_tickets()
        results = [{"ticket": t, "score": 1.0} for t in tickets]
    else:
        results = retrieve_filtered(parsed["search_query"], filters=filters)
        tickets = [r["ticket"] for r in results]

    print(f"Retrieved {len(tickets)} tickets")

    # Step 3: Route
    if intent in RISK_INTENTS:
        print("Path: Risk Analysis + Planning")

        # Risk Analysis
        findings = analyze_risks(tickets)
        validated, flagged = validate_findings(findings, tickets)
        severity = get_overall_severity(validated)

        # Planning
        raw_plan = generate_plan(user_query, validated, tickets)
        plan, plan_flags = validate_plan(raw_plan, validated, tickets)
        flagged.extend(plan_flags)

        print(f"Findings: {len(validated)} | Actions: {len(plan)}")

        return {
            "query": user_query,
            "intent": intent,
            "path": "risk",
            "tickets": tickets,
            "findings": validated,
            "flagged": flagged,
            "severity": severity,
            "summary": None,
            "plan": plan,
            "tokens": get_token_summary(),
            "trace": [
                {"agent": "Intake Agent", "status": "success", "detail": f"Intent: {intent} | Urgency: {parsed['urgency']}"},
                {"agent": "Retrieval Agent", "status": "success", "detail": f"Retrieved {len(tickets)} tickets"},
                {"agent": "Risk Analysis Agent", "status": "success", "detail": f"Generated {len(findings)} findings"},
                {"agent": "Critic Agent", "status": "success" if not flagged else "flagged", "detail": f"{len(validated)}/{len(findings)} validated | {len(flagged)} flagged"},
                {"agent": "Planning Agent", "status": "success", "detail": f"{len(plan)} actions generated"},
            ]
        }

    else:
        print("Path: Summary")
        answer = summarize(user_query, tickets, intent)
        print(f"Answer: {answer[:100]}...")

        return {
            "query": user_query,
            "intent": intent,
            "path": "summary",
            "tickets": tickets,
            "findings": [],
            "flagged": [],
            "severity": None,
            "summary": answer,
            "plan": [],
            "tokens": get_token_summary(),
            "trace": [
                {"agent": "Intake Agent", "status": "success", "detail": f"Intent: {intent} | Urgency: {parsed['urgency']}"},
                {"agent": "Retrieval Agent", "status": "success", "detail": f"Retrieved {len(tickets)} tickets"},
                {"agent": "Summary Agent", "status": "success", "detail": "Direct answer generated"},
            ]
        }

if __name__ == "__main__":
    queries = [
        "What is Aryan working on?",
        "What are the biggest risks this sprint?",
        "What is the overall project health?",
        "Show me all blocked tickets",
        "Who is overloaded?",
        "Give me the plan for today",
    ]
    for q in queries:
        result = run(q)
        if result["path"] == "summary":
            print(f"\nAnswer: {result['summary']}")
        else:
            for f in result["findings"]:
                print(f"  [{f['severity']}] {f['risk']}")
            for a in result["plan"]:
                print(f"  [{a['priority']}] {a['action']}")
        print("=" * 60)
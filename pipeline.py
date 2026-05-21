import sys
sys.path.append("data")

from agents.token_logger import reset_tokens, get_token_summary
from agents.intake_agent import parse_query
from agents.retrieval_agent import retrieve_filtered
from agents.risk_agent import analyze_risks, get_overall_severity
from agents.critic_agent import validate_findings, validate_plan
from agents.summary_agent import summarize
from agents.planning_agent import generate_plan, generate_write_actions
from agents.security_agent import validate_all_actions as security_validate
from data.tickets import get_all_tickets

WRITE_INTENTS = {"write_action", "create_ticket", "update_board"}
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

    if intent in ("project_summary", "ownership_gap", "risk_analysis", "blocker_analysis", "planning") or "overload" in parsed["search_query"].lower():
        tickets = get_all_tickets()
        results = [{"ticket": t, "score": 1.0} for t in tickets]
    else:
        results = retrieve_filtered(parsed["search_query"], filters=filters)
        tickets = [r["ticket"] for r in results]

    print(f"Retrieved {len(tickets)} tickets")

    # Step 3: Route
    if intent in WRITE_INTENTS:
        print("Path: Write Action")

        # Still do risk analysis for context
        findings = analyze_risks(tickets)
        validated, flagged = validate_findings(findings, tickets)
        severity = get_overall_severity(validated)

        # Generate write actions
        raw_actions = generate_write_actions(user_query, validated, tickets)
        cleared, blocked = security_validate(raw_actions)

        if blocked:
            flagged.extend([f"Security blocked: {a['security_reason']}" for a in blocked])

        print(f"Write actions: {len(cleared)} cleared | {len(blocked)} blocked")

        return {
            "query": user_query,
            "intent": intent,
            "path": "write",
            "tickets": tickets,
            "findings": validated,
            "flagged": flagged,
            "severity": severity,
            "summary": None,
            "plan": [],
            "pending_actions": cleared,
            "blocked_actions": blocked,
            "tokens": get_token_summary(),
            "trace": [
                {"agent": "Intake Agent", "status": "success", "detail": f"Intent: {intent} — write path"},
                {"agent": "Retrieval Agent", "status": "success", "detail": f"Retrieved {len(tickets)} tickets"},
                {"agent": "Risk Analysis Agent", "status": "success", "detail": f"{len(findings)} findings for context"},
                {"agent": "Planning Agent", "status": "success", "detail": f"{len(raw_actions)} actions generated"},
                {"agent": "Security Agent", "status": "success" if not blocked else "flagged", "detail": f"{len(cleared)} cleared | {len(blocked)} blocked"},
                {"agent": "Writer Agent", "status": "skipped", "detail": "Awaiting human approval"},
            ]
        }

    elif intent in RISK_INTENTS:
        print("Path: Risk Analysis + Planning")

        findings = analyze_risks(tickets)
        validated, flagged = validate_findings(findings, tickets)
        severity = get_overall_severity(validated)

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
            "pending_actions": [],
            "blocked_actions": [],
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
            "pending_actions": [],
            "blocked_actions": [],
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
        "Reassign SS-10 to Aryan Ghosh",
    ]
    for q in queries:
        result = run(q)
        if result["path"] == "summary":
            print(f"\nAnswer: {result['summary']}")
        elif result["path"] == "write":
            print(f"\nPending actions: {len(result['pending_actions'])}")
            for a in result["pending_actions"]:
                print(f"  {a['action_type']}: {a}")
        else:
            for f in result["findings"]:
                print(f"  [{f['severity']}] {f['risk']}")
            for a in result["plan"]:
                print(f"  [{a['priority']}] {a['action']}")
        print("=" * 60)
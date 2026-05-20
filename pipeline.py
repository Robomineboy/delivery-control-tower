import sys

from intake.intake_agent import parse_query
from retrieval.retrieval_agent import retrieve_filtered

def run(user_query):
    print(f"Query: '{user_query}'")
    print()

    # Step 1: Intake
    parsed = parse_query(user_query)
    print(f"Intent: {parsed['intent']} | Urgency: {parsed['urgency']}")
    print(f"Filters: {parsed['filters']}")
    print(f"Search query: '{parsed['query']}'")
    print()

    # Step 2: Retrieval
    results = retrieve_filtered(parsed['query'], filters=parsed['filters'] or None)

    print(f"Retrieved {len(results)} tickets:")
    for r in results:
        t = r['ticket']
        print(f"  [{r['score']}] {t['id']} — {t['title']}")
        print(f"           Status: {t['status']} | Priority: {t['priority']} | Assignee: {t['assignee'] or 'Unassigned'}")
    print()
    return parsed, results

if __name__ == "__main__":
    queries = [
        "What are the blocked tickets?",
        "Show me unassigned high priority issues",
        "What are the biggest risks in sensor firmware?",
    ]

    for q in queries:
        run(q)
        print("=" * 60)
        print()
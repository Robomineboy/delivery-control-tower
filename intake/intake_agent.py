def parse_query(user_query):
    query_lower = user_query.lower()

    # Detect intent
    if any(w in query_lower for w in ["risk", "risks", "broken", "failing", "problem"]):
        intent = "risk_analysis"
    elif any(w in query_lower for w in ["blocked", "blocker", "blocking"]):
        intent = "blocker_analysis"
    elif any(w in query_lower for w in ["unassigned", "no owner", "nobody"]):
        intent = "ownership_gap"
    elif any(w in query_lower for w in ["summary", "status", "overview", "health"]):
        intent = "project_summary"
    else:
        intent = "general"

    # Detect filters
    filters = {}
    if any(w in query_lower for w in ["blocked", "blocker"]):
        filters["status"] = "Blocked"
    if any(w in query_lower for w in ["unassigned", "no owner", "nobody"]):
        filters["assignee"] = None

    # Detect urgency
    if any(w in query_lower for w in ["urgent", "critical", "asap", "immediately"]):
        urgency = "critical"
    elif any(w in query_lower for w in ["high", "important", "priority"]):
        urgency = "high"
    else:
        urgency = "medium"

    # Clean query for retrieval
    stop_words = {"what", "are", "the", "is", "show", "me", "all", "any", "a", "an"}
    clean_query = " ".join(
        w for w in query_lower.split() if w not in stop_words
    )

    return {
        "intent": intent,
        "filters": filters,
        "query": clean_query,
        "urgency": urgency,
        "original": user_query,
    }

if __name__ == "__main__":
    test_queries = [
        "What are the blocked tickets?",
        "Show me unassigned high priority issues",
        "What are the biggest risks in sensor firmware?",
        "Give me a project health summary",
    ]

    for q in test_queries:
        result = parse_query(q)
        print(f"Input:   {q}")
        print(f"Output:  {result}")
        print()
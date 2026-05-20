import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def normalize(parsed):
    # Ensure required keys always exist
    parsed.setdefault("intent", "general")
    parsed.setdefault("search_query", parsed.get("original", ""))
    parsed.setdefault("filters", {})
    parsed.setdefault("urgency", "medium")
    parsed.setdefault("original", "")

    # Remove None-valued filters — they break downstream comparisons
    parsed["filters"] = {
        k: v for k, v in parsed["filters"].items()
        if v is not None or k == "assignee"  # assignee=None is valid (means unassigned)
    }

    return parsed

def parse_query(user_query):
    prompt = f"""You are parsing a user query about a software project management system.

Extract structured information from this query: "{user_query}"

Return ONLY a JSON object with no extra text:
{{
    "intent": one of [risk_analysis, blocker_analysis, ownership_gap, person_query, project_summary, general],
    "search_query": a clean 2-5 word search phrase to find relevant tickets,
    "filters": object with any of these exact keys if clearly implied:
        - "status": one of ["Blocked", "In Review", "To Do", "Done"]
        - "assignee_contains": first name of a person if query is about a specific person
        - "priority": one of ["Highest", "High", "Medium", "Low"]
        - "assignee": null if query asks about unassigned tickets
    "urgency": one of [critical, high, medium, low],
    "original": the original query
}}

Rules:
- Only include filters if they are clearly and explicitly implied
- search_query should capture the core topic
- If query mentions a person's name, set assignee_contains to their name
- If query asks about unassigned tickets, set assignee to null
- Never include both assignee and assignee_contains"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    parsed = json.loads(raw)
    return normalize(parsed)

if __name__ == "__main__":
    test_queries = [
        "What is Aryan working on?",
        "What are the biggest risks this sprint?",
        "Show me all blocked tickets",
        "Who is overloaded?",
        "What is the overall project health?",
        "Show me unassigned high priority tickets",
    ]

    for q in test_queries:
        result = parse_query(q)
        print(f"Input:  {q}")
        print(f"Intent: {result['intent']} | Urgency: {result['urgency']}")
        print(f"Filters: {result['filters']}")
        print(f"Search: {result['search_query']}")
        print()

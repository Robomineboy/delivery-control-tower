import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def tickets_to_prompt(tickets):
    lines = []
    for t in tickets:
        lines.append(
            f"- {t['id']}: {t['title']} | Status: {t['status']} | "
            f"Priority: {t['priority']} | Assignee: {t['assignee'] or 'Unassigned'} | "
            f"Type: {t['type']} | Due: {t.get('due_date') or 'None'} | "
            f"Blocked by: {t['blocked_by'] or 'None'}"
        )
    return "\n".join(lines)

def analyze_risks(tickets):
    ticket_text = tickets_to_prompt(tickets)

    prompt = f"""You are a senior delivery manager analyzing a software project's Jira board.

Here are the current tickets:

{ticket_text}

Today's date is {__import__('datetime').date.today().isoformat()}.

Analyze these tickets and identify the top risks. For each risk:
- Give it a title
- Assign severity: CRITICAL, HIGH, MEDIUM, or LOW
- Give a confidence score between 0.0 and 1.0
- List the ticket IDs that are evidence for this risk
- Write a clear detail explanation of why this is a risk

Return ONLY a JSON array with no extra text. Format:
[
  {{
    "risk": "risk title",
    "severity": "CRITICAL",
    "confidence": 0.95,
    "evidence": ["SS-15"],
    "detail": "explanation"
  }}
]"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    findings = json.loads(raw)
    return findings

def get_overall_severity(findings):
    for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if any(f["severity"] == level for f in findings):
            return level
    return "LOW"

if __name__ == "__main__":
    import sys
    sys.path.append("../data")
    from tickets import get_all_tickets

    tickets = get_all_tickets()
    print("Running LLM Risk Analysis...\n")

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
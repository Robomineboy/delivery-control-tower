import os
import json
from groq import Groq
from dotenv import load_dotenv
from agents.token_logger import log_tokens

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_plan(user_query, findings, tickets):
    if not findings:
        return []

    findings_text = "\n".join([
        f"- [{f['severity']}] {f['risk']} (confidence: {f['confidence']})\n"
        f"  Evidence: {', '.join(f['evidence'])}\n"
        f"  Detail: {f['detail']}"
        for f in findings
    ])

    ticket_map = {t["id"]: t for t in tickets}

    team_members = list(set(
        t["assignee"] for t in tickets if t["assignee"] is not None
    ))
    team_text = ", ".join(team_members) if team_members else "no assigned team members"

    prompt = f"""You are a senior delivery manager for a software project called SmartShoe.

The following risks have been identified:
{findings_text}

For each risk, generate a concrete recommended action.

Return ONLY a JSON array with no extra text:
[
  {{
    "risk": "exact risk title from above",
    "action": "specific action to take",
    "owner": "who should own this — use assignee names from evidence tickets if relevant",
    "priority": "IMMEDIATE, THIS_WEEK, or BACKLOG",
    "action_type": "reassign | escalate | schedule | investigate | unblock | monitor",
    "ticket_ids": ["relevant ticket IDs"]
  }}
]

The only real team members are: {team_text}.
Only assign ownership to real team members — if no one is a good fit, suggest "unassigned" and explain in the action detail.

Rules:
- Be specific and actionable — not generic advice
- IMMEDIATE = needs action today
- THIS_WEEK = needs action this sprint
- BACKLOG = low urgency, track it
- Owner should be a real person from the tickets where possible"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    log_tokens("Planning Agent", response.usage.prompt_tokens, response.usage.completion_tokens)
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "data"))  # dct/data
    sys.path.insert(0, str(Path(__file__).parent))                  # dct/agents
    from tickets import get_all_tickets
    from risk_agent import analyze_risks
    from critic_agent import validate_findings

    tickets = get_all_tickets()
    findings = analyze_risks(tickets)
    validated, _ = validate_findings(findings, tickets)

    print("Generating action plan...\n")
    plan = generate_plan("What are the risks?", validated, tickets)

    for p in plan:
        print(f"[{p['priority']}] {p['action']}")
        print(f"  Risk:    {p['risk']}")
        print(f"  Owner:   {p['owner']}")
        print(f"  Type:    {p['action_type']}")
        print(f"  Tickets: {p['ticket_ids']}")
        print()
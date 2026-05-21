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

def generate_write_actions(user_query, findings, tickets):
    """
    Generates specific Jira write actions from risk findings.
    Called when user explicitly requests changes.
    """
    from agents.writer_agent import TEAM_ACCOUNTS
    
    ticket_text = "\n".join([
        f"- {t['id']}: {t['title']} | Status: {t['status']} | "
        f"Priority: {t['priority']} | Assignee: {t['assignee'] or 'Unassigned'} | "
        f"Due: {t.get('due_date') or 'None'}"
        for t in tickets
    ])

    findings_text = "\n".join([
        f"- [{f['severity']}] {f['risk']} — Evidence: {', '.join(f['evidence'])}"
        for f in findings
    ])

    team = list(TEAM_ACCOUNTS.keys())

    prompt = f"""You are a Jira assistant executing a specific user request.

The user's EXACT request: "{user_query}"

Current tickets:
{ticket_text}

Valid team members: {', '.join(team)}
Valid priorities: Highest, High, Medium, Low
Today's date: {__import__('datetime').date.today().isoformat()}

IMPORTANT RULES:
- Execute EXACTLY what the user asked for — nothing more
- Do NOT add extra actions the user didn't request
- Do NOT reassign tickets the user didn't mention
- Do NOT set due dates unless the user asked for it
- Only reference ticket IDs that exist in the current tickets list
- Only use team members from the valid list

If the user said "assign SS-10 to Aryan", generate ONE action: update_assignee on SS-10 to Aryan.
If the user said "create a ticket for X", generate ONE action: create_ticket.

Return ONLY a JSON array with the minimum actions needed to fulfill the request:
[
  {{
    "action_type": "create_ticket|update_assignee|set_due_date|add_comment",
    "summary": "only for create_ticket",
    "description": "only for create_ticket", 
    "priority": "only for create_ticket",
    "assignee": "exact team member name — only for create_ticket or update_assignee",
    "ticket_id": "SS-XX — only for update_assignee, set_due_date, add_comment",
    "due_date": "YYYY-MM-DD — only for set_due_date",
    "comment": "only for add_comment",
    "reason": "one sentence explaining why"
  }}
]"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    from agents.token_logger import log_tokens
    log_tokens("Planning Agent", response.usage.prompt_tokens, response.usage.completion_tokens)

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
import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def summarize(user_query, tickets, intent):
    if not tickets:
        return "No tickets found matching your query."

    ticket_text = "\n".join([
        f"- {t['id']}: {t['title']} | Status: {t['status']} | "
        f"Priority: {t['priority']} | Assignee: {t['assignee'] or 'Unassigned'} | "
        f"Due: {t.get('due_date') or 'No due date'} | "
        f"Type: {t['type']}"
        for t in tickets
    ])

    prompt = f"""You are a delivery manager assistant for a software project called SmartShoe.

The user asked: "{user_query}"

Here are the relevant tickets:
{ticket_text}

Instructions:
- Answer the user's EXACT question directly in 2-4 sentences
- Be specific — use ticket IDs, names, statuses
- If asked about a person, summarize their workload clearly
- If asked about project health, give an honest assessment
- If asked about timelines, reference due dates
- Do not add generic advice or filler
- Write in plain conversational English"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    return response.choices[0].message.content.strip()

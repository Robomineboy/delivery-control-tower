import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))  # ensures dct/ is in path
from data.tickets import get_token

load_dotenv()

CLOUD_ID = "5d9f403d-19b0-4537-8fe4-f3a2e2780ef0"
PROJECT_KEY = "SS"

# Team account IDs — hardcoded from Jira
TEAM_ACCOUNTS = {
    "Sidharth Jain": "712020:2acfa153-b28a-4943-8933-91a245a61af1",
    "Robo Mineboy": "712020:9bdc815c-d35c-44ca-b4bc-4aa03eaf0321",
    "Aryan Ghosh": "712020:e924c121-1b4a-4059-83c8-8ee686d346df",
}

def get_account_id(name):
    """Get account ID for a team member by name (partial match)."""
    for member, aid in TEAM_ACCOUNTS.items():
        if name.lower() in member.lower():
            return aid
    return None

def _headers():
    token = get_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def create_ticket(summary, description, priority="Medium", assignee_account_id=None):
    """Create a new Jira ticket."""
    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
            },
            "issuetype": {"name": "Task"},
            "priority": {"name": priority}
        }
    }

    if assignee_account_id:
        payload["fields"]["assignee"] = {"accountId": assignee_account_id}

    response = requests.post(
        f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue",
        headers=_headers(),
        json=payload
    )

    if response.status_code == 201:
        data = response.json()
        return {"success": True, "ticket_id": data["key"], "message": f"Created {data['key']}: {summary}"}
    else:
        return {"success": False, "message": f"Failed to create ticket: {response.text}"}

def update_assignee(ticket_id, assignee_account_id):
    """Update the assignee of a ticket."""
    response = requests.put(
        f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{ticket_id}/assignee",
        headers=_headers(),
        json={"accountId": assignee_account_id}
    )

    if response.status_code == 204:
        return {"success": True, "message": f"Updated assignee for {ticket_id}"}
    else:
        return {"success": False, "message": f"Failed to update assignee: {response.text}"}

def set_due_date(ticket_id, due_date):
    """Set due date on a ticket. due_date format: YYYY-MM-DD"""
    response = requests.put(
        f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{ticket_id}",
        headers=_headers(),
        json={"fields": {"duedate": due_date}}
    )

    if response.status_code == 204:
        return {"success": True, "message": f"Set due date on {ticket_id} to {due_date}"}
    else:
        return {"success": False, "message": f"Failed to set due date: {response.text}"}

def add_comment(ticket_id, comment):
    """Add a comment to a ticket."""
    response = requests.post(
        f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/issue/{ticket_id}/comment",
        headers=_headers(),
        json={
            "body": {
                "type": "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]
            }
        }
    )

    if response.status_code == 201:
        return {"success": True, "message": f"Added comment to {ticket_id}"}
    else:
        return {"success": False, "message": f"Failed to add comment: {response.text}"}

def get_account_ids():
    """Get account IDs for all team members — needed for assignee updates."""
    response = requests.get(
        f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/user/assignable/search?project={PROJECT_KEY}",
        headers=_headers()
    )
    if response.status_code == 200:
        users = response.json()
        return {u["displayName"]: u["accountId"] for u in users}
    return {}

def get_account_ids_from_tickets():
    """Extract account IDs from existing tickets — works on free plan."""
    from data.tickets import get_token
    token = get_token()
    
    response = requests.post(
        f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/search/jql",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        json={
            "jql": "project=SS",
            "maxResults": 50,
            "fields": ["assignee", "summary"]
        }
    )
    
    users = {}
    if response.status_code == 200:
        for issue in response.json()["issues"]:
            assignee = issue["fields"].get("assignee")
            if assignee:
                users[assignee["displayName"]] = assignee["accountId"]
    
    print("Found account IDs:")
    for name, aid in users.items():
        print(f"  {name}: {aid}")
    return users



if __name__ == "__main__":
    # Test: add a comment to SS-16
    result = add_comment("SS-16", "DCT automated comment — write access confirmed.")
    print(result)
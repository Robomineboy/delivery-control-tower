import os
import json
import requests
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("JIRA_CLIENT_ID")
CLIENT_SECRET = os.getenv("JIRA_CLIENT_SECRET")
CLOUD_ID = "5d9f403d-19b0-4537-8fe4-f3a2e2780ef0"
TOKEN_FILE = "jira_token.json"

AUTH_CODE = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global AUTH_CODE
        params = parse_qs(urlparse(self.path).query)
        AUTH_CODE = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Done. Close this window.")

    def log_message(self, format, *args):
        pass

def _authorize_browser():
    """First time only — opens browser to get auth code."""
    params = {
        "audience": "api.atlassian.com",
        "client_id": CLIENT_ID,
        "scope": "read:jira-work offline_access",
        "redirect_uri": "http://localhost:8080/callback",
        "response_type": "code",
        "prompt": "consent"
    }
    url = "https://auth.atlassian.com/authorize?" + urllib.parse.urlencode(params)
    print("First time setup — opening browser for Jira authorization...")
    webbrowser.open(url)
    HTTPServer(("localhost", 8080), CallbackHandler).handle_request()
    return AUTH_CODE

def _exchange_code(code):
    """Exchange auth code for access + refresh tokens."""
    response = requests.post(
        "https://auth.atlassian.com/oauth/token",
        json={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": "http://localhost:8080/callback"
        }
    )
    return response.json()

def _refresh_access_token(refresh_token):
    """Use refresh token to get a new access token silently."""
    response = requests.post(
        "https://auth.atlassian.com/oauth/token",
        json={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token
        }
    )
    return response.json()

def get_token():
    """
    Returns a valid access token.
    - First run: opens browser, saves refresh token to jira_token.json
    - Subsequent runs: silently refreshes using saved token
    """
    # Check for saved token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            saved = json.load(f)

        print("Refreshing Jira token silently...")
        tokens = _refresh_access_token(saved["refresh_token"])

        if "access_token" in tokens:
            # Save updated tokens
            with open(TOKEN_FILE, "w") as f:
                json.dump({
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens.get("refresh_token", saved["refresh_token"])
                }, f)
            return tokens["access_token"]
        else:
            print("Refresh failed — re-authorizing...")
            os.remove(TOKEN_FILE)

    # First time — browser flow
    code = _authorize_browser()
    tokens = _exchange_code(code)

    if "access_token" not in tokens:
        raise Exception(f"Authorization failed: {tokens}")

    # Save tokens for next time
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"]
        }, f)

    print("Jira authorization complete. Token saved.")
    return tokens["access_token"]

def fetch_raw_issues(token):
    response = requests.post(
        f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3/search/jql",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        json={
            "jql": "project=SS AND issueType not in (Epic, Subtask) ORDER BY created DESC",
            "maxResults": 50,
            "fields": ["summary", "status", "priority", "assignee",
                      "labels", "comment", "duedate", "issuetype"]
        }
    )
    return response.json()["issues"]

def parse_tickets(raw_issues):
    tickets = []
    for issue in raw_issues:
        f = issue["fields"]

        if issue["key"] in ("SS-1", "SS-2", "SS-3", "SS-4"):
            continue

        assignee = f.get("assignee")
        comments = f.get("comment", {}).get("comments", [])

        tickets.append({
            "id": issue["key"],
            "title": f["summary"],
            "status": f["status"]["name"],
            "priority": f["priority"]["name"] if f.get("priority") else "Medium",
            "assignee": assignee["displayName"] if assignee else None,
            "type": f["type"]["name"] if f.get("type") else f["issuetype"]["name"],
            "labels": f.get("labels", []),
            "due_date": f.get("duedate"),
            "comments": [c["body"] for c in comments],
            "customer_impacting": "customer" in " ".join(f.get("labels", [])).lower(),
            "blocked_by": [],
        })

    return tickets

def get_all_tickets():
    token = get_token()
    raw = fetch_raw_issues(token)
    tickets = parse_tickets(raw)
    print(f"Loaded {len(tickets)} tickets from Jira")
    return tickets

if __name__ == "__main__":
    tickets = get_all_tickets()
    for t in tickets:
        print(f"{t['id']} — {t['title']} [{t['status']}] [{t['priority']}] — {t['assignee'] or 'Unassigned'}")
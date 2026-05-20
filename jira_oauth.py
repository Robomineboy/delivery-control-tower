import os
import requests
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("JIRA_CLIENT_ID")
CLIENT_SECRET = os.getenv("JIRA_CLIENT_SECRET")
DOMAIN = os.getenv("JIRA_DOMAIN")

AUTH_CODE = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global AUTH_CODE
        params = parse_qs(urlparse(self.path).query)
        AUTH_CODE = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Authorization complete. You can close this window.")
        print(f"\nGot auth code: {AUTH_CODE[:20]}...")

    def log_message(self, format, *args):
        pass

def authorize():
    params = {
        "audience": "api.atlassian.com",
        "client_id": CLIENT_ID,
        "scope": "read:jira-work offline_access",
        "redirect_uri": "http://localhost:8080/callback",
        "response_type": "code",
        "prompt": "consent"
    }
    url = "https://auth.atlassian.com/authorize?" + urllib.parse.urlencode(params)
    print(f"Opening browser for authorization...")
    webbrowser.open(url)

    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.handle_request()
    return AUTH_CODE

def exchange_code(code):
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
    print(f"Token exchange status: {response.status_code}")
    print(f"Token exchange response: {response.text[:200]}")
    return response.json().get("access_token")

def get_cloud_id(token):
    response = requests.get(
        "https://api.atlassian.com/oauth/token/accessible-resources",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
    )
    print(f"Resources status: {response.status_code}")
    print(f"Resources response: {response.text}")
    data = response.json()
    if not data:
        print("No accessible resources found.")
        return None
    return data[0]["id"]

def fetch_tickets(token, cloud_id):
    response = requests.post(
        f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/search/jql",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        json={
            "jql": "project=SS ORDER BY created DESC",
            "maxResults": 50,
            "fields": ["summary", "status", "priority", "assignee",
                      "labels", "comment", "duedate", "issuetype"]
        }
    )
    print(f"Tickets status: {response.status_code}")
    print(f"Tickets response: {response.text[:2000]}")
    return response.json()

if __name__ == "__main__":
    code = authorize()
    token = exchange_code(code)
    print(f"Token: {token[:20] if token else 'FAILED'}")
    cloud_id = get_cloud_id(token)
    print(f"Cloud ID: {cloud_id}")
    if cloud_id:
        fetch_tickets(token, cloud_id)
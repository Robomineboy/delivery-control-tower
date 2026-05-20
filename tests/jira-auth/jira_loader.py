import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

JIRA_DOMAIN = os.getenv("JIRA_DOMAIN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def whoami():
    url = f"https://{JIRA_DOMAIN}/rest/api/3/myself"
    r = requests.get(url, headers=headers, auth=auth)
    print("WHOAMI:", r.status_code)
    print(r.text)

def fetch_projects():
    url = f"https://{JIRA_DOMAIN}/rest/api/3/project/search"
    r = requests.get(url, headers=headers, auth=auth)
    print("PROJECTS:", r.status_code)
    print(r.text)

print(repr(JIRA_DOMAIN))
print(repr(JIRA_EMAIL))
print(len(JIRA_API_TOKEN))
whoami()
fetch_projects()
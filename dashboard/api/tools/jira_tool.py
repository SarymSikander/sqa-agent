import json
import os

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

JIRA_URL  = os.getenv("JIRA_URL", "")
EMAIL     = os.getenv("JIRA_EMAIL", "")
API_TOKEN = os.getenv("JIRA_API_TOKEN", "")

_auth         = HTTPBasicAuth(EMAIL, API_TOKEN)
_headers      = {"Accept": "application/json"}
_json_headers = {**_headers, "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

def create_ticket(project_key, summary, issue_type="Task", description=None):
    """Create a new Jira issue. Returns the new issue key (e.g. 'OMS-42')."""
    payload = {
        "fields": {
            "project":   {"key": project_key},
            "summary":   summary,
            "issuetype": {"name": issue_type},
        }
    }
    if description:
        payload["fields"]["description"] = {
            "type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
        }
    r = requests.post(
        f"{JIRA_URL}/rest/api/3/issue",
        headers=_json_headers, auth=_auth, data=json.dumps(payload),
    )
    r.raise_for_status()
    key = r.json()["key"]
    print(f"Created issue: {key}")
    return key


def get_tickets(project_key, max_results=100):
    """Return a list of issues for a project, printed as a summary table."""
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/search/jql",
        headers=_headers, auth=_auth,
        params={
            "jql":        f"project = {project_key} ORDER BY created DESC",
            "maxResults": max_results,
            "fields":     "summary,status,assignee,issuetype",
        },
    )
    r.raise_for_status()
    issues = r.json().get("issues", [])
    print(f"\nFound {len(issues)} issue(s) in {project_key}:\n")
    for issue in issues:
        f        = issue["fields"]
        assignee = (f.get("assignee") or {}).get("displayName", "Unassigned")
        print(f"  [{issue['key']}] {f['summary']}  |  {f['status']['name']}  |  {assignee}")
    return issues


def get_ticket(issue_key):
    """Fetch a single issue and return the full response dict."""
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}",
        headers=_headers, auth=_auth,
    )
    r.raise_for_status()
    return r.json()


def delete_ticket(issue_key):
    """Delete an issue by key."""
    r = requests.delete(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}",
        headers=_headers, auth=_auth,
    )
    r.raise_for_status()
    print(f"Deleted issue: {issue_key}")


def assign_ticket(issue_key, account_id):
    """Assign an issue to a user by their Jira accountId."""
    r = requests.put(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/assignee",
        headers=_json_headers, auth=_auth,
        data=json.dumps({"accountId": account_id}),
    )
    r.raise_for_status()
    print(f"Assigned {issue_key} to accountId {account_id}")


def update_ticket_status(issue_key, transition_name):
    """
    Move an issue to a new status by transition name (e.g. 'In Progress', 'Done').
    Looks up the matching transition ID automatically.
    """
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
        headers=_headers, auth=_auth,
    )
    r.raise_for_status()
    transitions = r.json().get("transitions", [])
    match = next(
        (t for t in transitions if t["name"].lower() == transition_name.lower()), None
    )
    if not match:
        available = [t["name"] for t in transitions]
        raise ValueError(f"Transition '{transition_name}' not found. Available: {available}")
    r2 = requests.post(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
        headers=_json_headers, auth=_auth,
        data=json.dumps({"transition": {"id": match["id"]}}),
    )
    r2.raise_for_status()
    print(f"Moved {issue_key} to '{transition_name}'")


def close_ticket(issue_key, comment=None):
    """
    Transition a ticket to Done and optionally add a closing comment.
    Tries 'Done' first; falls back to 'Closed' if the transition isn't available.
    """
    for name in ("Done", "Closed"):
        try:
            update_ticket_status(issue_key, name)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Could not find a Done/Closed transition for {issue_key}.")

    if comment:
        add_comment(issue_key, comment)
    print(f"Closed {issue_key}.")


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

def add_comment(issue_key, body):
    """Add a plain-text comment to an issue."""
    payload = {
        "body": {
            "type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": body}]}],
        }
    }
    r = requests.post(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/comment",
        headers=_json_headers, auth=_auth, data=json.dumps(payload),
    )
    r.raise_for_status()
    comment_id = r.json()["id"]
    print(f"Added comment {comment_id} to {issue_key}")
    return comment_id


def get_comments(issue_key):
    """Return a list of comment dicts for an issue."""
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/issue/{issue_key}/comment",
        headers=_headers, auth=_auth,
    )
    r.raise_for_status()
    return r.json().get("comments", [])


# ---------------------------------------------------------------------------
# Sprints
# ---------------------------------------------------------------------------

def get_board_id(project_key):
    """Return the first board ID associated with a project."""
    r = requests.get(
        f"{JIRA_URL}/rest/agile/1.0/board",
        headers=_headers, auth=_auth,
        params={"projectKeyOrId": project_key},
    )
    r.raise_for_status()
    boards = r.json().get("values", [])
    if not boards:
        raise ValueError(f"No boards found for project '{project_key}'")
    board_id = boards[0]["id"]
    print(f"Board ID for {project_key}: {board_id}")
    return board_id


def get_sprints(board_id, state=None):
    """
    Return sprints for a board. state can be 'active', 'future', 'closed', or None for all.
    """
    params = {"maxResults": 50}
    if state:
        params["state"] = state
    r = requests.get(
        f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/sprint",
        headers=_headers, auth=_auth, params=params,
    )
    r.raise_for_status()
    sprints = r.json().get("values", [])
    print(f"\nFound {len(sprints)} sprint(s) on board {board_id}:\n")
    for s in sprints:
        print(f"  [{s['id']}] {s['name']}  |  {s['state']}")
    return sprints


def start_sprint(sprint_id):
    """Transition a sprint to 'active' state."""
    r = requests.post(
        f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}",
        headers=_json_headers, auth=_auth,
        data=json.dumps({"state": "active"}),
    )
    r.raise_for_status()
    print(f"Started sprint {sprint_id}")


def end_sprint(sprint_id):
    """Transition an active sprint to 'closed' state."""
    r = requests.post(
        f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}",
        headers=_json_headers, auth=_auth,
        data=json.dumps({"state": "closed"}),
    )
    r.raise_for_status()
    print(f"Ended sprint {sprint_id}")


def add_to_sprint(sprint_id, issue_keys):
    """Add one or more issues to a sprint. issue_keys can be a str or list."""
    if isinstance(issue_keys, str):
        issue_keys = [issue_keys]
    r = requests.post(
        f"{JIRA_URL}/rest/agile/1.0/sprint/{sprint_id}/issue",
        headers=_json_headers, auth=_auth,
        data=json.dumps({"issues": issue_keys}),
    )
    r.raise_for_status()
    print(f"Added {issue_keys} to sprint {sprint_id}")


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

def get_project_members(project_key):
    """Return users who are assignable on a project."""
    r = requests.get(
        f"{JIRA_URL}/rest/api/3/user/assignable/search",
        headers=_headers, auth=_auth,
        params={"project": project_key, "maxResults": 50},
    )
    r.raise_for_status()
    members = r.json()
    print(f"\nAssignable members for {project_key}:\n")
    for m in members:
        print(f"  {m['displayName']}  |  accountId: {m['accountId']}  |  {m.get('emailAddress', '')}")
    return members


# ---------------------------------------------------------------------------
# Human-readable summary
# ---------------------------------------------------------------------------

def _extract_text(adf_node):
    """Recursively pull plain text out of an Atlassian Document Format node."""
    if not adf_node:
        return ""
    if adf_node.get("type") == "text":
        return adf_node.get("text", "")
    parts = [_extract_text(child) for child in adf_node.get("content", [])]
    joined = " ".join(p for p in parts if p)
    # Add a newline after block-level nodes so paragraphs don't run together
    if adf_node.get("type") in ("paragraph", "heading", "bulletList", "listItem"):
        joined = joined.strip() + "\n"
    return joined


def summarize_ticket(issue_key):
    """
    Return a clean human-readable summary string for a ticket including
    title, status, assignee, description, and all comments.
    Also prints the summary to stdout.
    """
    issue    = get_ticket(issue_key)
    comments = get_comments(issue_key)
    f        = issue["fields"]

    title       = f.get("summary", "—")
    status      = f.get("status", {}).get("name", "—")
    assignee    = (f.get("assignee") or {}).get("displayName", "Unassigned")
    issue_type  = f.get("issuetype", {}).get("name", "—")
    priority    = (f.get("priority") or {}).get("name", "—")
    description = _extract_text(f.get("description") or {}).strip() or "No description."

    lines = [
        f"{'='*60}",
        f"  {issue_key}  —  {title}",
        f"{'='*60}",
        f"  Type     : {issue_type}",
        f"  Status   : {status}",
        f"  Assignee : {assignee}",
        f"  Priority : {priority}",
        f"",
        f"  Description",
        f"  -----------",
    ]
    for desc_line in description.splitlines():
        lines.append(f"  {desc_line}")

    if comments:
        lines += ["", f"  Comments ({len(comments)})", f"  ---------"]
        for c in comments:
            author = c.get("author", {}).get("displayName", "Unknown")
            created = c.get("created", "")[:10]
            body = _extract_text(c.get("body") or {}).strip()
            lines.append(f"  [{created}] {author}: {body}")
    else:
        lines += ["", "  Comments: none"]

    lines.append("=" * 60)
    summary = "\n".join(lines)
    print(summary)
    return summary

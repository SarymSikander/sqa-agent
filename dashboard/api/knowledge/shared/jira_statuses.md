# Shared — Jira Status Transitions

## Jira Projects
- **OMS** — Zambeel Order Management
- **ZSP** — Zambeel Seller Portal
- URL: https://zambeel.atlassian.net

## Standard Status Transition Names
Use these exact string values when calling `update_ticket_status(issue_key, transition_name)`.

| From Status | Transition Name | To Status |
|-------------|----------------|-----------|
| To Do | "Start Progress" | In Progress |
| To Do | "Done" | Done |
| In Progress | "Stop Progress" | To Do |
| In Progress | "Done" | Done |
| In Progress | "Reopen" | To Do |
| Done | "Reopen" | To Do |
| Done | "Reopen Issue" | In Progress |

## Common Transition Aliases (try these if standard names fail)
| Alias | Likely Resolves To |
|-------|-------------------|
| "In Progress" | Start Progress |
| "Todo" | Stop Progress / Reopen |
| "Close" | Done |
| "Close Issue" | Done |
| "Resolve" | Done |
| "Resolve Issue" | Done |

## `jira_tool.py` Key Functions

```python
from tools.jira_tool import (
    create_ticket,
    get_tickets,
    get_ticket,
    delete_ticket,
    assign_ticket,
    update_ticket_status,   # transition_name = exact string above
    close_ticket,           # transitions to Done + adds comment
    add_comment,
    get_comments,
    get_board_id,
    get_sprints,            # state: "active" | "future" | "closed" | None
    start_sprint,
    end_sprint,
    add_to_sprint,
    get_project_members,    # returns list of {accountId, displayName, emailAddress}
    summarize_ticket,       # prints human-readable summary
)
```

## Issue Types Available
- Bug
- Story
- Task
- Epic
- Subtask

## Project Keys
| Project | Key |
|---------|-----|
| Zambeel Order Management | OMS |
| Zambeel Seller Portal | ZSP |

## Ticket Summary Format (from `summarize_ticket`)
```
Ticket: OMS-42
Status: In Progress
Assignee: John Doe
Summary: [title text]
Description: [description text]
Comments:
  - [author] (date): [comment body]
```

## Create Ticket Example
```python
key = create_ticket(
    project_key="OMS",
    summary="Login button not responding on Safari",
    issue_type="Bug",
    description="Reproducible steps: 1. Open Safari 2. Navigate to /login 3. Click Sign In"
)
# Returns: "OMS-123"
```

## Close Ticket Example
```python
close_ticket("OMS-42", comment="All tests passing on staging as of 2026-04-30")
```

## Assign Ticket Example
```python
members = get_project_members("OMS")
# members = [{"accountId": "abc123", "displayName": "Sarim"}]
assign_ticket("OMS-42", account_id="abc123")
```

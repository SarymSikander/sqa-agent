# SQA Agent — Zambeel

## Project overview
AI-powered SQA agent for the Zambeel platform. Automates Jira ticket management, browser login-validation testing, and Git branch operations across three environments and three portal types.

## Repos
- Frontend (Vue/Vite): /Users/sarimsikandar/Documents/GitHub/zambeel-fe — runs on http://localhost:5173
- Backend (Node/Express): /Users/sarimsikandar/Documents/GitHub/zambeel-api — runs on http://localhost:3000

## Environments
| Name       | URL                              |
|------------|----------------------------------|
| local      | http://localhost:5173            |
| staging    | https://staging.myzambeel.com    |
| production | https://portal.myzambeel.com     |

## Portal types
Three portal types: `seller`, `admin`, `agency`. Each logs in via email/password stored in `.env`.

## Auth credentials
All portals authenticate with email/password from `.env`. No session JSON files are used.

| Variable | Portal |
|----------|--------|
| `ADMIN_STAGING_EMAIL` / `ADMIN_STAGING_PASSWORD` | Admin, staging |
| `SELLER_STAGING_EMAIL` / `SELLER_STAGING_PASSWORD` | Seller, staging |
| `AGENCY_STAGING_EMAIL` / `AGENCY_STAGING_PASSWORD` | Agency, staging |
| `ADMIN_PRODUCTION_EMAIL` / `ADMIN_PRODUCTION_PASSWORD` | Admin, production |
| `SELLER_PRODUCTION_EMAIL` / `SELLER_PRODUCTION_PASSWORD` | Seller, production |
| `AGENCY_PRODUCTION_EMAIL` / `AGENCY_PRODUCTION_PASSWORD` | Agency, production |

## Success URLs per portal
These are the post-login landing paths the test checks for:

| Portal | Expected path                    |
|--------|----------------------------------|
| seller | `/get-started`                   |
| admin  | `/orders-management/dashboard`   |
| agency | `/get-started`                   |

If a portal starts redirecting to a different path after login, update `success_slugs` in `tools/playwright_tool.py:95`.

## Tools

### tools/playwright_tool.py
Browser login-validation tests using Playwright with email/password login from `.env`.

Key functions:
- `run_tests(portal, env)` — runs a headless login test; returns `("PASS"|"FAIL", message)`
- `login_to_portal(page, portal, env)` — fills login form with credentials from `.env`
- `start_local_server()` / `stop_local_server()` — spins the frontend dev server up/down for local tests
- Convenience wrappers: `run_tests_seller_local()`, `run_tests_admin_staging()`, etc.

Screenshots are saved to `screenshots/` as `portal_env_TIMESTAMP.png`.

### tools/explore_oms.py
Live UI exploration script — logs in as admin and visits every OMS page on staging.
Extracts all interactive elements (buttons, inputs, selects, tabs, modals, dropdowns).
Output saved to `tools/exploration_output/` as JSON + screenshots.

```
python tools/explore_oms.py
```

### tools/github_tool.py
Git branch operations on the frontend and backend repos.

Key functions:
- `get_current_branch(repo_path)` — returns active branch name
- `list_branches(repo_path)` — lists all local branches
- `switch_branch(repo_path, branch_name)` — checks out a branch
- `pull_latest(repo_path)` — pulls from the tracking remote

Repo paths are read from `GITHUB_FRONTEND_REPO` and `GITHUB_BACKEND_REPO` in `.env`.

### tools/jira_tool.py
Jira integration. (See Jira section below.)

Key functions:
- `create_ticket(project_key, summary, issue_type, description)` — creates an issue, returns key
- `get_tickets(project_key, max_results)` — lists issues for a project
- `get_ticket(issue_key)` — fetches a single issue as a raw dict
- `delete_ticket(issue_key)` — deletes an issue
- `assign_ticket(issue_key, account_id)` — assigns to a user by accountId
- `update_ticket_status(issue_key, transition_name)` — moves to any status by name (e.g. `"In Progress"`)
- `close_ticket(issue_key, comment)` — transitions to Done and adds an optional closing comment
- `add_comment(issue_key, body)` — adds a plain-text comment
- `get_comments(issue_key)` — returns all comments as a list of dicts
- `get_board_id(project_key)` — returns the first board ID for a project
- `get_sprints(board_id, state)` — lists sprints; state can be `"active"`, `"future"`, `"closed"`, or `None`
- `start_sprint(sprint_id)` / `end_sprint(sprint_id)` — transitions sprint state
- `add_to_sprint(sprint_id, issue_keys)` — adds issues to a sprint
- `get_project_members(project_key)` — lists assignable users with accountIds
- `summarize_ticket(issue_key)` — prints and returns a human-readable summary with title, status, assignee, description, and comments

### tools/db_tool.py
MySQL database access for local and staging environments. Credentials are loaded from `.env` per environment. **Write operations are blocked on production** — `run_write()` raises a `PermissionError` if `env="production"` is passed.

Key functions:
- `get_connection(env)` — returns an open `mysql.connector` connection for `local`, `staging`, or `production`
- `run_query(env, sql, params=None)` — executes a SELECT and returns results as a list of dicts
- `run_write(env, sql, params=None)` — executes INSERT/UPDATE/DELETE; blocked on production; returns affected row count
- `table_exists(env, table_name)` — returns `True`/`False` whether the table exists
- `get_tables(env)` — prints and returns a list of all table names in the database
- `get_row_count(env, table_name)` — returns the row count for a table
- `verify_record_exists(env, table_name, conditions)` — accepts a `{column: value}` dict and returns `True` if a matching row exists

DB credentials in `.env`:
- Local: fully configured (`zambeel_user` / `zambeel_db`)
- Staging / Production: host, user, password, and database name left blank — fill in when available

### tools/report_tool.py
Generates a full markdown health report for a given environment by combining Playwright test results and DB metrics.

Key functions:
- `generate_health_report(env)` — runs all three portal tests, queries DB for row counts and missing tables, writes a markdown report to `reports/health_<env>_<timestamp>.md`, and returns the file path

Reports include: timestamp, environment, per-portal pass/fail table, overall status, orders/users row counts, and any missing expected tables.

### tools/log_tool.py
Parses backend server log files for ERROR and WARNING lines.

Key functions:
- `parse_backend_logs(log_file_path, last_n_lines=200)` — reads the last N lines of a log file, extracts ERROR/WARNING entries, groups them by level and message fingerprint, and returns a structured summary dict with counts and sample lines

Return structure: `{ file, lines_scanned, total_issues, by_level: {ERROR/WARNING: {count, samples}}, by_message: {fingerprint: {level, count, sample}} }`

## Jira
- URL: https://zambeel.atlassian.net
- Projects: OMS (Zambeel Order Management), ZSP (Zambeel Seller Portal)

## Running tests

### Single test
```python
from tools.playwright_tool import run_tests
status, msg = run_tests("seller", "local")
```

### All 6 local + staging tests
```python
from tools.playwright_tool import run_tests

for portal in ["seller", "admin", "agency"]:
    for env in ["local", "staging"]:
        status, msg = run_tests(portal, env)
        print(f"[{status}] {portal}/{env} — {msg}")
```

Local tests automatically start and stop the frontend dev server. Staging tests hit the live URL directly.

## Example plain-English commands

You can give me any of these instructions directly:

**Running tests**
- "Run local tests for all three portals and show me a results table."
- "Run all 6 local and staging tests together."
- "Test the admin portal on staging."
- "Run a full test sweep across all environments."

**Auth sessions**
- "The seller staging session is failing — refresh it." *(I'll tell you the command to run since auth_setup requires manual interaction.)*
- "Which auth sessions do we have saved?"

**Branch management**
- "What branch is the frontend on?"
- "Switch the frontend to branch feature/new-checkout."
- "Pull the latest on both repos."
- "List all branches on the backend."

**Jira**
- "Show me open tickets in ZSP."
- "Create a Jira bug for the admin login redirect issue."
- "What's the status of OMS-42?"

**Database**
- "List all tables in the local database."
- "How many rows are in the orders table on local?"
- "Check if a user with email test@example.com exists in the local DB."
- "Does the `variants` table exist on staging?"
- "Run this query on local: SELECT * FROM orders WHERE status = 'pending' LIMIT 10."
- "Insert a test record into the users table on staging."
- "Verify that order OMS-123 exists in the orders table on local."

**Health reports**
- "Generate a full health report for staging."
- "Generate a health report for local and save it."
- "Run all tests and give me a summary report."

**Closing tickets**
- "Run all tests and close the Jira ticket OMS-42 if they pass."
- "Close OMS-55 with the comment 'All tests passing on staging'."
- "Mark ZSP-10 as done."

**Log analysis**
- "Check backend logs for errors and create tickets for anything critical."
- "Parse the last 500 lines of the backend log and show me what's failing."
- "Are there any warnings in the backend logs?"

**Debugging failures**
- "The agency staging test is failing — investigate."
- "Update the success URL for seller portal to /dashboard."

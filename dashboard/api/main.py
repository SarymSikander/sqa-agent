import asyncio
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Zambeel SQA Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://sqa-agent.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_HERE = Path(__file__).resolve().parent
SCREENSHOTS_DIR = _HERE / "screenshots"
REPORTS_DIR = _HERE / "reports"
SCREENSHOTS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")

REPO_PATHS = {
    "frontend": os.path.expanduser(os.getenv("GITHUB_FRONTEND_REPO", "~/Documents/GitHub/zambeel-fe")),
    "backend":  os.path.expanduser(os.getenv("GITHUB_BACKEND_REPO",  "~/Documents/GitHub/zambeel-api")),
}

REPO_API_NAMES = {
    "frontend": os.getenv("GITHUB_FRONTEND_REPO_API", ""),
    "backend":  os.getenv("GITHUB_BACKEND_REPO_API", ""),
}

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def _get_branches_via_api(repo_api_name: str):
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    r = requests.get(
        f"https://api.github.com/repos/{repo_api_name}/branches",
        headers=headers, timeout=10,
    )
    r.raise_for_status()
    branches = [b["name"] for b in r.json()]

    r2 = requests.get(
        f"https://api.github.com/repos/{repo_api_name}",
        headers=headers, timeout=10,
    )
    r2.raise_for_status()
    current = r2.json().get("default_branch", branches[0] if branches else "main")

    return branches, current

# ── Tool imports (done once at startup) ───────────────────────────────────────
import tools.jira_tool       as _jira
import tools.playwright_tool as _playwright
import tools.db_tool         as _db
import tools.report_tool     as _report
import tools.slack_tool      as _slack
import tools.github_tool     as _github
import tools.pr_review_tool  as _pr

# ── Pydantic models ───────────────────────────────────────────────────────────

class RunTestsBody(BaseModel):
    env: str
    portal: Optional[str] = None

class GenerateReportBody(BaseModel):
    env: str

class CreateTicketBody(BaseModel):
    project_key: str
    summary: str
    issue_type: str = "Task"
    description: Optional[str] = None

class CloseTicketBody(BaseModel):
    comment: Optional[str] = None

class AddCommentBody(BaseModel):
    comment: str

class SwitchBranchBody(BaseModel):
    repo: str
    branch: str

class DBQueryBody(BaseModel):
    env: str
    sql: str

class PRReviewBody(BaseModel):
    repo: str
    pr_number: int

# ── /health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}

# ── /tests ────────────────────────────────────────────────────────────────────

@app.post("/tests/run")
async def run_tests(body: RunTestsBody):
    portals = [body.portal] if body.portal else ["seller", "admin", "agency"]
    results = []
    for portal in portals:
        status, message = await asyncio.to_thread(_playwright.run_tests, portal, body.env)
        results.append({
            "portal": portal,
            "env": body.env,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        })
    return {"results": results}

@app.get("/tests/screenshots")
def list_screenshots():
    files = sorted(SCREENSHOTS_DIR.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
    return {
        "screenshots": [
            {
                "filename": f.name,
                "url": f"/screenshots/{f.name}",
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
            for f in files
        ]
    }

# ── /reports ──────────────────────────────────────────────────────────────────

@app.post("/reports/generate")
async def generate_report(body: GenerateReportBody):
    report_path = await asyncio.to_thread(_report.generate_health_report, body.env)
    content = Path(report_path).read_text()
    return {"path": report_path, "content": content, "filename": Path(report_path).name}

@app.get("/reports/list")
def list_reports():
    files = sorted(REPORTS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
    return {
        "reports": [
            {
                "filename": f.name,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
            for f in files
        ]
    }

@app.get("/reports/{filename}")
def get_report(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = REPORTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return {"filename": filename, "content": path.read_text()}

# ── /jira ─────────────────────────────────────────────────────────────────────

@app.post("/jira/tickets")
async def create_ticket(body: CreateTicketBody):
    key = await asyncio.to_thread(
        _jira.create_ticket,
        body.project_key, body.summary, body.issue_type, body.description,
    )
    return {"key": key, "url": f"https://zambeel.atlassian.net/browse/{key}"}

@app.get("/jira/tickets/{project_key}")
async def get_tickets(project_key: str):
    try:
        raw = await asyncio.to_thread(_jira.get_tickets, project_key, 50)
    except Exception as e:
        return {"tickets": [], "error": str(e)}
    return {
        "tickets": [
            {
                "key": t.get("key"),
                "summary": t["fields"].get("summary"),
                "status": t["fields"].get("status", {}).get("name"),
                "assignee": (t["fields"].get("assignee") or {}).get("displayName"),
                "issue_type": t["fields"].get("issuetype", {}).get("name"),
                "created": t["fields"].get("created"),
                "url": f"https://zambeel.atlassian.net/browse/{t.get('key')}",
            }
            for t in raw
        ]
    }

@app.post("/jira/tickets/{issue_key}/close")
async def close_ticket(issue_key: str, body: CloseTicketBody):
    await asyncio.to_thread(_jira.close_ticket, issue_key, body.comment)
    return {"success": True, "key": issue_key}

@app.post("/jira/tickets/{issue_key}/comment")
async def add_comment(issue_key: str, body: AddCommentBody):
    await asyncio.to_thread(_jira.add_comment, issue_key, body.comment)
    return {"success": True, "key": issue_key}

@app.get("/jira/sprints/{project_key}")
async def get_sprints(project_key: str):
    board_id = await asyncio.to_thread(_jira.get_board_id, project_key)
    if not board_id:
        return {"sprints": []}
    sprints = await asyncio.to_thread(_jira.get_sprints, board_id, "active")
    return {"sprints": sprints or []}

# ── /github ───────────────────────────────────────────────────────────────────

@app.get("/github/branches/{repo}")
async def get_branches(repo: str):
    repo_key = repo.lower()
    repo_path = REPO_PATHS.get(repo_key)
    if not repo_path:
        raise HTTPException(status_code=400, detail="repo must be 'frontend' or 'backend'")

    if Path(repo_path).exists():
        try:
            branches = await asyncio.to_thread(_github.list_branches, repo_path)
            current  = await asyncio.to_thread(_github.get_current_branch, repo_path)
            return {"repo": repo, "branches": branches, "current": current, "source": "local"}
        except Exception:
            pass

    repo_api_name = REPO_API_NAMES.get(repo_key, "")
    if not repo_api_name:
        raise HTTPException(
            status_code=400,
            detail=f"Local repo not found and GITHUB_{repo.upper()}_REPO_API is not set",
        )
    try:
        branches, current = await asyncio.to_thread(_get_branches_via_api, repo_api_name)
        return {"repo": repo, "branches": branches, "current": current, "source": "github_api"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/github/switch")
async def switch_branch(body: SwitchBranchBody):
    repo_path = REPO_PATHS.get(body.repo.lower())
    if not repo_path:
        raise HTTPException(status_code=400, detail="repo must be 'frontend' or 'backend'")
    try:
        await asyncio.to_thread(_github.switch_branch, repo_path, body.branch)
        return {"success": True, "repo": body.repo, "branch": body.branch}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ── /db ───────────────────────────────────────────────────────────────────────

@app.get("/db/tables/{env}")
async def get_db_tables(env: str):
    try:
        tables = await asyncio.to_thread(_db.get_tables, env)
        return {"env": env, "tables": tables}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/db/query")
async def run_db_query(body: DBQueryBody):
    sql = body.sql.strip()
    if not sql.upper().startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed from the dashboard")
    try:
        results = await asyncio.to_thread(_db.run_query, body.env, sql)
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ── /pr ───────────────────────────────────────────────────────────────────────

@app.get("/pr/open/{repo}")
async def get_open_prs(repo: str):
    try:
        prs = await asyncio.to_thread(_pr.get_open_prs, repo)
        return {"repo": repo, "prs": prs}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/pr/review")
async def review_pr_endpoint(body: PRReviewBody):
    review_text = await asyncio.to_thread(_pr.review_pr, body.repo, body.pr_number)
    try:
        await asyncio.to_thread(
            _slack.send_message,
            f"🤖 PR Review — {body.repo} #{body.pr_number}\n\n"
            + review_text[:800] + ("..." if len(review_text) > 800 else ""),
        )
    except Exception:
        pass
    return {"repo": body.repo, "pr_number": body.pr_number, "review": review_text}

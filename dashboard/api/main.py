import asyncio
import json
import os
import re
import secrets
import shutil
import time
import requests
import bcrypt
import jwt as _jwt
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI
from playwright.sync_api import sync_playwright

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


app = FastAPI(title="Zambeel SQA Dashboard API", version="1.0.0")

_db_cache = {'data': '', 'ts': 0}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://sqa-agent.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth config ───────────────────────────────────────────────────────────────
# SESSION_SECRET: JWT signing key.  Falls back to a random value so local dev
# works without config — set it explicitly on HF Space for persistence.
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_hex(32)
SESSION_HOURS  = 8

# SQA_USERS: JSON array of {"email": "...", "password": "<bcrypt hash>"}
# Build a dict keyed by email for O(1) lookup.
_users_raw = os.getenv("SQA_USERS", "[]")
try:
    _USERS: dict[str, dict] = {u["email"]: u for u in json.loads(_users_raw)}
except Exception:
    _USERS = {}

# Paths that bypass the auth middleware
_AUTH_EXEMPT_PREFIXES = ("/api-tests/",)
_AUTH_EXEMPT = {
    ("POST", "/auth/login"),
    ("GET",  "/health"),
}


@app.middleware("http")
async def _auth_middleware(request: Request, call_next):
    # Always pass CORS pre-flight through
    if request.method == "OPTIONS":
        return await call_next(request)

    if (request.method, request.url.path) in _AUTH_EXEMPT:
        return await call_next(request)

    # All /api-tests/* routes are exempt — called by both GitHub Actions
    # (no session) and the frontend before the token is attached.
    if any(request.url.path.startswith(p) for p in _AUTH_EXEMPT_PREFIXES):
        return await call_next(request)

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        # Fallback: token as query param for SSE endpoints that can't set headers
        query_token = request.query_params.get("token", "")
        if query_token:
            auth = f"Bearer {query_token}"

    if not auth.startswith("Bearer "):
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    token = auth.removeprefix("Bearer ").strip()
    try:
        _jwt.decode(token, SESSION_SECRET, algorithms=["HS256"])
    except _jwt.ExpiredSignatureError:
        return JSONResponse({"detail": "Session expired — please sign in again"}, status_code=401)
    except _jwt.InvalidTokenError:
        return JSONResponse({"detail": "Invalid token"}, status_code=401)

    return await call_next(request)

_HERE = Path(__file__).resolve().parent
SCREENSHOTS_DIR = _HERE / "screenshots"
REPORTS_DIR = _HERE / "reports"
SCREENSHOTS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# HF Docker spaces persist only /data — use it when available, else local reports/
_DATA_DIR = Path("/data")
try:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    _DATA_DIR = REPORTS_DIR

GITHUB_REPO = os.getenv("GITHUB_REPO", "SarymSikander/api-test-suite")
GITHUB_WORKFLOW_FILE = os.getenv("GITHUB_WORKFLOW_FILE", "api-tests.yml")

# Canonical knowledge directory — co-located with main.py so it works on HuggingFace (/app/)
KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
print(f"[startup] knowledge dir exists: {KNOWLEDGE_DIR.exists()}, "
      f"files: {[str(p.relative_to(KNOWLEDGE_DIR)) for p in sorted(KNOWLEDGE_DIR.rglob('*.md'))[:5]]}")


# Load knowledge base — concatenate all knowledge/*.md files, fall back to app_context.md
def _load_knowledge_base() -> str:
    """Load all knowledge base markdown files and concatenate them into one context string."""
    # Primary: co-located knowledge/ (works on HuggingFace and locally)
    # Fallback: repo-root knowledge/ for legacy local layouts
    _candidates = [
        KNOWLEDGE_DIR,
        Path(__file__).resolve().parent.parent.parent / "knowledge",
    ]
    _knowledge_dir = next((p for p in _candidates if p.is_dir()), None)

    chunks: list[str] = []

    if _knowledge_dir:
        _order = [
            "shared/auth.md",
            "shared/test_rules.md",
            "shared/api_endpoints.md",
            "shared/jira_statuses.md",
            "oms/overview.md",
            "oms/pages.md",
            "oms/selectors.md",
            "oms/flows.md",
            "oms/test_patterns.md",
            "seller/overview.md",
            "seller/pages.md",
            "seller/selectors.md",
            "seller/flows.md",
            "seller/test_patterns.md",
            "agency/overview.md",
            "agency/pages.md",
            "agency/selectors.md",
            "agency/flows.md",
            "agency/test_patterns.md",
        ]
        loaded, total_bytes = 0, 0
        for rel in _order:
            fpath = _knowledge_dir / rel
            if fpath.exists():
                try:
                    text = fpath.read_text()
                    chunks.append(f"\n\n{'='*60}\n# KNOWLEDGE: {rel}\n{'='*60}\n{text}")
                    loaded += 1
                    total_bytes += len(text)
                except Exception as _e:
                    print(f"[startup] Failed to load knowledge/{rel}: {_e}")
        # Pick up any extra files not in the ordered list
        for fpath in sorted(_knowledge_dir.rglob("*.md")):
            rel_str = str(fpath.relative_to(_knowledge_dir))
            if rel_str not in _order and fpath.exists():
                try:
                    text = fpath.read_text()
                    chunks.append(f"\n\n{'='*60}\n# KNOWLEDGE: {rel_str}\n{'='*60}\n{text}")
                    loaded += 1
                    total_bytes += len(text)
                except Exception:
                    pass
        print(f"[startup] Knowledge base loaded: {loaded} files, {total_bytes} bytes from {_knowledge_dir}")
    else:
        print("[startup] knowledge/ directory not found — falling back to app_context.md")

    # Always append app_context.md as a final fallback / supplement
    _app_ctx_candidates = [
        Path(__file__).resolve().parent / "app_context.md",
        Path(__file__).resolve().parent.parent.parent / "app_context.md",
    ]
    for _p in _app_ctx_candidates:
        if _p.exists():
            try:
                text = _p.read_text()
                chunks.append(f"\n\n{'='*60}\n# LEGACY app_context.md\n{'='*60}\n{text}")
                print(f"[startup] app_context.md appended: {len(text)} chars from {_p}")
            except Exception as _e:
                print(f"[startup] Failed to load app_context.md: {_e}")
            break

    return "".join(chunks)


APP_CONTEXT = _load_knowledge_base()
print(f"[startup] APP_CONTEXT total: {len(APP_CONTEXT)} chars")


def _load_knowledge_file(rel_path: str) -> str:
    """Read a single knowledge file by relative path (e.g. 'oms/selectors.md')."""
    for candidate in [
        KNOWLEDGE_DIR,
        Path(__file__).resolve().parent.parent.parent / "knowledge",
    ]:
        fpath = candidate / rel_path
        if fpath.exists():
            return fpath.read_text()
    print(f"[knowledge] File not found: {rel_path}")
    return ""


def _portal_knowledge(portal: str) -> str:
    """Return the full selectors.md + test_rules.md for the given portal."""
    selectors_file = {
        "admin":  "oms/selectors.md",
        "seller": "seller/selectors.md",
        "agency": "agency/selectors.md",
    }.get(portal.lower(), "oms/selectors.md")

    selectors  = _load_knowledge_file(selectors_file)
    test_rules = _load_knowledge_file("shared/test_rules.md")

    parts = []
    if selectors:
        parts.append(f"# {selectors_file}\n{selectors}")
    if test_rules:
        parts.append(f"# shared/test_rules.md\n{test_rules}")

    kb = "\n\n---\n\n".join(parts)
    print(f"[knowledge] portal={portal} → {selectors_file} + test_rules: {len(kb):,} chars")
    return kb


def get_portal_knowledge(portal):
    portal_dir = {'admin': 'oms', 'seller': 'seller', 'agency': 'agency'}.get(portal, 'oms')
    files_to_load = [
        KNOWLEDGE_DIR / portal_dir / 'selectors.md',
        KNOWLEDGE_DIR / portal_dir / 'pages.md',
        KNOWLEDGE_DIR / 'shared' / 'test_rules.md',
    ]
    content = ''
    for f in files_to_load:
        if f.exists():
            text = f.read_text()
            # selectors.md is loaded in full — it is the primary reference and must not be truncated
            cap = len(text) if f.name == 'selectors.md' else 5000
            content += text[:cap]
    result = content[:30000]  # raised from 12000 — selectors.md alone is ~21k chars
    print(f"[knowledge] get_portal_knowledge portal={portal} → {portal_dir}/ → {len(result):,} chars (MUST be >5000 or knowledge is missing)")
    if len(result) < 5000:
        print(f"[knowledge] WARNING: knowledge context is suspiciously short ({len(result)} chars) — check knowledge files exist")
    return result


_MANDATORY_SELECTOR_INSTRUCTION = """
ABSOLUTE RULES — VIOLATION MEANS THE TEST SUITE IS WORTHLESS:

1. NEVER use placeholder text as evidence. Evidence must be something that appears AFTER an action — e.g. a result row, a success message, a changed heading. An input placeholder is NOT evidence.
2. NEVER invent text like 'Showing X to Y' or '100 movements displayed' — only use text that actually exists on the page. Always verify against the KNOWLEDGE BASE before using any text as evidence.
3. Pagination evidence is PAGE-SPECIFIC: Inventory Movements uses text=/Page \\d+ of \\d+/ (rendered in an <h2>). Ticketing uses text=/Showing \\d+ to \\d+ of \\d+/ (rendered in a <p>). NEVER mix these up.
4. For ticketing search evidence: ONLY use text='TKT-XXXXX' where XXXXX is the actual ticket number you searched — never a column header, never a compound selector.
5. NEVER use button[type='submit'] — the ticketing search button is button:has-text('Search').
6. NEVER use select >> text='100' or any >> chaining on a select — always use CLICK_OPTION: 100.
7. For ticketing search by ticket number, ALWAYS include CLICK_OPTION: Ticket Number as the VERY FIRST step before any FILL. Without this, the input targets the wrong field.
8. Input placeholder for ticket number search is EXACTLY: 'Search by ticket number...' — three dots, nothing else. Any other spelling is wrong.
9. ALWAYS REFER TO THE KNOWLEDGE BASE BEFORE GENERATING ANY SELECTOR OR EVIDENCE. If it is not in the knowledge base and not visible in the screenshot, do not use it.
10. RULE — Actions button is DISABLED by default on ALL table pages. It only enables after at least one row checkbox is selected. MANDATORY sequence whenever a test needs to use Actions:
    Step N:   SELECT_ROW: nth=0
    Step N+1: WAIT: 800
    Step N+2: CLICK: button:has-text('Actions')
    Step N+3: CLICK_OPTION: [action name e.g. Revert]
    NEVER generate a CLICK on Actions without SELECT_ROW immediately before it.

MANDATORY: You MUST use ONLY selectors from the KNOWLEDGE BASE provided below.
Do NOT invent selectors.
Do NOT use data-testid unless you see it in the knowledge base.
Do NOT use placeholder text unless you see the EXACT text in the knowledge base.
If you cannot find the exact selector in the knowledge base, use ASSERT_EXISTS: text="Page Title" as evidence instead.
""".strip()

ZAMBEEL_OMS_ROUTES = """
MANDATORY ROUTE REFERENCE — USE EXACTLY THESE ROUTES, NEVER INVENT ROUTES:

- Inventory Movements:    /orders-management/inventory-movements
- Ticketing:              /orders-management/ticketing
- Orders:                 /orders-management/orders
- Commission Models:      /orders-management/commission-models
- Dispatch Batches:       /orders-management/dispatch-batches
- Agents:                 /orders-management/agents
- Agency Registrations:   /orders-management/agency-registrations
- Gold Subscriptions:     /orders-management/gold-subscriptions
- Ticker Config:          /orders-management/ticker-config
- Stores Settings:        /orders-management/stores-settings
- Purchase Orders:        /orders-management/purchase-orders
- Return Orders:          /orders-management/return-orders
"""

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
import tools.jest_tool       as _jest

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

class GenerateTicketBody(BaseModel):
    description: str
    project_key: str = "OMS"
    issue_type: str = "Bug"

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

class RunQABody(BaseModel):
    env: str
    frontend_branch: str
    backend_branch: str
    portal: Optional[str] = None

# ── /debug/files ──────────────────────────────────────────────────────────────

@app.get("/debug/files")
def debug_files():
    import os as _os
    result = {"cwd": _os.getcwd()}
    for path in ["/app", "/app/auth", "/app/tools", "/app/tools/../auth"]:
        resolved = str(Path(path).resolve()) if path != "/app/tools/../auth" else str(Path("/app/tools/../auth").resolve())
        exists = _os.path.exists(resolved)
        result[path] = {
            "resolved": resolved,
            "exists": exists,
            "listing": _os.listdir(resolved) if exists and _os.path.isdir(resolved) else None,
        }
    return result

# ── ADF → plain text helper ───────────────────────────────────────────────────

def _adf_to_text(node) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(_adf_to_text(c) for c in node)
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        parts = [_adf_to_text(c) for c in node.get("content", [])]
        sep = "\n" if node.get("type") in (
            "paragraph", "heading", "bulletList", "orderedList",
            "listItem", "blockquote", "doc",
        ) else ""
        return sep.join(p for p in parts if p)
    return str(node)

# ── /debug/auth ───────────────────────────────────────────────────────────────

@app.get("/debug/auth")
def debug_auth():
    """Show which portal credentials are configured via env vars."""
    creds = {}
    for portal in ("seller", "admin", "agency"):
        for env in ("staging", "production"):
            suffix = "STAGING" if env == "staging" else "PRODUCTION"
            email = os.getenv(f"{portal.upper()}_{suffix}_EMAIL", "").strip()
            creds[f"{portal}_{env}"] = "configured" if email else "missing"
    return {"credentials": creds}

# ── /health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    import os as _os
    app_contents = _os.listdir("/app") if _os.path.exists("/app") else None
    return {"status": "ok", "app_dir": app_contents}


# ── User auth ─────────────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
async def login(body: LoginBody):
    user = _USERS.get(body.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    try:
        match = await asyncio.to_thread(
            bcrypt.checkpw, body.password.encode(), user["password"].encode()
        )
    except Exception:
        match = False
    if not match:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    exp = datetime.now(tz=timezone.utc) + timedelta(hours=SESSION_HOURS)
    token = _jwt.encode(
        {"email": body.email, "exp": exp, "iat": datetime.now(tz=timezone.utc)},
        SESSION_SECRET,
        algorithm="HS256",
    )
    return {"token": token, "user": {"email": body.email}}


@app.post("/auth/logout")
async def logout():
    return {"success": True}


@app.get("/auth/me")
async def me(request: Request):
    # Middleware already validated the token; just decode for the payload.
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    try:
        payload = _jwt.decode(token, SESSION_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"email": payload.get("email")}

# ── /auth ─────────────────────────────────────────────────────────────────────

_ENV_ORIGINS = {
    "local":      "http://localhost:5173",
    "staging":    "https://staging.myzambeel.com",
    "production": "https://portal.myzambeel.com",
}

@app.get("/auth/status")
def auth_status():
    """Report which portals have email/password credentials configured in env."""
    sessions = []
    for portal in ("seller", "admin", "agency"):
        for env in ("staging", "production"):
            suffix = "STAGING" if env == "staging" else "PRODUCTION"
            email    = os.getenv(f"{portal.upper()}_{suffix}_EMAIL", "").strip()
            password = os.getenv(f"{portal.upper()}_{suffix}_PASSWORD", "").strip()
            sessions.append({
                "portal":        portal,
                "env":           env,
                "credentials":   "configured" if (email and password) else "missing",
                "email":         email if email else None,
            })
    return {"sessions": sessions}

# ── /tests ────────────────────────────────────────────────────────────────────

@app.post("/tests/run")
async def run_tests(body: RunTestsBody):
    portals = [body.portal] if body.portal else ["seller", "admin", "agency"]
    results = []
    for portal in portals:
        status, result = await asyncio.to_thread(_playwright.run_tests, portal, body.env)
        results.append({
            "portal": portal,
            "env": body.env,
            "status": status,
            "message": result.get("message", "") if isinstance(result, dict) else str(result),
            "url": result.get("url") if isinstance(result, dict) else None,
            "console_errors": result.get("console_errors", []) if isinstance(result, dict) else [],
            "nav_elements_found": result.get("nav_elements_found", []) if isinstance(result, dict) else [],
            "load_time_ms": result.get("load_time_ms") if isinstance(result, dict) else None,
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

@app.post("/jira/generate-ticket")
async def generate_ticket_ai(body: GenerateTicketBody):
    import re

    def _generate():
        is_bug = body.issue_type.lower() == "bug"
        desc_sections = (
            "**Problem Statement**\n[Clear description of the issue]\n\n"
            "**Expected Behavior**\n[What should happen]\n\n"
            + ("**Steps to Reproduce**\n1. [Step 1]\n2. [Step 2]\n3. [Step 3]\n\n" if is_bug else "")
            + "**Acceptance Criteria**\n1. [Criterion 1]\n2. [Criterion 2]"
        )
        prompt = (
            "You are a senior QA engineer writing a professional Jira ticket.\n\n"
            f"Issue Type: {body.issue_type}\n"
            f"Project: {body.project_key}\n\n"
            f"User description:\n{body.description}\n\n"
            "Return ONLY valid JSON (no markdown, no code fences) with exactly:\n"
            '{"summary": "<max 10 words, no trailing punctuation>", '
            '"description": "<full description with sections: '
            + ("Problem Statement, Expected Behavior, Steps to Reproduce, Acceptance Criteria" if is_bug
               else "Problem Statement, Expected Behavior, Acceptance Criteria")
            + '>"}'
        )

        client = OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=os.getenv("GITHUB_TOKEN"),
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900,
        )
        output = (response.choices[0].message.content or "").strip()

        code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", output, re.DOTALL)
        if code_match:
            output = code_match.group(1)

        parsed = json.loads(output)
        return {"summary": str(parsed["summary"]), "description": str(parsed["description"])}

    try:
        return await asyncio.to_thread(_generate)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/jira/ticket/{issue_key}")
async def get_ticket_detail(issue_key: str):
    ticket   = await asyncio.to_thread(_jira.get_ticket, issue_key)
    comments = await asyncio.to_thread(_jira.get_comments, issue_key)
    fields   = ticket.get("fields", {})
    desc_raw = fields.get("description")
    description = _adf_to_text(desc_raw) if isinstance(desc_raw, (dict, list)) else (desc_raw or "")
    return {
        "key":        ticket.get("key"),
        "summary":    fields.get("summary"),
        "status":     (fields.get("status") or {}).get("name"),
        "issue_type": (fields.get("issuetype") or {}).get("name"),
        "assignee":   (fields.get("assignee") or {}).get("displayName"),
        "description": description,
        "created":    fields.get("created"),
        "url":        f"https://zambeel.atlassian.net/browse/{ticket.get('key')}",
        "comments": [
            {
                "author":  (c.get("author") or {}).get("displayName", "?"),
                "body":    _adf_to_text(c["body"]) if isinstance(c.get("body"), (dict, list)) else (c.get("body") or ""),
                "created": c.get("created"),
            }
            for c in (comments or [])
        ],
    }

def extract_selectors_from_source(keywords: list) -> str:
    """
    Extract real UI elements from zambeel-fe/src matching the given keywords.
    Falls back to mining app_context.md if the source tree is unavailable (cloud).
    """
    import re as _re

    kw_set = set(kw.lower() for kw in keywords if kw and len(kw) >= 3)

    src_path = os.path.expanduser("~/Documents/GitHub/zambeel-fe/src")

    if os.path.isdir(src_path):
        # ── Local: scan .tsx / .ts files ──────────────────────────────────────
        matches = []
        for root, dirs, files in os.walk(src_path):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "dist")]
            for fname in files:
                if not (fname.endswith(".tsx") or fname.endswith(".ts")):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    content = open(fpath, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                if not any(kw in content.lower() for kw in kw_set):
                    continue

                rel = os.path.relpath(fpath, src_path)
                matches.append(f"[File: {rel}]")

                for m in _re.finditer(r"<[Bb]utton[^>]*>\s*([^<{]{1,60})\s*</[Bb]utton>", content):
                    txt = m.group(1).strip()
                    if txt:
                        matches.append(f"Button: '{txt}'")

                for m in _re.finditer(r'placeholder=["\']([^"\']{1,80})["\']', content):
                    matches.append(f"Input placeholder: '{m.group(1)}'")

                for m in _re.finditer(r"<label[^>]*>\s*([^<]{1,60})\s*</label>", content, _re.IGNORECASE):
                    txt = m.group(1).strip()
                    if txt:
                        matches.append(f"Label: '{txt}'")

                for m in _re.finditer(r"""path:\s*['"]([^'"]{2,80})['"]""", content):
                    matches.append(f"Route: {m.group(1)}")

                for m in _re.finditer(r"""to=['"](/[^'"]{1,80})['"]""", content):
                    matches.append(f"Nav link: {m.group(1)}")

                for m in _re.finditer(r'(?:data-testid|id)=["\']([^"\']{3,60})["\']', content):
                    matches.append(f"ID/testid: #{m.group(1)}")

                for m in _re.finditer(r'className=["\']([^"\']{4,60})["\']', content):
                    cls = m.group(1).split()[0]
                    if any(kw in cls.lower() for kw in kw_set):
                        matches.append(f"CSS class: .{cls}")

                for m in _re.finditer(
                    r'export\s+(?:default\s+)?(?:function|const)\s+([A-Z][A-Za-z0-9]+)', content
                ):
                    matches.append(f"Component: {m.group(1)}")

        seen: set = set()
        unique = [x for x in matches if not (x in seen or seen.add(x))]  # type: ignore[func-returns-value]
        items = unique[:120]
        source = "zambeel-fe/src (local scan)"
    else:
        # ── Cloud fallback: mine app_context.md ───────────────────────────────
        items = []
        if APP_CONTEXT:
            for line in APP_CONTEXT.splitlines():
                if not any(kw in line.lower() for kw in kw_set):
                    continue
                for m in _re.finditer(r'`(/[a-z0-9/\-_]+)`', line):
                    items.append(f"Route: {m.group(1)}")
                for m in _re.finditer(r'`([^`]{3,60})`', line):
                    txt = m.group(1)
                    if any(kw in txt.lower() for kw in kw_set):
                        items.append(f"Element: '{txt}'")
                for m in _re.finditer(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b', line):
                    items.append(f"Component: {m.group(1)}")
            seen2: set = set()
            items = [x for x in items if not (x in seen2 or seen2.add(x))][:80]  # type: ignore[func-returns-value]
        source = "app_context.md (cloud fallback)"

    if not items:
        return f"REAL SELECTORS FROM SOURCE:\n(No UI elements found in {source} for: {', '.join(list(kw_set)[:8])})"
    content_str = f"Source: {source}\n" + "\n".join(items)
    return f"REAL SELECTORS FROM SOURCE:\n{content_str[:2000]}"


def _extract_relevant_context(title: str, description: str, max_chars: int = 4000) -> str:
    """Score APP_CONTEXT paragraphs by keyword overlap with the ticket, return top sections."""
    import re as _re
    if not APP_CONTEXT:
        return ""

    combined  = f"{title} {description}".lower()
    stopwords = {"that", "this", "with", "from", "have", "will", "been", "they",
                 "when", "what", "which", "where", "then", "also", "should", "would"}
    keywords  = set(_re.findall(r'\b\w{4,}\b', combined)) - stopwords

    sections = _re.split(r'\n{2,}', APP_CONTEXT)
    scored   = sorted(
        ((sum(1 for kw in keywords if kw in s.lower()), s) for s in sections),
        key=lambda x: x[0], reverse=True,
    )

    result, total = [], 0
    for _, section in scored:
        if total >= max_chars:
            break
        chunk = section[:max_chars - total]
        result.append(chunk)
        total += len(chunk)
    return "\n\n".join(result)[:max_chars]


# Maps each portal route to the keywords that indicate a ticket is about that page.
# Longer / more specific phrases are listed first so they score higher than substrings.
_ROUTE_KEYWORDS: dict[str, dict[str, list]] = {
    "admin": {
        "/orders-management/inventory-movements": [
            "inventory movement", "inventory movements", "stock movement", "stock movements",
            "warehouse movement", "inventory log",
        ],
        "/orders-management/commission-models": [
            "commission model", "commission models", "new model", "add rule",
            "flat per order", "commission rate", "commission", "revenue model",
        ],
        "/orders-management/agency-management": [
            "agency management", "approve agency", "reject agency", "agency application",
            "agency registration", "onboard agency", "agency",
        ],
        "/orders-management/seller-management": [
            "seller management", "manage seller", "seller list", "seller profile",
        ],
        "/orders-management/dispatch-batches": [
            "dispatch batch", "dispatch batches", "tracking generated", "manifest",
            "shipment batch", "dispatch", "batch",
        ],
        "/orders-management/purchase-orders": [
            "purchase order", "purchase orders", "po ", "procurement",
        ],
        "/orders-management/team-management": [
            "team management", "team member", "team members", "invite member",
            "add member", "team", "staff role",
        ],
        "/orders-management/ticketing": [
            "oms ticketing", "support ticket", "ticketing", "ticket management",
            "ticket", "issue report",
        ],
        "/orders-management/all-orders": [
            "all orders", "order list", "update status", "upload orders", "edit order",
            "order details", "ndr", "put on hold", "cancel order", "process order",
            "approve order", "order", "orders",
        ],
        "/orders-management/dashboard": [
            "dashboard", "overview", "summary", "stats", "statistics", "kpi", "metrics",
        ],
    },
    "seller": {
        "/seller/inventory": [
            "seller inventory", "inventory management", "product inventory", "sku code",
            "inventory movement", "stock in warehouse", "inventory", "stock",
        ],
        "/stores/integration": [
            "store integration", "connect shopify", "connect easyorder", "connect store",
            "light funnels", "youcan", "manual store", "disconnect store",
            "store connection", "store", "integration",
        ],
        "/ticketing": [
            "create ticket", "ticket management", "seller ticket", "ticketing",
            "ticket", "support",
        ],
        "/settings": [
            "bank account", "payment method", "add account", "iban", "usdt", "paypal",
            "payment settings", "bank", "payment",
        ],
        "/orders": [
            "send to zambeel", "delete order", "csv upload", "order processing",
            "unprocessed orders", "processed orders", "orders dashboard", "order",
        ],
        "/orders-analytics": [
            "orders analytics", "order analytics", "analytics", "analysis",
        ],
        "/my-invoices": [
            "my invoices", "invoice", "invoices", "billing", "download invoice",
        ],
        "/profile": [
            "profile settings", "personal information", "update profile", "phone number",
            "agency connection", "disconnect agency", "profile",
        ],
        "/gold-subscription": [
            "gold subscription", "gold plan", "unlock gold", "gold", "subscription",
        ],
        "/academy": [
            "zambeel academy", "academy", "tutorial", "learning",
        ],
        "/dashboard": [
            "dashboard", "overview", "total orders", "kpi", "stats",
        ],
        "/get-started": [
            "get started", "onboarding", "dropshipping", "zambeel 360", "3pl",
        ],
    },
    "agency": {
        "/agency/portal/sellers": [
            "manage sellers", "seller list", "merchant list", "connect merchant",
            "seller management", "sellers", "merchants",
        ],
        "/agency/portal/ticketing": [
            "agency ticket", "create ticket", "ticket management", "ticketing",
            "ticket", "support",
        ],
        "/agency/portal/settings": [
            "agency settings", "agency profile", "team member", "add member",
            "agency information", "settings",
        ],
        "/agency/portal/dashboard": [
            "dashboard", "overview", "summary", "stats", "metrics",
        ],
        "/get-started": [
            "get started", "registration", "apply", "onboarding",
        ],
    },
}


def _identify_pages_from_ticket(title: str, description: str, portal: str) -> list:
    """Score each known route by keyword hits in the ticket text; return top matches."""
    text = f"{title} {description}".lower()
    keyword_map = _ROUTE_KEYWORDS.get(portal, {})

    scores: dict[str, int] = {}
    for route, keywords in keyword_map.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[route] = score

    if scores:
        ranked = sorted(scores, key=lambda r: scores[r], reverse=True)
        result = ranked[:3]
        print(f"[_identify_pages] keyword scores: {[(r, scores[r]) for r in result]}")
        return result

    # No keywords matched — fall back to the first route for the portal
    fallback = next(iter(keyword_map), None)
    print(f"[_identify_pages] no keyword match, fallback={fallback}")
    return [fallback] if fallback else []


def screenshot_page(portal, env, url_path):
    """Login, navigate to url_path, take an 800x600 screenshot, return base64."""
    from playwright.sync_api import sync_playwright
    import base64
    base_url = 'https://staging.myzambeel.com' if env == 'staging' else 'https://portal.myzambeel.com'
    email    = os.getenv(f'{portal.upper()}_{env.upper()}_EMAIL', '').strip()
    password = os.getenv(f'{portal.upper()}_{env.upper()}_PASSWORD', '').strip()
    full_url = f'{base_url}{url_path}'
    print(f'[screenshot_page] {portal}/{env} → {full_url}')
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 800, 'height': 600})
            page.goto(f'{base_url}/login')
            page.fill('input[type="email"]', email)
            page.fill('input[type="password"]', password)
            page.click('button[type="submit"]')
            page.wait_for_url(lambda u: '/login' not in u, timeout=30000)
            page.goto(full_url)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
            screenshot = page.screenshot(full_page=False)
            browser.close()
        b64 = base64.b64encode(screenshot).decode()
        print(f'[screenshot_page] done — {len(b64)} bytes base64')
        return {'base64': b64, 'url': full_url, 'url_path': url_path, 'portal': portal, 'env': env}
    except Exception as e:
        print(f'[screenshot_page] ERROR: {e}')
        return {'error': str(e), 'url': full_url, 'url_path': url_path}


def extract_page_dom(page) -> dict:
    """Extract all interactive elements from an already-loaded Playwright page.

    Also expands every native <select> to capture its full option list.
    Returns a dict suitable for passing directly to generate_test_cases.
    """
    # Collect native select options by querying each element from Python
    select_data = []
    try:
        selects = page.query_selector_all('select')
        for s in selects:
            options = s.query_selector_all('option')
            select_data.append([o.inner_text().strip() for o in options if o.inner_text().strip()])
    except Exception as e:
        print(f'[extract_page_dom] select extraction error: {e}')

    dom = page.evaluate('''() => ({
        buttons:  [...document.querySelectorAll('button')]
                      .map(b => b.innerText.trim()).filter(Boolean),
        inputs:   [...document.querySelectorAll('input')].map(i => ({
                      placeholder: i.placeholder, type: i.type, name: i.name
                  })).filter(i => i.placeholder || i.name),
        headings: [...document.querySelectorAll('h1,h2,h3')]
                      .map(h => h.innerText.trim()).filter(Boolean),
        pageText: document.body.innerText.slice(0, 1000)
    })''')
    dom['selects'] = select_data
    return dom


def extract_page_dom_live(portal, env, url_path) -> dict:
    """Login, navigate to url_path, extract DOM, return structured data.

    No screenshot is taken — DOM data is compact (<1000 tokens) and gives
    GPT-4o the exact elements that exist on the live page.
    """
    from playwright.sync_api import sync_playwright
    base_url = 'https://staging.myzambeel.com' if env == 'staging' else 'https://portal.myzambeel.com'
    email    = os.getenv(f'{portal.upper()}_{env.upper()}_EMAIL', '').strip()
    password = os.getenv(f'{portal.upper()}_{env.upper()}_PASSWORD', '').strip()
    full_url = f'{base_url}{url_path}'
    print(f'[extract_page_dom_live] {portal}/{env} → {full_url}')
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 900})
            page.goto(f'{base_url}/login')
            page.fill('input[type="email"]', email)
            page.fill('input[type="password"]', password)
            page.click('button[type="submit"]')
            page.wait_for_url(lambda u: '/login' not in u, timeout=30000)
            page.goto(full_url)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
            dom = extract_page_dom(page)
            browser.close()
        print(f'[extract_page_dom_live] done — buttons={len(dom["buttons"])} '
              f'inputs={len(dom["inputs"])} selects={len(dom["selects"])}')
        print(f'[DOM] buttons={dom["buttons"][:5]}, inputs={dom["inputs"][:3]}, selects={dom["selects"]}')
        return {'dom': dom, 'portal': portal, 'env': env, 'url_path': url_path, 'url': full_url}
    except Exception as e:
        print(f'[extract_page_dom_live] ERROR: {e}')
        return {'error': str(e), 'portal': portal, 'env': env, 'url_path': url_path}


_ZAMBEEL_SELECTOR_FIXES = [
    # Commission Models page — wrong button text
    ('button:has-text("Create Commission Model")', 'button:has-text("+ New Model")'),
    ("button:has-text('Create Commission Model')", "button:has-text('+ New Model')"),
    # Generic save button — always needs 'Model' suffix on this page
    ('button:has-text("Save")', 'button:has-text("Save Model")'),
    ("button:has-text('Save')", "button:has-text('Save Model')"),
    # Wrong model name input placeholders
    ('input[placeholder="Model Name"]', 'input[placeholder="Enter model name"]'),
    ("input[placeholder='Model Name']", "input[placeholder='Enter model name']"),
    ('input[placeholder="Enter Name"]', 'input[placeholder="Enter model name"]'),
    ("input[placeholder='Enter Name']", "input[placeholder='Enter model name']"),
    ('input[placeholder="Name"]', 'input[placeholder="Enter model name"]'),
    ("input[placeholder='Name']", "input[placeholder='Enter model name']"),
    # Wrong placeholder for commission value input
    ('input[placeholder="Amount"]', 'input[type="number"]'),
    ("input[placeholder='Amount']", "input[type='number']"),
    ('input[placeholder=\'Enter commission amount\']', 'input[type=\'number\']'),
    ('input[placeholder="Enter commission amount"]', 'input[type="number"]'),
    # Remove dialog-scoped Country/Type trigger clicks — use CLICK_OPTION directly
    ("CLICK: div[role='dialog'] >> text='Country*'", ''),
    ('CLICK: div[role="dialog"] >> text="Country*"', ''),
    ("CLICK: div[role='dialog'] >> text='Country'", ''),
    ('CLICK: div[role="dialog"] >> text="Country"', ''),
    ("CLICK: div[role='dialog'] >> text='Type*'", ''),
    ('CLICK: div[role="dialog"] >> text="Type*"', ''),
    ("CLICK: div[role='dialog'] >> text='Type'", ''),
    ('CLICK: div[role="dialog"] >> text="Type"', ''),
    ("CLICK: text='Country*'", ''),
    ('CLICK: text="Country*"', ''),
    ("CLICK: text='Type*'", ''),
    ('CLICK: text="Type*"', ''),
    # Convert country CLICK steps to CLICK_OPTION (background table cells intercept clicks)
    ("CLICK: text='Saudi Arabia'", 'CLICK_OPTION: Saudi Arabia'),
    ('CLICK: text="Saudi Arabia"', 'CLICK_OPTION: Saudi Arabia'),
    ("CLICK: text='Pakistan'", 'CLICK_OPTION: Pakistan'),
    ('CLICK: text="Pakistan"', 'CLICK_OPTION: Pakistan'),
    ("CLICK: text='UAE'", 'CLICK_OPTION: UAE'),
    ('CLICK: text="UAE"', 'CLICK_OPTION: UAE'),
    ("CLICK: text='Kuwait'", 'CLICK_OPTION: Kuwait'),
    ('CLICK: text="Kuwait"', 'CLICK_OPTION: Kuwait'),
    ("CLICK: text='Bahrain'", 'CLICK_OPTION: Bahrain'),
    ('CLICK: text="Bahrain"', 'CLICK_OPTION: Bahrain'),
    ("CLICK: text='Iraq'", 'CLICK_OPTION: Iraq'),
    ('CLICK: text="Iraq"', 'CLICK_OPTION: Iraq'),
    ("CLICK: text='Qatar'", 'CLICK_OPTION: Qatar'),
    ('CLICK: text="Qatar"', 'CLICK_OPTION: Qatar'),
    ("CLICK: text='Oman'", 'CLICK_OPTION: Oman'),
    ('CLICK: text="Oman"', 'CLICK_OPTION: Oman'),
    # Convert type CLICK steps to CLICK_OPTION + fix wrong type names
    ("CLICK: text='% of Revenue'", 'CLICK_OPTION: % of Revenue'),
    ('CLICK: text="% of Revenue"', 'CLICK_OPTION: % of Revenue'),
    ("CLICK: text='Flat per Order'", 'CLICK_OPTION: Flat per Order'),
    ('CLICK: text="Flat per Order"', 'CLICK_OPTION: Flat per Order'),
    ("CLICK: text='Percentage'", 'CLICK_OPTION: % of Revenue'),
    ('CLICK: text="Percentage"', 'CLICK_OPTION: % of Revenue'),
    ("CLICK: text='Flat Rate'", 'CLICK_OPTION: Flat per Order'),
    ('CLICK: text="Flat Rate"', 'CLICK_OPTION: Flat per Order'),
    # Invalid className pseudo-method GPT-4o generates for disabled state
    ('button:has-text(\'Save Model\').className(\'disabled\')', 'button.bg-indigo-300:has-text(\'Save Model\')'),
    ('button:has-text("Save Model").className("disabled")', 'button.bg-indigo-300:has-text("Save Model")'),
    # ASSERT_TEXT on dialog — dialog spans full page, use ASSERT_EXISTS
    ('ASSERT_TEXT: div[role=\'dialog\']', 'ASSERT_EXISTS: div[role=\'dialog\']'),
    ('ASSERT_TEXT: div[role="dialog"]', 'ASSERT_EXISTS: div[role="dialog"]'),
    # No confirmation/success toast exists — remove these false assertions
    ("ASSERT_EXISTS: text='Commission model saved successfully.'", ''),
    ('ASSERT_EXISTS: text="Commission model saved successfully."', ''),
    ("ASSERT_EXISTS: text='Model saved successfully.'", ''),
    ('ASSERT_EXISTS: text="Model saved successfully."', ''),
    ("ASSERT_EXISTS: text='Saved successfully.'", ''),
    ('ASSERT_EXISTS: text="Saved successfully."', ''),
    ("ASSERT_EXISTS: text='Success'", ''),
    ('ASSERT_EXISTS: text="Success"', ''),
    # Currency field is auto-populated — remove manual currency steps
    ("CLICK_OPTION: USD", ''),
    ('CLICK_OPTION: SAR', ''),
    ('CLICK_OPTION: AED', ''),
    ('CLICK_OPTION: PKR', ''),
    # Invalid enabled-state selector — use class-based check instead
    ("ASSERT_EXISTS: button:has-text('Save Model') :not(:disabled)", "ASSERT_EXISTS: button.bg-indigo-600:has-text('Save Model')"),
    ('ASSERT_EXISTS: button:has-text("Save Model") :not(:disabled)', 'ASSERT_EXISTS: button.bg-indigo-600:has-text("Save Model")'),
    # ASSERT_NOT_EXISTS on option text is unreliable
    ("ASSERT_NOT_EXISTS: text='Flat Rate'", ''),
    ('ASSERT_NOT_EXISTS: text="Flat Rate"', ''),
    ("ASSERT_NOT_EXISTS: text='Percentage'", ''),
    ('ASSERT_NOT_EXISTS: text="Percentage"', ''),
    # Fabricated duplicate-country validation messages — strip them
    ("ASSERT_EXISTS: text='Each country can only appear once inside the same model.'", ''),
    ('ASSERT_EXISTS: text="Each country can only appear once inside the same model."', ''),
    ("ASSERT_EXISTS: text='Duplicate country'", ''),
    ('ASSERT_EXISTS: text="Duplicate country"', ''),
    # Invalid Playwright syntax GPT-4o generates
    ('| disabled', ''),
    ('| not_exists', ''),
    # Wrong route paths — GPT-4o invents short paths; correct to full OMS routes
    ('/inventory-management', '/orders-management/inventory-movements'),
    ('/ticketing', '/orders-management/ticketing'),
    ('/orders', '/orders-management/orders'),
    # GPT-4o writes Python locator API as if it were a CSS selector — convert to CLICK_OPTION
    ("ASSERT_EXISTS: page.locator('select').last()", "CLICK_OPTION: 100"),
    ("CLICK: page.locator('select').last()", "CLICK_OPTION: 100"),
    # Wrong heading level for Ticketing Management
    ("h1:has-text('Ticketing Management')", "h2:has-text('Ticketing Management')"),
    ('h1:has-text("Ticketing Management")', 'h2:has-text("Ticketing Management")'),
    # Wrong placeholder — inventory search vs ticketing search
    ("input[placeholder='Search Movement ID']", "input[placeholder='Search by store name...']"),
    ('input[placeholder="Search Movement ID"]', 'input[placeholder="Search by store name..."]'),
    # Next/Previous button exact text (no arrows)
    ("button:has-text('Next >')", "button:has-text('Next')"),
    ('button:has-text("Next >")', 'button:has-text("Next")'),
    ("button:has-text('< Previous')", "button:has-text('Previous')"),
    ('button:has-text("< Previous")', 'button:has-text("Previous")'),
    # Page info text — regex doesn't work in evidence check; use simple partial text match
    ("text='Page 1 of'", "text='Page'"),
    ('text="Page 1 of"', "text='Page'"),
    ("text='Page 2 of'", "text='Page'"),
    ('text="Page 2 of"', "text='Page'"),
    (r"text=/Page \d+ of/", "text='Page'"),
    # ASSERT_TEXT pipe value wrapped in quotes — strip the quotes
    ("| 'TKT-", "| TKT-"),
    ('| "TKT-', '| TKT-'),
    # Ticketing evidence selector: table header compound >> text is wrong; use text= directly
    ("th:has-text('TICKET ID') >> text='TKT", "text='TKT"),
    # Invalid Playwright locator API used as CSS — replace with FILL step
    ("input >> 3", "FILL: input[aria-label='Go to page'] | 3"),
    # Ticketing: inject mandatory CLICK_OPTION: Ticket Number before ticket number FILL step
    ("FILL: input[placeholder='Search by ticket number...']",
     "CLICK_OPTION: Ticket Number\nFILL: input[placeholder='Search by ticket number...']"),
    # Ticketing: wrong placeholder for ticket number search input
    ("input[placeholder='Search by Ticket ID']", "input[placeholder='Search by ticket number...']"),
    ("input[placeholder='Search by ticket number']", "input[placeholder='Search by ticket number...']"),
    # Ticketing: store name placeholder used when ticket number input is needed
    ("input[placeholder='Search by store name...'] | TKT", "input[placeholder='Search by ticket number...'] | TKT"),
    # Inventory movements uses 'Page X of Y', not 'Showing X to Y of'
    ("text='Showing 1 to 100 of'", r"text=/Page \d+ of \d+/"),
    # Generic empty-state text fixes
    ("text='No results found'", "text=/Showing 0/"),
    ("text='No tickets found'", "text=/Showing 0/"),
    # Inventory movements has its own search input — not the store name placeholder
    ("input[placeholder='Search by store name...'] | MOVE", "input[placeholder='Search Movement ID'] | MOVE"),
    # Ticketing Create button — '+' is a <Plus> SVG icon, NOT text. has-text('+...') will never match.
    ("button:has-text('+ Create New Ticket')", "button:has-text('Create New Ticket')"),
    ('button:has-text("+ Create New Ticket")', 'button:has-text("Create New Ticket")'),
]


def _parse_test_cases(output: str) -> list:
    """Parse GPT-4o JSON output into a validated list of test case dicts."""
    if not output or not output.strip():
        print('[_parse_test_cases] Empty output from AI')
        return []
    clean = output.strip()
    if clean.startswith('```'):
        clean = '\n'.join(clean.split('\n')[1:])
    if clean.endswith('```'):
        clean = '\n'.join(clean.split('\n')[:-1])
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError as e:
        print(f'[_parse_test_cases] JSON error: {e}, output: {clean[:200]}')
        return []
    if isinstance(parsed, list):
        raw_cases = parsed
    elif isinstance(parsed, dict) and "test_cases" in parsed:
        raw_cases = parsed["test_cases"]
    else:
        print(f"[_parse_test_cases] Unexpected JSON shape: {type(parsed)}")
        return []

    valid = []
    for tc in raw_cases:
        if not isinstance(tc, dict):
            continue
        if not tc.get("test_name") or not tc.get("steps"):
            continue
        tc.setdefault("url_path", "/")
        tc.setdefault("portal", "seller")
        tc.setdefault("expected_result", "Feature works as expected")
        tc.setdefault("evidence_selector", "")
        # Apply selector + route fixes to all steps
        fixed_steps = []
        for s in tc.get("steps", []):
            if not s:
                continue
            for wrong, right in _ZAMBEEL_SELECTOR_FIXES:
                if wrong not in s:
                    continue
                # For route corrections: skip if the route is already correctly prefixed
                if (right and right.startswith('/orders-management')
                        and wrong.startswith('/')
                        and ('/orders-management' + wrong) in s):
                    continue
                s = s.replace(wrong, right)
                break
            fixed_steps.extend(line for line in s.split('\n') if line.strip())
        tc["steps"] = fixed_steps
        # Drop empty steps produced by fixes that replace with ''
        tc["steps"] = [s for s in tc["steps"] if s.strip()]
        # Apply route fixes to the top-level url_path field
        for wrong, right in _ZAMBEEL_SELECTOR_FIXES:
            if right and wrong in tc["url_path"]:
                # Guard: don't double-prepend /orders-management
                if not tc["url_path"].startswith('/orders-management'):
                    tc["url_path"] = tc["url_path"].replace(wrong, right)
                break
        valid.append(tc)

    print(f"[_parse_test_cases] {len(valid)} valid test cases")
    return valid


_TEST_CASE_JSON_SCHEMA = (
    "Each test case must be a JSON object with:\n"
    '- "test_name": string\n'
    '- "url_path": exact URL path (e.g. "/orders-management/commission-models")\n'
    '- "portal": "admin", "seller", or "agency"\n'
    '- "steps": array of strings, each starting with one of:\n'
    "    CLICK: css-selector\n"
    "    FILL: css-selector | value\n"
    "    WAIT: css-selector\n"
    "    NAVIGATE: /path\n"
    "    ASSERT_EXISTS: css-selector\n"
    "    ASSERT_NOT_EXISTS: css-selector\n"
    "    ASSERT_TEXT: css-selector | expected text\n"
    "    SCREENSHOT: label\n"
    "    CLICK_OPTION: option value\n"
    '- "expected_result": what success looks like\n'
    '- "evidence_selector": ONE CSS selector that proves the feature works\n\n'
    "Selector rules for this React/Tailwind app (NO element IDs exist):\n"
    '- Buttons: button:has-text("exact text")\n'
    '- Inputs:  input[placeholder="exact placeholder"]\n'
    '- Text:    text="exact visible text"\n'
    "- Modals:  div[role=\"dialog\"]\n"
    "- Dropdowns: CLICK_OPTION: value  (not CLICK on the trigger)\n"
    "- NEVER use #id selectors\n"
    "- NEVER wrap FILL/CLICK_OPTION values in quotes inside the step string\n\n"
    'Return ONLY valid JSON: {"test_cases": [...]}'
)


def generate_test_cases(ticket_key, title, description, screenshots: list = None):
    import re
    from groq import Groq

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # Detect portal from screenshots, then ticket key prefix, then default to admin
    if screenshots and screenshots[0].get("portal"):
        portal_hint = screenshots[0]["portal"].lower()
    elif ticket_key.upper().startswith("ZSP"):
        portal_hint = "seller"
    elif ticket_key.upper().startswith("AGN"):
        portal_hint = "agency"
    else:
        portal_hint = "admin"

    knowledge_base = get_portal_knowledge(portal_hint)

    if not screenshots:
        raise RuntimeError("generate_test_cases: no screenshots provided — cannot generate test cases")
    valid_shots = [s for s in screenshots if s.get("base64")]
    if not valid_shots:
        errors = [s.get("error", "no base64") for s in screenshots]
        raise RuntimeError(f"generate_test_cases: all screenshots failed — {errors}")
    print(f"[generate_test_cases] {len(valid_shots)} screenshot(s), "
          f"portal={portal_hint}, kb={len(knowledge_base):,} chars")

    pages_summary = ", ".join(s.get("url_path", s.get("url", "")) for s in valid_shots)
    prompt = (
        f"{_MANDATORY_SELECTOR_INSTRUCTION}\n\n"
        f"{ZAMBEEL_OMS_ROUTES}\n\n"
        "You are a senior QA engineer generating Playwright test cases for the Zambeel platform.\n\n"
        f"Ticket: {ticket_key}\n"
        f"Title: {title}\n"
        f"Description: {description}\n\n"
        f"Pages captured: {pages_summary}\n\n"
        f"CRITICAL: Generate test cases ONLY for the feature described in the ticket. "
        f"Do NOT generate tests for login, navigation, or unrelated features. "
        f"Every test case must directly test: {title}\n\n"
        "Cross-reference the KNOWLEDGE BASE below to confirm exact selector text:\n"
        "1. Identify every relevant UI element — exact button labels, input placeholders, "
        "dropdown option text, heading text.\n"
        "2. Generate 5 Playwright test cases. For each selector, verify it exists in the "
        "KNOWLEDGE BASE. If it does not appear there, use text= with the exact visible text.\n"
        "3. Never invent placeholder text or button labels not present in the KNOWLEDGE BASE.\n\n"
        f"KNOWLEDGE BASE ({portal_hint} portal):\n"
        f"{knowledge_base}\n\n"
        + _TEST_CASE_JSON_SCHEMA
    )

    print(f"[generate_test_cases] prompt (first 500 chars): {prompt[:500]}")

    _groq_models = ["llama-3.3-70b-versatile", "llama3-8b-8192", "mixtral-8x7b-32768"]
    output = ""
    for _model in _groq_models:
        try:
            print(f"[generate_test_cases] trying model={_model}")
            _resp = groq_client.chat.completions.create(
                model=_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            output = (_resp.choices[0].message.content or "").strip()
            print(f"[generate_test_cases] model={_model} succeeded ({len(output)} chars): {output[:1000]}")
            break
        except Exception as _err:
            if "429" in str(_err) or "rate" in str(_err).lower():
                print(f"[generate_test_cases] model={_model} rate limited, trying next")
                continue
            raise
    return _parse_test_cases(output)


def _build_qa_report(*, issue_key, summary, env, frontend_branch, backend_branch,
                     test_cases, test_results, all_pass, new_status, elapsed):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    branch_rows = (
        [f"| Frontend Branch | `{frontend_branch}` |", f"| Backend Branch | `{backend_branch}` |"]
        if env == "local" else []
    )
    lines = [
        f"# QA Report — {issue_key}",
        f"**{summary}**",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Ticket | [{issue_key}](https://zambeel.atlassian.net/browse/{issue_key}) |",
        f"| Environment | `{env.upper()}` |",
        *branch_rows,
        f"| Result | {'✅ All Passed' if all_pass else '❌ Some Failed'} |",
        f"| Jira Status | {new_status} |",
        f"| Elapsed | {elapsed}s |",
        f"| Generated | {ts} |",
        f"",
        f"---",
        f"",
        f"## Portal Test Results",
        f"",
    ]
    for r in test_results:
        icon = "✅" if r["status"] == "PASS" else "❌"
        lines += [
            f"### {icon} {r['portal'].capitalize()} — {r['status']}",
            f"- **URL:** {r.get('url') or '—'}",
            f"- **Load time:** {r.get('load_time_ms', 0)}ms",
            f"- **Console errors:** {len(r.get('console_errors') or [])}",
        ]
        for err in (r.get("console_errors") or [])[:3]:
            lines.append(f"  - `{err[:150]}`")
        evidence = r.get("feature_evidence") or []
        if evidence:
            lines.append(f"- **Feature evidence:**")
            for e in evidence:
                mark = "✓" if e.get("found") else "✗"
                lines.append(f"  - {mark} {e['description']} — `{e['selector']}` — {e.get('detail','')}")
        shots = r.get("screenshots") or []
        if shots:
            lines.append(f"- **Step screenshots:**")
            for s in shots:
                lines.append(f"  - `{s['filename']}` — {s['label']}")
        nav = r.get("nav_elements_found") or []
        if nav:
            lines.append(f"- **Nav elements found:** {', '.join(f'`{s}`' for s in nav)}")
        log = r.get("execution_log") or []
        if log:
            lines += ["", "<details><summary>Execution log</summary>", ""]
            lines.append("| Step | Result | Detail |")
            lines.append("|------|--------|--------|")
            for entry in log:
                detail = (entry.get("detail") or "").replace("|", "\\|")[:120]
                lines.append(f"| {entry['step'][:80]} | {entry['result']} | {detail} |")
            lines += ["", "</details>", ""]
        lines.append("")

    if test_cases:
        lines += [
            "---",
            "",
            f"## AI-Generated Test Cases ({len(test_cases)} total)",
            "",
        ]
        for i, tc in enumerate(test_cases, 1):
            lines += [
                f"### {i}. {tc.get('test_name', 'Test')}",
                f"_{tc.get('description', '')}_",
                f"",
            ]
            for s in (tc.get("steps") or []):
                lines.append(f"- {s}")
            lines.append(f"")
            lines.append(f"**Expected:** {tc.get('expected_result', '')}")
            if tc.get("evidence_selector"):
                lines.append(f"**Evidence selector:** `{tc['evidence_selector']}`")
            lines.append("")

    return "\n".join(lines)


@app.post("/jira/tickets/{issue_key}/run-qa")
async def run_qa_endpoint(issue_key: str, body: RunQABody):

    async def generate():
        t0 = time.time()

        def evt(data: dict) -> str:
            return f"data: {json.dumps(data)}\n\n"

        # ── helpers ────────────────────────────────────────────────────────────
        branches_switched = False
        test_results: list = []
        test_cases:   list = []
        all_pass      = False
        new_status    = ""
        elapsed       = 0.0

        # ── Stage: set QA In Progress immediately (before anything else) ───────
        yield evt({"stage": "setting_qa_in_progress", "status": "running"})
        try:
            await asyncio.to_thread(_jira.update_ticket_status, issue_key, "QA In Progress")
            yield evt({"stage": "setting_qa_in_progress", "status": "done"})
        except Exception as e:
            yield evt({"stage": "setting_qa_in_progress", "status": "error", "message": str(e)})
            # Non-fatal — continue with the run

        # ── Stage: fetch ticket ────────────────────────────────────────────────
        yield evt({"stage": "analysing_ticket", "status": "running"})
        try:
            ticket   = await asyncio.to_thread(_jira.get_ticket, issue_key)
            comments = await asyncio.to_thread(_jira.get_comments, issue_key)
            fields   = ticket.get("fields", {})
            summary  = fields.get("summary", "")
            desc_raw = fields.get("description")
            description = _adf_to_text(desc_raw) if isinstance(desc_raw, (dict, list)) else (desc_raw or "")
            assignee    = (fields.get("assignee") or {}).get("displayName", "")
            comment_texts = [
                f"{(c.get('author') or {}).get('displayName','?')}: "
                + (_adf_to_text(c["body"]) if isinstance(c.get("body"), (dict, list)) else (c.get("body") or ""))
                for c in (comments or [])
            ]
        except Exception as e:
            yield evt({"stage": "analysing_ticket", "status": "error", "message": str(e)})
            yield evt({"stage": "done", "error": str(e)})
            return
        yield evt({"stage": "analysing_ticket", "status": "done"})

        # ── Stage: switch branches (local only) ────────────────────────────────
        run_env = body.env  # may be overridden to 'staging' if repos unavailable
        if body.env == "local":
            yield evt({"stage": "switching_branches", "status": "running"})
            fe_path = REPO_PATHS.get("frontend", "")
            be_path = REPO_PATHS.get("backend", "")
            repos_available = fe_path and os.path.isdir(fe_path) and be_path and os.path.isdir(be_path)
            if not repos_available:
                yield evt({
                    "stage": "needs_local_setup",
                    "status": "needs_local_setup",
                    "issue_key": issue_key,
                    "frontend_branch": body.frontend_branch,
                    "backend_branch": body.backend_branch,
                    "portal": body.portal or "",
                })
                yield evt({"stage": "done", "result": {"needs_local_setup": True}})
                return
            else:
                try:
                    await asyncio.to_thread(_github.switch_branch, fe_path, body.frontend_branch)
                except Exception as e:
                    yield evt({"stage": "switching_branches", "status": "error",
                               "message": f"Frontend branch '{body.frontend_branch}' not found: {e}"})
                    yield evt({"stage": "done", "error": str(e)})
                    return
                try:
                    await asyncio.to_thread(_github.switch_branch, be_path, body.backend_branch)
                except Exception as e:
                    try:
                        await asyncio.to_thread(_github.switch_branch, fe_path, "main")
                    except Exception:
                        pass
                    yield evt({"stage": "switching_branches", "status": "error",
                               "message": f"Backend branch '{body.backend_branch}' not found: {e}"})
                    yield evt({"stage": "done", "error": str(e)})
                    return
                branches_switched = True
                yield evt({"stage": "switching_branches", "status": "done"})

        # ── Stage: screenshot relevant pages ──────────────────────────────────
        screenshots: list = []
        yield evt({"stage": "inspecting_page", "status": "running"})
        try:
            portal_for_inspect = (
                body.portal if (body.portal and body.portal != "all") else "seller"
            )
            pages = await asyncio.to_thread(
                _identify_pages_from_ticket, summary, description, portal_for_inspect
            )
            print(f"[inspecting_page] Identified pages: {pages}")
            for url_path in pages:
                yield f": keepalive\n\n"
                shot = await asyncio.to_thread(
                    screenshot_page, portal_for_inspect, run_env, url_path
                )
                if shot and not shot.get("error"):
                    screenshots.append(shot)
            yield evt({
                "stage": "inspecting_page",
                "status": "done",
                "pages_inspected": [s.get("url") for s in screenshots],
            })
        except Exception as e:
            print(f"[inspecting_page] ERROR: {e}")
            yield evt({"stage": "inspecting_page", "status": "error", "message": str(e)})

        # ── Stage: generate test cases ─────────────────────────────────────────
        yield evt({"stage": "generating_test_cases", "status": "running"})
        yield f": keepalive\n\n"
        test_cases = await asyncio.to_thread(
            generate_test_cases, issue_key, summary, description, screenshots or None
        )
        # save as Jira comment regardless of parse success
        if test_cases:
            try:
                _env_label = body.env.upper()
                _branch_label = f" | fe:`{body.frontend_branch}` be:`{body.backend_branch}`" if body.env == "local" else ""
                lines = [f"🤖 *AI-Generated QA Test Cases — {issue_key}* ({_env_label}{_branch_label})"]
                for i, tc in enumerate(test_cases, 1):
                    lines.append(f"\n*{i}. {tc.get('test_name','Test')}*\n_{tc.get('description','')}_")
                    for s in (tc.get("steps") or []):
                        lines.append(f"• {s}")
                    lines.append(f"✅ Expected: {tc.get('expected_result','')}")
                await asyncio.to_thread(_jira.add_comment, issue_key, "\n".join(lines))
            except Exception:
                pass
        yield evt({"stage": "generating_test_cases", "status": "done", "count": len(test_cases)})

        # ── Stage: run Playwright tests ────────────────────────────────────────
        yield evt({"stage": "running_tests", "status": "running"})

        # Derive portals from test case metadata; fall back to body.portal or all
        if test_cases:
            seen_portals: set = set()
            portals: list = []
            for _tc in test_cases:
                _p = (_tc.get("portal") or "seller").lower()
                if _p not in seen_portals:
                    portals.append(_p)
                    seen_portals.add(_p)
            print(f"\n[run_tests] AI test cases derive portals={portals}")
        else:
            portals = [body.portal] if (body.portal and body.portal != "all") else ["seller", "admin", "agency"]
            print(f"\n[run_tests] No test cases — login-only for portals={portals}")

        # ── Pre-loop debug dump ───────────────────────────────────────────────
        print(f"\n[run_qa DEBUG] ── test_cases generated: {len(test_cases)}")
        print(f"[run_qa DEBUG] ── portals to run: {portals}")
        print(f"[run_qa DEBUG] ── execution path: {'run_qa_test_cases' if test_cases else 'run_tests (fallback — no test cases)'}")
        for _i, _tc in enumerate(test_cases):
            print(f"[run_qa DEBUG]    tc[{_i}] portal={_tc.get('portal')} name={_tc.get('test_name')} "
                  f"url={_tc.get('url_path')} steps={len(_tc.get('steps') or [])}")
        if not test_cases:
            print("[run_qa DEBUG]    (full test_cases list is empty)")
        else:
            print(f"[run_qa DEBUG]    full test_cases: {json.dumps(test_cases, indent=2)}")
        print(f"[run_qa DEBUG] ────────────────────────────────────────────────\n")

        for portal in portals:
            yield f": keepalive\n\n"
            print(f"\n[run_tests] Running portal={portal} env={run_env} "
                  f"path={'run_qa_test_cases' if test_cases else 'run_tests fallback'}")
            try:
                if test_cases:
                    portal_tcs = [tc for tc in test_cases if tc.get("portal", "seller").lower() == portal]
                    r = await asyncio.to_thread(
                        _playwright.run_qa_test_cases, portal, run_env, portal_tcs
                    )
                    status = r.get("status", "FAIL")
                    print(f"[run_tests] run_qa_test_cases: portal={portal} status={status} "
                          f"steps={r.get('steps_executed',0)} evidence={len(r.get('feature_evidence',[]))}")
                    screenshots_for_portal = r.get("screenshots", [])
                    test_results.append({
                        "portal":             portal,
                        "status":             status,
                        "message":            r.get("message", ""),
                        "url":                r.get("url"),
                        "console_errors":     r.get("console_errors", []),
                        "load_time_ms":       r.get("load_time_ms", 0),
                        "nav_elements_found": r.get("nav_elements_found", []),
                        "screenshots":        [
                            {**s, "url": f"/screenshots/{s['filename']}"}
                            for s in screenshots_for_portal if s.get("filename")
                        ],
                        "execution_log":      r.get("execution_log", []),
                        "feature_evidence":   r.get("feature_evidence", []),
                        "steps_executed":     r.get("steps_executed", 0),
                    })
                else:
                    status, res = await asyncio.to_thread(_playwright.run_tests, portal, run_env)
                    r = res if isinstance(res, dict) else {}
                    print(f"[run_tests] run_tests done: portal={portal} status={status}")
                    screenshots_for_portal = r.get("screenshots", [])
                    test_results.append({
                        "portal":             portal,
                        "status":             status,
                        "message":            r.get("message", "") or str(res),
                        "url":                r.get("url"),
                        "console_errors":     r.get("console_errors", []),
                        "load_time_ms":       r.get("load_time_ms", 0),
                        "nav_elements_found": r.get("nav_elements_found", []),
                        "screenshots":        [
                            {**s, "url": f"/screenshots/{s['filename']}"}
                            for s in screenshots_for_portal if s.get("filename")
                        ],
                        "execution_log":      r.get("execution_log", []),
                        "feature_evidence":   r.get("feature_evidence", []),
                        "steps_executed":     0,
                    })
            except Exception as e:
                print(f"[run_tests] ERROR for portal={portal}: {type(e).__name__}: {e}")
                test_results.append({
                    "portal": portal, "status": "ERROR", "message": str(e),
                    "url": None, "console_errors": [], "load_time_ms": 0,
                    "nav_elements_found": [], "screenshots": [],
                    "execution_log": [{"step": "Run test", "result": "fail", "detail": str(e)}],
                    "feature_evidence": [], "steps_executed": 0,
                })
            yield evt({"stage": "running_tests", "status": "progress",
                       "portal": portal, "result": test_results[-1]["status"]})
        all_pass = bool(test_results) and all(r["status"] == "PASS" for r in test_results)
        yield evt({"stage": "running_tests", "status": "done", "all_pass": all_pass})

        # ── Stage: update Jira ────────────────────────────────────────────────
        yield evt({"stage": "updating_jira", "status": "running"})
        total_steps_executed = sum(r.get("steps_executed", 0) for r in test_results)
        if not test_cases or total_steps_executed == 0:
            yield evt({
                "stage": "updating_jira", "status": "skipped",
                "message": (
                    "QA Incomplete — no test cases generated. Ticket stays QA In Progress."
                    if not test_cases
                    else "QA Incomplete — zero steps executed. Ticket stays QA In Progress."
                ),
            })
        else:
            _branch_suffix = (
                f" | fe:`{body.frontend_branch}` be:`{body.backend_branch}`"
                if body.env == "local" else ""
            )
            try:
                if all_pass:
                    new_status = "Ready for Review"
                    await asyncio.to_thread(_jira.update_ticket_status, issue_key, new_status)
                else:
                    new_status = "QA In Progress"
                    # already QA In Progress — no transition needed
                if all_pass:
                    comment_lines = [f"✅ *QA Passed* — {body.env.upper()}{_branch_suffix}"]
                    for r in test_results:
                        comment_lines.append(f"• {r['portal'].upper()}: PASS — {r.get('url') or ''} | load: {r.get('load_time_ms',0)}ms")
                        found_ev = [e for e in (r.get("feature_evidence") or []) if e.get("found")]
                        if found_ev:
                            comment_lines.append("  Evidence: " + "; ".join(
                                f"{e['description']} ({e.get('detail','found')})" for e in found_ev[:4]
                            ))
                        shots = r.get("screenshots") or []
                        if shots:
                            comment_lines.append("  Screenshots: " + ", ".join(s["filename"] for s in shots))
                    if assignee:
                        comment_lines.append(f"\n@{assignee} All tests passing — moving to Ready for Review.")
                else:
                    comment_lines = [f"❌ *QA Failed* — {body.env.upper()}{_branch_suffix}"]
                    for r in test_results:
                        icon = "✅" if r["status"] == "PASS" else "❌"
                        comment_lines.append(f"• {r['portal'].upper()}: {icon} {r['status']} — {str(r.get('message',''))[:200]}")
                        for err in (r.get("console_errors") or [])[:3]:
                            comment_lines.append(f"  Console error: {str(err)[:120]}")
                        found_ev = [e for e in (r.get("feature_evidence") or []) if e.get("found")]
                        if found_ev:
                            comment_lines.append("  Elements found: " + "; ".join(
                                e["description"] for e in found_ev[:4]
                            ))
                        shots = r.get("screenshots") or []
                        if shots:
                            comment_lines.append("  Screenshots: " + ", ".join(s["filename"] for s in shots))
                    if assignee:
                        comment_lines.append(f"\n@{assignee} Tests failing — ticket stays in QA In Progress.")
                await asyncio.to_thread(_jira.add_comment, issue_key, "\n".join(comment_lines))
            except Exception as e:
                yield evt({"stage": "updating_jira", "status": "error", "message": str(e)})
            else:
                yield evt({"stage": "updating_jira", "status": "done", "new_status": new_status})

        # ── Restore branches ──────────────────────────────────────────────────
        if body.env == "local" and branches_switched:
            fe_path = REPO_PATHS.get("frontend", "")
            be_path = REPO_PATHS.get("backend", "")
            for path in [fe_path, be_path]:
                try:
                    await asyncio.to_thread(_github.switch_branch, path, "main")
                except Exception:
                    pass

        # ── Stage: Slack report ───────────────────────────────────────────────
        yield evt({"stage": "sending_slack", "status": "running"})
        elapsed = round(time.time() - t0, 1)
        try:
            tc_summary = "\n".join(f"• {tc.get('test_name','')}" for tc in test_cases) or "No test cases generated"
            results_summary = "\n".join(
                f"• {r['portal'].upper()}: {'✅ PASS' if r['status']=='PASS' else '❌ FAIL'} {r.get('url') or ''}"
                for r in test_results
            ) or "No tests run"
            _branch_lines = (
                f"*Frontend Branch:* `{body.frontend_branch}`\n"
                f"*Backend Branch:* `{body.backend_branch}`\n"
            ) if run_env == "local" else ""
            slack_msg = (
                f"🤖 *QA Run Complete* — <https://zambeel.atlassian.net/browse/{issue_key}|{issue_key}>\n"
                f"*{summary}*\n\n"
                f"*Environment:* `{run_env.upper()}`{' *(local repos unavailable, ran on staging)*' if run_env != body.env else ''}\n"
                f"{_branch_lines}"
                f"*AI-Generated Test Cases:*\n{tc_summary}\n\n"
                f"*Playwright Results:*\n{results_summary}\n\n"
                f"*Jira Status →* {'Ready for Review ✅' if all_pass else 'QA In Progress 🔄'}\n"
                f"*Time:* {elapsed}s"
            )
            await asyncio.to_thread(_slack.send_message, slack_msg)
        except Exception as e:
            yield evt({"stage": "sending_slack", "status": "error", "message": str(e)})
        else:
            yield evt({"stage": "sending_slack", "status": "done"})

        # ── Generate markdown QA report ───────────────────────────────────────
        report_markdown = _build_qa_report(
            issue_key=issue_key, summary=summary, env=body.env,
            frontend_branch=body.frontend_branch, backend_branch=body.backend_branch,
            test_cases=test_cases, test_results=test_results,
            all_pass=all_pass, new_status=new_status, elapsed=elapsed,
        )
        try:
            report_ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = REPORTS_DIR / f"qa_{issue_key}_{report_ts}.md"
            report_file.write_text(report_markdown)
        except Exception:
            pass

        # ── Final result ──────────────────────────────────────────────────────
        yield evt({
            "stage": "done",
            "result": {
                "issue_key":       issue_key,
                "env":             body.env,
                "frontend_branch": body.frontend_branch,
                "backend_branch":  body.backend_branch,
                "test_cases":      test_cases,
                "test_results":    test_results,
                "all_pass":        all_pass,
                "new_status":      new_status,
                "elapsed_seconds": elapsed,
                "report_markdown": report_markdown,
            },
        })

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )

@app.get("/jira/sprints/{project_key}")
async def get_sprints(project_key: str):
    board_id = await asyncio.to_thread(_jira.get_board_id, project_key)
    if not board_id:
        return {"sprints": []}
    sprints = await asyncio.to_thread(_jira.get_sprints, board_id, "active")
    return {"sprints": sprints or []}

@app.get("/jira/members")
async def get_members(project: str = "OMS"):
    try:
        members = await asyncio.to_thread(_jira.get_project_members, project)
        return {
            "members": [
                {"accountId": m["accountId"], "displayName": m.get("displayName", "?"),
                 "email": m.get("emailAddress", "")}
                for m in (members or [])
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AssignBody(BaseModel):
    account_id: str

@app.put("/jira/tickets/{issue_key}/assign")
async def assign_ticket(issue_key: str, body: AssignBody):
    try:
        await asyncio.to_thread(_jira.assign_ticket, issue_key, body.account_id)
        return {"success": True, "key": issue_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jira/sprint/{sprint_id}/start")
async def start_sprint(sprint_id: int):
    try:
        await asyncio.to_thread(_jira.start_sprint, sprint_id)
        return {"success": True, "sprint_id": sprint_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jira/sprint/{sprint_id}/end")
async def end_sprint(sprint_id: int):
    try:
        await asyncio.to_thread(_jira.end_sprint, sprint_id)
        return {"success": True, "sprint_id": sprint_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SprintIssueBody(BaseModel):
    issue_keys: list[str]

@app.post("/jira/sprint/{sprint_id}/issue")
async def add_to_sprint(sprint_id: int, body: SprintIssueBody):
    try:
        await asyncio.to_thread(_jira.add_to_sprint, sprint_id, body.issue_keys)
        return {"success": True, "sprint_id": sprint_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── /github ───────────────────────────────────────────────────────────────────

@app.get("/github/branches/{repo}")
async def get_branches(repo: str):
    repo_key = repo.lower()
    repo_api_name = REPO_API_NAMES.get(repo_key, "")
    if not repo_api_name:
        raise HTTPException(
            status_code=400,
            detail=f"GITHUB_{repo.upper()}_REPO_API env var is not set",
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

@app.get("/pr/detail/{repo}/{pr_number}")
async def get_pr_detail(repo: str, pr_number: int):
    repo_key     = repo.lower()
    repo_api_name = REPO_API_NAMES.get(repo_key, "")
    if not repo_api_name:
        raise HTTPException(status_code=400, detail=f"GITHUB_{repo.upper()}_REPO_API env var is not set")
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    def _fetch():
        r = requests.get(
            f"https://api.github.com/repos/{repo_api_name}/pulls/{pr_number}",
            headers=headers, timeout=10,
        )
        r.raise_for_status()
        pr = r.json()
        return {
            "number":        pr["number"],
            "title":         pr["title"],
            "author":        pr["user"]["login"],
            "url":           pr["html_url"],
            "head":          pr["head"]["ref"],
            "base":          pr["base"]["ref"],
            "body":          pr.get("body") or "",
            "changed_files": pr.get("changed_files", 0),
            "created_at":    pr.get("created_at"),
        }
    try:
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/pr/review")
async def review_pr_endpoint(body: PRReviewBody):
    try:
        review_text = await asyncio.to_thread(_pr.review_pr, body.repo, body.pr_number)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PR review failed: {e}")
    try:
        await asyncio.to_thread(
            _slack.send_message,
            f"🤖 PR Review — {body.repo} #{body.pr_number}\n\n"
            + review_text[:800] + ("..." if len(review_text) > 800 else ""),
        )
    except Exception:
        pass
    return {"repo": body.repo, "pr_number": body.pr_number, "review": review_text}

# ── /api-tests ─────────────────────────────────────────────────────────────────

class CreateJiraBugsBody(BaseModel):
    project_key: str = "OMS"
    bugs: list[dict]

class ApiTestRunBody(BaseModel):
    scope: str = "all"
    single_endpoint: str = ""

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


@app.get("/api-tests/results")
async def get_api_test_results():
    try:
        data = await asyncio.to_thread(_jest.get_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if data is None:
        return {"available": False, "message": "No results found. Run the test suite first."}

    # Jest --json stores pre-computed totals at the top level
    passed  = data.get("numPassedTests", 0)
    failed  = data.get("numFailedTests", 0)
    skipped = data.get("numPendingTests", 0)
    total   = data.get("numTotalTests", 0) or (passed + failed + skipped)
    pass_rate = round(passed / total * 100) if total else 0

    ts = data.get("startTime")
    run_at = (datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
              if ts else None)

    dim = {
        "perf":  {"pass": 0, "fail": 0},
        "auth":  {"pass": 0, "fail": 0},
        "valid": {"pass": 0, "fail": 0},
        "sec":   {"pass": 0, "fail": 0},
    }
    failures   = []
    suites_out = []

    # Each suite uses "name" for the file path and "assertionResults" for tests
    for suite in data.get("testResults", []):
        suite_file = suite.get("name", "").split("/")[-1]
        suite_tests = []

        for t in suite.get("assertionResults", []):
            ancestors = t.get("ancestorTitles") or []
            leaf      = t.get("title") or ""
            display   = " › ".join(ancestors + [leaf]) if ancestors else leaf

            status   = t.get("status", "")
            duration = t.get("duration")
            msgs     = t.get("failureMessages") or []
            error    = _ANSI_RE.sub("", msgs[0]).strip()[:200] if msgs else None

            # Dimension tag lives in fullName (concatenation of ancestor describe blocks)
            full_up = (t.get("fullName") or "").upper()
            if   "[PERF]"  in full_up: tag = "perf"
            elif "[AUTH]"  in full_up: tag = "auth"
            elif "[VALID]" in full_up: tag = "valid"
            elif "[SEC]"   in full_up: tag = "sec"
            else:                      tag = None
            if tag:
                if status == "passed":   dim[tag]["pass"] += 1
                elif status == "failed": dim[tag]["fail"] += 1

            if status == "failed":
                failures.append({"title": display, "suite": suite_file, "message": error or ""})

            suite_tests.append({
                "title":    display,
                "status":   status,
                "duration": duration,
                "error":    error,
            })

        suites_out.append({"file": suite_file, "tests": suite_tests})

    return {
        "available": True,
        "total":     total,
        "passed":    passed,
        "failed":    failed,
        "skipped":   skipped,
        "pass_rate": pass_rate,
        "run_at":    run_at,
        "perf":      dim["perf"],
        "auth":      dim["auth"],
        "valid":     dim["valid"],
        "sec":       dim["sec"],
        "failures":  failures,
        "suites":    suites_out,
    }


@app.get("/api-tests/sla")
async def get_api_test_sla():
    try:
        data = await asyncio.to_thread(_jest.get_sla)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    entries = []
    for k, v in data.items():
        if isinstance(v, dict):
            entries.append({"key": k, **v})
        else:
            entries.append({"key": k, "p95_baseline": None, "pass": None, "warn": None, "fail": None, "status": str(v)})
    return {"entries": entries}


@app.get("/api-tests/baseline")
async def get_api_test_baseline():
    try:
        md = await asyncio.to_thread(_jest.get_baseline_log)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"markdown": md}


@app.get("/api-tests/inventory")
async def get_api_test_inventory():
    try:
        items = await asyncio.to_thread(_jest.get_inventory)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"endpoints": items}


_GH_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


@app.post("/api-tests/run")
async def run_api_tests(body: ApiTestRunBody = None):
    if body is None:
        body = ApiTestRunBody()

    if not GITHUB_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="GITHUB_TOKEN not configured. Add it to the server environment to trigger remote test runs.",
        )

    headers = {**_GH_HEADERS, "Authorization": f"Bearer {GITHUB_TOKEN}"}
    trigger_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")

    def _dispatch():
        r = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW_FILE}/dispatches",
            json={
                "ref": "main",
                "inputs": {
                    # "single" is not a valid workflow choice; the workflow
                    # already gates on single_endpoint first, so "all" is correct.
                    "scope": "all" if body.single_endpoint else body.scope,
                    "single_endpoint": body.single_endpoint or "",
                },
            },
            headers=headers,
            timeout=15,
        )
        if r.status_code not in (204, 200):
            raise HTTPException(status_code=502, detail=f"GitHub dispatch failed ({r.status_code}): {r.text}")

    await asyncio.to_thread(_dispatch)

    # Poll up to 30 s for the triggered run to appear
    run_id = None
    run_url = None
    for _ in range(15):
        await asyncio.sleep(2)
        def _poll():
            return requests.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs"
                "?event=workflow_dispatch&per_page=5",
                headers=headers,
                timeout=15,
            ).json()
        data = await asyncio.to_thread(_poll)
        for run in data.get("workflow_runs", []):
            # created_at looks like "2024-01-01T12:34:56Z"; trigger_time is "2024-01-01T12:34"
            if run.get("created_at", "")[:16] >= trigger_time:
                run_id = run["id"]
                run_url = run["html_url"]
                break
        if run_id:
            break

    return {"status": "triggered", "run_id": run_id, "run_url": run_url}


@app.get("/api-tests/run-status/{run_id}")
async def get_run_status(run_id: int):
    if not GITHUB_TOKEN:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN not configured.")

    headers = {**_GH_HEADERS, "Authorization": f"Bearer {GITHUB_TOKEN}"}

    def _fetch():
        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs/{run_id}",
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    try:
        run = await asyncio.to_thread(_fetch)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "status":     run.get("status"),       # queued | in_progress | completed
        "conclusion": run.get("conclusion"),   # success | failure | null
        "run_url":    run.get("html_url"),
        "started_at": run.get("run_started_at"),
        "updated_at": run.get("updated_at"),
    }


@app.post("/api-tests/upload-results")
async def upload_results(file: UploadFile = File(...)):
    dest = _DATA_DIR / "results.json"
    dest.write_bytes(await file.read())
    return {"ok": True, "path": str(dest)}


@app.post("/api-tests/upload-sla")
async def upload_sla(file: UploadFile = File(...)):
    dest = _DATA_DIR / "sla-config.json"
    dest.write_bytes(await file.read())
    return {"ok": True, "path": str(dest)}


@app.post("/api-tests/upload-inventory")
async def upload_inventory(file: UploadFile = File(...)):
    dest = _DATA_DIR / "inventory.json"
    dest.write_bytes(await file.read())
    return {"ok": True, "path": str(dest)}


@app.post("/api-tests/upload-baseline")
async def upload_baseline(file: UploadFile = File(...)):
    dest = _DATA_DIR / "baseline-runs.json"
    dest.write_bytes(await file.read())
    return {"ok": True, "path": str(dest)}


@app.post("/api-tests/upload-perf-metrics")
async def upload_perf_metrics(file: UploadFile = File(...)):
    dest = _DATA_DIR / "perf-metrics.json"
    dest.write_bytes(await file.read())
    return {"ok": True, "path": str(dest)}


@app.get("/api-tests/perf-metrics")
async def get_api_test_perf_metrics():
    try:
        data = await asyncio.to_thread(_jest.get_perf_metrics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return data or []


# ── /ai/chat ──────────────────────────────────────────────────────────────────

def get_live_db_data():
    if time.time() - _db_cache['ts'] < 300:
        return _db_cache['data']
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.getenv('PRODUCTION_DB_HOST'),
            port=int(os.getenv('PRODUCTION_DB_PORT', 3306)),
            user=os.getenv('PRODUCTION_DB_USER'),
            password=os.getenv('PRODUCTION_DB_PASSWORD'),
            database=os.getenv('PRODUCTION_DB_NAME')
        )
        cursor = conn.cursor()

        def q(sql):
            try:
                cursor.execute(sql)
                result = cursor.fetchall()
                return result[0][0] if result else 0
            except Exception:
                return 0

        orders_today = q('SELECT COUNT(*) FROM orders WHERE DATE(createdAt) = CURDATE()')
        total_orders = q('SELECT COUNT(*) FROM orders')
        pending_orders = q("SELECT COUNT(*) FROM orders WHERE status_value = 'Confirmation Pending'")
        total_stores = q('SELECT COUNT(*) FROM stores')
        total_agencies = q('SELECT COUNT(*) FROM agencies WHERE status = "approved"')
        total_tickets = q('SELECT COUNT(*) FROM tickets')
        tickets_today = q('SELECT COUNT(*) FROM tickets WHERE DATE(createdAt) = CURDATE()')

        cursor.execute('''SELECT cp.name, COUNT(*) as cnt
            FROM dispatch_batches db
            JOIN courier_partners cp ON db.fk_courier_id = cp.id
            WHERE DATE(db.createdAt) = CURDATE()
            GROUP BY cp.name ORDER BY cnt DESC LIMIT 3''')
        top_couriers = cursor.fetchall()
        couriers_text = ', '.join([f'{r[0]}: {r[1]} batches' for r in top_couriers]) if top_couriers else 'none'

        conn.close()

        live_data = f'''LIVE PRODUCTION DATA (cached 5 min):
- Orders today: {orders_today}
- Total orders ever: {total_orders}
- Pending confirmation: {pending_orders}
- Top couriers today: {couriers_text}
- Active stores: {total_stores}
- Approved agencies: {total_agencies}
- Total tickets: {total_tickets}
- Tickets today: {tickets_today}'''

        _db_cache['data'] = live_data
        _db_cache['ts'] = time.time()
        return live_data
    except Exception as e:
        print(f'[AI-CHAT-DB] {e}')
        return _db_cache['data']


@app.post("/ai/chat")
async def ai_chat(request: Request):
    from groq import Groq

    body = await request.json()
    message = body.get("message", "")

    msg_lower = message.lower()
    if "seller" in msg_lower:
        dirs = ["seller", "shared"]
    elif "agency" in msg_lower:
        dirs = ["agency", "shared"]
    else:
        dirs = ["oms", "shared"]

    kb = ""
    # Always load system_data first - most important factual data
    system_data_path = KNOWLEDGE_DIR / "shared" / "system_data.md"
    if system_data_path.exists():
        kb += system_data_path.read_text()[:3000]

    # Then load portal-specific files
    for d in dirs:
        path = KNOWLEDGE_DIR / d
        if path.exists():
            for f in sorted(path.glob("*.md")):
                kb += f.read_text()[:800]

    kb = kb[:8000]  # hard cap to stay under Groq free tier token limit

    live_data = get_live_db_data()

    system = f"""You are a senior Zambeel platform expert who knows everything about this system. Answer questions directly and confidently. Never say 'I don't have access' or 'I cannot determine' — you have the knowledge base and live DB data below. Give specific, direct answers. If the answer is in the data provided, state it as fact. Be concise and professional like a senior colleague answering a quick question.

Zambeel repos:
- Frontend: https://github.com/MyZambeel/zambeel-FE
- Backend: https://github.com/MyZambeel/zambeel-api
- SQA Agent: https://github.com/SarymSikander/sqa-agent

Portals:
- Admin/OMS staging: https://staging.myzambeel.com
- Admin/OMS production: https://portal.myzambeel.com

{live_data}

KNOWLEDGE BASE:
{kb}"""

    try:
        groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        response = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': message}],
            max_tokens=1000
        )
        answer = response.choices[0].message.content
    except Exception as groq_err:
        if '429' in str(groq_err) or 'rate' in str(groq_err).lower():
            from openai import OpenAI
            fallback = OpenAI(base_url='https://models.inference.ai.azure.com', api_key=os.getenv('GITHUB_TOKEN'))
            response = fallback.chat.completions.create(
                model='gpt-4o',
                messages=[{'role': 'system', 'content': system[:3000]}, {'role': 'user', 'content': message}],
                max_tokens=1000
            )
            answer = response.choices[0].message.content
        else:
            raise
    return {"answer": answer}


@app.post("/api-tests/create-jira-bugs")
async def create_api_test_jira_bugs(body: CreateJiraBugsBody):
    created, errors = [], []
    for bug in body.bugs:
        try:
            key = await asyncio.to_thread(
                _jira.create_ticket,
                body.project_key,
                bug.get("summary", "API Test Failure"),
                "Bug",
                bug.get("description", ""),
            )
            created.append({"key": key, "summary": bug.get("summary")})
        except Exception as e:
            errors.append({"summary": bug.get("summary"), "error": str(e)})
    return {"created": created, "errors": errors}

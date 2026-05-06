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

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
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

# Load knowledge base — concatenate all knowledge/*.md files, fall back to app_context.md
def _load_knowledge_base() -> str:
    """Load all knowledge base markdown files and concatenate them into one context string."""
    # Search for knowledge/ directory relative to this file or repo root
    _candidates = [
        Path(__file__).resolve().parent / "knowledge",
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

class AuthRefreshBody(BaseModel):
    portal: str
    env: str

class AuthUploadBody(BaseModel):
    portal: str
    env: str
    auth_storage_value: str

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
    if os.path.exists("/app/auth"):
        return {"source": "/app/auth", "files": os.listdir("/app/auth")}
    return {"source": "/app", "files": os.listdir("/app")}

# ── /health ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    import os as _os
    app_contents = _os.listdir("/app") if _os.path.exists("/app") else None
    auth_contents = _os.listdir("/app/auth") if _os.path.exists("/app/auth") else None
    return {"status": "ok", "app_dir": app_contents, "auth_dir": auth_contents}


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

@app.post("/auth/refresh")
async def auth_refresh(body: AuthRefreshBody):
    portal = body.portal.lower()
    env    = body.env.lower()
    if portal not in {"seller", "admin", "agency"}:
        raise HTTPException(status_code=400, detail="portal must be seller, admin, or agency")
    if env not in {"local", "staging", "production"}:
        raise HTTPException(status_code=400, detail="env must be local, staging, or production")
    auth_path = _HERE / "auth" / f"{portal}_{env}.json"
    if not auth_path.exists():
        raise HTTPException(status_code=404, detail=f"Auth file not found: {portal}_{env}.json")
    try:
        return {"portal": portal, "env": env, "auth": json.loads(auth_path.read_text())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

_ENV_ORIGINS = {
    "local":      "http://localhost:5173",
    "staging":    "https://staging.myzambeel.com",
    "production": "https://portal.myzambeel.com",
}

@app.post("/auth/upload")
async def auth_upload(body: AuthUploadBody):
    portal = body.portal.lower()
    env    = body.env.lower()
    if portal not in {"seller", "admin", "agency"}:
        raise HTTPException(status_code=400, detail="portal must be seller, admin, or agency")
    if env not in {"local", "staging", "production"}:
        raise HTTPException(status_code=400, detail="env must be local, staging, or production")
    try:
        inner = json.loads(body.auth_storage_value)
        if not (inner.get("state") or {}).get("authToken"):
            raise HTTPException(status_code=400, detail="auth_storage_value must contain state.authToken")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in auth_storage_value: {e}")
    auth_doc = {
        "origins": [{
            "origin": _ENV_ORIGINS[env],
            "localStorage": [{"name": "auth-storage", "value": body.auth_storage_value}],
        }],
    }
    auth_dir = _HERE / "auth"
    auth_dir.mkdir(exist_ok=True)
    auth_path = auth_dir / f"{portal}_{env}.json"
    try:
        auth_path.write_text(json.dumps(auth_doc, indent=2))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    print(f"[auth/upload] Saved {auth_path.name} ({auth_path.stat().st_size} bytes)")
    return {"success": True, "file": f"{portal}_{env}.json", "portal": portal, "env": env}

@app.get("/auth/status")
def auth_status():
    auth_dir = _HERE / "auth"
    sessions = []
    for portal in ("seller", "admin", "agency"):
        for env in ("staging", "production"):
            path   = auth_dir / f"{portal}_{env}.json"
            exists = path.exists()
            sessions.append({
                "portal":   portal,
                "env":      env,
                "file":     f"{portal}_{env}.json",
                "exists":   exists,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat() if exists else None,
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


def generate_test_cases(ticket_key, title, description):
    import re

    relevant_context = _extract_relevant_context(title, description)

    # Extract keywords for source scan
    stopwords = {"that", "this", "with", "from", "have", "will", "been", "they",
                 "when", "what", "which", "where", "then", "also", "should", "would"}
    keywords = list(
        set(re.findall(r'\b\w{4,}\b', f"{title} {description}".lower())) - stopwords
    )[:25]
    selectors_context = extract_selectors_from_source(keywords)
    print(f"[generate_test_cases] selectors_context ({len(selectors_context)} chars)")

    prompt = (
        "You have access to a COMPLETE KNOWLEDGE BASE about the Zambeel platform extracted directly from source code.\n"
        "The knowledge base is provided in the 'Relevant app context' section below.\n\n"
        "KNOWLEDGE BASE USAGE RULES:\n"
        "- Use knowledge/oms/selectors.md for EXACT OMS selectors — never guess button text.\n"
        "- Use knowledge/seller/selectors.md for EXACT seller portal selectors.\n"
        "- Use knowledge/agency/selectors.md for EXACT agency portal selectors.\n"
        "- Use knowledge/oms/flows.md for step-by-step OMS flows — follow them exactly.\n"
        "- Use knowledge/seller/flows.md for step-by-step seller flows.\n"
        "- Use knowledge/agency/flows.md for step-by-step agency flows.\n"
        "- Use knowledge/shared/test_rules.md for global rules that apply to ALL tests.\n"
        "- Use knowledge/*/test_patterns.md for proven working test patterns to model your output on.\n\n"
        "CRITICAL SELECTOR RULES FOR ZAMBEEL:\n"
        "1. Never use WAIT: [role='option'] — skip this pattern entirely.\n"
        "2. After clicking a dropdown trigger, go straight to CLICK_OPTION — no waiting needed.\n"
        "3. Never check disabled state using CSS pseudo-classes like :disabled — use class-based selectors only if you can confirm the exact CSS class from context.\n"
        "4. After clicking Save/Submit/Confirm buttons, always add ASSERT_EXISTS with the expected result text to verify success.\n"
        "5. Country options for Zambeel are only: Bahrain, Iraq, Kuwait, Oman, Pakistan, Qatar, Saudi Arabia, UAE.\n"
        "6. After clicking Save and the modal closes, wait for the listing to update before asserting.\n"
        "7. Keep test cases simple — test what the ticket describes, not edge cases around UI state.\n"
        "8. Never generate a test case that checks if Save Model button is disabled after BOTH Country AND Type have been selected — at that point the number input auto-fills with 0 which is valid, so the button will be enabled. Only check disabled state when Country OR Type is still unselected.\n"
        "9. The number input for commission value has NO placeholder text — always use input[type=\"number\"] never input[placeholder=\"...\"] for the value field.\n"
        "10. Model name input placeholder is EXACTLY 'Enter model name' — never 'Enter Name', 'Name', or 'Model Name'.\n"
        "11. After CLICK: button:has-text('+ New Model'), always add WAIT: input[placeholder='Enter model name'] before any other modal steps.\n"
        "12. Never click a Country or Type dropdown trigger — use CLICK_OPTION: value directly. The selects are native HTML and select_option works without opening them.\n"
        "13. Commission Type values are ONLY '% of Revenue' or 'Flat per Order' — never 'Flat Rate', 'Percentage', or any other value.\n"
        "14. CRITICAL HAPPY FLOW — Save Model button enables as soon as Country is selected. Type and Value fields are NOT required to enable Save Model. Do NOT add steps that check Save is still disabled after filling only some fields.\n"
        "15. There is NO confirmation message or toast after clicking Save Model. Never assert text='Commission model saved successfully.' or any success toast. After Save Model is clicked and the modal closes, assert the model name appears in the listing table: ASSERT_EXISTS: text='<the model name you filled in>'.\n"
        "16. Currency is auto-populated when Country is selected — never add a step to fill or click the Currency field.\n"
        "17. The correct happy flow steps are: NAVIGATE → CLICK + New Model → WAIT modal → FILL model name → CLICK_OPTION country → CLICK Save Model → ASSERT_EXISTS model name in table.\n"
        "18. Never wrap FILL values or CLICK_OPTION values in quotes in the step string. Write FILL: selector | ModelName not FILL: selector | 'ModelName'. Write CLICK_OPTION: Saudi Arabia not CLICK_OPTION: 'Saudi Arabia'.\n"
        "19. Never use ASSERT_NOT_EXISTS to check that a dropdown option is absent — option text like 'Flat Rate' may appear anywhere in the page body and cause false failures. Only use ASSERT_EXISTS to confirm options that ARE present.\n"
        "20. To verify Save Model button is enabled after country selection, use ASSERT_EXISTS: button.bg-indigo-600:has-text('Save Model') — do not use :not(:disabled) or any pseudo-class.\n"
        "21. Never generate a test case for 'prevent duplicate country' by selecting the same country twice on the same select — that is a no-op. To add a second country row you must first CLICK: button:has-text('+ Add Rule'). Do not generate duplicate-country tests unless you can confirm the exact validation message from context.\n"
        "22. Never guess validation or error message text. Only use ASSERT_EXISTS for text that is explicitly stated in the ticket description, acceptance criteria, or the knowledge base selectors/flows files.\n\n"
        "CRITICAL: This React app has NO element IDs. Use ONLY these selector formats:\n"
        "- button:has-text(\"exact text\") for buttons\n"
        "- input[placeholder=\"exact placeholder\"] for inputs\n"
        "- text=\"exact visible text\" for any element by its text\n"
        "- div[role=\"dialog\"] for modals\n"
        "- Never use #id selectors. All selectors must come from the knowledge base or REAL UI ELEMENTS section below.\n\n"
        "You are an expert QA engineer for Zambeel, a B2B e-commerce platform.\n"
        "You write Playwright test scripts in Python that actually execute in a browser.\n\n"
        f"Ticket: {ticket_key}\n"
        f"Title: {title}\n"
        f"Description: {description}\n\n"
        f"Relevant app context (includes full knowledge base):\n{relevant_context}\n\n"
        f"{selectors_context}\n\n"
        "Generate 3-5 test cases as JSON. Each test case must have:\n"
        "- test_name: string\n"
        "- url_path: exact URL path to navigate to (e.g. /orders-management/dashboard)\n"
        "- portal: which portal to test (admin/seller/agency)\n"
        "- steps: array of Playwright actions as strings, each starting with one of:\n"
        "  CLICK: css-selector\n"
        "  FILL: css-selector | value\n"
        "  WAIT: css-selector\n"
        "  NAVIGATE: /path\n"
        "  ASSERT_EXISTS: css-selector\n"
        "  ASSERT_NOT_EXISTS: css-selector\n"
        "  ASSERT_TEXT: css-selector | expected text\n"
        "  SCREENSHOT: label\n"
        "- expected_result: what success looks like\n"
        "- evidence_selector: ONE valid CSS selector that proves the feature works\n\n"
        "IMPORTANT: This is a React app that uses Tailwind CSS and rarely uses IDs. "
        "Use ONLY these selector types: button:has-text(\"exact button text\"), "
        "input[placeholder=\"exact placeholder\"], text=\"exact visible text\", "
        ".className patterns from the source code provided. "
        "Never use #id selectors unless you see them explicitly in the source code provided.\n"
        "Return ONLY valid JSON: {\"test_cases\": [...]}"
    )

    try:
        client = OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=os.getenv("GITHUB_TOKEN"),
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
        )
        output = (response.choices[0].message.content or "").strip()
        print(f"[generate_test_cases] gpt-4o output ({len(output)} chars): {output[:500]}")

        # Strip markdown code fences
        code_match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", output, re.DOTALL)
        if code_match:
            output = code_match.group(1)

        parsed = json.loads(output)

        if isinstance(parsed, list):
            raw_cases = parsed
        elif isinstance(parsed, dict) and "test_cases" in parsed:
            raw_cases = parsed["test_cases"]
        else:
            print(f"[generate_test_cases] Unexpected JSON shape: {type(parsed)}")
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
            valid.append(tc)

        ZAMBEEL_SELECTOR_FIXES = [
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
            # ASSERT_NOT_EXISTS on option text is unreliable — the text may appear in the page body
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
        ]

        # Apply Zambeel selector fixes to all generated test case steps
        for tc in valid:
            tc['steps'] = [
                next((s.replace(wrong, right) for wrong, right in ZAMBEEL_SELECTOR_FIXES if wrong in s), s)
                for s in tc.get('steps', [])
            ]

        print(f"[generate_test_cases] Parsed {len(valid)} valid test cases")
        return valid

    except Exception as e:
        print(f"[generate_test_cases] ERROR: {e}")
        return []


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

        # ── Stage: generate test cases ─────────────────────────────────────────
        yield evt({"stage": "generating_test_cases", "status": "running"})
        yield f": keepalive\n\n"
        test_cases = await asyncio.to_thread(generate_test_cases, issue_key, summary, description)
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

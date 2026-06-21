import asyncio
import json
import os
import queue as _stdlib_queue
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

# Pending clarification queues keyed by run_id — set/awaited inside run_qa SSE generator
_clarification_store: dict[str, asyncio.Queue] = {}

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
_AUTH_EXEMPT_PREFIXES = ("/api-tests/", "/screenshots/")
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
REPORTS_DIR = _HERE / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# HF Docker spaces persist only /data — use it for both screenshots and reports.
_DATA_DIR = Path("/data")
try:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR = _DATA_DIR / "screenshots"
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
except OSError:
    _DATA_DIR = REPORTS_DIR
    SCREENSHOTS_DIR = _HERE / "screenshots"
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

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


# ── Semantic KB index for /ai/chat ────────────────────────────────────────────
import math as _math
import re as _re_kb

_STOPWORDS = {
    'a','an','the','is','are','was','were','be','been','being',
    'have','has','had','do','does','did','will','would','could',
    'should','may','might','shall','can','need','to','of','in',
    'on','at','by','for','with','about','as','into','through',
    'from','up','down','and','or','but','if','then','that','this',
    'these','those','it','its','i','we','you','he','she','they',
    'them','their','there','what','which','who','how','when',
    'where','why','all','any','both','each','more','most','other',
    'some','such','no','not','only','own','same','so','than','too',
    'very','just','because','while','also','are','its','get',
}

_KB_CHUNKS: list[dict] = []
_KB_IDF: dict[str, float] = {}


def _kb_tokenize(text: str) -> set:
    return {w for w in _re_kb.findall(r'[a-z0-9_]+', text.lower())
            if w not in _STOPWORDS and len(w) > 2}


def _build_kb_index():
    global _KB_CHUNKS, _KB_IDF
    chunks = []
    kb_dir = KNOWLEDGE_DIR
    if not kb_dir.exists():
        return
    for fpath in sorted(kb_dir.rglob("*.md")):
        rel = str(fpath.relative_to(kb_dir))
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Split on ## headings (keep the heading with its section body)
        sections = _re_kb.split(r'\n(?=#{1,2} )', text)
        for sec in sections:
            sec = sec.strip()
            if len(sec) < 80:
                continue
            heading = sec.split('\n')[0].strip('#').strip()
            chunks.append({
                "file": rel,
                "title": heading or rel,
                "text": sec,
                "tokens": _kb_tokenize(sec),
            })
    # Compute IDF
    df: dict = {}
    for c in chunks:
        for t in c["tokens"]:
            df[t] = df.get(t, 0) + 1
    n = max(len(chunks), 1)
    idf = {t: _math.log(n / (d + 1)) for t, d in df.items()}
    _KB_CHUNKS = chunks
    _KB_IDF = idf
    print(f"[startup] KB semantic index: {len(_KB_CHUNKS)} chunks across {len(set(c['file'] for c in _KB_CHUNKS))} files")


_build_kb_index()


def _retrieve_kb(query: str, top_k: int = 5, char_limit: int = 7000) -> str:
    """Return the top_k most relevant KB sections for query, capped at char_limit chars."""
    # Always anchor with system_data (factual ground truth), capped at 2000 chars
    result_parts: list[str] = []
    sd_path = KNOWLEDGE_DIR / "shared" / "system_data.md"
    if sd_path.exists():
        sd_text = sd_path.read_text(encoding="utf-8", errors="ignore")[:2000]
        result_parts.append(f"[shared/system_data.md]\n{sd_text}")

    char_used = sum(len(p) for p in result_parts)

    if not _KB_CHUNKS:
        return "\n\n---\n\n".join(result_parts) or APP_CONTEXT[:char_limit]

    query_tokens = _kb_tokenize(query)
    if not query_tokens:
        return "\n\n---\n\n".join(result_parts)

    # Score every chunk by sum of IDF weights for matching terms
    scored: list[tuple[float, int]] = []
    for i, chunk in enumerate(_KB_CHUNKS):
        overlap = query_tokens & chunk["tokens"]
        if not overlap:
            continue
        score = sum(_KB_IDF.get(t, 0.0) for t in overlap)
        scored.append((score, i))

    scored.sort(reverse=True)

    seen = {"shared/system_data.md"}
    retrieved = 0
    for _score, idx in scored[:top_k * 3]:
        if retrieved >= top_k:
            break
        chunk = _KB_CHUNKS[idx]
        # Skip exact duplicate file already included as system_data
        if chunk["file"] in seen and chunk["file"] == "shared/system_data.md":
            continue
        label = f"[{chunk['file']} — {chunk['title']}]"
        entry = f"{label}\n{chunk['text']}"
        if char_used + len(entry) > char_limit:
            budget = char_limit - char_used - len(label) - 4
            if budget > 200:
                result_parts.append(f"{label}\n{chunk['text'][:budget]}…")
                char_used += len(result_parts[-1])
            break
        result_parts.append(entry)
        char_used += len(entry)
        retrieved += 1

    return "\n\n---\n\n".join(result_parts)


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

# Keep playwright_tool's SCREENSHOTS_DIR in sync with main.py's resolved path
# so screenshots always land in the same directory served by StaticFiles.
_playwright.SCREENSHOTS_DIR = str(SCREENSHOTS_DIR)

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
    confirmed_pages: Optional[list[str]] = None

class ClarifyBody(BaseModel):
    run_id: str
    answer: str

# ── /qa/clarify ───────────────────────────────────────────────────────────────

@app.post("/qa/clarify")
async def qa_clarify(body: ClarifyBody):
    """Receive user's answer to a clarification question raised during a QA run."""
    q = _clarification_store.get(body.run_id)
    if q is None:
        raise HTTPException(status_code=404, detail="No pending clarification for this run_id")
    await q.put(body.answer)
    return {"ok": True}

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
        r = result if isinstance(result, dict) else {}
        results.append({
            "portal": portal,
            "env": body.env,
            "status": status,
            "message": r.get("message", "") or str(result),
            "url": r.get("url"),
            "console_errors": r.get("console_errors", []),
            "nav_elements_found": r.get("nav_elements_found", []),
            "load_time_ms": r.get("load_time_ms"),
            "screenshots": [
                {**s, "url": f"/screenshots/{s['filename']}"}
                for s in r.get("screenshots", []) if s.get("filename")
            ],
            "execution_log": r.get("execution_log", []),
            "feature_evidence": r.get("feature_evidence", []),
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

@app.get("/jira/portal-pages/{portal}")
async def get_portal_pages(portal: str):
    """Return all known pages for a portal derived from _ROUTE_KEYWORDS."""
    route_map = _ROUTE_KEYWORDS.get(portal.lower(), {})
    pages = []
    for path in route_map:
        last_seg = path.rstrip("/").rsplit("/", 1)[-1]
        label = last_seg.replace("-", " ").title()
        pages.append({"path": path, "label": label})
    return {"pages": pages}


@app.get("/jira/suggest-pages/{issue_key}")
async def suggest_pages(issue_key: str, portal: str = "admin"):
    """Return AI-suggested pages for this ticket + portal combination."""
    try:
        ticket   = await asyncio.to_thread(_jira.get_ticket, issue_key)
        fields   = ticket.get("fields", {})
        summary  = fields.get("summary", "")
        desc_raw = fields.get("description")
        description = _adf_to_text(desc_raw) if isinstance(desc_raw, (dict, list)) else (desc_raw or "")
        suggested = await asyncio.to_thread(
            _identify_pages_from_ticket, summary, description, portal
        )
        return {"suggested_pages": suggested or []}
    except Exception as e:
        return {"suggested_pages": [], "error": str(e)}


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


def extract_selectors_from_github(keywords: list, repo_api_name: str = None) -> str:
    """Search GitHub source for real UI elements matching the given keywords.

    Uses the GitHub Code Search API so it works on HuggingFace (no local checkout needed).
    Returns a formatted string in the same style as extract_selectors_from_source.
    Returns "" on any error (missing token, rate-limit, etc.) — never crashes callers.
    """
    import re as _re_gh
    import base64 as _b64
    import concurrent.futures

    repo = repo_api_name or REPO_API_NAMES.get("frontend", "")
    if not repo:
        print("[extract_selectors_from_github] GITHUB_FRONTEND_REPO_API not configured — skipping")
        return ""
    if not GITHUB_TOKEN:
        print("[extract_selectors_from_github] GITHUB_TOKEN not configured — skipping")
        return ""

    kw_set = {w.lower() for w in keywords if len(w) >= 3}
    if not kw_set:
        return ""

    def _fetch():
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
        }
        # Build search query — join first 5 keywords with OR
        query_terms = list(kw_set)[:5]
        q = " OR ".join(query_terms) + f"+repo:{repo}+language:TypeScript+language:JavaScript"
        search_url = f"https://api.github.com/search/code?q={q}&per_page=5"
        try:
            r = requests.get(search_url, headers=headers, timeout=10)
            r.raise_for_status()
            items = r.json().get("items", [])
        except Exception as e:
            print(f"[extract_selectors_from_github] search error: {e}")
            return ""

        matches: list = []
        for item in items[:3]:
            file_path = item.get("path", "")
            contents_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
            try:
                cr = requests.get(contents_url, headers=headers, timeout=10)
                cr.raise_for_status()
                raw_b64 = cr.json().get("content", "")
                content = _b64.b64decode(raw_b64.replace("\n", "")).decode("utf-8", errors="ignore")
            except Exception as e:
                print(f"[extract_selectors_from_github] fetch {file_path} error: {e}")
                continue

            if not any(kw in content.lower() for kw in kw_set):
                continue

            matches.append(f"[File: {file_path}]")
            for m in _re_gh.finditer(r"<[Bb]utton[^>]*>\s*([^<{]{1,60})\s*</[Bb]utton>", content):
                txt = m.group(1).strip()
                if txt:
                    matches.append(f"Button: '{txt}'")
            for m in _re_gh.finditer(r'placeholder=["\']([^"\']{1,80})["\']', content):
                matches.append(f"Input placeholder: '{m.group(1)}'")
            for m in _re_gh.finditer(r"<label[^>]*>\s*([^<]{1,60})\s*</label>", content, _re_gh.IGNORECASE):
                txt = m.group(1).strip()
                if txt:
                    matches.append(f"Label: '{txt}'")
            for m in _re_gh.finditer(r"""path:\s*['"]([^'"]{2,80})['"]""", content):
                matches.append(f"Route: {m.group(1)}")
            for m in _re_gh.finditer(r"""to=['"](/[^'"]{1,80})['"]""", content):
                matches.append(f"Nav link: {m.group(1)}")
            for m in _re_gh.finditer(r'(?:data-testid|id)=["\']([^"\']{3,60})["\']', content):
                matches.append(f"ID/testid: #{m.group(1)}")
            for m in _re_gh.finditer(r'className=["\']([^"\']{4,60})["\']', content):
                cls = m.group(1).split()[0]
                if any(kw in cls.lower() for kw in kw_set):
                    matches.append(f"CSS class: .{cls}")
            for m in _re_gh.finditer(
                r'export\s+(?:default\s+)?(?:function|const)\s+([A-Z][A-Za-z0-9]+)', content
            ):
                matches.append(f"Component: {m.group(1)}")

        seen: set = set()
        unique = [x for x in matches if not (x in seen or seen.add(x))][:120]  # type: ignore
        if not unique:
            return ""
        result = "REAL SELECTORS FROM SOURCE (GitHub):\n" + "\n".join(unique)
        return result[:2000]

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_fetch)
        try:
            return future.result(timeout=15) or ""
        except concurrent.futures.TimeoutError:
            print("[extract_selectors_from_github] timed out after 15s — skipping")
            return ""
        except Exception as e:
            print(f"[extract_selectors_from_github] unexpected error: {e}")
            return ""


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


_API_BUG_KEYWORDS = {
    # HTTP / status codes
    "401", "403", "404", "500", "502", "503", "422",
    "returns 200", "returns 201", "status code", "http status",
    # REST / API concepts
    "api", "endpoint", "route", "request", "response", "payload",
    "rest", "graphql", "webhook", "curl",
    # Auth / security
    "auth middleware", "missing auth", "token", "bearer", "jwt",
    "rate limit", "throttl",
    # Network / server
    "timeout", "latency", "cors", "header", "content-type",
    "400 bad request", "validation error", "schema",
    # Backend data
    "database", "query", "migration", "null pointer", "server error",
    "stack trace", "exception",
}

_UI_OVERRIDE_KEYWORDS = {
    "button", "modal", "dropdown", "form", "table", "page", "ui",
    "display", "render", "layout", "css", "style", "click", "scroll",
    "component", "view", "screen", "dialog", "tooltip", "icon",
    "sidebar", "navbar", "menu", "tab", "accordion",
}


def is_api_bug_ticket(description: str, summary: str = "") -> bool:
    """Return True when the ticket is clearly about backend API behaviour.

    A ticket is classified as an API bug when:
    - At least one API-specific keyword appears in the combined text, AND
    - The UI override keywords do NOT outnumber API keywords
      (avoids misclassifying 'the login button returns 401' as pure API).
    """
    text = f"{summary} {description}".lower()
    api_hits = sum(1 for kw in _API_BUG_KEYWORDS if kw in text)
    ui_hits  = sum(1 for kw in _UI_OVERRIDE_KEYWORDS if kw in text)
    result   = api_hits >= 1 and api_hits > ui_hits
    print(f"[is_api_bug_ticket] api_hits={api_hits} ui_hits={ui_hits} → {result}")
    return result


_API_ENVS = {
    "local":      os.getenv("LOCAL_API_URL",      "http://localhost:3000"),
    "staging":    os.getenv("STAGING_API_URL",    "https://staging.myzambeel.com"),
    "production": os.getenv("PRODUCTION_API_URL", "https://portal.myzambeel.com"),
}


def generate_api_test_cases(ticket_key: str, title: str, description: str) -> list:
    """Use Groq to generate a list of HTTP test specs from a ticket description."""
    from groq import Groq
    import json as _json

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = (
        "You are a senior QA engineer writing API integration tests.\n\n"
        f"Jira ticket: {ticket_key}\n"
        f"Title: {title}\n"
        f"Description: {description}\n\n"
        "Generate a JSON array of HTTP test cases that directly verify the bug described above.\n"
        "Each test case must be an object with these fields:\n"
        "  test_name: string\n"
        "  description: string  # what is being verified\n"
        "  method: GET|POST|PUT|PATCH|DELETE\n"
        "  path: string  # e.g. /api/v1/orders  (no base URL)\n"
        "  headers: object  # e.g. {\"Authorization\": \"Bearer <token>\"} — use placeholder tokens\n"
        "  body: object|null  # request body if applicable\n"
        "  expected_status: integer  # HTTP status code that indicates success\n"
        "  expected_body_contains: string|null  # substring to look for in response body\n"
        "  should_not_contain: string|null  # substring that must NOT appear (for security checks)\n\n"
        "RULES:\n"
        "- Generate only test cases that directly test what the ticket describes.\n"
        "- 1-3 test cases max.\n"
        "- If the ticket is about a 401 / auth issue, include an unauthenticated request as one test.\n"
        "- For rate-limit tickets, include a test that fires the endpoint rapidly.\n"
        "- Do NOT test unrelated endpoints.\n"
        "- Output ONLY the JSON array, no markdown, no explanation.\n"
    )
    import concurrent.futures
    def _call_groq():
        for model in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-20b"):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=1024,
                )
                raw = resp.choices[0].message.content.strip()
                raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                specs = _json.loads(raw)
                if isinstance(specs, list):
                    print(f"[generate_api_test_cases] model={model} → {len(specs)} specs")
                    return specs
            except Exception as e:
                print(f"[generate_api_test_cases] model={model} error: {e}")
        return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_call_groq)
        try:
            return future.result(timeout=20)
        except concurrent.futures.TimeoutError:
            print("[generate_api_test_cases] timed out after 20s — returning empty")
            return []


def run_api_tests(api_specs, env="production"):
    """Execute each HTTP test spec with requests; return a list of result dicts."""
    import requests as _req

    base_url = _API_ENVS.get(env, _API_ENVS["staging"]).rstrip("/")
    results  = []

    for spec in api_specs:
        method   = spec.get("method", "GET").upper()
        path     = spec.get("path", "/")
        headers  = spec.get("headers") or {}
        body     = spec.get("body")
        exp_status = int(spec.get("expected_status", 200))
        must_have  = spec.get("expected_body_contains")
        must_not   = spec.get("should_not_contain")
        url = f"{base_url}{path}"

        try:
            resp = _req.request(
                method, url,
                headers=headers,
                json=body if body else None,
                timeout=15,
            )
            actual_status = resp.status_code
            body_text     = resp.text[:2000]

            status_ok  = (actual_status == exp_status)
            contain_ok = (must_have is None) or (must_have.lower() in body_text.lower())
            absent_ok  = (must_not  is None) or (must_not.lower()  not in body_text.lower())
            passed     = status_ok and contain_ok and absent_ok

            failures = []
            if not status_ok:
                failures.append(f"expected HTTP {exp_status}, got {actual_status}")
            if not contain_ok:
                failures.append(f"response missing expected text: {must_have!r}")
            if not absent_ok:
                failures.append(f"response contains forbidden text: {must_not!r}")

            results.append({
                "test_name":      spec.get("test_name", path),
                "description":    spec.get("description", ""),
                "url":            url,
                "method":         method,
                "status":         "PASS" if passed else "FAIL",
                "actual_status":  actual_status,
                "expected_status": exp_status,
                "failures":       failures,
                "response_snippet": body_text[:500],
            })
            print(f"[run_api_tests] {method} {url} → {actual_status} {'PASS' if passed else 'FAIL'}")
        except Exception as e:
            results.append({
                "test_name":      spec.get("test_name", path),
                "description":    spec.get("description", ""),
                "url":            url,
                "method":         method,
                "status":         "ERROR",
                "actual_status":  None,
                "expected_status": exp_status,
                "failures":       [str(e)],
                "response_snippet": "",
            })
            print(f"[run_api_tests] {method} {url} → ERROR: {e}")

    return results


def _resolve_page_portal(url_path: str, fallback: str = "seller") -> str:
    """Return the portal name (admin/seller/agency) that owns url_path via _ROUTE_KEYWORDS."""
    for portal_name, routes in _ROUTE_KEYWORDS.items():
        if url_path in routes:
            return portal_name
    return fallback


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


def _resolve_base_url(env: str) -> str:
    if env == 'staging':
        return os.getenv('STAGING_URL', 'https://staging.myzambeel.com').rstrip('/')
    if env == 'production':
        return os.getenv('PRODUCTION_URL', 'https://portal.myzambeel.com').rstrip('/')
    return os.getenv('LOCAL_URL', 'http://localhost:5173').rstrip('/')


def screenshot_page(portal, env, url_path):
    """Login, navigate to url_path, take an 800x600 screenshot, return base64."""
    from playwright.sync_api import sync_playwright
    import base64
    base_url = _resolve_base_url(env)
    full_url = f'{base_url}{url_path}'
    print(f'[screenshot_page] {portal}/{env} → {full_url}')
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 800, 'height': 600})
            _playwright.login_to_portal(page, portal, env)
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
    """Login, navigate to url_path, extract DOM + network calls, return structured data."""
    from playwright.sync_api import sync_playwright
    from urllib.parse import urlparse as _urlparse
    base_url = _resolve_base_url(env)
    full_url = f'{base_url}{url_path}'
    print(f'[extract_page_dom_live] {portal}/{env} → {full_url}')
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 900})

            # Register network listener before navigation so all calls are captured
            network_calls: list = []
            def _on_response(response):
                try:
                    if '/api/' in response.url:
                        parsed = _urlparse(response.url)
                        network_calls.append({
                            "method": response.request.method,
                            "path":   parsed.path,
                            "status": response.status,
                        })
                except Exception:
                    pass
            page.on("response", _on_response)

            _playwright.login_to_portal(page, portal, env)
            page.goto(full_url)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
            dom = extract_page_dom(page)
            browser.close()
        print(f'[extract_page_dom_live] done — buttons={len(dom["buttons"])} '
              f'inputs={len(dom["inputs"])} selects={len(dom["selects"])} '
              f'network_calls={len(network_calls)}')
        print(f'[DOM] buttons={dom["buttons"][:5]}, inputs={dom["inputs"][:3]}, selects={dom["selects"]}')
        return {
            'dom': dom, 'network_calls': network_calls,
            'portal': portal, 'env': env, 'url_path': url_path, 'url': full_url,
        }
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
    start = clean.find('{')
    end = clean.rfind('}')
    if start == -1 or end == -1:
        print(f'[_parse_test_cases] No JSON found in: {clean[:200]}')
        return []
    clean = clean[start:end + 1]
    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError as e:
        print(f'[_parse_test_cases] JSON error: {e}')
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


def generate_test_cases(ticket_key, title, description, screenshots: list = None, dom_context: list = None, user_notes: str = ""):
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

    # Extract keywords from ticket for GitHub source search (Part 3)
    import re as _re_kw
    _kw_raw = f"{title} {description}"
    _kw_stopwords = {
        'this', 'that', 'with', 'from', 'have', 'will', 'been', 'they', 'when',
        'what', 'which', 'where', 'then', 'also', 'should', 'would', 'could',
        'button', 'modal', 'table', 'page', 'click', 'scroll',
    }
    _keywords = list(dict.fromkeys(
        w for w in _re_kw.findall(r'[a-zA-Z]{4,}', _kw_raw)
        if w.lower() not in _kw_stopwords
    ))[:8]
    _github_selectors = extract_selectors_from_github(_keywords)
    print(f"[generate_test_cases] github_selectors={len(_github_selectors)} chars, keywords={_keywords[:5]}")

    if not screenshots:
        print(f"[generate_test_cases] no screenshots for {ticket_key} — skipping test generation")
        return []
    valid_shots = [s for s in screenshots if s.get("base64")]
    if not valid_shots:
        errors = [s.get("error", "no base64") for s in screenshots]
        raise RuntimeError(f"generate_test_cases: all screenshots failed — {errors}")
    print(f"[generate_test_cases] {len(valid_shots)} screenshot(s), "
          f"portal={portal_hint}, kb={len(knowledge_base):,} chars")

    pages_summary = ", ".join(s.get("url_path", s.get("url", "")) for s in valid_shots)

    # Build DOM context section (Part 2)
    _dom_section = ""
    if dom_context:
        _dom_parts = []
        for dc in dom_context:
            dom = dc.get("dom", {})
            nc  = dc.get("network_calls", [])
            url_p = dc.get("url_path", dc.get("url", ""))
            _dom_parts.append(
                f"Page: {url_p}\n"
                f"Buttons: {', '.join(dom.get('buttons', [])[:15])}\n"
                f"Inputs: {', '.join((i.get('placeholder') or i.get('name') or '') for i in dom.get('inputs', [])[:8])}\n"
                f"Headings: {', '.join(dom.get('headings', [])[:8])}\n"
                f"Network calls: {', '.join(c['method'] + ' ' + c['path'] for c in nc[:10])}"
            )
        _dom_section = (
            "LIVE DOM CONTEXT (extracted from actual page — use these as selector evidence):\n"
            + "\n---\n".join(_dom_parts)
            + "\n\n"
        )

    complexity_instruction = (
        f"Analyze this ticket and decide how many test cases are needed:\n"
        f"- Simple UI change (button rename, color, text): 1-2 test cases\n"
        f"- Single feature (add search filter, add pagination): 2-3 test cases\n"
        f"- Medium feature (new modal, new form): 3-4 test cases\n"
        f"- Complex feature (multi-step flow, state machine): 4-6 test cases\n"
        f"- Bug fix verification: 1-2 test cases\n\n"
        f"Ticket: {title}\n"
        f"Description: {description}\n\n"
        f"Generate ONLY the number of test cases actually needed. Do not pad with irrelevant tests."
    )

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
        + (_dom_section)
        + "Cross-reference the KNOWLEDGE BASE below to confirm exact selector text:\n"
        "1. Identify every relevant UI element — exact button labels, input placeholders, "
        "dropdown option text, heading text.\n"
        f"2. {complexity_instruction}\n"
        "For each selector, verify it exists in the KNOWLEDGE BASE. If it does not appear "
        "there, use text= with the exact visible text.\n"
        "3. Never invent placeholder text or button labels not present in the KNOWLEDGE BASE.\n\n"
        f"KNOWLEDGE BASE ({portal_hint} portal):\n"
        f"{knowledge_base}\n\n"
        + (f"REAL SELECTORS FROM GITHUB SOURCE:\n{_github_selectors}\n\n" if _github_selectors else "")
        + (f"USER CLARIFICATIONS:\n{user_notes}\n\n" if user_notes else "")
        + _TEST_CASE_JSON_SCHEMA
    )

    print(f"[generate_test_cases] prompt (first 500 chars): {prompt[:500]}")

    try:
        _groq_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "openai/gpt-oss-20b",
        ]
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
                print(f"[generate_test_cases] model={_model} succeeded ({len(output)} chars): {output[:500]}")
                break
            except Exception as _err:
                err_str = str(_err)
                is_rate_limit = (
                    "RateLimitError" in type(_err).__name__ or
                    "429" in err_str or
                    "rate_limit" in err_str.lower() or
                    "rate limit" in err_str.lower()
                )
                if is_rate_limit:
                    print(f"[generate_test_cases] model={_model} rate limited — trying next")
                    continue
                raise
        if not output:
            return [{"is_error": True, "test_name": "Error", "steps": [], "evidence_selector": "",
                     "error": "Groq daily limit reached on all models. Please try again in a few hours."}]
        return _parse_test_cases(output)
    except Exception as _top_err:
        print(f"[generate_test_cases] unexpected error: {_top_err}")
        return [{"is_error": True, "test_name": "Error", "steps": [], "evidence_selector": "",
                 "error": f"Test generation failed: {str(_top_err)[:200]}"}]


def _check_uncertain_steps(test_cases: list) -> list:
    """Return uncertain steps that need user clarification before execution.

    Detects: '?' in step text (AI uncertainty marker), or generic
    input[type='text'] selectors without a placeholder attribute.
    Returns a list of dicts: {tc_index, step_index, step, question}.
    """
    uncertain = []
    for tc_i, tc in enumerate(test_cases):
        for s_i, step in enumerate(tc.get("steps", [])):
            question = ""
            if "?" in step:
                question = (
                    f"Step has an uncertainty marker: `{step[:120]}`. "
                    f"Can you clarify which element to interact with in the '{tc.get('test_name', '')}' test?"
                )
            elif re.search(r"input\[type=['\"]text['\"]\](?!\s*\[placeholder)", step):
                question = (
                    f"I need to fill a text input but the selector `input[type='text']` is too "
                    f"generic (no placeholder). What is the exact placeholder text for this input "
                    f"in the '{tc.get('test_name', '')}' test? (step: `{step[:80]}`)"
                )
            if question:
                uncertain.append({"tc_index": tc_i, "step_index": s_i, "step": step, "question": question})
    return uncertain


def _check_page_confidence(
    ticket_title: str,
    ticket_description: str,
    portal: str,
    confirmed_pages: list,
    dom_results: list,
) -> list:
    """Return plain-English questions for pages where the DOM has no match to the ticket.

    Never mentions selectors, CSS, DOM, or code — questions are human-readable.
    """
    import re as _re_conf

    _stopwords = {
        'this', 'that', 'with', 'from', 'have', 'will', 'been', 'they', 'when',
        'what', 'which', 'where', 'then', 'also', 'should', 'would', 'could',
        'page', 'button', 'form', 'list', 'item', 'data', 'info', 'show',
        'does', 'dont', 'cant', 'wont', 'isnt', 'arent',
    }
    combined = f"{ticket_title} {ticket_description}".lower()
    key_terms = list(dict.fromkeys(
        w for w in _re_conf.findall(r'[a-z]{4,}', combined)
        if w not in _stopwords
    ))[:10]

    if not key_terms:
        return []

    # Build a lookup: url_path → dom dict from screenshots
    path_to_dom: dict = {}
    for shot in dom_results:
        if shot.get("dom") and shot.get("url_path"):
            path_to_dom[shot["url_path"]] = shot["dom"]

    questions = []
    for url_path in confirmed_pages:
        dom = path_to_dom.get(url_path)
        if not dom:
            continue  # no DOM data — can't judge confidence

        buttons  = [b.lower() for b in dom.get("buttons",  []) if b]
        headings = [h.lower() for h in dom.get("headings", []) if h]
        inputs   = [
            (i.get("placeholder") or i.get("name") or "").lower()
            for i in dom.get("inputs", [])
        ]
        all_text = " ".join(buttons + headings + inputs)

        if any(term in all_text for term in key_terms):
            continue  # at least one term found — confident

        top_term = key_terms[0]
        questions.append(
            f"I didn't find anything matching '{top_term}' on the page you selected "
            f"({url_path}). Is this the right page for this feature, or has the page "
            f"layout changed recently?"
        )

    return questions


def learn_from_run(test_cases: list, test_results: list):
    """Append newly-discovered working selectors to the relevant knowledge/selectors.md files
    and commit the changes to git."""
    import subprocess

    today = datetime.now().strftime("%Y-%m-%d")
    changed_files = []

    for result in test_results:
        portal = result.get("portal", "admin")
        portal_dir = {"admin": "oms", "seller": "seller", "agency": "agency"}.get(portal, "oms")
        selectors_file = KNOWLEDGE_DIR / portal_dir / "selectors.md"
        if not selectors_file.exists():
            continue

        existing = selectors_file.read_text()
        new_lines = []

        for entry in result.get("execution_log", []):
            step = entry.get("step", "")
            if entry.get("result", "").lower() != "pass":
                continue
            if not any(step.startswith(p) for p in ("CLICK:", "FILL:", "ASSERT_EXISTS:")):
                continue

            colon_idx = step.index(":")
            selector = step[colon_idx + 1:].strip()
            if "|" in selector:
                selector = selector.split("|")[0].strip()
            if not selector or len(selector) < 6:
                continue

            action = step[:colon_idx]
            if selector not in existing:
                new_lines.append(f"- `{selector}` — {action} (verified passing {today})")

        if not new_lines:
            continue

        if "## Learned from QA runs" not in existing:
            existing += "\n\n## Learned from QA runs\n"
        existing += f"\n### {today}\n" + "\n".join(new_lines) + "\n"
        selectors_file.write_text(existing)
        changed_files.append(selectors_file)
        print(f"[learn_from_run] {len(new_lines)} new selector(s) → {selectors_file.name}")

    if not changed_files:
        print("[learn_from_run] nothing new to commit")
        return

    cwd = str(KNOWLEDGE_DIR.parent)
    if not Path(cwd, '.git').exists():
        print("[learn_from_run] knowledge file(s) updated locally (no git repo — skipping commit)")
        return
    try:
        for f in changed_files:
            subprocess.run(["git", "add", str(f)], check=True, capture_output=True, cwd=cwd)
        subprocess.run(
            ["git", "commit", "-m", f"chore(knowledge): auto-learn selectors from QA run {today}"],
            check=True, capture_output=True, cwd=cwd,
        )
        print("[learn_from_run] committed to git")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        print(f"[learn_from_run] git error: {stderr}")


def learn_page_structure(portal: str, url_path: str, dom_data: dict, network_calls: list):
    """Append discovered page structure to the portal's selectors.md knowledge file."""
    import subprocess
    try:
        portal_dir = {"admin": "oms", "seller": "seller", "agency": "agency"}.get(portal, "oms")
        selectors_file = KNOWLEDGE_DIR / portal_dir / "selectors.md"
        if not selectors_file.exists():
            print(f"[learn_page_structure] {selectors_file} not found — skipping")
            return

        today = datetime.now().strftime("%Y-%m-%d")
        existing = selectors_file.read_text()

        section_header = f"### Page structure — {url_path} ({today})"
        if section_header in existing:
            print(f"[learn_page_structure] already recorded for {url_path} today")
            return

        buttons   = dom_data.get("buttons", [])[:20]
        inputs    = dom_data.get("inputs",  [])[:10]
        net_lines = [
            f"  {nc['method']} {nc['path']} → {nc['status']}"
            for nc in (network_calls or [])[:15]
        ]

        new_section = f"\n\n## Learned from QA runs\n" if "## Learned from QA runs" not in existing else ""
        new_section += f"\n{section_header}\n"
        if buttons:
            new_section += "Buttons: " + ", ".join(f"'{b}'" for b in buttons) + "\n"
        if inputs:
            _inp_strs = ["placeholder='" + i.get("placeholder", "") + "'" for i in inputs if i.get("placeholder")]
            new_section += "Inputs: " + ", ".join(_inp_strs) + "\n"
        if net_lines:
            new_section += "Network calls:\n" + "\n".join(net_lines) + "\n"

        selectors_file.write_text(existing + new_section)
        print(f"[learn_page_structure] appended structure for {url_path} → {selectors_file.name}")

        cwd = str(KNOWLEDGE_DIR.parent)
        if Path(cwd, '.git').exists():
            subprocess.run(["git", "add", str(selectors_file)], check=True, capture_output=True, cwd=cwd)
            subprocess.run(
                ["git", "commit", "-m", f"chore(knowledge): page structure for {url_path} ({today})"],
                check=True, capture_output=True, cwd=cwd,
            )
            print("[learn_page_structure] committed to git")
        else:
            print("[learn_page_structure] knowledge file updated locally (no git repo — skipping commit)")
    except Exception as e:
        print(f"[learn_page_structure] error (non-fatal): {e}")


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

        # ── Route: API bug vs UI bug ───────────────────────────────────────────
        _is_api_ticket = is_api_bug_ticket(description, summary)
        yield evt({"stage": "ticket_classified", "is_api_ticket": _is_api_ticket})
        print(f"[run_qa] ticket_type={'api' if _is_api_ticket else 'ui'} for {issue_key}")

        if _is_api_ticket:
            yield evt({"stage": "generating_api_tests", "status": "running"})

            # Extract endpoints directly from ticket description — no LLM needed
            import re as _re2
            import requests as _req2

            found_endpoints = list(dict.fromkeys(_re2.findall(r'/api/[\w/:\-]+', description)))[:8]
            print(f"[run_qa] API ticket — extracted endpoints: {found_endpoints}")

            api_base = _API_ENVS.get(body.env, _API_ENVS["production"]).rstrip("/")

            # Build test specs directly from what we found — no LLM
            api_specs = []
            for ep in found_endpoints:
                api_specs.append({
                    "test_name": f"{ep} — no auth should return 401",
                    "description": f"Unauthenticated request to {ep} must return 401",
                    "method": "GET",
                    "path": ep,
                    "headers": {},
                    "body": None,
                    "expected_status": 401,
                    "expected_body_contains": None,
                    "should_not_contain": None,
                })
                api_specs.append({
                    "test_name": f"{ep} — expired token should return 401",
                    "description": f"Expired token request to {ep} must return 401",
                    "method": "GET",
                    "path": ep,
                    "headers": {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.expired.token"},
                    "body": None,
                    "expected_status": 401,
                    "expected_body_contains": None,
                    "should_not_contain": None,
                })

            yield evt({"stage": "generating_api_tests", "status": "done", "count": len(api_specs)})
            yield evt({"stage": "running_tests", "status": "running"})

            api_results = await asyncio.to_thread(run_api_tests, api_specs, body.env)
            all_pass = bool(api_results) and all(r["status"] == "PASS" for r in api_results)

            # Map to the same shape the rest of the function expects
            test_results = [{
                "portal":             "api",
                "status":             ("PASS" if all_pass else "FAIL") if api_results else "ERROR",
                "message":            "; ".join(
                    f"{r['test_name']}: {', '.join(r['failures'])}"
                    for r in api_results if r["status"] != "PASS"
                ) or "All API tests passed",
                "url":                None,
                "console_errors":     [],
                "load_time_ms":       0,
                "nav_elements_found": [],
                "screenshots":        [],
                "execution_log":      [
                    {"step": r["test_name"], "result": r["status"].lower(),
                     "detail": f"{r['method']} {r['url']} → {r['actual_status']}; {'; '.join(r['failures'])}"}
                    for r in api_results
                ],
                "feature_evidence":   [],
                "steps_executed":     len(api_results),
                "api_results":        api_results,
            }]
            yield evt({
                "stage": "running_tests", "status": "done",
                "all_pass": all_pass,
                "api_results": api_results,
            })

            # Save API test specs as Jira comment
            try:
                lines = [f"*AI-Generated API Test Cases — {issue_key}* ({body.env.upper()})"]
                for i, spec in enumerate(api_specs, 1):
                    r = api_results[i - 1] if i <= len(api_results) else {}
                    icon = "PASS" if r.get("status") == "PASS" else "FAIL"
                    lines.append(
                        f"\n*{i}. {spec.get('test_name', spec.get('path', ''))}* [{icon}]\n"
                        f"_{spec.get('description', '')}_\n"
                        f"{spec.get('method', 'GET')} `{spec.get('path', '')}` "
                        f"→ expected {spec.get('expected_status')} "
                        f"/ got {r.get('actual_status', '?')}"
                    )
                await asyncio.to_thread(_jira.add_comment, issue_key, "\n".join(lines))
            except Exception:
                pass

            # ── Update Jira status ─────────────────────────────────────────────
            total_steps_executed = len(api_results)
            yield evt({"stage": "updating_jira", "status": "running"})
            try:
                if all_pass and total_steps_executed:
                    new_status = "Ready for Review"
                    await asyncio.to_thread(_jira.update_ticket_status, issue_key, new_status)
                    comment = (
                        f"QA Passed (API tests) — {body.env.upper()}\n"
                        + "\n".join(
                            f"- {r['method']} {r['url']} → {r['actual_status']} PASS"
                            for r in api_results
                        )
                    )
                    await asyncio.to_thread(_jira.add_comment, issue_key, comment)
                else:
                    new_status = "QA In Progress"
                    if api_results:
                        fail_lines = [
                            f"- {r['test_name']}: {', '.join(r['failures'])}"
                            for r in api_results if r["status"] != "PASS"
                        ]
                        comment = (
                            f"QA Failed (API tests) — {body.env.upper()}\n"
                            + "\n".join(fail_lines)
                        )
                        await asyncio.to_thread(_jira.add_comment, issue_key, comment)
                yield evt({"stage": "updating_jira", "status": "done", "new_status": new_status})
            except Exception as e:
                yield evt({"stage": "updating_jira", "status": "error", "message": str(e)})

            # ── Slack report for API ticket ───────────────────────────────────
            try:
                _api_results = test_results[0].get("api_results", []) if test_results else []
                _pass_count = sum(1 for r in _api_results if r.get("status") == "PASS")
                _fail_count = sum(1 for r in _api_results if r.get("status") != "PASS")
                _results_lines = "\n".join(
                    f"{'✅' if r.get('status') == 'PASS' else '❌'} `{r.get('method','GET')} {r.get('url','')}` → {r.get('actual_status','?')} ({'PASS' if r.get('status')=='PASS' else 'FAIL'})"
                    for r in _api_results
                )
                slack_msg = (
                    f"🤖 *QA Run Complete* — <https://zambeel.atlassian.net/browse/{issue_key}|{issue_key}>\n"
                    f"*{summary}*\n\n"
                    f"*Type:* API Security Tests\n"
                    f"*Environment:* `{body.env.upper()}`\n\n"
                    f"*Results:* {_pass_count} passed · {_fail_count} failed\n"
                    f"{_results_lines}\n\n"
                    f"*Jira Status →* {'Ready for Review ✅' if all_pass else 'QA In Progress 🔄'}\n"
                    f"*Time:* {round(time.time() - t0, 1)}s"
                )
                await asyncio.to_thread(_slack.send_message, slack_msg)
            except Exception as _se:
                print(f"[slack] API ticket report error: {_se}")

            elapsed = round(time.time() - t0, 1)
            yield evt({
                "stage": "done",
                "all_pass":  all_pass,
                "results":   test_results,
                "new_status": new_status,
                "elapsed":   elapsed,
                "ticket_type": "api",
            })
            yield "data: {\"stage\": \"done\"}\n\n"
            return

        # ── UI path continues below ────────────────────────────────────────────

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

        try:
            # ── Stage: screenshot relevant pages + DOM extraction ──────────────────
            screenshots: list = []
            pages: list = []
            portal_for_inspect = (
                body.portal if (body.portal and body.portal != "all") else "seller"
            )
            yield evt({"stage": "inspecting_page", "status": "running"})
            try:
                if body.confirmed_pages:
                    pages = body.confirmed_pages
                    print(f"[run_qa] using user-confirmed pages: {pages}")
                else:
                    pages = await asyncio.to_thread(
                        _identify_pages_from_ticket, summary, description, portal_for_inspect
                    )
                    print(f"[run_qa] no confirmed pages — AI guess fallback: {pages}")
                for url_path in pages:
                    yield f": keepalive\n\n"
                    page_portal = (
                        body.portal if (body.portal and body.portal != "all")
                        else _resolve_page_portal(url_path, fallback="seller")
                    )
                    shot = await asyncio.to_thread(
                        screenshot_page, page_portal, run_env, url_path
                    )
                    if shot and not shot.get("error"):
                        screenshots.append(shot)
                        try:
                            dom_result = await asyncio.to_thread(
                                extract_page_dom_live, page_portal, run_env, url_path
                            )
                            if dom_result and not dom_result.get("error"):
                                shot["dom"] = dom_result.get("dom", {})
                                shot["network_calls"] = dom_result.get("network_calls", [])
                        except Exception as _de:
                            print(f"[dom_extract] non-fatal error for {url_path}: {_de}")
                        try:
                            await asyncio.to_thread(
                                learn_page_structure, page_portal, url_path,
                                shot.get("dom", {}), shot.get("network_calls", [])
                            )
                        except Exception as _lps:
                            print(f"[learn_page_structure] non-fatal: {_lps}")
                yield evt({
                    "stage": "inspecting_page",
                    "status": "done",
                    "pages_inspected": [s.get("url") for s in screenshots],
                })
            except Exception as e:
                print(f"[inspecting_page] ERROR: {e}")
                yield evt({"stage": "inspecting_page", "status": "error", "message": str(e)})

            # ── Stage: page confidence check ──────────────────────────────────────
            _user_notes_parts: list = []
            if screenshots:
                _confidence_questions = _check_page_confidence(
                    summary, description, portal_for_inspect, pages, screenshots
                )
                for _cq_text in _confidence_questions:
                    _cq_run_id = f"{issue_key}_conf_{int(time.time())}"
                    _cq_queue: asyncio.Queue = asyncio.Queue()
                    _clarification_store[_cq_run_id] = _cq_queue
                    yield evt({
                        "type": "clarification_needed",
                        "run_id": _cq_run_id,
                        "question": _cq_text,
                    })
                    try:
                        _cq_ans = await asyncio.wait_for(_cq_queue.get(), timeout=300)
                        if _cq_ans:
                            _user_notes_parts.append(f"Q: {_cq_text}\nA: {_cq_ans}")
                    except asyncio.TimeoutError:
                        pass
                    finally:
                        _clarification_store.pop(_cq_run_id, None)
            _user_notes = "\n\n".join(_user_notes_parts)

            # ── Stage: generate test cases ─────────────────────────────────────────
            yield evt({"stage": "generating_test_cases", "status": "running"})
            yield f": keepalive\n\n"
            dom_context = [s for s in screenshots if s.get("dom")]
            test_cases = await asyncio.to_thread(
                generate_test_cases, issue_key, summary, description,
                screenshots or None, dom_context or None, _user_notes
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

            # ── Stage: interactive clarification for uncertain selectors ───────────
            if test_cases:
                _run_id = f"{issue_key}_{int(time.time())}"
                _uncertain = _check_uncertain_steps(test_cases)
                for _u in _uncertain:
                    _q: asyncio.Queue = asyncio.Queue()
                    _clarification_store[_run_id] = _q
                    yield evt({
                        "type": "clarification_needed",
                        "run_id": _run_id,
                        "question": _u["question"],
                    })
                    try:
                        _answer = await asyncio.wait_for(_q.get(), timeout=300)
                        if _answer:
                            # Patch the uncertain step in-place with user's guidance as a comment
                            _tc = test_cases[_u["tc_index"]]
                            _old_step = _tc["steps"][_u["step_index"]]
                            _tc["steps"][_u["step_index"]] = f"{_old_step}  # user: {_answer}"
                            print(f"[clarify] step updated: {_tc['steps'][_u['step_index']][:120]}")
                    except asyncio.TimeoutError:
                        print(f"[clarify] timeout waiting for answer to: {_u['question'][:80]}")
                    finally:
                        _clarification_store.pop(_run_id, None)

            # ── Stage: run Playwright tests ────────────────────────────────────────
            yield evt({"stage": "running_tests", "status": "running"})

            # Strip error sentinel objects returned by generate_test_cases on failure
            test_cases = [tc for tc in test_cases if not tc.get("is_error") and "error" not in tc]

            # User's explicit portal selection overrides whatever the LLM assigned
            if body.portal and body.portal != "all":
                for tc in test_cases:
                    tc["portal"] = body.portal

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
                        _cq_req  = _stdlib_queue.Queue()
                        _cq_resp = _stdlib_queue.Queue()
                        _loop    = asyncio.get_running_loop()
                        _future  = _loop.run_in_executor(
                            None,
                            lambda: _playwright.run_qa_test_cases(
                                portal, run_env, portal_tcs, _cq_req, _cq_resp
                            ),
                        )
                        # Poll for mid-run clarification requests while the thread executes
                        while not _future.done():
                            try:
                                _cq_item = _cq_req.get_nowait()
                                _cq_run_id = f"{issue_key}_step_{int(time.time())}"
                                _cq_q: asyncio.Queue = asyncio.Queue()
                                _clarification_store[_cq_run_id] = _cq_q
                                yield evt({
                                    "type":    "clarification_needed",
                                    "run_id":  _cq_run_id,
                                    "question": _cq_item["question"],
                                    "step":    _cq_item["step"],
                                })
                                try:
                                    _cq_answer = await asyncio.wait_for(_cq_q.get(), timeout=300)
                                except asyncio.TimeoutError:
                                    _cq_answer = ""
                                finally:
                                    _clarification_store.pop(_cq_run_id, None)
                                _cq_resp.put(_cq_answer)
                            except _stdlib_queue.Empty:
                                await asyncio.sleep(0.1)
                        r = _future.result()
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

            # ── Auto-learn: record working selectors to knowledge files ───────────
            try:
                await asyncio.to_thread(learn_from_run, test_cases, test_results)
            except Exception as _le:
                print(f"[learn_from_run] error (non-fatal): {_le}")

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
        except Exception as e:
            print(f"[run_qa UI] unhandled exception: {type(e).__name__}: {e}")
            yield evt({"stage": "done", "error": str(e), "result": {"all_pass": False}})
            return

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
async def run_api_tests_endpoint(body: ApiTestRunBody = None):
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

    kb = _retrieve_kb(message, top_k=5, char_limit=7000)
    print(f"[ai/chat] retrieved KB: {len(kb)} chars for query: {message[:80]!r}")

    live_data = get_live_db_data()

    system = f"""You are a senior Zambeel platform expert who knows everything about this system. Answer questions directly and confidently. Never say 'I don't have access' or 'I cannot determine' — you have the knowledge base and live DB data below. Give specific, direct answers. If the answer is in the data provided, state it as fact. Be concise and professional like a senior colleague answering a quick question.

Zambeel repos:
- Frontend: https://github.com/MyZambeel/zambeel-FE
- Backend: https://github.com/MyZambeel/zambeel-api
- SQA Agent: https://github.com/SarymSikander/sqa-agent

Portals (all three portals share the same base URL; portal type is determined by route path after login):
- Seller portal staging:       https://staging.myzambeel.com  → lands at /get-started
- Admin/OMS portal staging:    https://staging.myzambeel.com  → lands at /orders-management/dashboard
- Agency portal staging:       https://staging.myzambeel.com  → lands at /get-started
- Seller portal production:    https://portal.myzambeel.com   → lands at /get-started
- Admin/OMS portal production: https://portal.myzambeel.com   → lands at /orders-management/dashboard
- Agency portal production:    https://portal.myzambeel.com   → lands at /get-started

{live_data}

RELEVANT KNOWLEDGE BASE SECTIONS:
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
                messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': message}],
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

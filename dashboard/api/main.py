import asyncio
import json
import os
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional

from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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

# Load app context for Claude prompts — prefer local copy, fall back to repo root
_APP_CONTEXT_PATH = Path(__file__).resolve().parent / "app_context.md"
if not _APP_CONTEXT_PATH.exists():
    _APP_CONTEXT_PATH = Path(__file__).resolve().parent.parent.parent / "app_context.md"

_app_context_found = _APP_CONTEXT_PATH.exists()
_app_context_size  = _APP_CONTEXT_PATH.stat().st_size if _app_context_found else 0
print(f"[startup] app_context.md found={_app_context_found} path={_APP_CONTEXT_PATH} size={_app_context_size} bytes")

try:
    _raw_ctx = _APP_CONTEXT_PATH.read_text()
    APP_CONTEXT = _raw_ctx
except Exception as _e:
    print(f"[startup] Failed to load app_context.md: {_e}")
    APP_CONTEXT = ""

print(f"[startup] APP_CONTEXT loaded: {len(APP_CONTEXT)} chars")

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

    prompt = (
        "You are an expert QA engineer for Zambeel, a B2B e-commerce platform.\n"
        "You write Playwright test scripts in Python that actually execute in a browser.\n\n"
        f"Ticket: {ticket_key}\n"
        f"Title: {title}\n"
        f"Description: {description}\n\n"
        f"Relevant app context:\n{relevant_context}\n\n"
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
        "Use real CSS selectors based on the app context. "
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

        print(f"[generate_test_cases] Parsed {len(valid)} valid test cases")
        return valid

    except Exception as e:
        print(f"[generate_test_cases] ERROR: {e}")
        return []


def _build_qa_report(*, issue_key, summary, env, frontend_branch, backend_branch,
                     test_cases, test_results, all_pass, new_status, elapsed):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# QA Report — {issue_key}",
        f"**{summary}**",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Ticket | [{issue_key}](https://zambeel.atlassian.net/browse/{issue_key}) |",
        f"| Environment | `{env.upper()}` |",
        f"| Frontend Branch | `{frontend_branch}` |",
        f"| Backend Branch | `{backend_branch}` |",
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
                lines = [f"🤖 *AI-Generated QA Test Cases — {issue_key}* ({body.env.upper()} | fe:`{body.frontend_branch}` be:`{body.backend_branch}`)"]
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

        for portal in portals:
            yield f": keepalive\n\n"
            print(f"\n[run_tests] Running portal={portal} env={run_env}")
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
                    "QA Incomplete — no test cases generated. Jira status unchanged."
                    if not test_cases
                    else "QA Incomplete — zero steps executed. Jira status unchanged."
                ),
            })
        else:
            try:
                new_status = "Ready for Review" if all_pass else "Dev In Progress"
                await asyncio.to_thread(_jira.update_ticket_status, issue_key, new_status)
                if all_pass:
                    comment_lines = [f"✅ *QA Passed* — {body.env.upper()} | fe:`{body.frontend_branch}` be:`{body.backend_branch}`"]
                    for r in test_results:
                        comment_lines.append(f"• {r['portal'].upper()}: PASS — {r.get('url') or ''} | load: {r.get('load_time_ms',0)}ms")
                        evidence = r.get("feature_evidence") or []
                        found_ev = [e for e in evidence if e.get("found")]
                        if found_ev:
                            comment_lines.append(f"  Evidence: " + "; ".join(
                                f"{e['description']} ({e.get('detail','found')})"
                                for e in found_ev[:4]
                            ))
                        shots = r.get("screenshots") or []
                        if shots:
                            comment_lines.append("  Screenshots: " + ", ".join(
                                s["filename"] for s in shots
                            ))
                    if assignee:
                        comment_lines.append(f"\n@{assignee} All tests passing — moving to Ready for Review.")
                else:
                    comment_lines = [f"❌ *QA Failed* — {body.env.upper()} | fe:`{body.frontend_branch}` be:`{body.backend_branch}`"]
                    for r in test_results:
                        icon = "✅" if r["status"] == "PASS" else "❌"
                        comment_lines.append(f"• {r['portal'].upper()}: {icon} {r['status']} — {str(r.get('message',''))[:200]}")
                        for err in (r.get("console_errors") or [])[:3]:
                            comment_lines.append(f"  Console error: {str(err)[:120]}")
                        evidence = r.get("feature_evidence") or []
                        found_ev = [e for e in evidence if e.get("found")]
                        if found_ev:
                            comment_lines.append(f"  Elements found: " + "; ".join(
                                f"{e['description']}" for e in found_ev[:4]
                            ))
                        shots = r.get("screenshots") or []
                        if shots:
                            comment_lines.append("  Screenshots: " + ", ".join(
                                s["filename"] for s in shots
                            ))
                    if assignee:
                        comment_lines.append(f"\n@{assignee} Tests failing — moving back to Dev In Progress.")
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
            slack_msg = (
                f"🤖 *QA Run Complete* — <https://zambeel.atlassian.net/browse/{issue_key}|{issue_key}>\n"
                f"*{summary}*\n\n"
                f"*Environment:* `{run_env.upper()}`{' *(local repos unavailable, ran on staging)*' if run_env != body.env else ''}\n"
                f"*Frontend Branch:* `{body.frontend_branch}`\n"
                f"*Backend Branch:* `{body.backend_branch}`\n\n"
                f"*AI-Generated Test Cases:*\n{tc_summary}\n\n"
                f"*Playwright Results:*\n{results_summary}\n\n"
                f"*Jira Status → * {'Ready for Review ✅' if all_pass else 'Dev In Progress ❌'}\n"
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

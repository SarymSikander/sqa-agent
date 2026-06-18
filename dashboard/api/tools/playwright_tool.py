import os
import subprocess
import time
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

import pathlib as _pathlib

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

LOCAL_URL      = os.getenv("LOCAL_URL", "http://localhost:5173")
STAGING_URL    = os.getenv("STAGING_URL", "https://staging.myzambeel.com")
PRODUCTION_URL = os.getenv("PRODUCTION_URL", "https://portal.myzambeel.com")

FRONTEND_REPO_PATH = os.getenv("FRONTEND_REPO_PATH")
FRONTEND_DEV_CMD   = os.getenv("FRONTEND_DEV_CMD", "npm run dev")

# Prefer /data/screenshots (persistent on HuggingFace); fall back to local path.
_data_shots = _pathlib.Path("/data/screenshots")
try:
    _data_shots.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR = str(_data_shots)
except OSError:
    SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

URL_MAP = {
    "local":      LOCAL_URL,
    "staging":    STAGING_URL,
    "production": PRODUCTION_URL,
}

# Nav selectors checked after a successful login
_NAV_SELECTORS = [
    "nav",
    "[role='navigation']",
    "header",
    ".sidebar",
    "[class*='sidebar']",
    "[class*='navbar']",
    "[class*='nav-menu']",
    "[class*='top-bar']",
]

# Feature-specific elements to probe per portal (selector, human description)
_FEATURE_SELECTORS = {
    "admin": [
        ("input[type='number']",         "Number input field"),
        ("input[min='0']",               "Input with min=0 (allows zero commission)"),
        ("[class*='commission']",        "Commission-related element"),
        ("[class*='dashboard']",         "Dashboard element"),
        ("table, [class*='table']",      "Data table"),
        ("[class*='order']",             "Orders element"),
        ("button[type='submit']",        "Submit / save button"),
    ],
    "seller": [
        ("[class*='get-started']",       "Get-started page element"),
        ("[class*='onboard']",           "Onboarding element"),
        ("[class*='product']",           "Product element"),
        ("[class*='store']",             "Store element"),
        ("button",                       "Action button"),
    ],
    "agency": [
        ("[class*='get-started']",       "Get-started page element"),
        ("[class*='seller']",            "Seller management element"),
        ("[class*='account']",           "Account element"),
        ("button",                       "Action button"),
    ],
}

_ENV_SUFFIX = {"staging": "STAGING", "production": "PRODUCTION", "local": "LOCAL"}


def login_to_portal(page, portal, env):
    """Fill the login form with credentials from .env and wait until off /login."""
    # Read URLs fresh at call time so HF Space secret updates take effect without restart
    if env == "staging":
        base_url = (os.getenv("STAGING_URL") or "https://staging.myzambeel.com").rstrip("/").split("/login")[0]
    elif env == "production":
        base_url = (os.getenv("PRODUCTION_URL") or "https://portal.myzambeel.com").rstrip("/").split("/login")[0]
    else:
        base_url = (os.getenv("LOCAL_URL") or "http://localhost:5173").rstrip("/")
    suffix    = _ENV_SUFFIX.get(env, env.upper())
    email_key = f"{portal.upper()}_{suffix}_EMAIL"
    pass_key  = f"{portal.upper()}_{suffix}_PASSWORD"
    email     = os.getenv(email_key, "").strip()
    password  = os.getenv(pass_key, "").strip()
    print(f"[LOGIN] portal={portal} env={env} email_key={email_key} email={email!r} password_set={bool(password)}")
    print(f"[LOGIN] navigating to: {base_url}/login")
    page.goto(f"{base_url}/login")
    page.wait_for_selector('input[type="email"], input[type="text"]', timeout=15000)
    page.fill('input[type="email"], input[type="text"]', email)
    page.fill('input[type="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url(lambda url: "/login" not in url, timeout=30000)
    print(f"[LOGIN] success — landed on {page.url}")


def start_local_server():
    print(f"Starting dev server: {FRONTEND_DEV_CMD} in {FRONTEND_REPO_PATH}")
    cmd = FRONTEND_DEV_CMD.split()
    process = subprocess.Popen(
        cmd,
        cwd=FRONTEND_REPO_PATH,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print("Waiting 5 seconds for dev server to boot...")
    time.sleep(5)
    return process


def stop_local_server(process):
    if process and process.poll() is None:
        process.terminate()
        process.wait()
        print("Dev server stopped.")


def run_tests(portal, env):
    """
    Run a full login + post-login validation test for the given portal and environment.

    Returns (status, result_dict). result_dict keys:
      status, message, url, console_errors, nav_elements_found, load_time_ms,
      screenshot_path  — main full-page screenshot (backwards compat)
      screenshots      — list of {label, path, filename} step-by-step evidence
      execution_log    — list of {step, result, detail} Playwright steps
      feature_evidence — list of {selector, description, found, detail}
    """
    portal = portal.lower()
    env    = env.lower()

    url = URL_MAP.get(env)
    if not url:
        return ("FAIL", {
            "status": "FAIL",
            "message": f"Unknown environment '{env}'. Choose: local, staging, production.",
            "url": None, "console_errors": [], "nav_elements_found": [], "load_time_ms": 0,
            "screenshot_path": None, "screenshots": [], "execution_log": [], "feature_evidence": [],
        })

    success_slugs = {
        "admin":  "/orders-management/dashboard",
        "seller": "/get-started",
        "agency": "/get-started",
    }
    expected = success_slugs.get(portal, "")

    local_process = None
    if env == "local":
        local_process = start_local_server()

    screenshots        = []
    execution_log      = []
    feature_evidence   = []
    console_errors     = []
    nav_elements_found = []
    load_time_ms       = 0
    current_url        = url
    screenshot_path    = None
    status             = "FAIL"
    message            = "Test did not complete"

    def _log(step, result="ok", detail=None):
        execution_log.append({"step": step, "result": result, "detail": detail})

    def _screenshot(page, label):
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe  = (label.lower()
                 .replace(" ", "_").replace("/", "_").replace(":", "")
                 .replace("(", "").replace(")", "").replace("—", ""))
        fname = f"{portal}_{env}_{safe}_{ts}.png"
        path  = os.path.join(SCREENSHOTS_DIR, fname)
        try:
            page.screenshot(path=path, full_page=True, timeout=12000)
            screenshots.append({"label": label, "path": path, "filename": fname})
            _log(f"Screenshot: {label}", "ok", f"Saved as {fname}")
            return path
        except Exception as ex:
            _log(f"Screenshot: {label}", "warn", f"Skipped — {ex}")
            return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page    = context.new_page()

            def _capture_console(msg):
                if msg.type == "error":
                    console_errors.append(msg.text)
            page.on("console", _capture_console)

            _log(f"Logging in as {portal}/{env}", "ok")
            t0 = time.time()
            try:
                login_to_portal(page, portal, env)
            except Exception as e:
                _log("login_to_portal failed", "fail", str(e))
                _screenshot(page, "login_failed")
                status  = "FAIL"
                message = f"Login failed: {e}"
                browser.close()
                return ("FAIL", {
                    "status": "FAIL", "message": message, "url": page.url,
                    "console_errors": console_errors, "nav_elements_found": [],
                    "load_time_ms": 0, "screenshot_path": None,
                    "screenshots": screenshots, "execution_log": execution_log,
                    "feature_evidence": [],
                })

            current_url  = page.url
            load_time_ms = int((time.time() - t0) * 1000)
            _log(f"Post-login URL: {current_url}", "ok", f"load={load_time_ms}ms")
            _screenshot(page, "After login")

            if "/login" in current_url:
                status  = "FAIL"
                message = "Still on login page after login attempt"
                _log("Auth failed — still on /login", "fail", current_url)
                _screenshot(page, "auth_failed")
            else:
                if expected and expected in current_url:
                    status  = "PASS"
                    message = f"Logged in successfully. Landed on: {current_url}"
                    _log(f"URL check PASS — '{expected}' present in URL", "pass", current_url)
                else:
                    status  = "FAIL"
                    message = f"Unexpected URL after login (expected '{expected}'). URL: {current_url}"
                    _log("URL check FAIL — unexpected path", "fail",
                         f"Got: {current_url} | Expected: {expected}")

                _screenshot(page, f"Feature page — {status}")

                # ── Nav element checks ────────────────────────────────────────────
                if status == "PASS":
                    _log("Checking navigation / shell elements", "ok")
                    for selector in _NAV_SELECTORS:
                        try:
                            found = bool(page.query_selector(selector))
                            if found:
                                nav_elements_found.append(selector)
                            _log(f"Nav selector: {selector}",
                                 "found" if found else "not_found")
                        except Exception:
                            pass

                # ── Feature-specific evidence ─────────────────────────────────────
                _log(f"Checking {portal} feature-specific selectors", "ok")
                for selector, desc in _FEATURE_SELECTORS.get(portal, []):
                    try:
                        el    = page.query_selector(selector)
                        found = bool(el)
                        detail = None
                        if found and el:
                            for attr in ("min", "max", "type", "name", "value"):
                                try:
                                    val = el.get_attribute(attr)
                                    if val is not None:
                                        detail = (detail or "") + f"{attr}={val} "
                                except Exception:
                                    pass
                        feature_evidence.append({
                            "selector":    selector,
                            "description": desc,
                            "found":       found,
                            "detail":      (detail.strip() if detail else None) or
                                           ("Element present" if found else "Element not found"),
                        })
                        _log(f"Feature check — {desc}",
                             "found" if found else "not_found", selector)
                    except Exception as ex:
                        _log(f"Feature check — {desc}", "error", str(ex))

                # ── Console error summary ─────────────────────────────────────────
                if console_errors:
                    _log(f"{len(console_errors)} JS console error(s) captured", "warn",
                         " | ".join(console_errors[:3]))
                else:
                    _log("No JS console errors", "ok")

                # ── Final full-page screenshot ────────────────────────────────────
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(
                    SCREENSHOTS_DIR, f"{portal}_{env}_{status}_{timestamp}.png"
                )
                try:
                    page.screenshot(path=screenshot_path, full_page=True, timeout=15000)
                    _log("Full-page screenshot saved", "ok", os.path.basename(screenshot_path))
                    print(f"Screenshot saved: {screenshot_path}")
                except Exception:
                    _log("Full-page screenshot skipped", "warn")
                    screenshot_path = None

            browser.close()

    except Exception as e:
        status  = "FAIL"
        message = f"Playwright error: {e}"
        _log("Playwright exception", "fail", str(e))
    finally:
        if local_process:
            stop_local_server(local_process)

    result = {
        "status":             status,
        "message":            message,
        "url":                current_url,
        "console_errors":     console_errors,
        "nav_elements_found": nav_elements_found,
        "load_time_ms":       load_time_ms,
        "screenshot_path":    screenshot_path,
        "screenshots":        screenshots,
        "execution_log":      execution_log,
        "feature_evidence":   feature_evidence,
    }
    print(f"[{status}] {portal}/{env} — {message} | load:{load_time_ms}ms | "
          f"steps:{len(execution_log)} | evidence:{len(feature_evidence)}")
    return (status, result)


# ---------------------------------------------------------------------------
# AI test case executor
# ---------------------------------------------------------------------------

def _human_friendly_question(step_str: str) -> str:
    """Return a plain-English clarification question a non-developer QA tester can answer.

    Returns an empty string for steps that are pure timing/infrastructure failures
    (SELECT_ROW, WAIT, NAVIGATE, ASSERT_*) — those aren't user-answerable.
    """
    import re as _re

    # Infrastructure/timing steps — the tester can't help with these
    _skip = (
        "SELECT_ROW:", "WAIT:", "NAVIGATE:", "ASSERT_EXISTS:", "ASSERT_NOT_EXISTS:",
        "ASSERT_TEXT:", "ASSERT_DISABLED:", "ASSERT_URL:", "SCREENSHOT:",
        "CLICK_OPTION:", "SELECT_OPTION:",
    )
    if any(step_str.startswith(p) for p in _skip):
        return ""

    if step_str.startswith("CLICK:"):
        sel = step_str[6:].strip()
        m = _re.search(r"has-text\(['\"](.+?)['\"]\)", sel)
        if m:
            label = m.group(1)
            return (
                f"I couldn't find a button or link labeled \"{label}\" on the page.\n\n"
                f"• Does this element exist on the current page?\n"
                f"• If yes — what is its exact label or text?"
            )
        m = _re.search(r"text=['\"](.+?)['\"]", sel)
        if m:
            txt = m.group(1)
            return (
                f"I couldn't find the text \"{txt}\" on the page.\n\n"
                f"• Is this text visible on the current page?\n"
                f"• If yes — what is the exact wording?"
            )
        return (
            "I couldn't find the element I needed to click on this page.\n\n"
            "• Does a clickable button or link exist here?\n"
            "• If yes — what does it say?"
        )

    if step_str.startswith("FILL:"):
        parts = step_str[5:].split("|", 1)
        sel = parts[0].strip()
        val = parts[1].strip().strip("'\"") if len(parts) > 1 else ""
        m = _re.search(r"placeholder=['\"](.+?)['\"]", sel)
        if m:
            ph = m.group(1)
            return (
                f"I couldn't find the input field that says \"{ph}\".\n\n"
                f"• Does this input field exist on the current page?\n"
                f"• If yes — what does the placeholder text say exactly?\n"
                + (f"• I was going to type: \"{val}\"" if val else "")
            )
        return (
            "I couldn't find an input field to type into on this page.\n\n"
            "• Does a text input or form field exist here?\n"
            "• If yes — describe where it is or what its label says."
        )

    if step_str.startswith("CLICK_DROPDOWN_ITEM:"):
        val = step_str[len("CLICK_DROPDOWN_ITEM:"):].strip().strip("'\"")
        return (
            f"I opened the dropdown menu but couldn't find an option called \"{val}\".\n\n"
            f"• Is \"{val}\" visible in the dropdown?\n"
            f"• If not — what options are shown in the dropdown?"
        )

    return ""


_STEP_KEYWORDS = [
    "NAVIGATE", "ASSERT_TEXT", "ASSERT_EXISTS", "ASSERT_NOT_EXISTS",
    "ASSERT_DISABLED", "ASSERT_URL", "CLICK_DROPDOWN_ITEM", "CLICK_OPTION",
    "SELECT_OPTION", "SCREENSHOT", "FILL", "CLICK", "WAIT", "SELECT_ROW",
]

def _normalize_step(step: str) -> str:
    """Add colon after keyword when GPT-4o omitted it (e.g. 'NAVIGATE /path' → 'NAVIGATE: /path')."""
    step = step.strip()
    for kw in _STEP_KEYWORDS:
        if step.startswith(kw + " ") and not step.startswith(kw + ":"):
            return kw + ": " + step[len(kw):].lstrip()
    return step


def run_qa_test_cases(portal: str, env: str, test_cases: list,
                      clarify_req_queue=None, clarify_resp_queue=None) -> dict:
    """
    Execute AI-generated structured test cases for a single portal/env.

    Each test case step string begins with a keyword:
      CLICK: selector
      FILL: selector | value
      WAIT: selector
      NAVIGATE: /path
      ASSERT_EXISTS: selector
      ASSERT_NOT_EXISTS: selector
      ASSERT_TEXT: selector | expected text
      SCREENSHOT: label

    After all steps, the evidence_selector is checked to determine PASS/FAIL.
    Returns a result dict compatible with run_tests().
    """
    portal = portal.lower()
    env    = env.lower()

    url = URL_MAP.get(env)
    if not url:
        return {
            "status": "FAIL",
            "message": f"Unknown environment '{env}'. Choose: local, staging, production.",
            "url": None, "console_errors": [], "nav_elements_found": [], "load_time_ms": 0,
            "screenshot_path": None, "screenshots": [], "execution_log": [],
            "feature_evidence": [], "steps_executed": 0,
        }

    local_process = None
    if env == "local":
        local_process = start_local_server()

    base_url = url.rstrip("/").split("/login")[0]

    screenshots        = []
    execution_log      = []
    feature_evidence   = []
    console_errors     = []
    load_time_ms       = 0
    current_url        = base_url
    overall_status     = "PASS"
    steps_executed     = 0

    def _log(step, result="ok", detail=None):
        execution_log.append({"step": step, "result": result, "detail": detail})

    def _take_screenshot(page, label):
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe  = (label.lower()
                 .replace(" ", "_").replace("/", "_").replace(":", "")
                 .replace("(", "").replace(")", "").replace("—", ""))
        fname = f"{portal}_{env}_{safe}_{ts}.png"
        path  = os.path.join(SCREENSHOTS_DIR, fname)
        try:
            page.screenshot(path=path, full_page=True, timeout=12000)
            screenshots.append({"label": label, "path": path, "filename": fname})
            _log(f"Screenshot: {label}", "ok", fname)
            return path
        except Exception as ex:
            _log(f"Screenshot: {label}", "warn", str(ex))
            return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page    = context.new_page()

            def _capture_console(msg):
                if msg.type == "error":
                    console_errors.append(msg.text)
            page.on("console", _capture_console)

            _log(f"Logging in as {portal}/{env}", "ok")
            t0 = time.time()
            try:
                login_to_portal(page, portal, env)
            except Exception as e:
                _log("login_to_portal failed", "fail", str(e))
                overall_status = "FAIL"
                _take_screenshot(page, f"login_failed_{portal}_{env}")
                browser.close()
                return {
                    "status": "FAIL", "message": f"Login failed: {e}", "url": page.url,
                    "console_errors": console_errors, "nav_elements_found": [],
                    "load_time_ms": 0, "screenshot_path": None,
                    "screenshots": screenshots, "execution_log": execution_log,
                    "feature_evidence": [], "steps_executed": 0,
                }

            current_url  = page.url
            load_time_ms = int((time.time() - t0) * 1000)
            _log(f"Post-login URL: {current_url}", "ok")

            auth_ok = "/login" not in current_url
            if not auth_ok:
                _log("Auth failed — still on /login", "fail", current_url)
                feature_evidence.append({
                    "selector":    "N/A",
                    "description": "Auth check",
                    "found":       False,
                    "detail":      f"Still on {current_url} after login attempt",
                })
                overall_status = "FAIL"
                _take_screenshot(page, f"auth_failed_{portal}_{env}")

            for tc in test_cases:
                if not auth_ok:
                    break
                tc_name = tc.get("test_name", "Unnamed test")
                _log(f"── Test case: {tc_name} ──", "ok")
                tc_pass = True

                for step_str in (tc.get("steps") or []):
                    step_str = _normalize_step(step_str.strip())
                    if not step_str:
                        continue
                    for _attempt in range(2):
                        try:
                            if step_str.startswith("SELECT_ROW:"):
                                val = step_str[len("SELECT_ROW:"):].strip()
                                n = 0
                                if val.lstrip("-").isdigit():
                                    n = int(val)
                                elif val.startswith("nth="):
                                    try:
                                        n = int(val[4:])
                                    except ValueError:
                                        n = 0
                                try:
                                    page.locator("table tbody tr").nth(n).locator('input[type="checkbox"]').click(timeout=5000)
                                except Exception:
                                    page.locator("tbody tr").nth(n).locator('[role="checkbox"]').click(timeout=5000)
                                # Wait for UI to update and Actions button to become enabled
                                page.wait_for_timeout(1000)
                                _log(f"[SELECT_ROW] Clicked checkbox on row {n}", "pass")
                                steps_executed += 1

                            elif step_str.startswith("CLICK:"):
                                sel = step_str[6:].strip()
                                page.wait_for_selector(sel, timeout=8000)
                                # Check if element is disabled before clicking
                                el = page.query_selector(sel)
                                is_disabled = False
                                if el:
                                    try:
                                        disabled_attr = el.get_attribute("disabled")
                                        el_class = el.get_attribute("class") or ""
                                        is_disabled = (
                                            disabled_attr is not None or
                                            any(c in el_class for c in ["disabled", "opacity-50", "cursor-not-allowed", "pointer-events-none"])
                                        )
                                    except Exception:
                                        pass
                                if is_disabled:
                                    _log(f"[DISABLED BUTTON] {sel} is currently disabled — skipping", "fail")
                                    _log("Button is disabled — row checkbox must be selected first using SELECT_ROW step", "fail")
                                    tc_pass = False
                                    steps_executed += 1
                                    break
                                if sel.strip().startswith("select"):
                                    page.locator(sel).last.click(force=True)
                                else:
                                    page.click(sel, timeout=8000)
                                _log(f"CLICK: {sel}", "pass")
                                steps_executed += 1
                                if "save" in sel.lower():
                                    page.wait_for_timeout(2000)
                                    page.wait_for_load_state("networkidle")
                                    _log("Post-save wait: networkidle", "ok")
                                if "+ new model" in sel.lower() or "new model" in sel.lower():
                                    page.wait_for_selector("input[placeholder='Enter model name']", timeout=8000)
                                    _log("Post-modal wait: modal input visible", "ok")

                            elif step_str.startswith("FILL:"):
                                parts = step_str[5:].split("|", 1)
                                sel   = parts[0].strip()
                                val   = parts[1].strip().strip("'\"") if len(parts) > 1 else ""
                                page.wait_for_selector(sel, timeout=8000)
                                page.fill(sel, val)
                                _log(f"FILL: {sel} → '{val}'", "pass")
                                steps_executed += 1

                            elif step_str.startswith("WAIT:"):
                                val = step_str[5:].strip()
                                if val.lstrip("-").isdigit():
                                    # Numeric value → millisecond timeout
                                    page.wait_for_timeout(int(val))
                                    _log(f"WAIT: {val}ms", "pass")
                                    steps_executed += 1
                                elif '[role="option"]' in val or "[role='option']" in val:
                                    _log(f"WAIT: {val} (skipped — role=option not applicable)", "skip")
                                else:
                                    page.wait_for_selector(val, timeout=10000)
                                    _log(f"WAIT: {val}", "pass")
                                    steps_executed += 1

                            elif step_str.startswith("NAVIGATE:"):
                                path = step_str[9:].strip()
                                if path.count('/orders-management') > 1:
                                    path = path.replace('/orders-management/orders-management', '/orders-management')
                                page.goto(base_url + path, timeout=30000, wait_until="domcontentloaded")
                                page.wait_for_timeout(1500)
                                _log(f"NAVIGATE: {path}", "pass", page.url)
                                steps_executed += 1

                            elif step_str.startswith("ASSERT_EXISTS:"):
                                sel   = step_str[14:].strip()
                                found = bool(page.query_selector(sel))
                                _log(f"ASSERT_EXISTS: {sel}", "pass" if found else "fail",
                                     None if found else "Element not found")
                                if not found:
                                    tc_pass = False
                                steps_executed += 1

                            elif step_str.startswith("ASSERT_NOT_EXISTS:"):
                                sel   = step_str[18:].strip()
                                found = bool(page.query_selector(sel))
                                _log(f"ASSERT_NOT_EXISTS: {sel}",
                                     "pass" if not found else "fail",
                                     None if not found else "Element unexpectedly present")
                                if found:
                                    tc_pass = False
                                steps_executed += 1

                            elif step_str.startswith("ASSERT_TEXT:"):
                                payload = step_str[12:].strip()
                                if "|" in payload:
                                    parts    = payload.split("|", 1)
                                    sel      = parts[0].strip()
                                    expected = parts[1].strip().strip("'")
                                else:
                                    sel      = payload  # text embedded in selector e.g. h2:has-text('...')
                                    expected = ""
                                el = page.query_selector(sel)
                                if el:
                                    if expected:
                                        actual = el.inner_text()
                                        if expected.lower() in actual.lower():
                                            _log(f"ASSERT_TEXT: {sel}", "pass", f"Found '{expected}'")
                                        else:
                                            _log(f"ASSERT_TEXT: {sel}", "fail",
                                                 f"Expected '{expected}' in '{actual[:100]}'")
                                            tc_pass = False
                                    else:
                                        _log(f"ASSERT_TEXT: {sel}", "pass", "Element exists")
                                else:
                                    _log(f"ASSERT_TEXT: {sel}", "fail", "Element not found")
                                    tc_pass = False
                                steps_executed += 1

                            elif step_str.startswith("SCREENSHOT:"):
                                _take_screenshot(page, step_str[11:].strip())
                                steps_executed += 1

                            elif step_str.startswith("CLICK_OPTION:"):
                                val = step_str[len("CLICK_OPTION:"):].strip().strip("'\"")
                                page.locator("select").filter(has=page.locator(f'option:has-text("{val}")')).first.select_option(label=val)
                                _log(f"CLICK_OPTION: {val}", "pass")
                                steps_executed += 1

                            elif step_str.startswith("CLICK_DROPDOWN_ITEM:"):
                                val = step_str[len("CLICK_DROPDOWN_ITEM:"):].strip().strip("'\"")
                                # Wait for dropdown animation, then click menu item by text
                                page.wait_for_timeout(500)
                                item_loc = page.locator(
                                    f'[role="menuitem"]:has-text("{val}"), '
                                    f'li:has-text("{val}"), '
                                    f'a:has-text("{val}")'
                                ).first
                                item_loc.wait_for(timeout=5000)
                                item_loc.click(timeout=5000)
                                _log(f"CLICK_DROPDOWN_ITEM: {val}", "pass")
                                steps_executed += 1

                            else:
                                _log(f"UNKNOWN step (skipped): {step_str[:80]}", "skip")

                        except Exception as e:
                            if _attempt == 0:
                                # First failure — wait and retry once
                                try:
                                    page.wait_for_timeout(1000)
                                except Exception:
                                    pass
                                continue
                            # Second failure — only ask the user if it's a question they can answer
                            _question = _human_friendly_question(step_str)
                            if _question and clarify_req_queue is not None:
                                clarify_req_queue.put({"step": step_str, "question": _question})
                                try:
                                    answer = clarify_resp_queue.get(timeout=300)
                                    _log(f"Clarification received: {answer}", "ok")
                                except Exception:
                                    _log("Clarification timeout — proceeding without guidance", "warn")
                            _log(f"ERROR — {step_str[:80]}", "fail", str(e))
                            tc_pass = False
                        else:
                            break  # step succeeded — exit retry loop

                ev_sel = tc.get("evidence_selector", "").strip()
                if ev_sel:
                    try:
                        el    = page.query_selector(ev_sel)
                        found = bool(el)
                        detail = None
                        if found and el:
                            try:
                                detail = el.inner_text()[:100].strip() or el.get_attribute("class") or "present"
                            except Exception:
                                detail = "present"
                        feature_evidence.append({
                            "selector":    ev_sel,
                            "description": tc_name,
                            "found":       found,
                            "detail":      detail or ("Element found" if found else "Element not found"),
                        })
                        _log(f"Evidence {'PASS' if found else 'FAIL'}: {ev_sel}",
                             "pass" if found else "fail",
                             detail if found else "Selector not found on page")
                        if not found:
                            tc_pass = False
                    except Exception as e:
                        _log(f"Evidence ERROR: {ev_sel}", "fail", str(e))
                        tc_pass = False

                _take_screenshot(page, f"{tc_name} — {'PASS' if tc_pass else 'FAIL'}")

                if not tc_pass:
                    overall_status = "FAIL"

            try:
                current_url = page.url
            except Exception:
                pass

            browser.close()

    except Exception as e:
        overall_status = "FAIL"
        _log("Playwright exception", "fail", str(e))
    finally:
        if local_process:
            stop_local_server(local_process)

    if steps_executed == 0:
        overall_status = "FAIL"
        _log("No steps executed — result forced to FAIL", "fail")

    auth_ev = next(
        (e for e in feature_evidence
         if e.get("description") == "Auth check" and not e.get("found")),
        None,
    )
    message = (
        f"Login failed — check credentials for {portal}/{env}"
        if auth_ev else
        f"Executed {steps_executed} step(s) across {len(test_cases)} test case(s). "
        f"Evidence: {len(feature_evidence)} selector(s) checked."
    )
    result = {
        "status":             overall_status,
        "message":            message,
        "url":                current_url,
        "console_errors":     console_errors,
        "nav_elements_found": [],
        "load_time_ms":       load_time_ms,
        "screenshot_path":    screenshots[-1]["path"] if screenshots else None,
        "screenshots":        screenshots,
        "execution_log":      execution_log,
        "feature_evidence":   feature_evidence,
        "steps_executed":     steps_executed,
    }
    print(f"[{overall_status}] run_qa_test_cases {portal}/{env} — {steps_executed} steps | "
          f"evidence:{len(feature_evidence)} | screenshots:{len(screenshots)}")
    return result


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------

def run_tests_seller_local():      return run_tests("seller", "local")
def run_tests_seller_staging():    return run_tests("seller", "staging")
def run_tests_seller_production(): return run_tests("seller", "production")

def run_tests_admin_local():       return run_tests("admin", "local")
def run_tests_admin_staging():     return run_tests("admin", "staging")
def run_tests_admin_production():  return run_tests("admin", "production")

def run_tests_agency_local():      return run_tests("agency", "local")
def run_tests_agency_staging():    return run_tests("agency", "staging")
def run_tests_agency_production(): return run_tests("agency", "production")

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

LOCAL_URL      = os.getenv("LOCAL_URL")
STAGING_URL    = os.getenv("STAGING_URL")
PRODUCTION_URL = os.getenv("PRODUCTION_URL")

FRONTEND_REPO_PATH = os.getenv("FRONTEND_REPO_PATH")
FRONTEND_DEV_CMD   = os.getenv("FRONTEND_DEV_CMD", "npm run dev")

AUTH_DIR        = os.path.join(os.path.dirname(__file__), "..", "auth")
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


def get_auth_file(portal, env):
    path = os.path.join(AUTH_DIR, f"{portal}_{env}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Auth session not found: {path}\n"
            f"Run this first:  python tools/auth_setup.py {portal} {env}"
        )
    return path


def _load_auth_token(auth_file):
    """Return (auth_data, authToken) from auth-storage in origins[0].localStorage.

    Handles both the full Playwright storage format {cookies, origins: [...]}
    and the uploaded format {origins: [...]} (no cookies key).
    The auth-storage value may be a JSON string (standard) or already a dict.
    """
    with open(auth_file) as f:
        auth_data = json.load(f)
    try:
        ls = auth_data["origins"][0]["localStorage"]
        for item in ls:
            if item.get("name") == "auth-storage":
                val = item["value"]
                inner = json.loads(val) if isinstance(val, str) else val
                token = (inner.get("state") or {}).get("authToken")
                if token:
                    return auth_data, token
    except (KeyError, IndexError, ValueError, TypeError):
        pass
    return auth_data, None


_LOGIN_API = {
    "local":      "http://localhost:3000/api/auth/login",
    "staging":    "https://staging.myzambeel.com/api/auth/login",
    "production": "https://portal.myzambeel.com/api/auth/login",
}


def _fetch_auth_token(portal, env):
    """POST portal credentials from .env to the login API and return the JWT token.

    Reads {PORTAL}_{ENV}_EMAIL / {PORTAL}_{ENV}_PASSWORD first (per-env),
    then falls back to {PORTAL}_EMAIL / {PORTAL}_PASSWORD (generic).
    Values are stripped of surrounding whitespace.
    """
    portal_up = portal.upper()
    env_up    = env.upper()
    email    = (os.getenv(f"{portal_up}_{env_up}_EMAIL", "").strip()
                or os.getenv(f"{portal_up}_EMAIL", "").strip())
    password = (os.getenv(f"{portal_up}_{env_up}_PASSWORD", "").strip()
                or os.getenv(f"{portal_up}_PASSWORD", "").strip())
    if not email or not password:
        print(f"[AUTH] {portal}/{env} — credentials not configured "
              f"({portal_up}_{env_up}_EMAIL / {portal_up}_{env_up}_PASSWORD not set in .env)")
        return None
    login_url = _LOGIN_API.get(env)
    if not login_url:
        print(f"[AUTH] {portal}/{env} — no login API URL for env '{env}'")
        return None
    payload = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        login_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        token = (data.get("token")
                 or data.get("authToken")
                 or data.get("accessToken")
                 or data.get("access_token"))
        if token:
            print(f"[AUTH] {portal}/{env} — API login OK, token len={len(token)}")
            return token
        print(f"[AUTH] {portal}/{env} — API login: no token field in response "
              f"(keys={list(data.keys())})")
        return None
    except urllib.error.HTTPError as e:
        print(f"[AUTH] {portal}/{env} — API login HTTP {e.code}: "
              f"{e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"[AUTH] {portal}/{env} — API login error: {e}")
        return None


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

    # ── Acquire JWT: programmatic API login, fallback to saved auth file ─────
    auth_token = _fetch_auth_token(portal, env)
    if auth_token is None:
        try:
            auth_file = get_auth_file(portal, env)
            _, auth_token = _load_auth_token(auth_file)
            if auth_token:
                print(f"[AUTH] {portal}/{env} — using saved auth file (API credentials not set)")
        except FileNotFoundError:
            pass
    if auth_token is None:
        _msg = (f"No auth token for {portal}/{env}. "
                f"Set {portal.upper()}_EMAIL + {portal.upper()}_PASSWORD in .env "
                f"or run: python tools/auth_setup.py {portal} {env}")
        return ("FAIL", {
            "status": "FAIL", "message": _msg, "url": None,
            "console_errors": [], "nav_elements_found": [], "load_time_ms": 0,
            "screenshot_path": None, "screenshots": [],
            "execution_log": [{"step": "Acquire auth token", "result": "fail", "detail": _msg}],
            "feature_evidence": [],
        })
    print(f"[AUTH] {portal}/{env} — token acquired (len={len(auth_token)})")

    local_process = None
    if env == "local":
        local_process = start_local_server()

    success_slugs = {
        "admin":  "/orders-management/dashboard",
        "seller": "/get-started",
        "agency": "/get-started",
    }
    expected   = success_slugs.get(portal, "")
    base_url   = url.rstrip("/").split("/login")[0]
    target_url = base_url + expected

    # mutable accumulators
    screenshots       = []
    execution_log     = []
    feature_evidence  = []
    console_errors    = []
    nav_elements_found = []
    load_time_ms      = 0
    current_url       = target_url
    screenshot_path   = None
    status            = "FAIL"
    message           = "Test did not complete"

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

            # ── Step 1: capture the login page (unauthenticated) ─────────────────
            _log("Launch browser (no auth) to capture login page", "ok", "Headless Chromium")
            browser_pre = p.chromium.launch(headless=True)
            try:
                ctx_pre  = browser_pre.new_context()
                page_pre = ctx_pre.new_page()
                _log(f"Navigate to base URL: {base_url}", "ok")
                page_pre.goto(base_url, timeout=30000, wait_until="domcontentloaded")
                page_pre.wait_for_timeout(2000)
                _log(f"Login page loaded: {page_pre.url}", "ok")
                _screenshot(page_pre, "Login page")
            except Exception as e:
                _log("Login page capture failed", "warn", str(e))
            finally:
                browser_pre.close()

            # ── Step 2: authenticated test ────────────────────────────────────────
            _log(f"Launch authenticated browser for {portal}/{env}", "ok",
                 f"Auth: {portal}_{env}.json (JWT token only — no session state)")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()

            # ── Set auth token as cookie ──────────────────────────────────────────
            if auth_token:
                parsed_url = urlparse(base_url)
                context.add_cookies([{
                    "name":     "authToken",
                    "value":    auth_token,
                    "domain":   parsed_url.hostname,
                    "path":     "/",
                    "httpOnly": False,
                    "secure":   parsed_url.scheme == "https",
                    "sameSite": "Lax",
                }])
                _log("Auth cookie set", "ok", f"domain={parsed_url.hostname}")

            page = context.new_page()

            # ── Inject token into localStorage before page scripts run ────────────
            if auth_token:
                auth_storage_payload = json.dumps({"state": {"authToken": auth_token}})
                page.add_init_script(
                    f"window.localStorage.setItem('auth-storage', {json.dumps(auth_storage_payload)});"
                )
                _log("localStorage init script registered", "ok", "auth-storage injected pre-load")

            def _capture_console(msg):
                if msg.type == "error":
                    console_errors.append(msg.text)
            page.on("console", _capture_console)

            # ── Bearer token route interception (all requests) ────────────────────
            if auth_token:
                def _bearer_handler(route, request):
                    route.continue_(headers={**request.headers, "Authorization": f"Bearer {auth_token}"})
                page.route("**/*", _bearer_handler)
                print(f"[AUTH] {portal}/{env} — **/* interceptor active, injecting Bearer token on every request")
                _log("Bearer token route interceptor registered for **/*", "ok",
                     f"token len={len(auth_token)}")
            else:
                print(f"[AUTH] {portal}/{env} — no authToken, route interceptor not registered")
                _log("No authToken found in auth JSON — proceeding without Bearer injection", "warn")

            _log(f"Navigate to target: {target_url}", "ok", f"Expected path: {expected}")
            t0 = time.time()
            page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            # Wait for networkidle so the Zustand store has time to rehydrate from
            # localStorage before the route guard checks auth state.
            _log("Waiting for networkidle — Zustand rehydration", "ok")
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                _log("networkidle timeout — continuing", "warn")
            page.wait_for_timeout(3000)
            current_url = page.url
            print(f"[AUTH] {portal}/{env} — URL after initial wait: {current_url}")

            # ── Force-navigate if still on /login ────────────────────────────────
            if "/login" in current_url:
                _log("Still on /login — forcing JS navigation to target", "warn", current_url)
                _screenshot(page, f"pre_force_nav_{portal}")
                page.evaluate(f"window.location.href = '{target_url}'")
                _log("JS navigation triggered, waiting for networkidle", "ok")
                try:
                    page.wait_for_load_state("networkidle", timeout=30000)
                except Exception:
                    _log("networkidle timeout after force-nav — continuing", "warn")
                page.wait_for_timeout(3000)
                current_url = page.url
                print(f"[AUTH] {portal}/{env} — URL after force-nav: {current_url}")

            if "/login" in current_url:
                status  = "FAIL"
                message = f"Auth failed after force-nav — run: python3 tools/auth_setup.py {portal} {env}"
                _log("Still on /login after force-nav", "fail", current_url)
                _screenshot(page, f"auth_failed_{portal}")
            else:
                _screenshot(page, f"After auth — {portal}")
                load_time_ms = int((time.time() - t0) * 1000)
                _log(f"Page settled at {current_url}", "ok", f"Total load time: {load_time_ms}ms")

                if expected and expected in current_url:
                    status  = "PASS"
                    message = f"Logged in successfully. Landed on: {current_url}"
                    _log(f"URL check PASS — '{expected}' present in URL", "pass", current_url)
                else:
                    status  = "FAIL"
                    message = f"Unexpected URL after auth (expected '{expected}'). URL: {current_url}"
                    _log("URL check FAIL — unexpected path", "fail",
                         f"Got: {current_url} | Expected: {expected}")

                # ── Settled-state screenshot (labelled with pass/fail) ────────────────
                _screenshot(page, f"Feature page — {status}")

                # ── Nav element checks ────────────────────────────────────────────────
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

                # ── Feature-specific evidence ─────────────────────────────────────────
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

                # ── Console error summary ─────────────────────────────────────────────
                if console_errors:
                    _log(f"{len(console_errors)} JS console error(s) captured", "warn",
                         " | ".join(console_errors[:3]))
                else:
                    _log("No JS console errors", "ok")

                # ── Final full-page screenshot (backwards-compat field) ───────────────
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

def run_qa_test_cases(portal: str, env: str, test_cases: list) -> dict:
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

    # ── Acquire JWT: programmatic API login, fallback to saved auth file ─────
    auth_token = _fetch_auth_token(portal, env)
    if auth_token is None:
        try:
            auth_file = get_auth_file(portal, env)
            _, auth_token = _load_auth_token(auth_file)
            if auth_token:
                print(f"[AUTH] {portal}/{env} — using saved auth file (API credentials not set)")
        except FileNotFoundError:
            pass
    if auth_token is None:
        _msg = (f"No auth token for {portal}/{env}. "
                f"Set {portal.upper()}_EMAIL + {portal.upper()}_PASSWORD in .env "
                f"or run: python tools/auth_setup.py {portal} {env}")
        return {
            "status": "FAIL", "message": _msg, "url": None,
            "console_errors": [], "nav_elements_found": [], "load_time_ms": 0,
            "screenshot_path": None, "screenshots": [],
            "execution_log": [{"step": "Acquire auth token", "result": "fail", "detail": _msg}],
            "feature_evidence": [], "steps_executed": 0,
        }
    print(f"[AUTH] {portal}/{env} — token acquired (len={len(auth_token)})")

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

            # ── Set auth token as cookie ──────────────────────────────────────────
            if auth_token:
                parsed_url = urlparse(base_url)
                context.add_cookies([{
                    "name":     "authToken",
                    "value":    auth_token,
                    "domain":   parsed_url.hostname,
                    "path":     "/",
                    "httpOnly": False,
                    "secure":   parsed_url.scheme == "https",
                    "sameSite": "Lax",
                }])
                _log("Auth cookie set", "ok", f"domain={parsed_url.hostname}")

            page = context.new_page()

            # ── Inject token into localStorage before page scripts run ────────────
            if auth_token:
                auth_storage_payload = json.dumps({"state": {"authToken": auth_token}})
                page.add_init_script(
                    f"window.localStorage.setItem('auth-storage', {json.dumps(auth_storage_payload)});"
                )
                _log("localStorage init script registered", "ok", "auth-storage injected pre-load")

            def _capture_console(msg):
                if msg.type == "error":
                    console_errors.append(msg.text)
            page.on("console", _capture_console)

            # ── Bearer token route interception (all requests) ────────────────────
            if auth_token:
                def _bearer_handler(route, request):
                    route.continue_(headers={**request.headers, "Authorization": f"Bearer {auth_token}"})
                page.route("**/*", _bearer_handler)
                print(f"[AUTH] {portal}/{env} — **/* interceptor active, injecting Bearer token on every request")
                _log("Bearer token route interceptor registered for **/*", "ok",
                     f"token len={len(auth_token)}")
            else:
                print(f"[AUTH] {portal}/{env} — no authToken, route interceptor not registered")
                _log("No authToken found in auth JSON — proceeding without Bearer injection", "warn")

            # Warm-up navigation to first test case's path
            first_path = (test_cases[0].get("url_path") or "/") if test_cases else "/"
            nav_target = base_url + first_path
            t0 = time.time()
            page.goto(nav_target, timeout=60000, wait_until="domcontentloaded")
            _log("Waiting for networkidle — Zustand rehydration", "ok")
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                _log("networkidle timeout — continuing", "warn")
            page.wait_for_timeout(3000)
            current_url = page.url
            print(f"[AUTH] {portal}/{env} — URL after initial wait: {current_url}")

            # ── Force-navigate if still on /login ────────────────────────────────
            if "/login" in current_url:
                _log("Still on /login — forcing JS navigation to target", "warn", current_url)
                _take_screenshot(page, f"pre_force_nav_{portal}_{env}")
                page.evaluate(f"window.location.href = '{nav_target}'")
                _log("JS navigation triggered, waiting for networkidle", "ok")
                try:
                    page.wait_for_load_state("networkidle", timeout=30000)
                except Exception:
                    _log("networkidle timeout after force-nav — continuing", "warn")
                page.wait_for_timeout(3000)
                current_url = page.url
                print(f"[AUTH] {portal}/{env} — URL after force-nav: {current_url}")

            load_time_ms = int((time.time() - t0) * 1000)
            _log(f"Initial navigation → {first_path}", "ok", current_url)

            # ── Auth check: fail fast if auth failed ──────────────────────────
            auth_ok = "/login" not in current_url
            if not auth_ok:
                err_msg = f"Auth failed after force-nav — run: python3 tools/auth_setup.py {portal} {env}"
                _log("Auth check failed", "fail", err_msg)
                feature_evidence.append({
                    "selector":    "N/A",
                    "description": "Auth session check",
                    "found":       False,
                    "detail":      f"Still on {current_url} after force-nav",
                })
                overall_status = "FAIL"
                _take_screenshot(page, f"auth_failed_{portal}_{env}")

            for tc in test_cases:
                if not auth_ok:
                    break
                tc_name = tc.get("test_name", "Unnamed test")
                _log(f"── Test case: {tc_name} ──", "ok")
                tc_pass = True

                # Navigate to test case URL
                url_path = tc.get("url_path") or "/"
                try:
                    page.goto(base_url + url_path, timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(1500)
                    _log(f"NAVIGATE to {url_path}", "pass", page.url)
                    steps_executed += 1
                except Exception as e:
                    _log(f"NAVIGATE to {url_path}", "fail", str(e))
                    tc_pass = False

                # Execute each step
                for step_str in (tc.get("steps") or []):
                    step_str = step_str.strip()
                    if not step_str:
                        continue
                    try:
                        if step_str.startswith("CLICK:"):
                            sel = step_str[6:].strip()
                            page.wait_for_selector(sel, timeout=8000)
                            page.click(sel, timeout=8000)
                            _log(f"CLICK: {sel}", "pass")
                            steps_executed += 1

                        elif step_str.startswith("FILL:"):
                            parts = step_str[5:].split("|", 1)
                            sel   = parts[0].strip()
                            val   = parts[1].strip() if len(parts) > 1 else ""
                            page.wait_for_selector(sel, timeout=8000)
                            page.fill(sel, val)
                            _log(f"FILL: {sel} → '{val}'", "pass")
                            steps_executed += 1

                        elif step_str.startswith("WAIT:"):
                            sel = step_str[5:].strip()
                            page.wait_for_selector(sel, timeout=10000)
                            _log(f"WAIT: {sel}", "pass")
                            steps_executed += 1

                        elif step_str.startswith("NAVIGATE:"):
                            path = step_str[9:].strip()
                            page.goto(base_url + path, timeout=30000, wait_until="domcontentloaded")
                            page.wait_for_timeout(1500)
                            _log(f"NAVIGATE: {path}", "pass", page.url)
                            steps_executed += 1

                        elif step_str.startswith("ASSERT_EXISTS:"):
                            sel = step_str[14:].strip()
                            found = bool(page.query_selector(sel))
                            if found:
                                _log(f"ASSERT_EXISTS: {sel}", "pass")
                            else:
                                _log(f"ASSERT_EXISTS: {sel}", "fail", "Element not found")
                                tc_pass = False
                            steps_executed += 1

                        elif step_str.startswith("ASSERT_NOT_EXISTS:"):
                            sel = step_str[18:].strip()
                            found = bool(page.query_selector(sel))
                            if not found:
                                _log(f"ASSERT_NOT_EXISTS: {sel}", "pass")
                            else:
                                _log(f"ASSERT_NOT_EXISTS: {sel}", "fail", "Element unexpectedly present")
                                tc_pass = False
                            steps_executed += 1

                        elif step_str.startswith("ASSERT_TEXT:"):
                            parts    = step_str[12:].split("|", 1)
                            sel      = parts[0].strip()
                            expected = parts[1].strip() if len(parts) > 1 else ""
                            el = page.query_selector(sel)
                            if el:
                                actual = el.inner_text()
                                if expected.lower() in actual.lower():
                                    _log(f"ASSERT_TEXT: {sel}", "pass", f"Found '{expected}'")
                                else:
                                    _log(f"ASSERT_TEXT: {sel}", "fail",
                                         f"Expected '{expected}' in '{actual[:100]}'")
                                    tc_pass = False
                            else:
                                _log(f"ASSERT_TEXT: {sel}", "fail", "Element not found")
                                tc_pass = False
                            steps_executed += 1

                        elif step_str.startswith("SCREENSHOT:"):
                            label = step_str[11:].strip()
                            _take_screenshot(page, label)
                            steps_executed += 1

                        else:
                            _log(f"UNKNOWN step (skipped): {step_str[:80]}", "skip")

                    except Exception as e:
                        _log(f"ERROR — {step_str[:80]}", "fail", str(e))
                        tc_pass = False

                # Check evidence selector
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
                        if found:
                            _log(f"Evidence PASS: {ev_sel}", "pass", detail)
                        else:
                            _log(f"Evidence FAIL: {ev_sel}", "fail", "Selector not found on page")
                            tc_pass = False
                    except Exception as e:
                        _log(f"Evidence ERROR: {ev_sel}", "fail", str(e))
                        tc_pass = False

                # Screenshot after each test case
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

    # Hard guard: zero steps executed → FAIL regardless
    if steps_executed == 0:
        overall_status = "FAIL"
        _log("No steps executed — result forced to FAIL", "fail")

    # Build human-readable message
    auth_ev = next((e for e in feature_evidence if e.get("description") == "Auth session check" and not e.get("found")), None)
    if auth_ev:
        message = f"Session expired — run: python3 tools/auth_setup.py {portal} {env}"
    else:
        message = (
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

import json
import os
import subprocess
import time
from datetime import datetime
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

    try:
        auth_file = get_auth_file(portal, env)
    except FileNotFoundError as e:
        return ("FAIL", {
            "status": "FAIL", "message": str(e), "url": None,
            "console_errors": [], "nav_elements_found": [], "load_time_ms": 0,
            "screenshot_path": None, "screenshots": [],
            "execution_log": [{"step": "Load auth session", "result": "fail", "detail": str(e)}],
            "feature_evidence": [],
        })

    local_process = None
    if env == "local":
        local_process = start_local_server()

    with open(auth_file) as f:
        auth_data = json.load(f)
    auth_storage_value = None
    for origin in auth_data.get("origins", []):
        for item in origin.get("localStorage", []):
            if item["name"] == "auth-storage":
                auth_storage_value = item["value"]
                break

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
                 f"Auth: {portal}_{env}.json")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=auth_file)
            page    = context.new_page()

            def _capture_console(msg):
                if msg.type == "error":
                    console_errors.append(msg.text)
            page.on("console", _capture_console)

            if auth_storage_value:
                page.add_init_script(f"""
                    localStorage.setItem('auth-storage', {json.dumps(auth_storage_value)});
                """)
                _log("Injected auth-storage via localStorage init script", "ok")

            _log(f"Navigate to target: {target_url}", "ok", f"Expected path: {expected}")
            t0 = time.time()
            page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            _screenshot(page, f"After auth — {portal}")

            page.wait_for_timeout(2000)
            load_time_ms = int((time.time() - t0) * 1000)
            current_url  = page.url
            _log(f"Page settled at {current_url}", "ok", f"Total load time: {load_time_ms}ms")

            if expected and expected in current_url:
                status  = "PASS"
                message = f"Logged in successfully. Landed on: {current_url}"
                _log(f"URL check PASS — '{expected}' present in URL", "pass", current_url)
            elif "/login" in current_url:
                status  = "FAIL"
                message = f"Redirected to login — session may be expired. URL: {current_url}"
                _log("URL check FAIL — redirected to /login (session expired?)", "fail", current_url)
            else:
                status  = "FAIL"
                message = f"Unexpected URL after auth (expected '{expected}'). URL: {current_url}"
                _log(f"URL check FAIL — unexpected path", "fail",
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
                        # capture meaningful attributes as evidence
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
                                       (f"Element present" if found else "Element not found"),
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

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

# Nav selectors checked after a successful login — order matters (most specific first)
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


def get_auth_file(portal, env):
    """Return path to the saved auth JSON for (portal, env). Raises if missing."""
    path = os.path.join(AUTH_DIR, f"{portal}_{env}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Auth session not found: {path}\n"
            f"Run this first:  python tools/auth_setup.py {portal} {env}"
        )
    return path


def start_local_server():
    """Start the frontend dev server and return the process handle."""
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
    """Terminate the dev server process."""
    if process and process.poll() is None:
        process.terminate()
        process.wait()
        print("Dev server stopped.")


def run_tests(portal, env):
    """
    Run a full login + post-login validation test for the given portal and environment.

    Returns a tuple: (status, result_dict) where status is "PASS" | "FAIL" and
    result_dict contains:
      - status, message, url
      - console_errors: list of JS console error strings
      - nav_elements_found: list of matched CSS selectors (empty on FAIL)
      - load_time_ms: int (ms from navigation start to page settled)
      - screenshot_path: saved full-page screenshot path
    """
    portal = portal.lower()
    env = env.lower()

    url = URL_MAP.get(env)
    if not url:
        result = {
            "status": "FAIL",
            "message": f"Unknown environment '{env}'. Choose: local, staging, production.",
            "url": None, "console_errors": [], "nav_elements_found": [], "load_time_ms": 0,
            "screenshot_path": None,
        }
        return ("FAIL", result)

    try:
        auth_file = get_auth_file(portal, env)
    except FileNotFoundError as e:
        result = {
            "status": "FAIL", "message": str(e), "url": None,
            "console_errors": [], "nav_elements_found": [], "load_time_ms": 0,
            "screenshot_path": None,
        }
        return ("FAIL", result)

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
    expected = success_slugs.get(portal, "")
    base_url = url.rstrip("/").split("/login")[0]
    target_url = base_url + expected

    console_errors = []
    nav_elements_found = []
    load_time_ms = 0
    current_url = target_url
    screenshot_path = None
    status = "FAIL"
    message = "Test did not complete"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=auth_file)
            page = context.new_page()

            def _capture_console(msg):
                if msg.type == "error":
                    console_errors.append(msg.text)
            page.on("console", _capture_console)

            if auth_storage_value:
                page.add_init_script(f"""
                    localStorage.setItem('auth-storage', {json.dumps(auth_storage_value)});
                """)

            print(f"Navigating to {target_url} as {portal} ({env})...")
            t0 = time.time()
            page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            load_time_ms = int((time.time() - t0) * 1000)

            current_url = page.url

            if expected and expected in current_url:
                status = "PASS"
                message = f"Logged in successfully. Landed on: {current_url}"
            elif "/login" in current_url:
                status = "FAIL"
                message = f"Redirected to login — session may be expired. URL: {current_url}"
            else:
                status = "FAIL"
                message = f"Unexpected URL after auth (expected path '{expected}'). URL: {current_url}"

            # Post-login checks (only meaningful on PASS)
            if status == "PASS":
                for selector in _NAV_SELECTORS:
                    try:
                        if page.query_selector(selector):
                            nav_elements_found.append(selector)
                    except Exception:
                        pass

            # Full-page screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(
                SCREENSHOTS_DIR, f"{portal}_{env}_{status}_{timestamp}.png"
            )
            try:
                page.screenshot(path=screenshot_path, full_page=True, timeout=15000)
                print(f"Screenshot saved: {screenshot_path}")
            except Exception:
                print("Screenshot skipped (timeout or rendering error)")
                screenshot_path = None

            browser.close()

    except Exception as e:
        status = "FAIL"
        message = f"Playwright error: {e}"
    finally:
        if local_process:
            stop_local_server(local_process)

    result = {
        "status": status,
        "message": message,
        "url": current_url,
        "console_errors": console_errors,
        "nav_elements_found": nav_elements_found,
        "load_time_ms": load_time_ms,
        "screenshot_path": screenshot_path,
    }
    print(f"[{status}] {portal}/{env} — {message} | load:{load_time_ms}ms | "
          f"console_errors:{len(console_errors)} | nav_elements:{len(nav_elements_found)}")
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

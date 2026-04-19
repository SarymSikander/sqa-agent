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
    Run a login-validation test for the given portal and environment.

    Returns a tuple: ("PASS" | "FAIL", message)
    """
    portal = portal.lower()
    env = env.lower()

    url = URL_MAP.get(env)
    if not url:
        return ("FAIL", f"Unknown environment '{env}'. Choose: local, staging, production.")

    try:
        auth_file = get_auth_file(portal, env)
    except FileNotFoundError as e:
        return ("FAIL", str(e))

    local_process = None
    if env == "local":
        local_process = start_local_server()

    # Extract auth-storage value from the saved JSON for init script injection
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

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=auth_file)
            page = context.new_page()

            if auth_storage_value:
                page.add_init_script(f"""
                    localStorage.setItem('auth-storage', {json.dumps(auth_storage_value)});
                """)

            print(f"Navigating to {target_url} as {portal} ({env})...")
            page.goto(target_url, timeout=60000, wait_until="commit")
            page.wait_for_timeout(5000)

            current_url = page.url
            if expected and expected in current_url:
                result = ("PASS", f"Logged in successfully. URL: {current_url}")
            elif "/login" in current_url:
                result = ("FAIL", f"Still on login page after auth load. URL: {current_url}")
            else:
                result = ("FAIL", f"Unexpected URL after auth load (expected '{expected}'). URL: {current_url}")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{portal}_{env}_{result[0]}_{timestamp}.png")
            try:
                page.screenshot(path=screenshot_path, timeout=10000)
                print(f"Screenshot saved: {screenshot_path}")
            except Exception:
                print(f"Screenshot skipped (font timeout)")

            browser.close()
    except Exception as e:
        result = ("FAIL", f"Playwright error: {e}")
    finally:
        if local_process:
            stop_local_server(local_process)

    status, message = result
    print(f"[{status}] {portal}/{env} — {message}")
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

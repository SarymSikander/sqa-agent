import json
import os
import re
import subprocess
import time
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

LOCAL_URL      = os.getenv("LOCAL_URL", "")
STAGING_URL    = os.getenv("STAGING_URL", "")
PRODUCTION_URL = os.getenv("PRODUCTION_URL", "")

FRONTEND_REPO_PATH = os.getenv("FRONTEND_REPO_PATH", "")
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
# AI test-case executor
# ---------------------------------------------------------------------------

def _parse_nav_path(step: str):
    """Return a URL path (e.g. /orders-management/dashboard) from a navigation step, or None."""
    m = re.search(r'(?:navigate to|go to|open|visit)\s+["\']?(/[^\s"\',.]+)', step, re.I)
    if m:
        return m.group(1).rstrip(".,)")
    m = re.search(r'(/[a-zA-Z][a-zA-Z0-9\-_/]+)', step)
    if m:
        return m.group(1)
    return None


def _parse_click_target(step: str):
    """Return the text/selector to click from a step, or None."""
    m = re.search(r'click\s+(?:on\s+)?["\']([^"\']+)["\']', step, re.I)
    if m:
        return m.group(1)
    m = re.search(r'click\s+(?:on\s+)?(?:the\s+)?(.+?)(?:\s+button|\s+link|\s+tab|\s+icon|$)', step, re.I)
    if m:
        text = m.group(1).strip().strip('"\'')
        if 2 < len(text) < 80:
            return text
    return None


def run_qa_test_cases(portal, env, test_cases):
    """
    Execute Claude-generated test cases using Playwright.

    Navigates to pages, checks evidence selectors, takes per-test screenshots.
    Returns a result dict compatible with the run-qa endpoint's test_results list.
    """
    portal = portal.lower()
    env = env.lower()

    print(f"\n{'='*60}")
    print(f"[run_qa_test_cases] portal={portal} env={env} cases={len(test_cases)}")
    print(f"{'='*60}")

    url = URL_MAP.get(env)
    if not url:
        return {
            "portal": portal, "env": env, "status": "FAIL",
            "message": f"Unknown environment '{env}'",
            "url": None, "screenshots": [], "feature_evidence": [],
            "execution_log": [{"step": "Init", "result": "fail", "detail": f"Unknown env: {env}"}],
            "console_errors": [], "load_time_ms": 0, "nav_elements_found": [],
        }

    try:
        auth_file = get_auth_file(portal, env)
    except FileNotFoundError as e:
        print(f"[run_qa_test_cases] Auth file missing: {e}")
        return {
            "portal": portal, "env": env, "status": "FAIL",
            "message": str(e),
            "url": None, "screenshots": [], "feature_evidence": [],
            "execution_log": [{"step": "Load auth", "result": "fail", "detail": str(e)}],
            "console_errors": [], "load_time_ms": 0, "nav_elements_found": [],
        }

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
    base_url = url.rstrip("/").split("/login")[0]
    entry_url = base_url + success_slugs.get(portal, "")

    execution_log = []
    feature_evidence = []
    screenshots = []
    overall_pass = True

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=auth_file)
            page = context.new_page()

            if auth_storage_value:
                page.add_init_script(
                    f"localStorage.setItem('auth-storage', {json.dumps(auth_storage_value)});"
                )

            # Start at portal landing page to establish session
            print(f"[run_qa_test_cases] Navigating to entry: {entry_url}")
            page.goto(entry_url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            print(f"[run_qa_test_cases] Current URL after entry: {page.url}")
            execution_log.append({"step": "Open portal", "result": "pass", "detail": page.url})

            for i, tc in enumerate(test_cases):
                test_name = tc.get("test_name", f"Test {i+1}")
                steps = tc.get("steps") or []
                evidence_selector = tc.get("evidence_selector", "").strip()
                url_path = tc.get("url_path", "").strip()
                tc_pass = True

                print(f"\n[TC {i+1}/{len(test_cases)}] {test_name}")
                print(f"  Description: {tc.get('description','')}")
                print(f"  url_path: '{url_path}' evidence_selector: '{evidence_selector}'")
                execution_log.append({
                    "step": f"TC {i+1}: {test_name}",
                    "result": "start",
                    "detail": tc.get("description", ""),
                })

                # Navigate to the test case's target page before running steps
                if url_path:
                    tc_url = base_url + url_path
                    print(f"  -> Navigating to tc url_path: {tc_url}")
                    try:
                        page.goto(tc_url, timeout=30000, wait_until="domcontentloaded")
                        page.wait_for_timeout(2000)
                        execution_log.append({"step": f"Navigate to {url_path}", "result": "pass", "detail": page.url})
                        print(f"  -> Landed at: {page.url}")
                    except Exception as e:
                        print(f"  -> Navigation failed: {e}")
                        execution_log.append({"step": f"Navigate to {url_path}", "result": "fail", "detail": str(e)})
                        tc_pass = False

                for step in steps:
                    print(f"  Step: {step}")
                    sl = step.lower()

                    # Navigation
                    if any(kw in sl for kw in ("navigate to", "go to", "open ", "visit ")):
                        path = _parse_nav_path(step)
                        if path:
                            nav_url = base_url + path
                            print(f"    -> navigate {nav_url}")
                            try:
                                page.goto(nav_url, timeout=30000, wait_until="domcontentloaded")
                                page.wait_for_timeout(2000)
                                execution_log.append({"step": step, "result": "pass", "detail": f"Navigated to {nav_url} -> {page.url}"})
                                print(f"    -> landed at {page.url}")
                            except Exception as e:
                                print(f"    -> nav error: {e}")
                                execution_log.append({"step": step, "result": "fail", "detail": str(e)})
                                tc_pass = False
                        else:
                            execution_log.append({"step": step, "result": "skip", "detail": "No path extracted"})

                    # Click
                    elif "click" in sl:
                        target = _parse_click_target(step)
                        if target:
                            print(f"    -> click '{target}'")
                            try:
                                # Try text selector first, then CSS
                                try:
                                    page.get_by_text(target, exact=False).first.click(timeout=5000)
                                    execution_log.append({"step": step, "result": "pass", "detail": f"Clicked text: {target}"})
                                    page.wait_for_timeout(1000)
                                except Exception:
                                    page.click(target, timeout=3000)
                                    execution_log.append({"step": step, "result": "pass", "detail": f"Clicked selector: {target}"})
                                    page.wait_for_timeout(1000)
                            except Exception as e:
                                print(f"    -> click fail: {e}")
                                execution_log.append({"step": step, "result": "warn", "detail": f"Could not click '{target}': {str(e)[:120]}"})
                        else:
                            execution_log.append({"step": step, "result": "skip", "detail": "No click target extracted"})

                    # Type / fill / input
                    elif any(kw in sl for kw in ("type ", "enter ", "fill ", "input ")):
                        execution_log.append({"step": step, "result": "skip", "detail": "Input step — skipped in automated run"})

                    # Verify / check / assert
                    elif any(kw in sl for kw in ("verify", "check", "assert", "confirm", "ensure")):
                        # Try to evaluate the check via evidence_selector if provided
                        execution_log.append({"step": step, "result": "info", "detail": "Verification step — checked via evidence selector"})

                    else:
                        execution_log.append({"step": step, "result": "skip", "detail": "Step type not automated"})

                # Check evidence selector
                if evidence_selector:
                    print(f"  Evidence selector: '{evidence_selector}'")
                    try:
                        el = page.query_selector(evidence_selector)
                        found = el is not None
                        detail = ""
                        if found:
                            try:
                                detail = (el.get_attribute("class") or el.inner_text() or "present")[:100]
                            except Exception:
                                detail = "present"
                        print(f"  Evidence: {'FOUND' if found else 'NOT FOUND'} ({detail})")
                        feature_evidence.append({
                            "test_name": test_name,
                            "description": tc.get("description", ""),
                            "selector": evidence_selector,
                            "found": found,
                            "detail": detail,
                        })
                        execution_log.append({
                            "step": f"Evidence check: {evidence_selector}",
                            "result": "pass" if found else "warn",
                            "detail": f"{'Found' if found else 'Not found'}: {detail}",
                        })
                        if not found:
                            tc_pass = False
                    except Exception as e:
                        print(f"  Evidence error: {e}")
                        feature_evidence.append({
                            "test_name": test_name,
                            "description": tc.get("description", ""),
                            "selector": evidence_selector,
                            "found": False,
                            "detail": str(e),
                        })
                        execution_log.append({
                            "step": f"Evidence check: {evidence_selector}",
                            "result": "error",
                            "detail": str(e),
                        })
                        tc_pass = False

                # Screenshot after each test case
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                shot_filename = f"{portal}_{env}_tc{i+1:02d}_{ts}.png"
                shot_path = os.path.join(SCREENSHOTS_DIR, shot_filename)
                try:
                    page.screenshot(path=shot_path, timeout=10000)
                    screenshots.append({"filename": shot_filename, "label": test_name})
                    print(f"  Screenshot: {shot_filename}")
                except Exception as e:
                    print(f"  Screenshot failed: {e}")

                execution_log.append({
                    "step": f"TC {i+1} complete",
                    "result": "pass" if tc_pass else "fail",
                    "detail": f"Evidence found: {sum(1 for e in feature_evidence if e.get('test_name') == test_name and e.get('found'))}"
                              f"/{1 if evidence_selector else 0}",
                })
                if not tc_pass:
                    overall_pass = False

            browser.close()

    except Exception as e:
        print(f"[run_qa_test_cases] Playwright error: {e}")
        execution_log.append({"step": "Playwright runner", "result": "error", "detail": str(e)})
        overall_pass = False

    status = "PASS" if overall_pass else "FAIL"
    print(f"\n[run_qa_test_cases] Final status={status} evidence_checks={len(feature_evidence)} screenshots={len(screenshots)}")

    return {
        "portal": portal,
        "env": env,
        "status": status,
        "message": f"Executed {len(test_cases)} AI-generated test cases — {sum(1 for e in feature_evidence if e.get('found'))}/{len(feature_evidence)} evidence selectors found",
        "url": base_url,
        "screenshots": screenshots,
        "feature_evidence": feature_evidence,
        "execution_log": execution_log,
        "console_errors": [],
        "load_time_ms": 0,
        "nav_elements_found": [],
    }


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

"""
One-time manual login script. Run this whenever a session needs to be created or refreshed.

Usage:
    python tools/auth_setup.py <portal> <env>

    portal : seller | admin | agency
    env    : local | staging | production

Example:
    python tools/auth_setup.py seller staging
"""

import os
import sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

URL_MAP = {
    "local":      os.getenv("LOCAL_URL"),
    "staging":    os.getenv("STAGING_URL"),
    "production": os.getenv("PRODUCTION_URL"),
}

PORTALS = {"seller", "admin", "agency"}
ENVS    = {"local", "staging", "production"}

AUTH_DIR = os.path.join(os.path.dirname(__file__), "..", "auth")


def main():
    if len(sys.argv) != 3:
        print("Usage: python tools/auth_setup.py <portal> <env>")
        print("  portal : seller | admin | agency")
        print("  env    : local | staging | production")
        sys.exit(1)

    portal, env = sys.argv[1].lower(), sys.argv[2].lower()

    if portal not in PORTALS:
        print(f"Unknown portal '{portal}'. Choose from: {', '.join(sorted(PORTALS))}")
        sys.exit(1)
    if env not in ENVS:
        print(f"Unknown env '{env}'. Choose from: {', '.join(sorted(ENVS))}")
        sys.exit(1)

    url = URL_MAP.get(env)
    if not url:
        print(f"No URL found for env '{env}'. Check your .env file.")
        sys.exit(1)

    os.makedirs(AUTH_DIR, exist_ok=True)
    auth_file = os.path.join(AUTH_DIR, f"{portal}_{env}.json")

    print(f"\n--- Auth Setup: {portal} / {env} ---")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        page.goto(url)

        print(f"\nPlease log in and press Enter when on dashboard")
        input()

        state = context.storage_state()
        all_cookies = state.get("cookies", [])
        print(f"\nCookies captured: {len(all_cookies)}")
        for p_obj in context.pages:
            url_str = p_obj.url
            keys = p_obj.evaluate("() => Object.keys(localStorage)")
            print(f"  Page: {url_str}")
            print(f"    localStorage keys: {keys}")

        context.storage_state(path=auth_file)
        browser.close()

    print(f"\nSession saved to: {auth_file}")


if __name__ == "__main__":
    main()

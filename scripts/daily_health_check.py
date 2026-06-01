"""
Daily health check script.
Run from the project root:  python scripts/daily_health_check.py
Scheduled via launchd:      com.zambeel.sqa.daily.plist (9:00 AM daily)
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.report_tool import generate_health_report
from tools.slack_tool import send_alert, send_health_report

ENV = "staging"

SYSTEM_DATA_PATHS = [
    Path(__file__).resolve().parent.parent / "knowledge" / "shared" / "system_data.md",
    Path(__file__).resolve().parent.parent / "dashboard" / "api" / "knowledge" / "shared" / "system_data.md",
]


def refresh_system_data():
    """Query production DB for live counts and patch the LIVE_COUNTS block in system_data.md."""
    print("Refreshing system_data.md from production DB...")
    try:
        # Import db_tool from dashboard/api/tools (has the full implementation)
        api_dir = Path(__file__).resolve().parent.parent / "dashboard" / "api"
        sys.path.insert(0, str(api_dir))
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=True)

        import tools.db_tool as db

        # Point at production using root .env credentials
        db._DB_CONFIG["production"] = {
            "host":     os.getenv("PRODUCTION_DB_HOST"),
            "port":     int(os.getenv("PRODUCTION_DB_PORT", 3306)),
            "user":     os.getenv("PRODUCTION_DB_USER"),
            "password": os.getenv("PRODUCTION_DB_PASSWORD"),
            "database": os.getenv("PRODUCTION_DB_NAME"),
        }

        counts = {
            "Total Orders":    db.run_query("production", "SELECT COUNT(*) AS n FROM orders")[0]["n"],
            "Total Tickets":   db.run_query("production", "SELECT COUNT(*) AS n FROM tickets")[0]["n"],
            "Total Stores":    db.run_query("production", "SELECT COUNT(*) AS n FROM stores")[0]["n"],
            "Total Users":     db.run_query("production", "SELECT COUNT(*) AS n FROM users")[0]["n"],
            "Supported Countries": db.run_query("production", "SELECT COUNT(*) AS n FROM countries")[0]["n"],
        }

        print("  Counts fetched:", counts)

    except Exception as e:
        print(f"  DB refresh failed: {e}")
        return

    # Build replacement block
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = "\n".join(f"| {k} | {v:,} |" for k, v in counts.items())
    new_block = (
        f"<!-- LIVE_COUNTS_START -->\n"
        f"_Last updated: {now}_\n\n"
        f"| Metric | Count |\n"
        f"|--------|-------|\n"
        f"{rows}\n"
        f"<!-- LIVE_COUNTS_END -->"
    )

    # Patch every copy of system_data.md
    pattern = re.compile(
        r"<!-- LIVE_COUNTS_START -->.*?<!-- LIVE_COUNTS_END -->",
        re.DOTALL,
    )
    for path in SYSTEM_DATA_PATHS:
        if not path.exists():
            print(f"  Skipping (not found): {path}")
            continue
        original = path.read_text()
        updated = pattern.sub(new_block, original)
        if updated != original:
            path.write_text(updated)
            print(f"  Updated: {path}")
        else:
            print(f"  No LIVE_COUNTS block found in: {path}")


def main():
    # Refresh system_data.md first so the knowledge base is current
    refresh_system_data()

    print(f"Running daily health check for {ENV}...")

    report_path = generate_health_report(ENV)
    send_health_report(report_path)

    # Detect failures from the saved report without re-running tests
    with open(report_path) as f:
        content = f.read()

    overall = re.search(r"\*\*Overall Status:\*\*\s*(.+)", content)
    is_fail = overall and "FAIL" in overall.group(1).upper()

    if is_fail:
        failed_portals = re.findall(r"\|\s*(seller|admin|agency)\s*\|[^|]*❌[^|]*\|", content)
        portal_list    = ", ".join(failed_portals) if failed_portals else "unknown"
        send_alert(
            title=f"Health Check FAILED — {ENV.upper()}",
            message=(
                f"One or more portal login tests failed on *{ENV}*.\n"
                f"Failed portals: *{portal_list}*\n"
                f"Report: `{os.path.basename(report_path)}`"
            ),
            severity="critical",
        )

    print("Daily health check complete.")


if __name__ == "__main__":
    main()

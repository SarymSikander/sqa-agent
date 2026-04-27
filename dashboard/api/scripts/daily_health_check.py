"""
Daily health check script.
Run from the project root:  python scripts/daily_health_check.py
Scheduled via launchd:      com.zambeel.sqa.daily.plist (9:00 AM daily)
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.report_tool import generate_health_report
from tools.slack_tool import send_alert, send_health_report

ENV = "production"


def main():
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

import os
import re

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

_SEVERITY_ICON = {
    "info":     "🟢",
    "warning":  "🟡",
    "critical": "🔴",
}

_SEVERITY_COLOR = {
    "info":     "#36a64f",
    "warning":  "#ffcc00",
    "critical": "#cc0000",
}


def _post(payload):
    """POST a payload dict to the Slack webhook. Raises on HTTP error."""
    if not SLACK_WEBHOOK_URL:
        raise ValueError("SLACK_WEBHOOK_URL is not set in .env")
    r = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    r.raise_for_status()
    return r.text


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def send_message(text):
    """Send a plain text message to Slack."""
    response = _post({"text": text})
    print(f"Slack message sent. Response: {response}")
    return response


def send_health_report(report_path):
    """
    Read a markdown health report and send a formatted Slack message with
    environment, timestamp, pass/fail summary, and DB stats.
    """
    with open(report_path) as f:
        content = f.read()

    # Parse key fields from the markdown
    env       = _extract(r"\*\*Environment:\*\*\s*(\S+)", content, "unknown")
    timestamp = _extract(r"\*\*Generated:\*\*\s*(.+?)  ", content, "unknown")
    overall   = _extract(r"\*\*Overall Status:\*\*\s*(.+)", content, "unknown")
    summary   = _extract(r"\*\*Summary:\*\*\s*(.+)", content, "")

    # Collect portal rows from the test table
    portal_lines = re.findall(r"\|\s*(seller|admin|agency)\s*\|\s*(.*?)\s*\|.*?\|", content)
    portal_text  = "\n".join(f"  • *{p}*: {s.strip()}" for p, s in portal_lines)

    # Extract only the ## Database Health section (stop at the next ## heading)
    db_section_match = re.search(r"## Database.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    db_section = db_section_match.group(1).strip() if db_section_match else ""

    # Look for actual DB metric rows (table rows with a numeric value in the second column)
    db_rows = re.findall(r"\|\s*`?([^`|]+)`?\s*\|\s*([^|]+)\s*\|", db_section)
    _skip = {"metric", "table", "status", "detail", "---", ""}
    db_entries = [
        f"  • {k.strip()}: *{v.strip()}*"
        for k, v in db_rows
        if k.strip().lower() not in _skip
        and not k.strip().startswith("-")
        and re.search(r"\d", v)
    ]
    # Fall back to not-configured if section is empty or has no numeric data
    db_text = "\n".join(db_entries) if db_entries else None

    is_pass = "PASS" in overall.upper()
    color   = _SEVERITY_COLOR["info"] if is_pass else _SEVERITY_COLOR["critical"]
    icon    = "✅" if is_pass else "❌"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{icon} Zambeel Health Report — {env.upper()}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Generated:*\n{timestamp}"},
                {"type": "mrkdwn", "text": f"*Overall:*\n{overall}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Portal Tests*\n{portal_text or '_No portal results found._'}"},
        },
    ]

    if summary:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Summary:* {summary}"},
        })

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Database Stats*\n{db_text}" if db_text else "*Database Stats*\n  _not configured (no credentials)_",
        },
    })

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": blocks,
            }
        ]
    }

    response = _post(payload)
    print(f"Slack health report sent. Response: {response}")
    return response


def send_alert(title, message, severity="info"):
    """
    Send a color-coded alert. severity: 'info' | 'warning' | 'critical'.
    """
    severity  = severity.lower()
    icon      = _SEVERITY_ICON.get(severity, "🟢")
    color     = _SEVERITY_COLOR.get(severity, _SEVERITY_COLOR["info"])

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"{icon} {title}"},
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": message},
                    },
                    {
                        "type": "context",
                        "elements": [{"type": "mrkdwn", "text": f"Severity: *{severity.upper()}*"}],
                    },
                ],
            }
        ]
    }

    response = _post(payload)
    print(f"Slack alert sent [{severity}]. Response: {response}")
    return response


def send_test_results(results):
    """
    Send a formatted table of test results to Slack.
    results: list of dicts with keys: portal, env, status, message
    """
    passed = sum(1 for r in results if r.get("status") == "PASS")
    total  = len(results)
    icon   = "✅" if passed == total else "❌"

    rows = "\n".join(
        f"  {'✅' if r.get('status') == 'PASS' else '❌'} *{r.get('portal', '?')}/{r.get('env', '?')}*: {r.get('message', '')}"
        for r in results
    )

    payload = {
        "attachments": [
            {
                "color": _SEVERITY_COLOR["info"] if passed == total else _SEVERITY_COLOR["critical"],
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"{icon} SQA Test Results — {passed}/{total} passed"},
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": rows or "_No results._"},
                    },
                ],
            }
        ]
    }

    response = _post(payload)
    print(f"Slack test results sent. Response: {response}")
    return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract(pattern, text, default=""):
    m = re.search(pattern, text)
    return m.group(1).strip() if m else default

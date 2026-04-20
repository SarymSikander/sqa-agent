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
    Read a markdown health report and send a rich, structured Slack message
    with per-portal URLs, console error counts, nav checks, load times,
    overall health score, and DB status.
    """
    with open(report_path) as f:
        content = f.read()

    env          = _extract(r"\*\*Environment:\*\*\s*(\S+)", content, "unknown")
    timestamp    = _extract(r"\*\*Generated:\*\*\s*(.+?)  ", content, "unknown")
    overall      = _extract(r"\*\*Overall Status:\*\*\s*(.+?)  ", content,
                             _extract(r"\*\*Overall Status:\*\*\s*(.+)", content, "unknown"))
    health_score = _extract(r"\*\*Health Score:\*\*\s*(\d+%)", content, "—")
    summary      = _extract(r"\*\*Summary:\*\*\s*(.+)", content, "")

    is_pass = "PASS" in overall.upper()
    color   = _SEVERITY_COLOR["info"] if is_pass else _SEVERITY_COLOR["critical"]
    status_icon = "✅" if is_pass else "❌"

    # ── Parse per-portal table rows ──────────────────────────────────────────
    # Table columns: Portal | Status | URL | Console Errors | Nav Check | Load Time
    portal_rows = re.findall(
        r"\|\s*(seller|admin|agency)\s*\|\s*([^|]+)\s*\|\s*`?([^`|]*)`?\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|",
        content,
    )

    portal_blocks = []
    for row in portal_rows:
        portal, p_status, url, console_errs, nav_check, load_time = [c.strip() for c in row]
        p_icon = "✅" if "PASS" in p_status.upper() else "❌"
        url_display = url if url and url != "—" else "_no URL captured_"
        errs_display = console_errs if console_errs else "✅ 0 errors"
        nav_display  = nav_check if nav_check else "—"
        load_display = load_time if load_time else "—"

        portal_blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*{p_icon} {portal.upper()}*\n`{url_display}`"},
                {"type": "mrkdwn", "text": f"*Console Errors:* {errs_display}\n*Nav Elements:* {nav_display}\n*Load Time:* {load_display}"},
            ],
        })

    # Fall back if new table format not found (old reports)
    if not portal_rows:
        legacy = re.findall(r"\|\s*(seller|admin|agency)\s*\|\s*(.*?)\s*\|.*?\|", content)
        for portal, p_status in legacy:
            p_icon = "✅" if "PASS" in p_status.upper() else "❌"
            portal_blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{p_icon} *{portal.upper()}*: {p_status.strip()}"},
            })

    # ── Parse DB section ─────────────────────────────────────────────────────
    db_section_match = re.search(r"## Database.*?\n(.*?)(?=\n---|\Z)", content, re.DOTALL)
    db_raw = db_section_match.group(1).strip() if db_section_match else ""
    db_rows = re.findall(r"\|\s*`?([^`|]+)`?\s*\|\s*([^|]+)\s*\|", db_raw)
    _skip = {"metric", "table", "status", "detail", "---", ""}
    db_entries = [
        f"• {k.strip()}: *{v.strip()}*"
        for k, v in db_rows
        if k.strip().lower() not in _skip
        and not k.strip().startswith("-")
        and re.search(r"\d", v)
    ]
    db_text = "\n".join(db_entries) if db_entries else "_Not configured — no credentials set._"

    # ── Console error details ─────────────────────────────────────────────────
    err_section_match = re.search(r"### Console Errors Detail\n(.*?)(?=\n---|\n##|\Z)", content, re.DOTALL)
    err_detail = err_section_match.group(1).strip() if err_section_match else ""

    # ── Assemble Slack blocks ─────────────────────────────────────────────────
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{status_icon}  Zambeel SQA — {env.upper()} Health Report",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Environment:*\n{env.upper()}"},
                {"type": "mrkdwn", "text": f"*Generated:*\n{timestamp}"},
                {"type": "mrkdwn", "text": f"*Overall Status:*\n{status_icon} {'All portals healthy' if is_pass else 'Issues detected'}"},
                {"type": "mrkdwn", "text": f"*Health Score:*\n{health_score}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Portal Test Results*  |  {summary}"},
        },
    ]

    blocks.extend(portal_blocks)
    blocks.append({"type": "divider"})

    if err_detail:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*⚠️ Console Errors Detected*\n```{err_detail[:600]}{'...' if len(err_detail) > 600 else ''}```",
            },
        })
        blocks.append({"type": "divider"})

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*Database Status*\n{db_text}"},
    })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": (
                    f"🤖 *Zambeel QA Bot*  |  Automated test run  |  {timestamp}  |  "
                    f"<https://sarimsikander-zambeel-sqa.hf.space|Open Dashboard>"
                ),
            }
        ],
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

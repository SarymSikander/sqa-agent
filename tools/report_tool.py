import os
from datetime import datetime

from tools.db_tool import get_row_count, get_tables
from tools.playwright_tool import run_tests

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

PORTALS = ["seller", "admin", "agency"]

EXPECTED_TABLES = [
    "orders", "users", "products", "variants", "stores",
    "tickets", "invoices", "agencies", "customers", "warehouse",
]


def generate_health_report(env):
    """
    Run all Playwright tests for env, collect DB health metrics, and write a
    markdown report to reports/health_<env>_<timestamp>.md.
    Returns the file path of the saved report.
    """
    timestamp     = datetime.now()
    ts_label      = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    ts_filename   = timestamp.strftime("%Y%m%d_%H%M%S")
    report_path   = os.path.join(REPORTS_DIR, f"health_{env}_{ts_filename}.md")

    print(f"\n{'='*60}")
    print(f"  Generating health report — env: {env}")
    print(f"{'='*60}\n")

    # ------------------------------------------------------------------
    # 1. Playwright tests
    # ------------------------------------------------------------------
    print("Running Playwright tests...")
    test_results = {}
    for portal in PORTALS:
        print(f"  Testing {portal}/{env}...")
        test_results[portal] = run_tests(portal, env)

    passed  = [p for p, (s, _) in test_results.items() if s == "PASS"]
    failed  = [p for p, (s, _) in test_results.items() if s == "FAIL"]
    overall = "PASS" if not failed else "FAIL"
    health_pct = int(len(passed) / len(PORTALS) * 100)

    # ------------------------------------------------------------------
    # 2. DB health (skip gracefully if credentials are missing)
    # ------------------------------------------------------------------
    print("\nCollecting DB metrics...")
    db_available = True
    db_error     = None
    row_counts   = {}
    missing_tables = []
    extra_tables   = []

    try:
        actual_tables = get_tables(env)
        actual_set    = set(actual_tables)
        expected_set  = set(EXPECTED_TABLES)
        missing_tables = sorted(expected_set - actual_set)
        extra_tables   = sorted(actual_set - expected_set)

        for table in ["orders", "users"]:
            if table in actual_set:
                row_counts[table] = get_row_count(env, table)
    except Exception as e:
        db_available = False
        db_error     = str(e)
        print(f"  DB unavailable: {db_error}")

    # ------------------------------------------------------------------
    # 3. Build markdown report
    # ------------------------------------------------------------------
    lines = [
        f"# Zambeel Health Report — {env.upper()}",
        f"",
        f"**Generated:** {ts_label}  ",
        f"**Environment:** {env}  ",
        f"**Overall Status:** {'✅ PASS' if overall == 'PASS' else '❌ FAIL'}  ",
        f"**Health Score:** {health_pct}%  ",
        f"**Summary:** {len(passed)}/{len(PORTALS)} portals passed"
        + (f" — Failed: {', '.join(failed)}" if failed else ""),
        f"",
        f"---",
        f"",
        f"## Playwright Login Tests",
        f"",
        f"| Portal | Status | URL | Console Errors | Nav Check | Load Time |",
        f"|--------|--------|-----|---------------|-----------|-----------|",
    ]

    for portal in PORTALS:
        status, result = test_results[portal]
        icon = "✅" if status == "PASS" else "❌"
        url = result.get("url") or "—"
        err_count = len(result.get("console_errors", []))
        err_cell = f"⚠️ {err_count}" if err_count else "✅ 0"
        nav_found = result.get("nav_elements_found", [])
        nav_cell = f"✅ {len(nav_found)} elements" if nav_found else ("—" if status == "FAIL" else "⚠️ none")
        load_ms = result.get("load_time_ms", 0)
        load_cell = f"{load_ms:,}ms" if load_ms else "—"
        lines.append(f"| {portal} | {icon} {status} | `{url}` | {err_cell} | {nav_cell} | {load_cell} |")

    # Console error detail section
    any_errors = any(len(r.get("console_errors", [])) > 0 for _, r in test_results.values())
    if any_errors:
        lines += ["", "### Console Errors Detail", ""]
        for portal in PORTALS:
            _, result = test_results[portal]
            errs = result.get("console_errors", [])
            if errs:
                lines.append(f"**{portal}:**")
                for err in errs[:5]:
                    lines.append(f"- `{err}`")
                if len(errs) > 5:
                    lines.append(f"- _…and {len(errs) - 5} more_")
                lines.append("")

    lines += [
        f"",
        f"---",
        f"",
        f"## Database Health",
        f"",
    ]

    if not db_available:
        lines += [
            f"⚠️ DB connection unavailable for `{env}`: `{db_error}`",
            f"",
        ]
    else:
        lines += [
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total tables | {len(actual_tables)} |",
        ]
        for table, count in row_counts.items():
            lines.append(f"| `{table}` row count | {count:,} |")

        if missing_tables:
            lines += [
                f"",
                f"### ⚠️ Missing expected tables",
                f"",
            ]
            for t in missing_tables:
                lines.append(f"- `{t}`")
        else:
            lines += [f"", f"✅ All expected tables present."]

    lines += [
        f"",
        f"---",
        f"",
        f"*Report saved to: `{report_path}`*",
    ]

    report_text = "\n".join(lines)

    with open(report_path, "w") as f:
        f.write(report_text)

    print(f"\nReport saved: {report_path}")
    print(f"\n{report_text}")
    return report_path

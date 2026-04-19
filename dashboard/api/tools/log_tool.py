import re
from collections import defaultdict


# Patterns that qualify a line as an error or warning
_LEVEL_PATTERNS = [
    (re.compile(r"\bERROR\b",   re.IGNORECASE), "ERROR"),
    (re.compile(r"\bWARN(?:ING)?\b", re.IGNORECASE), "WARNING"),
]

# Optional: capture a short message token after the level keyword
_MSG_STRIP = re.compile(
    r"^.*?(?:ERROR|WARN(?:ING)?)[\s:\-–]*(.*?)$", re.IGNORECASE
)


def parse_backend_logs(log_file_path, last_n_lines=200):
    """
    Read the last `last_n_lines` lines of a backend log file, extract ERROR
    and WARNING lines, group them by level and message fingerprint, and return
    a structured summary dict.

    Return format:
    {
        "file": str,
        "lines_scanned": int,
        "total_issues": int,
        "by_level": {
            "ERROR":   {"count": int, "samples": [str, ...]},
            "WARNING": {"count": int, "samples": [str, ...]},
        },
        "by_message": {
            "<fingerprint>": {"level": str, "count": int, "sample": str}
        }
    }
    """
    with open(log_file_path, "r", errors="replace") as f:
        all_lines = f.readlines()

    scanned = all_lines[-last_n_lines:]

    by_level   = defaultdict(lambda: {"count": 0, "samples": []})
    by_message = defaultdict(lambda: {"level": None, "count": 0, "sample": ""})

    for raw in scanned:
        line = raw.rstrip()
        level = None
        for pattern, lvl in _LEVEL_PATTERNS:
            if pattern.search(line):
                level = lvl
                break
        if not level:
            continue

        # Extract a short message fingerprint (first 80 chars after the keyword)
        m = _MSG_STRIP.match(line)
        msg_fragment = m.group(1).strip()[:80] if m else line.strip()[:80]

        by_level[level]["count"] += 1
        if len(by_level[level]["samples"]) < 3:
            by_level[level]["samples"].append(line)

        entry = by_message[msg_fragment]
        entry["level"]  = level
        entry["count"] += 1
        entry["sample"] = line

    total = sum(v["count"] for v in by_level.values())

    summary = {
        "file":          log_file_path,
        "lines_scanned": len(scanned),
        "total_issues":  total,
        "by_level":      dict(by_level),
        "by_message":    dict(by_message),
    }

    _print_summary(summary)
    return summary


def _print_summary(summary):
    print(f"\nLog file  : {summary['file']}")
    print(f"Scanned   : {summary['lines_scanned']} lines")
    print(f"Issues    : {summary['total_issues']}")

    for level, data in summary["by_level"].items():
        print(f"\n  {level} ({data['count']} occurrence(s)):")
        for s in data["samples"]:
            print(f"    {s}")

    if summary["by_message"]:
        print(f"\n  Grouped by message fingerprint:")
        for msg, info in sorted(
            summary["by_message"].items(), key=lambda x: -x[1]["count"]
        ):
            print(f"    [{info['level']}] x{info['count']}  {msg}")

import json
import os
from pathlib import Path

# HF Docker spaces persist only /data — check there first
_DATA_DIR = Path("/data")

SUITE_PATH = Path(os.getenv('API_TEST_SUITE_PATH', '/Users/sarimsikandar/Desktop/api-test-suite'))

# Local fallback: reports/ sibling to this file's api/ parent
_API_DIR = Path(__file__).resolve().parent.parent
_FALLBACK_REPORTS = _API_DIR / "reports"


def _find(*paths: Path) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def get_results() -> dict | None:
    p = _find(
        _DATA_DIR / 'results.json',
        SUITE_PATH / 'reports' / 'results.json',
        _FALLBACK_REPORTS / 'results.json',
    )
    if p is None:
        return None
    with open(p) as f:
        return json.load(f)


def get_sla() -> dict:
    p = _find(
        _DATA_DIR / 'sla-config.json',
        SUITE_PATH / 'sla-config.json',
        _FALLBACK_REPORTS / 'sla-config.json',
    )
    if p is None:
        return {}
    with open(p) as f:
        return json.load(f)


def get_baseline_log() -> str:
    p = _find(
        _DATA_DIR / 'baseline-runs.json',
        SUITE_PATH / 'docs' / 'baseline-log.md',
        _FALLBACK_REPORTS / 'baseline-log.md',
    )
    if p is None:
        return '_No baseline log found. Run `npm run baseline` first._'
    return p.read_text()


def get_inventory() -> list:
    p = _find(
        _DATA_DIR / 'inventory.json',
        SUITE_PATH / 'api-inventory.json',
        _FALLBACK_REPORTS / 'api-inventory.json',
    )
    if p is None:
        return []
    with open(p) as f:
        return json.load(f)

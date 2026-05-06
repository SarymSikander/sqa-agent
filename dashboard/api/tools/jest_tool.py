import json
import os
from pathlib import Path

# HF Docker spaces persist only /data — check there first
_DATA_DIR = Path("/data")

# Static files baked into the repo image — survive every restart
_API_DIR    = Path(__file__).resolve().parent.parent
_STATIC_DIR = _API_DIR / "static"

# Local dev override via env var (not available inside the container)
SUITE_PATH = Path(os.getenv('API_TEST_SUITE_PATH', '/Users/sarimsikandar/Desktop/api-test-suite'))

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
    # Priority: /data/ (GH Actions upload) → static/ (baked) → local dev
    p = _find(
        _DATA_DIR / 'sla-config.json',
        _STATIC_DIR / 'sla-config.json',
        SUITE_PATH / 'sla-config.json',
        _FALLBACK_REPORTS / 'sla-config.json',
    )
    if p is None:
        return {}
    with open(p) as f:
        return json.load(f)


def get_baseline_log() -> str:
    # Priority: /data/ runtime upload → static/ baked markdown → local dev
    p = _find(
        _DATA_DIR / 'baseline-runs.json',
        _STATIC_DIR / 'baseline-log.md',
        SUITE_PATH / 'docs' / 'baseline-log.md',
        _FALLBACK_REPORTS / 'baseline-log.md',
    )
    if p is None:
        return '_No baseline log found. Run `npm run baseline` first._'
    return p.read_text()


def get_inventory() -> list:
    # Priority: /data/ (GH Actions upload) → static/ (baked) → local dev
    p = _find(
        _DATA_DIR / 'inventory.json',
        _STATIC_DIR / 'api-inventory.json',
        SUITE_PATH / 'api-inventory.json',
        _FALLBACK_REPORTS / 'api-inventory.json',
    )
    if p is None:
        return []
    with open(p) as f:
        return json.load(f)

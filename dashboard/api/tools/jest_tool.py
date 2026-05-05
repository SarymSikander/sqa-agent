import json
import os
from pathlib import Path

SUITE_PATH = Path(os.getenv('API_TEST_SUITE_PATH', '/Users/sarimsikandar/Desktop/api-test-suite'))

# Fallback: look next to this file's parent (the api/ directory) → reports/
_API_DIR = Path(__file__).resolve().parent.parent
_FALLBACK_REPORTS = _API_DIR / "reports"


def _find(primary: Path, fallback: Path) -> Path | None:
    if primary.exists():
        return primary
    if fallback.exists():
        return fallback
    return None


def get_results() -> dict | None:
    p = _find(SUITE_PATH / 'reports' / 'results.json',
              _FALLBACK_REPORTS / 'results.json')
    if p is None:
        return None
    with open(p) as f:
        return json.load(f)


def get_sla() -> dict:
    p = _find(SUITE_PATH / 'sla-config.json',
              _FALLBACK_REPORTS / 'sla-config.json')
    if p is None:
        return {}
    with open(p) as f:
        return json.load(f)


def get_baseline_log() -> str:
    p = _find(SUITE_PATH / 'docs' / 'baseline-log.md',
              _FALLBACK_REPORTS / 'baseline-log.md')
    if p is None:
        return '_No baseline log found. Run `npm run baseline` first._'
    return p.read_text()


def get_inventory() -> list:
    p = _find(SUITE_PATH / 'api-inventory.json',
              _FALLBACK_REPORTS / 'api-inventory.json')
    if p is None:
        return []
    with open(p) as f:
        return json.load(f)

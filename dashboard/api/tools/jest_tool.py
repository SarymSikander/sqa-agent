import json
import os
from pathlib import Path

SUITE_PATH = Path(os.getenv('API_TEST_SUITE_PATH', '/Users/sarimsikandar/Desktop/api-test-suite'))


def get_results() -> dict | None:
    p = SUITE_PATH / 'reports' / 'results.json'
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def get_sla() -> dict:
    p = SUITE_PATH / 'sla-config.json'
    if not p.exists():
        return {}
    with open(p) as f:
        return json.load(f)


def get_baseline_log() -> str:
    p = SUITE_PATH / 'docs' / 'baseline-log.md'
    if not p.exists():
        return '_No baseline log found. Run `npm run baseline` first._'
    return p.read_text()


def get_inventory() -> list:
    p = SUITE_PATH / 'api-inventory.json'
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)

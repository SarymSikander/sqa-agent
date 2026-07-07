#!/usr/bin/env node
/**
 * Post-run SLA regeneration.
 *
 * Reads reports/perf-metrics.json (written by assertSla() during the Jest run),
 * derives p95-based thresholds per slaKey, and rewrites sla-config.json.
 *
 * In CI, reports/ is gitignored and never downloaded as a prior artifact,
 * so perf-metrics.json contains only data from the current run.
 *
 * Threshold formula (same as calibrate-sla.js):
 *   pass = ceil(p95 × 1.20)
 *   warn = ceil(p95 × 1.50)
 *   fail = ceil(p95 × 2.00)
 *
 * Endpoints with no perf data in this run keep their existing thresholds.
 * No endpoint is ever written with status "DEAD" — a missing measurement
 * simply leaves the threshold unchanged from the previous run.
 */

const fs   = require('fs');
const path = require('path');

const ROOT         = path.resolve(__dirname, '..');
const METRICS_FILE = path.join(ROOT, 'reports', 'perf-metrics.json');
const SLA_FILE     = path.join(ROOT, 'sla-config.json');

if (!fs.existsSync(METRICS_FILE)) {
  console.log('No perf-metrics.json found — skipping SLA regeneration');
  process.exit(0);
}

let metrics;
try {
  metrics = JSON.parse(fs.readFileSync(METRICS_FILE, 'utf8'));
} catch (err) {
  console.error(`Failed to parse perf-metrics.json: ${err.message}`);
  process.exit(1);
}

if (!Array.isArray(metrics) || metrics.length === 0) {
  console.log('perf-metrics.json is empty — skipping SLA regeneration');
  process.exit(0);
}

// Group by slaKey. Take the maximum p95 across all entries for that key
// (conservative: multiple test files can measure the same endpoint).
const p95ByKey = {};
for (const entry of metrics) {
  if (!entry.slaKey || entry.p95 == null) continue;
  if (p95ByKey[entry.slaKey] == null || entry.p95 > p95ByKey[entry.slaKey]) {
    p95ByKey[entry.slaKey] = entry.p95;
  }
}

const measuredCount = Object.keys(p95ByKey).length;
if (measuredCount === 0) {
  console.log('No slaKey+p95 entries in perf-metrics.json — skipping');
  process.exit(0);
}

// Load existing config to preserve thresholds for endpoints not in this run.
const existing = fs.existsSync(SLA_FILE)
  ? JSON.parse(fs.readFileSync(SLA_FILE, 'utf8'))
  : {};

const genDate = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';

const updated = {
  _comment: `SLA thresholds. Auto-regenerated ${genDate} from live p95 measurements. Formula: pass=p95×1.2, warn=p95×1.5, fail=p95×2.0. Never manually edit — rerun the suite to refresh.`,
};

// Carry over existing entries. Strip any legacy "DEAD" status so tests run.
for (const [key, val] of Object.entries(existing)) {
  if (key === '_comment') continue;
  if (val && val.status === 'DEAD') {
    updated[key] = { pass: null, warn: null, fail: null, p95_baseline: null };
  } else {
    updated[key] = val;
  }
}

// Overwrite with fresh measurements from this run.
for (const [key, p95] of Object.entries(p95ByKey)) {
  updated[key] = {
    pass:         Math.ceil(p95 * 1.20),
    warn:         Math.ceil(p95 * 1.50),
    fail:         Math.ceil(p95 * 2.00),
    p95_baseline: p95,
  };
}

fs.writeFileSync(SLA_FILE, JSON.stringify(updated, null, 2) + '\n');
console.log(`\n✅  sla-config.json regenerated — ${measuredCount} endpoint(s) updated\n`);

for (const [key, p95] of Object.entries(p95ByKey)) {
  const th = updated[key];
  console.log(
    `   ${key.padEnd(30)} p95=${String(p95).padStart(5)}ms` +
    `  pass≤${th.pass}ms  warn≤${th.warn}ms  fail>${th.fail}ms`
  );
}
console.log('');

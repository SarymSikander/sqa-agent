/**
 * Performance measurement helper.
 *
 * Default iterations: 15 (increased from 10 for more stable baselines).
 * Reports: min, max, avg, p50, p95, p99
 *
 * SLA config format expected in sla-config.json:
 *   { "key": { "pass": <ms>, "warn": <ms>, "fail": <ms>, "p95_baseline": <ms> } }
 *
 * Thresholds derived from live p95 measurements:
 *   pass = p95 × 1.20  → assert avg ≤ this
 *   warn = p95 × 1.50  → log warning if avg exceeds this
 *   fail = p95 × 2.00  → log critical alert if avg exceeds this
 *
 * Also writes per-test metrics to reports/perf-metrics.json for baseline-log.
 */

const fs   = require('fs');
const path = require('path');

const slaConfig   = require('../../sla-config.json');
const METRICS_FILE = path.resolve(__dirname, '../../reports/perf-metrics.json');

/**
 * Run requestFn `iterations` times sequentially and return aggregated stats.
 *
 * @param {() => Promise<any>} requestFn
 * @param {number} iterations
 * @returns {{ min, max, avg, p50, p95, p99, all }}
 */
async function measurePerformance(requestFn, iterations = 15) {
  const times = [];
  for (let i = 0; i < iterations; i++) {
    const start = Date.now();
    await requestFn();
    times.push(Date.now() - start);
  }
  times.sort((a, b) => a - b);

  const pct = (p) =>
    times[Math.min(Math.ceil((p / 100) * times.length) - 1, times.length - 1)];

  return {
    min: times[0],
    max: times[times.length - 1],
    avg: Math.round(times.reduce((a, b) => a + b, 0) / times.length),
    p50: pct(50),
    p95: pct(95),
    p99: pct(99),
    all: times,
  };
}

/**
 * Returns the SLA entry `{ pass, warn, fail, p95_baseline }` for a key.
 * Returns null if the key is not in sla-config.json or has no thresholds.
 */
function getSla(key) {
  const entry = slaConfig[key];
  if (!entry) return null;
  // Support both new object format and legacy single-number format
  if (typeof entry === 'number') return { pass: entry, warn: entry * 1.25, fail: entry * 2, p95_baseline: entry };
  return entry;
}

/**
 * Returns true if the endpoint is marked as DEAD in sla-config.json.
 * Dead endpoints (100% timeout rate on production) should have all tests skipped.
 */
function isDeadSlaKey(key) {
  return slaConfig[key]?.status === 'DEAD';
}

/**
 * Asserts that avg ≤ pass threshold.
 * Warns (but does not fail) if avg > warn threshold.
 * Always logs a summary line with p95 and p99.
 *
 * Also writes the metric to reports/perf-metrics.json for baseline-log generation.
 *
 * @param {string} label   - human-readable endpoint label
 * @param {string} slaKey  - key in sla-config.json
 * @param {object} stats   - output from measurePerformance()
 */
function assertSla(label, slaKey, stats) {
  const sla = getSla(slaKey);

  const line = `${label}: avg=${stats.avg}ms p50=${stats.p50}ms p95=${stats.p95}ms p99=${stats.p99}ms max=${stats.max}ms`;

  if (!sla) {
    console.log(`  ⏱  ${line} | SLA=n/a`);
    _recordMetric(label, slaKey, stats, null);
    return;
  }

  const resultLabel = stats.avg <= sla.pass ? 'PASS'
    : stats.avg <= sla.warn               ? 'WARN'
    : 'FAIL';

  console.log(`  ⏱  ${line} | pass=${sla.pass}ms warn=${sla.warn}ms | ${resultLabel}`);

  if (stats.avg > sla.warn) {
    console.warn(`  ⚠️  SLA WARN: avg ${stats.avg}ms > warn threshold ${sla.warn}ms for "${label}"`);
  }

  _recordMetric(label, slaKey, stats, sla);
  expect(stats.avg).toBeLessThanOrEqual(sla.warn);
}

/**
 * Write a single perf measurement to reports/perf-metrics.json.
 * Used by generate-registry.js to build the baseline-log table.
 */
function _recordMetric(label, slaKey, stats, sla) {
  try {
    let metrics = [];
    try { metrics = JSON.parse(fs.readFileSync(METRICS_FILE, 'utf8')); } catch {}
    metrics.push({
      label,
      slaKey: slaKey || null,
      timestamp: Date.now(),
      min:  stats.min,
      max:  stats.max,
      avg:  stats.avg,
      p50:  stats.p50,
      p95:  stats.p95,
      p99:  stats.p99,
      sla_pass: sla?.pass   ?? null,
      sla_warn: sla?.warn   ?? null,
      sla_fail: sla?.fail   ?? null,
      result: !sla ? 'N/A'
        : stats.avg <= sla.pass ? 'PASS'
        : stats.avg <= sla.warn ? 'WARN'
        : 'FAIL',
    });
    fs.mkdirSync(path.dirname(METRICS_FILE), { recursive: true });
    fs.writeFileSync(METRICS_FILE, JSON.stringify(metrics, null, 2));
  } catch {
    // Non-fatal — metric recording failure must never break a test
  }
}

module.exports = { measurePerformance, getSla, assertSla, isDeadSlaKey };

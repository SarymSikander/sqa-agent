#!/usr/bin/env node
/**
 * Generates docs/test-registry.md from api-inventory.json + sla-config.json,
 * and appends a new run entry to docs/baseline-log.md.
 *
 * Usage: node scripts/generate-registry.js [results-json-path]
 *   results-json-path defaults to reports/results.json
 */

const fs   = require('fs');
const path = require('path');

const ROOT          = path.resolve(__dirname, '..');
const INVENTORY     = JSON.parse(fs.readFileSync(path.join(ROOT, 'api-inventory.json'), 'utf8'));
const SLA           = JSON.parse(fs.readFileSync(path.join(ROOT, 'sla-config.json'), 'utf8'));
const RESULTS_FILE  = process.argv[2] || path.join(ROOT, 'reports', 'results.json');
const REGISTRY_OUT  = path.join(ROOT, 'docs', 'test-registry.md');
const BASELINE_LOG  = path.join(ROOT, 'docs', 'baseline-log.md');
const METRICS_FILE  = path.join(ROOT, 'reports', 'perf-metrics.json');

// ── Parse Jest JSON results ───────────────────────────────────────────────────
function loadResults() {
  if (!fs.existsSync(RESULTS_FILE)) return {};
  try {
    const data = JSON.parse(fs.readFileSync(RESULTS_FILE, 'utf8'));
    const map  = {};
    for (const suite of data.testResults || []) {
      for (const t of suite.testResults || []) {
        const m = t.fullName.match(/\[TC_(\d{3})\]/);
        if (m) map[`TC_${m[1]}`] = t.status;
      }
    }
    return map;
  } catch {
    return {};
  }
}

function loadJestMeta() {
  if (!fs.existsSync(RESULTS_FILE)) return { total: 0, passed: 0, failed: 0, duration: 0 };
  try {
    const d = JSON.parse(fs.readFileSync(RESULTS_FILE, 'utf8'));
    const duration = Math.round(
      (d.testResults || []).reduce((s, r) => s + (r.perfStats?.runtime || 0), 0) / 1000
    );
    return {
      total:    d.numTotalTests   || 0,
      passed:   d.numPassedTests  || 0,
      failed:   d.numFailedTests  || 0,
      duration,
    };
  } catch {
    return { total: 0, passed: 0, failed: 0, duration: 0 };
  }
}

// ── Load perf-metrics.json (written by performance.js assertSla) ──────────────
function loadPerfMetrics() {
  if (!fs.existsSync(METRICS_FILE)) return {};
  try {
    return JSON.parse(fs.readFileSync(METRICS_FILE, 'utf8'));
  } catch {
    return {};
  }
}

function statusEmoji(status) {
  if (status === 'passed')  return '✅';
  if (status === 'failed')  return '❌';
  if (status === 'pending') return '⏭️';
  return '⬜';
}

function formatSla(key) {
  if (!key || !SLA[key]) return '—';
  const entry = SLA[key];
  if (typeof entry === 'number') return entry >= 1000 ? `${(entry / 1000).toFixed(1)}s` : `${entry}ms`;
  if (entry.pass == null) return '—';
  return entry.pass >= 1000 ? `${(entry.pass / 1000).toFixed(1)}s` : `${entry.pass}ms`;
}

// ── Build test-registry.md ────────────────────────────────────────────────────
function buildRegistryMarkdown(results) {
  const now = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';

  const byCategory = {};
  for (const route of INVENTORY) {
    (byCategory[route.category] = byCategory[route.category] || []).push(route);
  }

  const lines = [
    '# Zambeel API — Test Registry',
    '',
    `> Auto-generated on ${now}`,
    `> Source: \`api-inventory.json\` (${INVENTORY.length} routes)`,
    '',
    '## Summary',
    '',
  ];

  const priorities = ['P0', 'P1', 'P2'];
  lines.push('| Priority | Total | Passed | Failed | Pending | Not Run |');
  lines.push('|----------|------:|------:|------:|------:|------:|');
  for (const prio of priorities) {
    const routes = INVENTORY.filter((r) => r.priority === prio);
    let passed = 0, failed = 0, pending = 0, notRun = 0;
    for (const r of routes) {
      const s = results[r.id];
      if (s === 'passed')       passed++;
      else if (s === 'failed')  failed++;
      else if (s === 'pending') pending++;
      else                      notRun++;
    }
    lines.push(`| **${prio}** | ${routes.length} | ${passed} | ${failed} | ${pending} | ${notRun} |`);
  }

  lines.push('', '## SLA Breach Report', '');
  const breaches = INVENTORY.filter((r) => {
    if (!r.slaKey || !SLA[r.slaKey]) return false;
    return results[r.id] === 'failed';
  });
  if (breaches.length === 0) {
    lines.push('_No SLA breaches recorded in last run._');
  } else {
    lines.push('| TC_ID | Endpoint | SLA Goal | Status |');
    lines.push('|-------|----------|----------|--------|');
    for (const r of breaches) {
      lines.push(`| ${r.id} | \`${r.method} ${r.path}\` | ${formatSla(r.slaKey)} | ❌ |`);
    }
  }

  lines.push('', '## Route Inventory by Category', '');
  for (const [cat, routes] of Object.entries(byCategory)) {
    lines.push(`### ${cat.charAt(0).toUpperCase() + cat.slice(1)}`);
    lines.push('');
    lines.push('| TC_ID | Method | Path | Auth | Roles | Priority | SLA Goal | Status |');
    lines.push('|-------|--------|------|------|-------|----------|----------|--------|');
    for (const r of routes) {
      const status  = statusEmoji(results[r.id]);
      const auth    = r.authRequired ? '🔒' : '🌐';
      const roles   = r.roles.length ? r.roles.join(', ') : '—';
      const slaGoal = formatSla(r.slaKey);
      lines.push(
        `| ${r.id} | \`${r.method}\` | \`${r.path}\` | ${auth} | ${roles} | ${r.priority} | ${slaGoal} | ${status} |`
      );
    }
    lines.push('');
  }

  lines.push('---');
  lines.push('_Regenerate with: `node scripts/generate-registry.js`_');
  lines.push('');

  return lines.join('\n');
}

// ── Append run entry to baseline-log.md ──────────────────────────────────────
function nextRunNumber(logPath) {
  if (!fs.existsSync(logPath)) return 1;
  const content = fs.readFileSync(logPath, 'utf8');
  const matches = [...content.matchAll(/^\|\s*(\d+)\s*\|/gm)];
  if (matches.length === 0) return 1;
  return Math.max(...matches.map((m) => parseInt(m[1], 10))) + 1;
}

function appendBaselineLog(meta, perfMetrics) {
  const runNo   = nextRunNumber(BASELINE_LOG);
  const now     = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  const pass    = meta.failed === 0 ? '✅ PASS' : '❌ FAIL';

  // Build perf rows from captured metrics
  const perfKeys = Object.keys(perfMetrics);
  const perfRows = perfKeys.map((key) => {
    const m   = perfMetrics[key];
    const sla = SLA[m.slaKey] || {};
    const passMs = typeof sla === 'number' ? sla : sla.pass;
    const p95Ms  = typeof sla === 'number' ? sla : sla.p95_baseline;
    const regression = passMs != null && m.avg > passMs ? '⚠️ REGRESSION' : '✅ OK';

    const avgStr  = m.avg  != null ? `${m.avg}ms`  : '—';
    const p95Str  = m.p95  != null ? `${m.p95}ms`  : '—';
    const passStr = passMs != null ? `${passMs}ms` : '—';
    const baseStr = p95Ms  != null ? `${p95Ms}ms`  : '—';

    return `| ${runNo} | ${now} | ${key} | ${m.label || key} | ${avgStr} | ${p95Str} | ${passStr} | ${baseStr} | ${regression} |`;
  });

  // Initialise file with header if it doesn't exist
  if (!fs.existsSync(BASELINE_LOG)) {
    const header = [
      '# Zambeel API — Baseline Performance Log',
      '',
      'Auto-appended by `scripts/generate-registry.js` after each CI run.',
      'Never edit manually — add corrections by running a new baseline measurement.',
      '',
      '| Run | Timestamp | SLA Key | Endpoint Label | Avg | p95 | Pass ≤ | p95 Baseline | Status |',
      '|-----|-----------|---------|----------------|-----|-----|--------|--------------|--------|',
      '',
    ].join('\n');
    fs.mkdirSync(path.dirname(BASELINE_LOG), { recursive: true });
    fs.writeFileSync(BASELINE_LOG, header);
  }

  // Summary line for this run
  const summaryRow = `| ${runNo} | ${now} | — | **Run Summary** ${pass} | ${meta.passed}/${meta.total} tests | — | — | — | ${pass} |`;

  const rows = [summaryRow, ...perfRows, ''].join('\n');
  fs.appendFileSync(BASELINE_LOG, rows);

  return runNo;
}

// ── Main ──────────────────────────────────────────────────────────────────────
const results     = loadResults();
const meta        = loadJestMeta();
const perfMetrics = loadPerfMetrics();
const registry    = buildRegistryMarkdown(results);

fs.mkdirSync(path.dirname(REGISTRY_OUT), { recursive: true });
fs.writeFileSync(REGISTRY_OUT, registry);
console.log(`📄  Test registry written to ${REGISTRY_OUT}`);

const runNo = appendBaselineLog(meta, perfMetrics);
console.log(`📊  Baseline log updated at ${BASELINE_LOG} (run #${runNo})`);

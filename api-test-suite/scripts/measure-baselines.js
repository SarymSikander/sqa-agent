#!/usr/bin/env node
/**
 * Phase 2 — Baseline Measurement
 *
 * Run on every CI pass or after any deployment to verify performance
 * has not regressed against the calibrated thresholds in sla-config.json.
 *
 * Reads every GET endpoint from api-inventory.json (plus POST /api/login),
 * substitutes path params from env vars, and runs 10 iterations per endpoint.
 *
 * Methodology:
 *   • 10 iterations per endpoint
 *   • Discard first 1 (warm-up)
 *   • Compare avg of remaining 9 against sla-config.json thresholds
 *   • Flag regressions where avg worsened by > 15% vs the previous run
 *
 * Writes:
 *   docs/baseline-log.md         — append-only human-readable run history
 *   reports/baseline-runs.json   — machine-readable run history (last 20 runs)
 *
 * Usage:
 *   npm run baseline               (production — default)
 *   npm run baseline:staging       (staging)
 *
 * Prerequisite: run `npm run calibrate` at least once first to populate sla-config.json.
 */

require('dotenv').config({ path: require('path').resolve(__dirname, '../.env') });

const https          = require('https');
const httpPlain      = require('http');
const path           = require('path');
const fs             = require('fs');
const { execFileSync } = require('child_process');
const { getToken, getFirebaseIdToken } = require('../tests/helpers/auth');

const ROOT            = path.resolve(__dirname, '..');
const INVENTORY_PATH  = path.join(ROOT, 'api-inventory.json');
const SLA_PATH        = path.join(ROOT, 'sla-config.json');
const BASELINE_LOG    = path.join(ROOT, 'docs', 'baseline-log.md');
const BASELINE_RUNS   = path.join(ROOT, 'reports', 'baseline-runs.json');

const ENV = process.argv.includes('--env')
  ? process.argv[process.argv.indexOf('--env') + 1]
  : 'prod';

const TOTAL_ITER      = 10;
const WARMUP_ITER     = 1;
const EFFECTIVE_ITER  = TOTAL_ITER - WARMUP_ITER;   // 9
const DEFAULT_TIMEOUT = 10_000;
const EXPORT_TIMEOUT  = 30_000;
const MAX_STORED_RUNS = 20;
const REGRESSION_PCT  = 0.15;   // 15% avg increase from previous run = regression

const BASE_URL = (
  ENV === 'prod'
    ? process.env.PROD_BASE_URL
    : process.env.BASE_URL || 'http://localhost:3000'
).replace(/\/$/, '');
const parsedBase   = new URL(BASE_URL);
const isHttps      = parsedBase.protocol === 'https:';
const requester    = isHttps ? https : httpPlain;
const TRIGGERED_BY = process.env.TRIGGERED_BY || 'manual';

// ── Optional: refresh api-inventory.json from local backend repo ──────────────
function maybeRefreshInventory() {
  if (!process.env.API_REPO_PATH) {
    console.log('  (API_REPO_PATH not set — using existing api-inventory.json)');
    return;
  }
  process.stdout.write('  Refreshing api-inventory.json… ');
  try {
    execFileSync(process.execPath, [path.join(ROOT, 'scripts', 'discover-routes.js')], {
      cwd: ROOT, stdio: ['ignore', 'ignore', 'ignore'], timeout: 30_000,
    });
    console.log('done');
  } catch (err) {
    console.log(`skipped (${err.message})`);
  }
}

// ── Path param substitution values per environment ────────────────────────────
function getParamMap(env) {
  return env === 'prod' ? {
    orderId:   process.env.PROD_SAMPLE_ORDER_ID,
    ticketId:  process.env.PROD_SAMPLE_TICKET_ID,
    storeId:   process.env.PROD_TICKET_STORE_ID,
    variantId: process.env.PROD_VARIANT_ID,
  } : {
    orderId:   process.env.TEST_ORDER_ID,
    ticketId:  process.env.TEST_TICKET_ID,
    storeId:   process.env.TEST_TICKET_STORE_ID,
    variantId: process.env.TEST_VARIANT_ID,
  };
}

// ── Pick the best available token for a given roles array ─────────────────────
function selectRole(roles) {
  if (!roles || roles.length === 0) return null;  // public endpoint
  if (roles.includes('Admin'))  return 'admin';
  if (roles.includes('Seller')) return 'seller';
  if (roles.includes('Agency')) return 'agency';
  return null;
}

// ── Build the endpoint list dynamically from api-inventory.json ───────────────
function buildEndpointList(env) {
  if (!fs.existsSync(INVENTORY_PATH)) {
    console.error(`❌  ${INVENTORY_PATH} not found. Run: node scripts/discover-routes.js`);
    process.exit(1);
  }

  const inventory = JSON.parse(fs.readFileSync(INVENTORY_PATH, 'utf8'));
  const paramMap  = getParamMap(env);

  // Only GET routes + POST /api/login
  const eligible = inventory.filter(r =>
    r.method === 'GET' || (r.method === 'POST' && r.path === '/api/login')
  );

  const endpoints = [];
  const skipped   = [];

  for (const route of eligible) {
    const isLogin = route.method === 'POST' && route.path === '/api/login';

    // Substitute path parameters
    const paramNames = (route.path.match(/:(\w+)/g) || []).map(p => p.slice(1));
    let resolvedPath = route.path;
    let skipReason   = null;

    for (const param of paramNames) {
      if (!(param in paramMap)) {
        skipReason = `no substitution rule for :${param}`;
        break;
      }
      const value = paramMap[param];
      if (!value) {
        skipReason = `env var for :${param} not set`;
        break;
      }
      resolvedPath = resolvedPath.replace(`:${param}`, value);
    }

    if (skipReason) {
      skipped.push({ route, reason: skipReason });
      continue;
    }

    const role      = isLogin ? 'login' : selectRole(route.roles);
    const key       = route.slaKey || route.id.toLowerCase();
    const timeoutMs = route.path.includes('/export') ? EXPORT_TIMEOUT : DEFAULT_TIMEOUT;

    endpoints.push({
      key,
      tcId:         route.id,
      priority:     route.priority || 'P2',
      method:       route.method,
      path:         resolvedPath,        // resolved — used for the actual HTTP request
      originalPath: route.path,          // original pattern — used for display
      role,
      timeoutMs,
    });
  }

  // Sort P0 → P1 → P2, then by TC id
  const order = { P0: 0, P1: 1, P2: 2 };
  endpoints.sort((a, b) => {
    const d = (order[a.priority] ?? 3) - (order[b.priority] ?? 3);
    return d !== 0 ? d : a.tcId.localeCompare(b.tcId);
  });

  return { endpoints, skipped, total: eligible.length };
}

// ── HTTP request that resolves with elapsed ms ────────────────────────────────
function timedRequest(method, urlPath, authHeader, bodyObj, timeoutMs = DEFAULT_TIMEOUT) {
  return new Promise((resolve, reject) => {
    const body = bodyObj ? JSON.stringify(bodyObj) : null;
    const opts = {
      hostname: parsedBase.hostname,
      port:     parsedBase.port || (isHttps ? 443 : 80),
      path:     urlPath,
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(body       && { 'Content-Length': Buffer.byteLength(body) }),
        ...(authHeader && { Authorization: authHeader }),
      },
    };
    const t0  = Date.now();
    const req = requester.request(opts, res => {
      res.on('data', () => {});
      res.on('end', () => resolve(Date.now() - t0));
    });
    req.setTimeout(timeoutMs, () => {
      req.destroy();
      reject(Object.assign(new Error('TIMEOUT'), { isTimeout: true }));
    });
    req.on('error', err => reject(err));
    if (body) req.write(body);
    req.end();
  });
}

// ── Collect readings (discard warmup, stop on timeout) ────────────────────────
async function collectReadings(requestFn, timeoutMs) {
  const readings = [];   // effective only (after warmup, not timed out)
  let timedOut   = false;

  for (let i = 0; i < TOTAL_ITER; i++) {
    try {
      const ms = await requestFn();
      if (i >= WARMUP_ITER) readings.push(ms);
    } catch (err) {
      if (err.isTimeout) {
        timedOut = true;
        break;
      }
      // Other errors: treat as slow response (use timeout value)
      if (i >= WARMUP_ITER) readings.push(timeoutMs);
    }
  }

  return { readings, timedOut };
}

// ── Statistics ────────────────────────────────────────────────────────────────
function computeStats(readings) {
  if (readings.length === 0) return null;
  const sorted = [...readings].sort((a, b) => a - b);
  const n = sorted.length;
  const pct = p => sorted[Math.min(Math.ceil(n * p) - 1, n - 1)];
  return {
    n,
    min: sorted[0],
    max: sorted[n - 1],
    avg: Math.round(sorted.reduce((s, v) => s + v, 0) / n),
    p50: pct(0.50),
    p95: pct(0.95),
  };
}

// ── Compare avg against sla-config thresholds ─────────────────────────────────
function evaluateResult(avg, slaEntry) {
  if (!slaEntry) return { label: '⬜ NO SLA', code: 'no_sla' };
  const { pass, warn, fail } = typeof slaEntry === 'number'
    ? { pass: slaEntry, warn: Math.ceil(slaEntry * 1.25), fail: Math.ceil(slaEntry * 2) }
    : slaEntry;

  if (pass == null) return { label: '⬜ NO SLA', code: 'no_sla' };
  if (avg <= pass)  return { label: '✅ PASS',   code: 'pass', threshold: pass };
  if (avg <= warn)  return { label: '⚠️  WARN',  code: 'warn', threshold: warn };
  return               { label: '❌ FAIL',   code: 'fail', threshold: fail };
}

// ── Persist run data for regression detection ─────────────────────────────────
function loadRunHistory() {
  if (!fs.existsSync(BASELINE_RUNS)) return { runs: [] };
  try { return JSON.parse(fs.readFileSync(BASELINE_RUNS, 'utf8')); }
  catch { return { runs: [] }; }
}

function saveRunHistory(history) {
  fs.mkdirSync(path.dirname(BASELINE_RUNS), { recursive: true });
  fs.writeFileSync(BASELINE_RUNS, JSON.stringify(history, null, 2) + '\n');
}

// ── Detect regressions vs the most recent previous run ────────────────────────
function detectRegressions(currentResults, previousRun) {
  if (!previousRun) return [];
  const regressions = [];
  for (const { ep, stats } of currentResults) {
    if (!stats) continue;
    const prev = previousRun.results[ep.key];
    if (!prev?.avg) continue;
    const pct = (stats.avg - prev.avg) / prev.avg;
    if (pct > REGRESSION_PCT) {
      regressions.push({
        key:     ep.key,
        tcId:    ep.tcId,
        path:    ep.originalPath || ep.path,
        method:  ep.method,
        prevAvg: prev.avg,
        currAvg: stats.avg,
        pct:     Math.round(pct * 100),
      });
    }
  }
  return regressions;
}

// ── Next run number ───────────────────────────────────────────────────────────
function nextRunNumber() {
  if (!fs.existsSync(BASELINE_LOG)) return 1;
  const content = fs.readFileSync(BASELINE_LOG, 'utf8');
  const matches = [...content.matchAll(/^## Run #(\d+)/gm)];
  if (matches.length === 0) return 1;
  return Math.max(...matches.map(m => parseInt(m[1], 10))) + 1;
}

// ── Append a run entry to docs/baseline-log.md ───────────────────────────────
function appendBaselineLog(runNumber, runDate, results, regressions, summary, prevRunNumber) {
  const runNo3 = String(runNumber).padStart(3, '0');

  const header = [
    '',
    `## Run #${runNo3}`,
    '',
    `_Date: ${runDate} | Environment: ${ENV === 'prod' ? 'Production' : 'Staging'} | Iterations: ${TOTAL_ITER} (${EFFECTIVE_ITER} effective) | Triggered by: ${TRIGGERED_BY}_`,
    '',
    '| TC ID | API Endpoint | Method | Min | Max | Avg | p95 | SLA Goal | Result |',
    '|-------|-------------|--------|-----|-----|-----|-----|----------|--------|',
  ];

  const rows = results.map(({ ep, stats, evalResult, slaEntry }) => {
    const displayPath = (ep.originalPath || ep.path).split('?')[0];
    if (!stats) {
      return `| ${ep.tcId} | \`${displayPath}\` | \`${ep.method}\` | — | — | — | — | — | ⏭️ SKIPPED |`;
    }
    const sla  = slaEntry;
    const goal = sla?.pass != null ? `≤ ${sla.pass}ms` : (typeof sla === 'number' ? `≤ ${sla}ms` : '—');
    return (
      `| ${ep.tcId} | \`${displayPath}\` | \`${ep.method}\`` +
      ` | ${stats.min}ms | ${stats.max}ms | ${stats.avg}ms | ${stats.p95}ms` +
      ` | ${goal} | ${evalResult.label} |`
    );
  });

  const footerLines = [
    '',
    `**Summary:** ${summary.pass} passed · ${summary.warn} warning · ${summary.fail} failed · ${summary.skipped} skipped`,
  ];

  if (regressions.length === 0) {
    const prevRef = prevRunNumber ? `Run #${String(prevRunNumber).padStart(3, '0')}` : 'previous run';
    footerLines.push(`**Regressions vs ${prevRef}:** none`);
  } else {
    const prevRef = prevRunNumber ? `Run #${String(prevRunNumber).padStart(3, '0')}` : 'previous run';
    footerLines.push(`**Regressions vs ${prevRef}:** ${regressions.length} endpoint(s) degraded by >15%`);
    for (const r of regressions) {
      footerLines.push(`  - \`${r.method} ${r.path.split('?')[0]}\` — avg ${r.prevAvg}ms → ${r.currAvg}ms (+${r.pct}%)`);
    }
  }

  footerLines.push('');

  const block = [...header, ...rows, ...footerLines].join('\n');

  if (!fs.existsSync(BASELINE_LOG) || fs.readFileSync(BASELINE_LOG, 'utf8').trim() === '') {
    const docHeader = [
      '# Zambeel API — Baseline Performance Log',
      '',
      'Auto-appended by `scripts/measure-baselines.js` after each Phase 2 run.',
      'Never edit manually. Re-calibrate with `npm run calibrate` after major deployments.',
      '',
    ].join('\n');
    fs.mkdirSync(path.dirname(BASELINE_LOG), { recursive: true });
    fs.writeFileSync(BASELINE_LOG, docHeader);
  }

  fs.appendFileSync(BASELINE_LOG, block);
}

function pad(s, w) { return String(s).padStart(w); }

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  const runDate = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';

  if (!fs.existsSync(SLA_PATH)) {
    console.error('❌  sla-config.json not found. Run `npm run calibrate` first.');
    process.exit(1);
  }
  const slaConfig = JSON.parse(fs.readFileSync(SLA_PATH, 'utf8'));

  console.log('\n📊  Zambeel Baseline Measurement — Phase 2');
  console.log(`    Target:  ${ENV === 'prod' ? 'production' : 'staging'} (${BASE_URL})`);
  console.log(`    Config:  ${TOTAL_ITER} iter · ${WARMUP_ITER} warm-up · ${EFFECTIVE_ITER} effective`);
  console.log('');

  maybeRefreshInventory();

  // Build endpoint list from inventory
  const { endpoints, skipped, total } = buildEndpointList(ENV);
  console.log(`\n  Inventory: ${total} eligible routes (GET + POST /api/login)`);
  console.log(`  Runnable:  ${endpoints.length}  |  Skipped at build: ${skipped.length}`);
  if (skipped.length) {
    for (const { route, reason } of skipped) {
      console.log(`    ⏭️  ${route.id}  ${route.path}  — ${reason}`);
    }
  }
  console.log('');

  // ── Auth ──────────────────────────────────────────────────────────────────
  const tokens = {};
  for (const role of ['admin', 'seller', 'agency']) {
    process.stdout.write(`  Auth ${role}… `);
    tokens[role] = await getToken(role, ENV).catch(() => null);
    console.log(tokens[role] ? '✓' : 'SKIPPED');
  }

  let loginIdToken = null;
  process.stdout.write('  Firebase idToken for login… ');
  try {
    loginIdToken = await getFirebaseIdToken('admin', ENV);
    console.log('✓');
  } catch (err) {
    console.log(`SKIPPED (${err.message})`);
  }
  console.log('');

  // ── Measurement loop ──────────────────────────────────────────────────────
  const runResults    = [];
  const runResultsMap = {};

  for (const ep of endpoints) {
    const epTimeout   = ep.timeoutMs || DEFAULT_TIMEOUT;
    const displayPath = (ep.originalPath || ep.path).split('?')[0];
    const label       = `${ep.method} ${ep.originalPath}`.padEnd(50);
    process.stdout.write(`  [${ep.priority}] ${label} `);

    let requestFn;
    if (ep.role === 'login') {
      if (!loginIdToken) {
        console.log('SKIPPED (no Firebase idToken)');
        runResults.push({ ep, stats: null, evalResult: { label: '⏭️ SKIPPED', code: 'skipped' }, slaEntry: null });
        continue;
      }
      requestFn = () => timedRequest('POST', ep.path, null, { idToken: loginIdToken }, epTimeout);
    } else {
      const token   = ep.role ? tokens[ep.role] : null;
      const authHdr = token ? `Bearer ${token}` : null;
      if (ep.role && !token) {
        console.log('SKIPPED (no token)');
        runResults.push({ ep, stats: null, evalResult: { label: '⏭️ SKIPPED', code: 'skipped' }, slaEntry: null });
        continue;
      }
      requestFn = () => timedRequest(ep.method, ep.path, authHdr, null, epTimeout);
    }

    const { readings, timedOut } = await collectReadings(requestFn, epTimeout);

    if (timedOut && readings.length === 0) {
      console.log('TIMEOUT — all effective iterations timed out, skipping');
      runResults.push({ ep, stats: null, evalResult: { label: '❌ TIMEOUT', code: 'timeout' }, slaEntry: null });
      continue;
    }

    const stats      = computeStats(readings);
    const slaEntry   = slaConfig[ep.key];
    const evalResult = evaluateResult(stats.avg, slaEntry);

    runResultsMap[ep.key] = { avg: stats.avg, p95: stats.p95, min: stats.min, max: stats.max };

    const timeoutNote = timedOut ? ' (partial)' : '';
    console.log(
      `avg=${pad(stats.avg, 5)}ms  p50=${pad(stats.p50, 5)}ms  p95=${pad(stats.p95, 5)}ms  ${evalResult.label}${timeoutNote}`
    );
    runResults.push({ ep, stats, evalResult, slaEntry });
  }

  console.log('');

  // ── Summarise ─────────────────────────────────────────────────────────────
  const summary = { pass: 0, warn: 0, fail: 0, skipped: 0 };
  for (const { evalResult } of runResults) {
    if      (evalResult.code === 'pass')    summary.pass++;
    else if (evalResult.code === 'warn')    summary.warn++;
    else if (evalResult.code === 'fail')    summary.fail++;
    else                                    summary.skipped++;
  }

  console.log(`  Results: ✅ ${summary.pass} pass · ⚠️  ${summary.warn} warn · ❌ ${summary.fail} fail · ⏭️  ${summary.skipped} skipped`);

  // ── Final inventory summary ───────────────────────────────────────────────
  const { total: invTotal, skipped: buildSkipped, endpoints: eps } = buildEndpointList(ENV);
  const buildSkippedByReason = {};
  for (const { reason } of buildSkipped) buildSkippedByReason[reason] = (buildSkippedByReason[reason] || 0) + 1;

  console.log('');
  console.log('  ─────────────────────────────────────────────────');
  console.log(`  Total GET routes in inventory : ${invTotal}`);
  console.log(`  Endpoints measured            : ${eps.length}`);
  console.log(`  Skipped (build-time)          : ${buildSkipped.length}`);
  if (buildSkipped.length) {
    for (const [r, n] of Object.entries(buildSkippedByReason)) console.log(`    ${n}× ${r}`);
  }
  console.log(`  Skipped (run-time)            : ${summary.skipped}`);

  // ── Regression detection ──────────────────────────────────────────────────
  const history     = loadRunHistory();
  const prevRun     = history.runs.length > 0 ? history.runs[history.runs.length - 1] : null;
  const regressions = detectRegressions(runResults, prevRun);

  if (regressions.length > 0) {
    console.log(`\n  ⚠️  Regressions detected (avg worsened by >${Math.round(REGRESSION_PCT * 100)}% vs Run #${String(prevRun.runNumber).padStart(3, '0')}):`);
    for (const r of regressions) {
      console.log(`     ${r.method} ${r.path.split('?')[0]} — ${r.prevAvg}ms → ${r.currAvg}ms (+${r.pct}%)`);
    }
  } else if (prevRun) {
    console.log(`  No regressions vs Run #${String(prevRun.runNumber).padStart(3, '0')}`);
  }

  // ── Persist ───────────────────────────────────────────────────────────────
  const runNumber = nextRunNumber();

  history.runs.push({ runNumber, date: runDate, triggeredBy: TRIGGERED_BY, results: runResultsMap, summary });
  if (history.runs.length > MAX_STORED_RUNS) history.runs = history.runs.slice(-MAX_STORED_RUNS);
  saveRunHistory(history);

  appendBaselineLog(runNumber, runDate, runResults, regressions, summary, prevRun?.runNumber ?? null);

  console.log(`\n  📄  Run #${String(runNumber).padStart(3, '0')} appended to docs/baseline-log.md`);
  console.log(`  💾  Run history saved to reports/baseline-runs.json\n`);
}

main().catch(err => { console.error('\n❌  Fatal:', err.message); process.exit(1); });

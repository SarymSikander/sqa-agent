#!/usr/bin/env node
/**
 * Phase 1 — SLA Calibration
 *
 * Run ONCE when setting up or after a major infrastructure change.
 * Reads every GET endpoint from api-inventory.json (plus POST /api/login),
 * runs 30 iterations per endpoint, discards the first 3 warm-up hits,
 * and derives pass/warn/fail thresholds from the p95 of the remaining 27.
 *
 * Writes:
 *   sla-config.json        — thresholds consumed by Phase 2 and Jest perf tests
 *   docs/sla-reference.md  — SLA standards document with raw calibration data
 *
 * Usage:
 *   npm run calibrate               (production — default)
 *   npm run calibrate:staging       (staging)
 *   npm run calibrate -- --dry-run  (print, do not write)
 */

require('dotenv').config({ path: require('path').resolve(__dirname, '../.env') });

const https     = require('https');
const httpPlain = require('http');
const path      = require('path');
const fs        = require('fs');
const { execFileSync }           = require('child_process');
const { getToken, getFirebaseIdToken } = require('../tests/helpers/auth');

const ROOT           = path.resolve(__dirname, '..');
const INVENTORY_PATH = path.join(ROOT, 'api-inventory.json');
const SLA_PATH       = path.join(ROOT, 'sla-config.json');
const SLA_REF_PATH   = path.join(ROOT, 'docs', 'sla-reference.md');

const DRY_RUN = process.argv.includes('--dry-run');
const ENV     = process.argv.includes('--env')
  ? process.argv[process.argv.indexOf('--env') + 1]
  : 'prod';

const TOTAL_ITER      = 30;
const WARMUP_ITER     = 3;
const EFFECTIVE_ITER  = TOTAL_ITER - WARMUP_ITER;  // 27
const DEFAULT_TIMEOUT = 10_000;
const EXPORT_TIMEOUT  = 30_000;

const BASE_URL = (
  ENV === 'prod'
    ? process.env.PROD_BASE_URL
    : process.env.BASE_URL || 'http://localhost:3000'
).replace(/\/$/, '');

const parsedBase = new URL(BASE_URL);
const isHttps    = parsedBase.protocol === 'https:';
const requester  = isHttps ? https : httpPlain;

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
  const eligible  = inventory.filter(r =>
    r.method === 'GET' || (r.method === 'POST' && r.path === '/api/login')
  );

  const endpoints = [];
  const skipped   = [];

  for (const route of eligible) {
    const isLogin = route.method === 'POST' && route.path === '/api/login';

    // Substitute path parameters
    const paramNames  = (route.path.match(/:(\w+)/g) || []).map(p => p.slice(1));
    let resolvedPath  = route.path;
    let skipReason    = null;

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

// ── HTTP request that resolves with elapsed ms; rejects on timeout / error ────
function timedRequest(method, urlPath, authHeader, bodyObj, timeoutMs) {
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

// ── Collect all 30 readings, marking warm-up iterations ──────────────────────
async function collectReadings(requestFn, total, warmup, timeoutMs) {
  const all      = [];
  let   timeouts = 0;

  for (let i = 0; i < total; i++) {
    const isWarmup = i < warmup;
    try {
      const ms = await requestFn();
      all.push({ ms, isWarmup, timedOut: false });
      process.stdout.write('.');
    } catch (err) {
      all.push({ ms: timeoutMs, isWarmup, timedOut: true });
      process.stdout.write(err.isTimeout ? 'T' : 'E');
      timeouts++;
    }
  }

  const effective = all.filter(r => !r.isWarmup && !r.timedOut).map(r => r.ms);
  return { all, effective, timeouts };
}

// ── Statistics ────────────────────────────────────────────────────────────────
function computeStats(readings) {
  if (readings.length === 0) return null;
  const sorted = [...readings].sort((a, b) => a - b);
  const n      = sorted.length;
  const pct    = p => sorted[Math.min(Math.ceil(n * p) - 1, n - 1)];
  return {
    n,
    min: sorted[0],
    max: sorted[n - 1],
    avg: Math.round(sorted.reduce((s, v) => s + v, 0) / n),
    p50: pct(0.50),
    p75: pct(0.75),
    p95: pct(0.95),
    p99: pct(0.99),
  };
}

function thresholds(p95) {
  return {
    pass:         Math.ceil(p95 * 1.20),
    warn:         Math.ceil(p95 * 1.50),
    fail:         Math.ceil(p95 * 2.00),
    p95_baseline: p95,
  };
}

const ms  = n => n != null ? `${n}ms` : '—';
const pad = (s, w) => String(s).padStart(w);

// ── Generate docs/sla-reference.md ───────────────────────────────────────────
function buildSlaReference(calibrationDate, envLabel, results, skippedList) {
  const lines = [];

  lines.push('# Zambeel API — SLA Reference', '');
  lines.push(
    `_Calibrated: ${calibrationDate} | Environment: ${envLabel} | Base URL: ${BASE_URL}_`,
    `_Iterations: ${TOTAL_ITER} total · ${WARMUP_ITER} warm-up discarded · ${EFFECTIVE_ITER} effective readings per endpoint_`,
    ''
  );
  lines.push('---', '');

  lines.push('## Methodology', '');
  lines.push(
    'Thresholds are derived using an **Apdex-aligned p95 baseline method**:',
    '',
    `1. Run each endpoint **${TOTAL_ITER} times** against the ${envLabel.toLowerCase()} environment.`,
    `2. Discard the first **${WARMUP_ITER} iterations** as warm-up (cold TCP connections, DNS,`,
    '   connection-pool establishment artificially inflate initial response times).',
    '3. Compute the **95th percentile** of the remaining effective readings as the calibrated baseline.',
    '4. Apply buffer factors to produce three alert levels:',
    ''
  );
  lines.push('| Level | Formula | Meaning |');
  lines.push('|-------|---------|---------|');
  lines.push('| ✅ **Pass**    | p95 × 1.20 | 20% headroom — normal operation          |');
  lines.push('| ⚠️ **Warning** | p95 × 1.50 | 50% above p95 — degraded, investigate    |');
  lines.push('| ❌ **Fail**    | p95 × 2.00 | Double p95 — SLA breach, escalate        |');
  lines.push('');
  lines.push(
    '> **Phase 2 ongoing testing** (`npm run baseline`) runs **10 iterations**, discards the first 1,',
    '> and compares the **average of the remaining 9** against these thresholds.',
    '> Historical run data lives in `docs/baseline-log.md`.',
    ''
  );
  lines.push('---', '');

  // Thresholds tables by priority
  lines.push('## SLA Thresholds by Category', '');
  const priorityMeta = [
    { key: 'P0', label: 'P0 — Critical _(SLA breach blocks merge)_' },
    { key: 'P1', label: 'P1 — High'   },
    { key: 'P2', label: 'P2 — Medium' },
  ];

  for (const { key: prio, label } of priorityMeta) {
    const rows = results.filter(r => r.ep.priority === prio && r.stats);
    if (rows.length === 0) continue;
    lines.push(`### ${label}`, '');
    lines.push('| TC ID | Endpoint | Method | Avg | p50 | p95 | Pass ≤ | Warn ≤ | Fail > |');
    lines.push('|-------|----------|--------|-----|-----|-----|--------|--------|--------|');
    for (const { ep, stats, thresh } of rows) {
      lines.push(
        `| ${ep.tcId} | \`${ep.originalPath}\` | \`${ep.method}\`` +
        ` | ${ms(stats.avg)} | ${ms(stats.p50)} | ${ms(stats.p95)}` +
        ` | ${ms(thresh.pass)} | ${ms(thresh.warn)} | ${ms(thresh.fail)} |`
      );
    }
    lines.push('');
  }

  // Dead endpoints (100% timeout rate)
  const deadResults = results.filter(r => r.isDead);
  if (deadResults.length) {
    lines.push('### Dead Endpoints — Requires Backend Investigation', '');
    lines.push('_These endpoints returned 100% timeouts across all calibration iterations and have no SLA threshold._', '');
    lines.push('| TC ID | Priority | Endpoint | Method | Note |');
    lines.push('|-------|----------|----------|--------|------|');
    for (const { ep } of deadResults) {
      lines.push(`| ${ep.tcId} | ${ep.priority} | \`${ep.originalPath}\` | \`${ep.method}\` | 100% timeout rate on production |`);
    }
    lines.push('');
  }

  // Endpoints that partially failed or were skipped
  const noStats = results.filter(r => !r.stats && !r.isDead);
  if (noStats.length || skippedList.length) {
    lines.push('### Skipped / Not Calibrated', '');
    lines.push('| TC ID | Endpoint | Reason |');
    lines.push('|-------|----------|--------|');
    for (const { ep, skipReason } of noStats) {
      lines.push(`| ${ep.tcId} | \`${ep.originalPath}\` | ${skipReason} |`);
    }
    for (const { route, reason } of skippedList) {
      lines.push(`| ${route.id} | \`${route.path}\` | ${reason} |`);
    }
    lines.push('');
  }

  lines.push('---', '');
  lines.push('## Calibration Raw Data', '');
  lines.push(
    `All ${TOTAL_ITER} readings per endpoint. First ${WARMUP_ITER} are warm-up and excluded from threshold computation.`,
    ''
  );

  for (const { ep, all, stats, timeouts } of results) {
    const warmupMs    = all.slice(0, WARMUP_ITER).map(r => r.timedOut ? 'TIMEOUT' : `${r.ms}ms`).join(', ');
    const effectiveMs = all.slice(WARMUP_ITER).map(r => r.timedOut ? 'TIMEOUT' : `${r.ms}ms`).join(', ');

    lines.push(`### ${ep.tcId} — \`${ep.method} ${ep.originalPath}\``);
    if (timeouts > 0) lines.push(`> ⚠️ ${timeouts} iteration(s) timed out and were excluded`);
    lines.push(`**Warm-up (${WARMUP_ITER} discarded):** ${warmupMs}  `);
    lines.push(`**Effective readings (${EFFECTIVE_ITER}):** ${effectiveMs}  `);
    if (stats) {
      lines.push(
        `**Stats —** min: ${ms(stats.min)} · avg: ${ms(stats.avg)} · ` +
        `p50: ${ms(stats.p50)} · p95: ${ms(stats.p95)} · max: ${ms(stats.max)}`
      );
    } else {
      lines.push('**Stats —** insufficient effective readings (all iterations timed out)');
    }
    lines.push('');
  }

  lines.push('---');
  lines.push(`_Generated by \`scripts/calibrate-sla.js\` on ${calibrationDate}_`);
  lines.push('');

  return lines.join('\n');
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  const calibDate = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  const envLabel  = ENV === 'prod' ? 'Production' : 'Staging';

  console.log('\n🎯  Zambeel SLA Calibration — Phase 1');
  console.log(`    Target:  ${ENV === 'prod' ? 'production' : 'staging'} (${BASE_URL})`);
  console.log(`    Config:  ${TOTAL_ITER} iter · ${WARMUP_ITER} warm-up · ${EFFECTIVE_ITER} effective`);
  if (DRY_RUN) console.log('    Mode:    dry-run — will not write files');
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
  process.stdout.write('  Firebase idToken for login endpoint… ');
  try {
    loginIdToken = await getFirebaseIdToken('admin', ENV);
    console.log('✓');
  } catch (err) {
    console.log(`SKIPPED (${err.message})`);
  }
  console.log('');

  // ── Calibration loop ──────────────────────────────────────────────────────
  const results    = [];
  const slaEntries = {};
  let   calibrated = 0;

  for (const ep of endpoints) {
    const epTimeout = ep.timeoutMs || DEFAULT_TIMEOUT;
    const label     = `${ep.method} ${ep.originalPath}`.padEnd(50);
    process.stdout.write(`  [${ep.priority}] ${label} `);

    // Build request function
    let requestFn;
    if (ep.role === 'login') {
      if (!loginIdToken) {
        console.log('SKIPPED (no Firebase idToken)');
        results.push({ ep, all: [], stats: null, thresh: null, timeouts: 0, skipReason: 'no Firebase idToken' });
        continue;
      }
      requestFn = () => timedRequest('POST', ep.path, null, { idToken: loginIdToken }, epTimeout);
    } else {
      const token   = ep.role ? tokens[ep.role] : null;
      if (ep.role && !token) {
        console.log(`SKIPPED (no ${ep.role} token)`);
        results.push({ ep, all: [], stats: null, thresh: null, timeouts: 0, skipReason: `no ${ep.role} token` });
        continue;
      }
      const authHdr = token ? `Bearer ${token}` : null;
      requestFn = () => timedRequest(ep.method, ep.path, authHdr, null, epTimeout);
    }

    const { all, effective, timeouts } = await collectReadings(requestFn, TOTAL_ITER, WARMUP_ITER, epTimeout);
    process.stdout.write('  ');

    if (effective.length === 0) {
      slaEntries[ep.key] = { status: 'DEAD', pass: null, warn: null, fail: null };
      console.log(`💀  100% timeout rate — marked as DEAD`);
      results.push({ ep, all, stats: null, thresh: null, timeouts, skipReason: '100% timeout rate on production', isDead: true });
      continue;
    }
    if (effective.length < 10) {
      const reason = `only ${effective.length}/${EFFECTIVE_ITER} effective readings`;
      console.log(`⚠️  ${reason} — skipping threshold`);
      results.push({ ep, all, stats: null, thresh: null, timeouts, skipReason: reason });
      continue;
    }

    const st = computeStats(effective);
    const th = thresholds(st.p95);
    slaEntries[ep.key] = th;
    calibrated++;

    console.log(
      `avg=${pad(st.avg, 5)}ms  p50=${pad(st.p50, 5)}ms  p95=${pad(st.p95, 5)}ms  → pass ≤ ${ms(th.pass)}`
    );
    results.push({ ep, all, stats: st, thresh: th, timeouts });
  }

  console.log('');

  // ── Summary ───────────────────────────────────────────────────────────────
  const deadCount     = results.filter(r => r.isDead).length;
  const notCalibrated = endpoints.length - calibrated - deadCount;
  console.log('  ─────────────────────────────────────────────────');
  console.log(`  Total GET routes in inventory : ${total}`);
  console.log(`  Endpoints measured            : ${endpoints.length}`);
  console.log(`  Successfully calibrated       : ${calibrated}`);
  console.log(`  Dead (100% timeout)           : ${deadCount}`);
  console.log(`  Skipped (build-time)          : ${skipped.length}`);
  console.log(`  Skipped (run-time)            : ${notCalibrated}`);

  if (deadCount > 0) {
    console.log('\n  💀  Dead endpoints (require backend investigation):');
    for (const { ep } of results.filter(r => r.isDead)) {
      console.log(`     [${ep.priority}] ${ep.method} ${ep.originalPath}`);
    }
  }

  if (skipped.length) {
    console.log('\n  Build-time skips (path params):');
    const byReason = {};
    for (const { reason } of skipped) byReason[reason] = (byReason[reason] || 0) + 1;
    for (const [r, n] of Object.entries(byReason)) console.log(`    ${n}× ${r}`);
  }

  console.log('');

  // ── Write outputs ─────────────────────────────────────────────────────────
  if (DRY_RUN) {
    console.log('📋  sla-config.json (dry-run):');
    console.log(JSON.stringify({ _comment: 'Phase 1 calibration — dry run', ...slaEntries }, null, 2));
    console.log('\n📋  docs/sla-reference.md would be written');
    return;
  }

  const existing = fs.existsSync(SLA_PATH) ? JSON.parse(fs.readFileSync(SLA_PATH, 'utf8')) : {};
  const merged   = {
    _comment: `SLA thresholds. Calibrated ${calibDate} against ${envLabel}. ` +
              `Phase 1: ${TOTAL_ITER} iter, ${WARMUP_ITER} warm-up, p95×1.2/1.5/2.0.`,
    ...existing,
    ...slaEntries,
  };
  fs.writeFileSync(SLA_PATH, JSON.stringify(merged, null, 2) + '\n');
  console.log(`✅  sla-config.json written  (${Object.keys(slaEntries).length} endpoints)`);

  fs.mkdirSync(path.join(ROOT, 'docs'), { recursive: true });
  const slaRef = buildSlaReference(calibDate, envLabel, results, skipped);
  fs.writeFileSync(SLA_REF_PATH, slaRef);
  console.log(`✅  docs/sla-reference.md written`);

  console.log(`\n🏁  Calibration complete — ${calibrated}/${endpoints.length} endpoints calibrated`);
  console.log('    Run Phase 2 with: npm run baseline\n');
}

main().catch(err => { console.error('\n❌  Fatal:', err.message); process.exit(1); });

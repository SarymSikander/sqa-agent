#!/usr/bin/env node
/**
 * Slack notifier for the Zambeel production smoke test results.
 *
 * Reads reports/smoke-results.json (Jest --json output) and posts a
 * Block Kit message to SLACK_WEBHOOK_URL.
 *
 * Environment variables (all passed from the GitHub Actions workflow):
 *   SLACK_WEBHOOK_URL   — Incoming Webhook URL from the SQA Agent Slack app
 *   TRIGGERED_BY        — GitHub Actions "deployed_by" workflow input
 *   GITHUB_RUN_URL      — Full URL to this Actions run (for the footer link)
 *   RESULTS_FILE        — Optional override path (default: reports/smoke-results.json)
 */

require('dotenv').config({ path: require('path').resolve(__dirname, '../.env') });

const fs   = require('fs');
const path = require('path');
const http = require('https');

const WEBHOOK_URL   = process.env.SLACK_WEBHOOK_URL;
const TRIGGERED_BY  = process.env.TRIGGERED_BY  || 'unknown';
const RUN_URL       = process.env.GITHUB_RUN_URL || '#';
const RESULTS_FILE  = process.env.RESULTS_FILE   ||
  path.resolve(__dirname, '../reports/smoke-results.json');
const SLA_CONFIG    = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../sla-config.json'), 'utf8')
);

if (!WEBHOOK_URL) {
  console.error('❌  SLACK_WEBHOOK_URL not set — skipping Slack notification');
  process.exit(0); // soft exit so CI doesn't fail on missing webhook
}

// ── Parse Jest JSON results ───────────────────────────────────────────────────
function parseResults(filePath) {
  if (!fs.existsSync(filePath)) {
    return { error: `Results file not found: ${filePath}`, total: 0, passed: 0, failed: 0, duration: 0, failures: [], slaBreaches: [] };
  }

  const data        = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  const failures    = [];
  const slaBreaches = [];

  for (const suite of data.testResults || []) {
    for (const t of suite.testResults || []) {
      if (t.status !== 'failed') continue;

      // Parse TC_ID, endpoint, dimension from fullName
      // Expected format: "[SMOKE-TC_001][perf] ..."
      const tcMatch   = t.fullName.match(/\[SMOKE-(TC_\d+)\]/);
      const dimMatch  = t.fullName.match(/\[(perf|auth|validation|security)\]/);
      const tcId      = tcMatch  ? tcMatch[1]  : '?';
      const dimension = dimMatch ? dimMatch[1] : 'unknown';

      // Parse endpoint from ancestor titles (describe block names contain it)
      const ancestors  = (t.ancestorTitles || []).join(' > ');
      const epMatch    = ancestors.match(/(?:GET|POST|PUT|PATCH|DELETE)\s+(\/[^\s>]+)/);
      const endpoint   = epMatch ? `${epMatch[0]}` : ancestors;

      // Parse expected vs actual from Jest failure message
      let expectedVsActual = '';
      const msg = (t.failureMessages || []).join('\n');
      const expectMatch = msg.match(/Expected[:\s]+([^\n]+)\s*\nReceived[:\s]+([^\n]+)/);
      if (expectMatch) {
        expectedVsActual = `Expected: ${expectMatch[1].trim()} | Received: ${expectMatch[2].trim()}`;
      } else {
        // Truncate the raw message if no structured expect
        const clean = msg.replace(/\x1b\[[0-9;]*m/g, '').split('\n')[0].slice(0, 120);
        expectedVsActual = clean;
      }

      // Detect SLA breach (perf dimension failure)
      if (dimension === 'perf') {
        const slaMatch = msg.match(/(\d+)\s+to be less than or equal to\s+(\d+)/);
        if (slaMatch) {
          const actual    = parseInt(slaMatch[1], 10);
          const threshold = parseInt(slaMatch[2], 10);
          slaBreaches.push({ tcId, endpoint, actual, threshold });
        }
      }

      failures.push({ tcId, endpoint, dimension, expectedVsActual });
    }
  }

  return {
    total:    data.numTotalTests    || 0,
    passed:   data.numPassedTests   || 0,
    failed:   data.numFailedTests   || 0,
    pending:  data.numPendingTests  || 0,
    duration: Math.round((data.testResults || []).reduce((sum, s) => sum + (s.perfStats?.runtime || 0), 0) / 1000),
    failures,
    slaBreaches,
  };
}

// ── Build Block Kit payload ───────────────────────────────────────────────────
function buildPayload(results) {
  const allPass     = results.failed === 0 && !results.error;
  const now         = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  const statusEmoji = allPass ? '✅' : '🚨';
  const headerText  = allPass
    ? 'Zambeel Production — All Clear'
    : 'Zambeel Production — Smoke Test Failed';

  const blocks = [];

  // Header
  blocks.push({
    type: 'header',
    text: { type: 'plain_text', text: `${statusEmoji} ${headerText}`, emoji: true },
  });

  // Summary fields
  blocks.push({
    type: 'section',
    fields: [
      { type: 'mrkdwn', text: `*Time:*\n${now}` },
      { type: 'mrkdwn', text: `*Triggered by:*\n${TRIGGERED_BY}` },
      { type: 'mrkdwn', text: `*Results:*\n${results.passed}/${results.total} passed` },
      { type: 'mrkdwn', text: `*Duration:*\n${results.duration}s` },
    ],
  });

  // Results file error (fallback if Jest never produced output)
  if (results.error) {
    blocks.push({ type: 'divider' });
    blocks.push({
      type: 'section',
      text: { type: 'mrkdwn', text: `⚠️ *${results.error}*\n_Check the GitHub Actions log for details._` },
    });
  }

  // Failure table — only on failures
  if (results.failures.length > 0) {
    blocks.push({ type: 'divider' });
    blocks.push({
      type: 'section',
      text: { type: 'mrkdwn', text: '*Failed Tests*' },
    });

    // Slack limits block text to 3000 chars; chunk if needed
    const rows = results.failures.map((f) =>
      `• *${f.tcId}* \`[${f.dimension}]\`  ${f.endpoint}\n  _${f.expectedVsActual}_`
    );
    // Split into chunks of 10 rows to stay within block text limits
    for (let i = 0; i < rows.length; i += 10) {
      blocks.push({
        type: 'section',
        text: { type: 'mrkdwn', text: rows.slice(i, i + 10).join('\n') },
      });
    }
  }

  // SLA breach section
  if (results.slaBreaches.length > 0) {
    blocks.push({ type: 'divider' });
    blocks.push({
      type: 'section',
      text: { type: 'mrkdwn', text: '*⏱ SLA Breaches*' },
    });
    const breachRows = results.slaBreaches.map((b) =>
      `• *${b.tcId}*  ${b.endpoint}  —  avg *${b.actual}ms* (threshold: ${b.threshold}ms)`
    );
    blocks.push({
      type: 'section',
      text: { type: 'mrkdwn', text: breachRows.join('\n') },
    });
  }

  // Footer
  blocks.push({ type: 'divider' });
  blocks.push({
    type: 'context',
    elements: [
      {
        type: 'mrkdwn',
        text: `📄 <${RUN_URL}|Full report on GitHub Actions>  |  Zambeel SQA Agent`,
      },
    ],
  });

  return { blocks };
}

// ── HTTP POST to Slack ────────────────────────────────────────────────────────
function postToSlack(payload) {
  return new Promise((resolve, reject) => {
    const body    = JSON.stringify(payload);
    const url     = new URL(WEBHOOK_URL);
    const options = {
      hostname: url.hostname,
      path:     url.pathname,
      method:   'POST',
      headers:  {
        'Content-Type':   'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(data);
        } else {
          reject(new Error(`Slack returned ${res.statusCode}: ${data}`));
        }
      });
    });

    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  console.log(`📖  Reading results from ${RESULTS_FILE}`);
  const results = parseResults(RESULTS_FILE);

  console.log(`   Total: ${results.total}  Passed: ${results.passed}  Failed: ${results.failed}`);
  if (results.slaBreaches.length) {
    console.log(`   SLA breaches: ${results.slaBreaches.length}`);
  }

  const payload = buildPayload(results);

  console.log('📤  Posting to Slack...');
  try {
    await postToSlack(payload);
    console.log('✅  Slack notification sent');
  } catch (err) {
    console.error(`❌  Slack POST failed: ${err.message}`);
    // Do NOT exit 1 — a failed notification must not abort the CI job
    process.exit(0);
  }
}

main();

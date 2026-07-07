#!/usr/bin/env node
/**
 * Zambeel SQA Agent — Slack Bolt app (Socket Mode)
 *
 * Slash command: /zambeel-test [subcommand]
 *
 * Subcommands:
 *   major              — runs the full staging test suite (all test files)
 *   smoke              — runs only tests/smoke (production read-only)
 *   feature:<name>     — runs tests/<name>.test.js  (e.g. feature:orders)
 *   api:<path>         — grep by URL fragment (e.g. api:/api/dashboard)
 *
 * Required env vars (set in .env or PM2 ecosystem):
 *   SLACK_BOT_TOKEN         — xoxb-... from the "SQA Agent" Slack app
 *   SLACK_APP_TOKEN         — xapp-... Socket Mode app-level token
 *
 * Optional:
 *   AGENT_TEST_TIMEOUT_MS   — max ms before the jest child is killed (default 600000)
 */

require('dotenv').config({ path: require('path').resolve(__dirname, '../.env') });

const { App }         = require('@slack/bolt');
const { spawn }       = require('child_process');
const path            = require('path');
const fs              = require('fs');

const ROOT            = path.resolve(__dirname, '..');
const TIMEOUT_MS      = parseInt(process.env.AGENT_TEST_TIMEOUT_MS || '600000', 10);

// ── Validate required env vars ────────────────────────────────────────────────
['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN'].forEach((key) => {
  if (!process.env[key]) {
    console.error(`❌  ${key} is not set — the SQA Agent cannot start without it.`);
    process.exit(1);
  }
});

const app = new App({
  token:       process.env.SLACK_BOT_TOKEN,
  appToken:    process.env.SLACK_APP_TOKEN,
  socketMode:  true,
  logLevel:    'error',
});

// ── Build the jest command for each subcommand ────────────────────────────────
function buildCommand(subcommand) {
  const npx  = process.platform === 'win32' ? 'npx.cmd' : 'npx';
  const base = [npx, 'jest', '--ci', '--forceExit', '--json',
    `--outputFile=${path.join(ROOT, 'reports', 'agent-results.json')}`];

  if (!subcommand || subcommand === 'major') {
    return { args: [...base, '--config', path.join(ROOT, 'jest.config.js')], label: 'Full Test Suite' };
  }

  if (subcommand === 'smoke') {
    return { args: [...base, '--config', path.join(ROOT, 'jest.smoke.js')], label: 'Production Smoke Tests' };
  }

  if (subcommand.startsWith('feature:')) {
    const name = subcommand.slice('feature:'.length).trim();
    const file = path.join(ROOT, 'tests', `${name}.test.js`);
    if (!fs.existsSync(file)) {
      return { error: `No test file found for *${name}*.\nExpected: \`tests/${name}.test.js\`` };
    }
    return { args: [...base, file], label: `Feature Suite: ${name}` };
  }

  if (subcommand.startsWith('api:')) {
    const fragment = subcommand.slice('api:'.length).trim();
    return {
      args: [...base, '--testNamePattern', fragment, '--config', path.join(ROOT, 'jest.config.js')],
      label: `API Path Filter: \`${fragment}\``,
    };
  }

  return { error: `Unknown subcommand: *${subcommand}*\n\nUsage:\n• \`/zambeel-test major\`\n• \`/zambeel-test smoke\`\n• \`/zambeel-test feature:<name>\`\n• \`/zambeel-test api:<path>\`` };
}

// ── Parse jest JSON output into a summary ─────────────────────────────────────
function parseSummary(resultsPath) {
  try {
    if (!fs.existsSync(resultsPath)) return null;
    const d = JSON.parse(fs.readFileSync(resultsPath, 'utf8'));
    const failures = [];
    for (const suite of d.testResults || []) {
      for (const t of suite.testResults || []) {
        if (t.status === 'failed') failures.push(t.fullName);
      }
    }
    return {
      total:    d.numTotalTests   || 0,
      passed:   d.numPassedTests  || 0,
      failed:   d.numFailedTests  || 0,
      pending:  d.numPendingTests || 0,
      duration: Math.round(((d.testResults || []).reduce((s, r) => s + (r.perfStats?.runtime || 0), 0)) / 1000),
      failures: failures.slice(0, 10),
      overflow: Math.max(0, failures.length - 10),
    };
  } catch {
    return null;
  }
}

// ── Block Kit builders ────────────────────────────────────────────────────────
function startBlocks(label, user) {
  return [
    {
      type: 'header',
      text: { type: 'plain_text', text: '⏳  Zambeel SQA Agent — Tests Running', emoji: true },
    },
    {
      type: 'section',
      fields: [
        { type: 'mrkdwn', text: `*Suite:*\n${label}` },
        { type: 'mrkdwn', text: `*Triggered by:*\n<@${user}>` },
      ],
    },
    {
      type: 'context',
      elements: [{ type: 'mrkdwn', text: '_Results will appear here when the run completes._' }],
    },
  ];
}

function resultBlocks(label, summary, elapsed) {
  if (!summary) {
    return [
      {
        type: 'header',
        text: { type: 'plain_text', text: '⚠️  Zambeel SQA Agent — No Results', emoji: true },
      },
      {
        type: 'section',
        text: { type: 'mrkdwn', text: `Suite *${label}* completed but produced no parseable results.\nCheck the server logs for details.` },
      },
    ];
  }

  const allPass   = summary.failed === 0;
  const icon      = allPass ? '✅' : '🚨';
  const headline  = allPass ? 'All Clear' : `${summary.failed} Failure${summary.failed > 1 ? 's' : ''}`;
  const blocks    = [];

  blocks.push({
    type: 'header',
    text: { type: 'plain_text', text: `${icon}  Zambeel SQA Agent — ${headline}`, emoji: true },
  });

  blocks.push({
    type: 'section',
    fields: [
      { type: 'mrkdwn', text: `*Suite:*\n${label}` },
      { type: 'mrkdwn', text: `*Duration:*\n${elapsed}s` },
      { type: 'mrkdwn', text: `*Passed:*\n${summary.passed} / ${summary.total}` },
      { type: 'mrkdwn', text: `*Failed:*\n${summary.failed}` },
    ],
  });

  if (summary.failures.length > 0) {
    blocks.push({ type: 'divider' });
    const rows = summary.failures.map((n) => `• ${n.slice(0, 100)}`).join('\n');
    const suffix = summary.overflow > 0 ? `\n_…and ${summary.overflow} more_` : '';
    blocks.push({
      type: 'section',
      text: { type: 'mrkdwn', text: `*Failed Tests*\n${rows}${suffix}` },
    });
  }

  blocks.push({ type: 'divider' });
  blocks.push({
    type: 'context',
    elements: [{ type: 'mrkdwn', text: `Zambeel SQA Agent  |  <@agent>` }],
  });

  return blocks;
}

function errorBlocks(label, message) {
  return [
    {
      type: 'header',
      text: { type: 'plain_text', text: '🔴  Zambeel SQA Agent — Error', emoji: true },
    },
    {
      type: 'section',
      text: { type: 'mrkdwn', text: `Suite *${label}* encountered an error:\n\`\`\`${message.slice(0, 500)}\`\`\`` },
    },
  ];
}

// ── Slash command handler ─────────────────────────────────────────────────────
app.command('/zambeel-test', async ({ command, ack, respond }) => {
  await ack();

  const subcommand = (command.text || '').trim();
  const built      = buildCommand(subcommand);

  if (built.error) {
    await respond({
      response_type: 'ephemeral',
      text:          built.error,
    });
    return;
  }

  const { args, label } = built;

  // Acknowledge immediately with a "running" message
  await respond({
    response_type: 'in_channel',
    blocks:        startBlocks(label, command.user_id),
    text:          `Running ${label}…`,
  });

  const started  = Date.now();
  const resultsPath = path.join(ROOT, 'reports', 'agent-results.json');

  // Remove stale results file so we don't accidentally read a prior run
  if (fs.existsSync(resultsPath)) fs.unlinkSync(resultsPath);

  const [cmd, ...cmdArgs] = args;

  const child = spawn(cmd, cmdArgs, {
    cwd:   ROOT,
    env:   { ...process.env, CI: 'true', NODE_ENV: 'test', FORCE_COLOR: '0' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  let stderr = '';
  child.stderr.on('data', (d) => { stderr += d.toString(); });

  const timer = setTimeout(() => {
    child.kill('SIGTERM');
    stderr += '\n[SQA Agent] Jest process killed after timeout';
  }, TIMEOUT_MS);

  child.on('close', async (code) => {
    clearTimeout(timer);
    const elapsed = Math.round((Date.now() - started) / 1000);
    const summary = parseSummary(resultsPath);

    try {
      if (code !== 0 && !summary) {
        // Jest didn't produce output — likely config/startup error
        await respond({
          replace_original: false,
          response_type:    'in_channel',
          blocks:           errorBlocks(label, stderr || `Exit code ${code}`),
          text:             `${label} failed with exit code ${code}`,
        });
      } else {
        await respond({
          replace_original: false,
          response_type:    'in_channel',
          blocks:           resultBlocks(label, summary, elapsed),
          text:             summary
            ? `${label}: ${summary.passed}/${summary.total} passed in ${elapsed}s`
            : `${label} completed in ${elapsed}s`,
        });
      }
    } catch (err) {
      console.error('[SQA Agent] Failed to post result to Slack:', err.message);
    }
  });
});

// ── Start the app ─────────────────────────────────────────────────────────────
(async () => {
  await app.start();
  console.log('🤖  Zambeel SQA Agent is running (Socket Mode)');
})();

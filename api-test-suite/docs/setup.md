# Zambeel API Test Suite — Setup Guide

## 1. Prerequisites

| Tool | Minimum version | Check |
|------|----------------|-------|
| Node.js | 18 LTS | `node -v` |
| npm | 9 | `npm -v` |
| PM2 (optional, for Slack agent) | 5 | `pm2 -v` |

Clone this repo alongside `zambeel-api` (only needed for route discovery, not for running tests):

```
~/Documents/GitHub/
  zambeel-api/          ← backend source
  api-test-suite/       ← this repo
```

---

## 2. Installation

```bash
cd api-test-suite
npm install
```

---

## 3. Environment configuration

Copy the example file and fill in the values:

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```
BASE_URL=http://localhost:3000        # or your staging server URL
JWT_SECRET=<same value as zambeel-api JWT_SECRET>

ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=<admin account password>

SELLER_EMAIL=seller@example.com
SELLER_PASSWORD=<seller account password>

AGENCY_EMAIL=agency@example.com
AGENCY_PASSWORD=<agency account password>
```

The suite calls `POST /api/login` with these credentials at test start and caches the tokens for the run. **No manual token rotation is ever needed.**

### Stable entity IDs

Set `TEST_ORDER_ID`, `TEST_TICKET_ID`, `TEST_VARIANT_ID` to real IDs that exist in staging and will not be deleted between runs. Completed or archived records work best.

---

## 4. Running the tests

### Full staging suite

```bash
npm test                   # all test files, interactive
npm run test:ci            # CI mode — JSON output to reports/results.json
```

### By category

```bash
npm run test:auth          # auth.test.js
npm run test:orders        # orders.test.js
npm run test:dashboard     # dashboard.test.js
npm run test:inventory     # inventory.test.js
npm run test:support       # support.test.js
npm run test:bulk-ops      # bulk-ops.test.js
npm run test:reporting     # reporting.test.js
npm run test:admin         # admin.test.js
```

### P0 only (fast gate)

```bash
npm run test:p0            # runs only [P0] tagged tests
```

### Production smoke (read-only)

Requires the `PROD_*` env vars in `.env`:

```bash
npx jest --config jest.smoke.js --ci --json --outputFile=reports/smoke-results.json
```

---

## 5. SLA baselines

SLA thresholds live in `sla-config.json`. Re-measure them against staging after major infrastructure changes:

```bash
node scripts/measure-baselines.js             # measures & writes sla-config.json
node scripts/measure-baselines.js --dry-run   # print only, do not write
```

The script runs 15 iterations per endpoint and computes:

| Threshold | Formula |
|-----------|---------|
| `pass`    | `ceil(p95 × 1.20)` |
| `warn`    | `ceil(p95 × 1.50)` |
| `fail`    | `ceil(p95 × 2.00)` |

After updating `sla-config.json`, commit it so CI picks up the new baselines.

---

## 6. Slack agent (live /zambeel-test commands)

### One-time Slack app setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch** → name it `SQA Agent`.
2. Enable **Socket Mode** under *Settings > Socket Mode* → generate an App-Level Token with `connections:write` scope → copy it to `SLACK_APP_TOKEN`.
3. Add a slash command `/zambeel-test` under *Features > Slash Commands* (Request URL can be anything — Socket Mode ignores it).
4. Add bot scopes under *OAuth & Permissions*: `commands`, `chat:write`.
5. Install the app to your workspace → copy the Bot User OAuth Token to `SLACK_BOT_TOKEN`.
6. Invite `@SQA Agent` to the channel where you plan to use `/zambeel-test`.

### Running the agent locally

```bash
npm run agent              # starts scripts/slack-agent.js directly
```

### Running via PM2 (production)

```bash
npm run agent:pm2          # pm2 start scripts/start-agent.js
pm2 logs zambeel-sqa-agent # tail logs
pm2 save                   # persist across reboots
pm2 startup                # install system service
```

### Slash command usage

```
/zambeel-test major             — full staging suite
/zambeel-test smoke             — production smoke tests
/zambeel-test feature:orders    — tests/orders.test.js only
/zambeel-test api:/api/dashboard — filter by URL fragment
```

---

## 7. CI/CD setup (GitHub Actions)

### Required GitHub Secrets (staging)

| Secret | Description |
|--------|-------------|
| `BASE_URL` | Staging API URL |
| `JWT_SECRET` | Staging JWT secret |
| `ADMIN_EMAIL` | Admin account email |
| `ADMIN_PASSWORD` | Admin account password |
| `SELLER_EMAIL` | Seller account email |
| `SELLER_PASSWORD` | Seller account password |
| `AGENCY_EMAIL` | Agency account email |
| `AGENCY_PASSWORD` | Agency account password |
| `TEST_ORDER_ID` | Stable order ID |
| `TEST_TICKET_ID` | Stable ticket ID |
| `TEST_TICKET_STORE_ID` | Stable ticket store ID |
| `TEST_VARIANT_ID` | Stable variant ID |

### Required GitHub Secrets (production smoke)

| Secret | Description |
|--------|-------------|
| `PROD_BASE_URL` | Production API URL |
| `PROD_ADMIN_EMAIL` | Prod admin email |
| `PROD_ADMIN_PASSWORD` | Prod admin password |
| `PROD_SELLER_EMAIL` | Prod seller email |
| `PROD_SELLER_PASSWORD` | Prod seller password |
| `PROD_AGENCY_EMAIL` | Prod agency email |
| `PROD_AGENCY_PASSWORD` | Prod agency password |
| `PROD_JWT_SECRET` | Prod JWT secret (for expired-token tests only) |
| `PROD_SAMPLE_ORDER_ID` | Stable prod order ID |
| `PROD_SAMPLE_TICKET_ID` | Stable prod ticket ID |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook for smoke alerts |

### Workflows

| Workflow | Trigger | File |
|----------|---------|------|
| `Zambeel API Tests` | Push / PR to `main` or `staging` | `.github/workflows/api-tests.yml` |
| `Production Smoke Tests` | Manual (`workflow_dispatch`) | `.github/workflows/smoke-prod.yml` |

The staging workflow enforces a **P0 gate**: any `[P0]` test failure blocks the merge. P1/P2 failures produce warnings but do not block.

The smoke workflow never fails the job (production stays live); results are reported to Slack and stored as artifacts.

# Zambeel API Testing Standards

_Version 1.0 | Owner: SQA | Last updated: 2026-05-04_

---

## 1. Purpose & Scope

This document defines the standards, methodology, and conventions for the Zambeel API automated test suite. It is the authoritative reference for anyone adding, modifying, or reviewing API tests for the Zambeel dropshipping and warehousing platform.

**In scope:** All HTTP endpoints exposed by the Zambeel backend (`/api/*`), including authentication, orders, inventory, reporting, support, and admin routes.

**Out of scope:** Frontend/UI testing, third-party integrations (Firebase, Shopify, Salla, YouCan) beyond the Zambeel-side contract, and database-level tests.

---

## 2. Testing Dimensions

Every endpoint in the test suite is tested across four dimensions. A test file for an endpoint must cover all applicable dimensions.

### Dimension 1 — Performance
**What it tests:** Response time under repeated load against the calibrated SLA threshold.

**Method:** Run the endpoint 15 times sequentially. Compute avg, p50, p95, p99. Assert that `avg ≤ warn threshold` (p95 × 1.5 from calibration).

**Pass means:** The average response time across 15 iterations is within the warn-level SLA, indicating no active performance regression.

### Dimension 2 — Auth & Authorization
**What it tests:** The endpoint correctly enforces authentication and role-based access.

**Method:** Send requests with (a) no token, (b) an expired token, (c) a valid token for a role that is not permitted on this route.

**Pass means:** Unauthenticated requests return 401. Role-unauthorised requests return 403. Authorised requests do not return 401 or 403.

### Dimension 3 — Input Validation
**What it tests:** The endpoint safely handles malformed, missing, or out-of-range input without returning 500.

**Method:** Send requests with missing required fields, wrong types, empty bodies, non-numeric IDs, oversized strings, and boundary values.

**Pass means:** All invalid inputs return a 4xx response. No invalid input causes a 500 Internal Server Error.

### Dimension 4 — Security
**What it tests:** The endpoint is resistant to common injection attacks and does not degrade under rapid load.

**Method:** Send SQL injection payloads, XSS payloads, and 25 rapid concurrent requests.

**Pass means:** No payload causes a 500. Rate-limit responses (429) are acceptable. 5xx responses are not.

---

## 3. SLA Methodology — Two-Phase System

The SLA system uses a two-phase approach to separate calibration from ongoing monitoring.

### Phase 1 — Calibration (`npm run calibrate`)

Run once when setting up the suite or after a major infrastructure change.

1. Run each eligible GET endpoint 30 times against production.
2. Discard the first 3 iterations as warm-up (eliminates cold TCP/DNS overhead).
3. Compute the **p95** of the remaining 27 effective readings as the calibrated baseline.
4. Derive three threshold levels using buffer factors:

| Level | Formula | Meaning |
|---|---|---|
| ✅ Pass | p95 × 1.20 | 20% headroom above p95 — normal operation |
| ⚠️ Warn | p95 × 1.50 | 50% above p95 — degraded, investigate |
| ❌ Fail | p95 × 2.00 | Double p95 — SLA breach, escalate |

Results are written to `sla-config.json` and `docs/sla-reference.md`.

### Phase 2 — Baseline Measurement (`npm run baseline`)

Run on every CI pass or after any deployment.

1. Run each endpoint 10 times. Discard the first 1 (warm-up). Use the remaining 9.
2. Compare the **average** of the 9 effective readings against the Phase 1 thresholds.
3. Flag regressions where the avg worsened by more than 15% versus the previous run.
4. Append results to `docs/baseline-log.md` and `reports/baseline-runs.json`.

### Threshold in Jest Tests

Jest performance tests assert `avg ≤ warn threshold` (p95 × 1.5), not the pass threshold. This accommodates normal production variance while still catching meaningful regressions. The pass threshold is used only in `npm run baseline` reporting.

---

## 4. Priority Definitions

Priorities are assigned in `api-inventory.json` and drive calibration order, SLA stringency expectations, and how failures are treated in CI.

| Priority | Label | Definition | SLA Breach Action | Examples |
|---|---|---|---|---|
| **P0** | Critical | Core user journeys — a failure here blocks the product from functioning | Blocks merge; page on-call | Login, order status counts, seller dashboard |
| **P1** | High | Common features used by most users daily | Investigated same day | Order details, inventory, ticket list, teams |
| **P2** | Medium | Secondary or infrequent features | Investigated this sprint | Auth check-email, billing status, admin routes |

---

## 5. Auth Contract

The Zambeel platform uses Firebase-issued idTokens exchanged for Zambeel JWTs at `POST /api/login`. The test suite maintains three role tokens obtained via `getToken(role)` in `beforeAll`.

| Role | Access level | Token source |
|---|---|---|
| `admin` | Full access to all routes | `ADMIN_EMAIL` / `ADMIN_PASSWORD` |
| `seller` | Seller-scoped routes only | `SELLER_EMAIL` / `SELLER_PASSWORD` |
| `agency` | Agency-scoped routes only | `AGENCY_EMAIL` / `AGENCY_PASSWORD` |

### Expected status codes by scenario

| Scenario | Expected |
|---|---|
| No `Authorization` header | 401 |
| Malformed token (`Bearer notvalid`) | 401 |
| Expired token (valid signature, past `exp`) | 401 |
| Valid token, wrong role for this route | 403 |
| Valid token, correct role | 2xx |

Any deviation from this contract — especially a route returning 200 for an unauthenticated or wrong-role request — is classified as a **Critical** bug.

---

## 6. Security Testing Standards

### What we probe

| Attack type | Payloads | Applied to |
|---|---|---|
| SQL injection | `' OR '1'='1`, `'; DROP TABLE orders; --`, `' OR 1=1 --`, `admin'--` | Query params, path params, body fields |
| XSS | `<script>alert(1)</script>`, `"><img src=x onerror=alert(1)>`, `javascript:alert(1)` | String body fields, query params |
| Rate limiting | 25 concurrent identical requests | All endpoints |

### Pass criteria

| Scenario | Pass | Fail |
|---|---|---|
| SQL injection payload | Any 4xx, any 2xx (input rejected or harmlessly handled) | 500 |
| XSS payload | Any 4xx, any 2xx (stored or rejected — XSS is a frontend concern) | 500 |
| 25 rapid requests | All responses are non-5xx (429 acceptable) | Any 5xx |

SQL injection returning 500 is the highest-severity security finding: it indicates the payload reached the database layer unsanitised.

---

## 7. Input Validation Standards

### What we send

| Input type | Example |
|---|---|
| Missing required field | Empty body `{}` on POST |
| Wrong type | String where integer expected (`page: "abc"`) |
| Out of range | `limit: -1`, `limit: 999999` |
| Non-existent resource | Large numeric ID unlikely to exist |
| Oversized string | 100KB string for a text field |
| Non-numeric path param | `/api/resource/not-a-number` |

### Pass criteria

All invalid inputs must return a 4xx status code. A 500 for any of the above is a **High** priority bug — it indicates missing input validation allowing invalid data to reach the database or business logic layer.

---

## 8. Dead Endpoint Policy

An endpoint is declared **DEAD** when it returns 100% timeouts (0 effective readings out of 30 calibration iterations).

### What happens

1. `npm run calibrate` writes `{ "status": "DEAD", "pass": null, "warn": null, "fail": null }` to `sla-config.json`.
2. The endpoint appears in a dedicated **Dead Endpoints — Requires Backend Investigation** section in `docs/sla-reference.md`.
3. In Jest test files, the endpoint's `describe` block is automatically skipped via `(isDeadSlaKey(key) ? describe.skip : describe)(...)`. All four test dimensions are skipped — a dead endpoint that blocks on every request would stall the entire test suite.
4. `npm run baseline` records the endpoint as TIMEOUT and excludes it from SLA comparison.

### Re-enabling a dead endpoint

Once the backend team confirms the endpoint is fixed:
1. Remove the `"status": "DEAD"` entry from `sla-config.json` (or update `pass`/`warn`/`fail` with valid thresholds).
2. Run `npm run calibrate` to establish a fresh baseline.
3. The `describe.skip` in the test file will automatically revert to `describe` on the next run.

---

## 9. Pass / Warn / Fail Criteria — Formal Definitions

### In Jest tests (`npm test`)

| Dimension | Pass | Fail |
|---|---|---|
| Performance | `avg ≤ sla.warn` (p95 × 1.5) | `avg > sla.warn` |
| Auth | Correct HTTP status for each scenario | Wrong status code |
| Input validation | All invalid inputs → 4xx | Any invalid input → 5xx |
| Security | No payload causes 5xx; rate-limit produces no 5xx | Any 5xx from payload or rate-limit |

### In baseline measurement (`npm run baseline`)

| Result | Condition |
|---|---|
| ✅ PASS | `avg ≤ sla.pass` (p95 × 1.2) |
| ⚠️ WARN | `sla.pass < avg ≤ sla.warn` (p95 × 1.5) |
| ❌ FAIL | `avg > sla.warn` |
| ⬜ NO SLA | No entry in `sla-config.json` |
| 💀 DEAD | `status === "DEAD"` in `sla-config.json` |

### Regression detection

A regression is flagged when the current run's avg exceeds the previous run's avg by more than **15%**. Regressions are logged in `docs/baseline-log.md` but do not automatically fail CI — they are informational.

---

## 10. How to Add a New API Endpoint to the Test Suite

### Step 1 — Add the route to `api-inventory.json`

```json
{
  "id": "TC_NNN",
  "method": "GET",
  "path": "/api/your/endpoint",
  "authRequired": true,
  "roles": ["Admin", "Seller"],
  "category": "orders",
  "priority": "P1",
  "slaKey": "yourEndpointKey"
}
```

Choose `priority` based on the definitions in Section 4. Set `slaKey` to a camelCase key that will be used in `sla-config.json`.

### Step 2 — Calibrate to generate the SLA threshold

```bash
npm run calibrate
```

This populates `sla-config.json` with `{ pass, warn, fail, p95_baseline }` for your new `slaKey`. If the endpoint times out consistently, it will be marked DEAD — investigate before writing tests.

### Step 3 — Write the test file entry

Add a `describe` block to the appropriate test file (or create a new file following the existing pattern). Cover all four dimensions:

```javascript
const { measurePerformance, assertSla, isDeadSlaKey } = require('./helpers/performance');

(isDeadSlaKey('yourEndpointKey') ? describe.skip : describe)('[TC_NNN] METHOD /api/your/endpoint', () => {
  describe('[PERF] Performance', () => {
    test('[P1][TC_NNN] endpoint avg responds within SLA', async () => {
      const stats = await measurePerformance(() => /* request */, 15);
      assertSla('METHOD /api/your/endpoint', 'yourEndpointKey', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_NNN] returns 401 with no token', ...);
    test('[TC_NNN] returns 401 with expired token', ...);
    // Add 403 tests if the route is role-restricted
  });

  describe('[VALID] Input Validation', () => {
    // Test missing fields, wrong types, boundary values
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)('[TC_NNN] SQL injection does not cause 500: %s', ...);
    test.each(XSS_PAYLOADS)('[TC_NNN] XSS does not cause 500: %s', ...);
    test('[TC_NNN] rate limit — 25 rapid requests do not produce 5xx', ...);
  });
});
```

### Step 4 — Run the full suite

```bash
npm test
```

All four dimensions must pass before the endpoint is considered covered.

### Step 5 — Verify in baseline

```bash
npm run baseline
```

Confirm the endpoint shows ✅ PASS in the baseline output and is included in `docs/baseline-log.md`.

---

_Questions or proposed changes to these standards should be raised with the SQA team lead._

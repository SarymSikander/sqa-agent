# Zambeel API — Bug Report

_Generated: 2026-05-04 | Source: Automated test suite Run #002 + npm test_

---

## Critical — Fix Immediately

### BUG-001 · SQL Injection Returning 500 on variantId Routes

| Field | Detail |
|---|---|
| **Endpoints** | `GET /api/inventory/purchase-order/:variantId` · `GET /api/inventory/inventory-movements/:variantId` |
| **Test cases** | TC_015 · TC_017 |
| **Priority** | P1 |

**Expected behaviour:** SQL injection payloads in `:variantId` path param return 400 or 422. The server sanitises or rejects the input before it reaches the database layer.

**Actual behaviour:** Returns `500 Internal Server Error`. The payload is being passed unsanitised to the database query, triggering an unhandled exception.

**Payloads that triggered 500:**
- `' OR '1'='1`
- `'; DROP TABLE orders; --`
- `' OR 1=1 --`
- `admin'--`

**Suggested fix:** Add path-param validation middleware that rejects non-numeric variantId values with 400 before they reach the controller. Ensure all ORM queries use parameterised statements — never string-interpolate path params into raw SQL.

---

### BUG-002 · Auth Middleware Missing on /api/teams and /api/agents

| Field | Detail |
|---|---|
| **Endpoints** | `GET /api/teams` · `GET /api/agents` |
| **Test cases** | TC_007 · TC_008 |
| **Priority** | P0 (potential auth bypass) |

**Expected behaviour:**
- No token → 401
- Expired token → 401
- Seller token on Admin/Agent route → 403
- Agency token on Admin/Agent route → 403

**Actual behaviour:** Tests for all four conditions are failing, indicating the endpoints are either returning 200 (auth bypass) or 5xx (server error before auth check runs).

**Suggested fix:** Verify that `verifyJWT` middleware and the Admin/Agent role guard are applied to both routes. Check route registration order — a wildcard or earlier route may be intercepting requests before auth middleware fires.

---

## High — Fix This Sprint

### BUG-003 · 500 on Invalid Pagination Params in Seller Inventory

| Field | Detail |
|---|---|
| **Endpoint** | `GET /api/inventory/seller-inventory` |
| **Test case** | TC_013 |
| **Priority** | P1 |

**Expected behaviour:** `?page=abc` and `?limit=-1` return 400. The API validates query params before passing them to the ORM.

**Actual behaviour:** Returns `500 Internal Server Error`. The ORM is receiving invalid values and throwing an unhandled exception.

**Suggested fix:** Add query-param validation (e.g. Joi schema or express-validator) that coerces `page` and `limit` to positive integers and rejects non-numeric values with 400.

---

### BUG-004 · 500 for Non-Existent Ticket in Comments Endpoint

| Field | Detail |
|---|---|
| **Endpoint** | `GET /api/comments/ticket/:ticketId` |
| **Test case** | TC_023 (support.test.js) |
| **Priority** | P1 |

**Expected behaviour:** A `:ticketId` that does not exist in the database returns 404 Not Found.

**Actual behaviour:** Returns `500 Internal Server Error`. The controller does not check whether the ticket exists before querying its comments.

**Suggested fix:** Add an existence check: `SELECT 1 FROM tickets WHERE id = :ticketId`. Return 404 if not found, proceed only if found.

---

### BUG-005 · Agency Role Not Receiving 403 on Bulk Approve

| Field | Detail |
|---|---|
| **Endpoint** | `PUT /api/orders/approve-status/bulk` |
| **Test case** | TC_087 |
| **Priority** | P1 |

**Expected behaviour:** A request made with an Agency-role JWT returns 403 Forbidden. The route is restricted to Admin/Agent/Seller roles.

**Actual behaviour:** Agency token does not receive 403 — the role guard is either absent or incorrectly configured.

**Suggested fix:** Confirm the route's role guard explicitly lists permitted roles. If using an allowlist, ensure `Agency` is not included. If using a blocklist, ensure `Agency` is listed.

---

### BUG-006 · Test Suite Crash — Invalid `tokens` Import in tickets.test.js

| Field | Detail |
|---|---|
| **File** | `tests/tickets.test.js` |
| **Priority** | P1 (blocks CI) |

**Expected behaviour:** Suite runs all test cases for TC_018–TC_024.

**Actual behaviour:** Suite fails to start. `tokens` is destructured from `helpers/auth.js` which does not export a `tokens` object — it exports the async `getToken()` function. Module evaluation crashes at line 21 with `TypeError: Cannot read properties of undefined`.

**Status:** Fixed — import changed to `getToken` called inside a `beforeAll` block. Matches the pattern used by all other test files.

---

## Dead Endpoints — Backend Investigation Required

These endpoints returned 100% timeouts across all calibration iterations (30 runs) and both baseline measurement runs. They have been marked `status: "DEAD"` in `sla-config.json` and their test blocks are automatically skipped.

| TC ID | Method | Endpoint | Priority | Note |
|---|---|---|---|---|
| TC_004 | GET | `/api/verify-email` | P2 | 100% timeout rate on production |
| TC_071 | GET | `/api/orders/substatusOrders` | P2 | 100% timeout rate on production |
| TC_072 | GET | `/api/orders/seller-orders` | P2 | 100% timeout rate on production |
| TC_112 | GET | `/api/orders/substatus-orders-for-csv` | P2 | 100% timeout rate on production |
| — | GET | `/api/orders/status-counts` | P0 | Intermittent — full timeout in Run #001, slow (988ms avg) in Run #002 |

**Recommended action:** Route these to the backend team for investigation. Possible causes: missing route registration, middleware deadlock, DB query without timeout, or misconfigured proxy.

---

## Performance Regressions — Current Test Run

All measurements are `avg` of 15 iterations against production. Threshold is the calibrated `warn` level (p95 × 1.5). Endpoints failing this threshold in the current run:

| Endpoint | Avg | Warn Threshold | Delta |
|---|---|---|---|
| `GET /api/dashboard/data` | 756ms | 281ms | +169% |
| `GET /api/agents` | 2002ms | 372ms | +438% |
| `GET /api/teams` | 915ms | 351ms | +161% |
| `POST /api/remarks` | 2113ms | 345ms | +513% |
| `POST /api/tags` | 1223ms | 315ms | +288% |
| `GET /api/orders/tracking-generation-report` | 1158ms | 251ms | +361% |
| `GET /api/orders/dispatch-batches` | 648ms | 248ms | +161% |
| `POST /api/orders/courier-assignment/report` | 559ms | — (no SLA) | — |
| `GET /api/orders/status-counts` | 988ms | 282ms | +250% |
| `GET /api/orders/:orderId/logs` | 556ms | 290ms | +92% |
| `GET /api/orders/order-analytics` | 813ms | 705ms | +15% |
| `GET /api/inventory/seller-inventory` | 635ms | 309ms | +105% |
| `GET /api/admin/gold-subscriptions/users` | 633ms | 284ms | +123% |
| `GET /api/tickets` | 630ms | 558ms | +13% |
| `GET /api/comments/ticket/:ticketId` | 553ms | 285ms | +94% |

**Context:** Baseline Run #001 and #002 showed high run-to-run variance on the same endpoints, suggesting intermittent server-side load rather than a code regression. Recommend investigating DB connection pool saturation, N+1 queries, and missing indexes on the `/api/orders/*` endpoints which show the widest spread.

---

_Generated by automated test suite. Re-run `npm test` after fixes to verify resolution._

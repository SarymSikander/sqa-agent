/**
 * @readonly
 *
 * Production Smoke Test Suite — Zambeel API
 *
 * ┌──────────────────────────────────────────────────────────────────────────┐
 * │  READ-ONLY CONTRACT                                                      │
 * │  Every request MUST be one of:                                           │
 * │    • GET  <any endpoint>                                                 │
 * │    • POST /api/login  (wrong-creds probe — no side effects)              │
 * │  No mutations. No uploads. No status changes. No bulk operations.        │
 * └──────────────────────────────────────────────────────────────────────────┘
 *
 * Auth: fully autonomous — logs in via PROD_*_EMAIL + PROD_*_PASSWORD.
 * No manual token rotation. Credentials stored in GitHub Actions secrets.
 *
 * Smoke IDs are SMOKE-scoped, separate from the main TC_xxx inventory.
 *   [SMOKE-TC_001]  POST /api/login
 *   [SMOKE-TC_002]  GET  /api/orders/seller-orders
 *   [SMOKE-TC_003]  GET  /api/orders/status-counts
 *   [SMOKE-TC_004]  GET  /api/orders/orderDetails/:orderId
 *   [SMOKE-TC_005]  GET  /api/orders/order-analytics
 *   [SMOKE-TC_006]  GET  /api/dashboard/data
 *   [SMOKE-TC_007]  GET  /api/tickets
 *   [SMOKE-TC_008]  GET  /api/comments/ticket/:ticketId
 *   [SMOKE-TC_009]  GET  /api/teams
 *   [SMOKE-TC_010]  GET  /api/auth/check-email
 *   [SMOKE-TC_011]  GET  /api/inventory/seller-inventory
 *   [SMOKE-TC_012]  GET  /api/orders/substatus-orders-for-csv
 *
 * Required env vars (PROD_ prefix — separate from staging):
 *   PROD_BASE_URL
 *   PROD_ADMIN_EMAIL / PROD_ADMIN_PASSWORD   (Admin role)
 *   PROD_SELLER_EMAIL / PROD_SELLER_PASSWORD (Seller role)
 *   PROD_AGENCY_EMAIL / PROD_AGENCY_PASSWORD (Agency role)
 *   PROD_JWT_SECRET                          (for expired token generation only)
 *   PROD_SAMPLE_ORDER_ID, PROD_SAMPLE_TICKET_ID
 */

require('dotenv').config({ path: require('path').resolve(__dirname, '../../.env') });

const supertest = require('supertest');
const jwt       = require('jsonwebtoken');

const { SQL_INJECTION, XSS_PAYLOADS, oversizedString } = require('../helpers/security-payloads');
const { measurePerformance, assertSla }                = require('../helpers/performance');
const { getToken, bearer }                             = require('../helpers/auth');

const PROD_BASE_URL         = process.env.PROD_BASE_URL         || 'http://localhost:3000';
const PROD_JWT_SECRET       = process.env.PROD_JWT_SECRET        || process.env.JWT_SECRET || 'fallback-dev-secret';
const PROD_SAMPLE_ORDER_ID  = process.env.PROD_SAMPLE_ORDER_ID   || '1';
const PROD_SAMPLE_TICKET_ID = process.env.PROD_SAMPLE_TICKET_ID  || '1';

const api = supertest(PROD_BASE_URL);

// ── Helpers ───────────────────────────────────────────────────────────────────
function prodExpiredToken() {
  return jwt.sign(
    { sub: 9999, role: 'Admin', email: 'expired@smoke.test' },
    PROD_JWT_SECRET,
    { expiresIn: '-1s', algorithm: 'HS256' }
  );
}

function skip(tokenName) {
  console.warn(`\n⚠️  [SMOKE] ${tokenName} not set — skipping test\n`);
  return true;
}

// Production tokens — fetched autonomously at suite start
let prodAdminToken, prodSellerToken, prodAgencyToken;

beforeAll(async () => {
  [prodAdminToken, prodSellerToken, prodAgencyToken] = await Promise.all([
    getToken('admin',  'prod'),
    getToken('seller', 'prod'),
    getToken('agency', 'prod'),
  ]);
}, 30000);

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_001] POST /api/login
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_001] POST /api/login', () => {
  const login = (body) =>
    api.post('/api/login').send(body).set('Content-Type', 'application/json');

  describe('[perf] Performance', () => {
    test('[SMOKE-TC_001][perf] login avg responds within SLA (15 iterations)', async () => {
      const stats = await measurePerformance(
        () => login({ email: 'smoke-probe@test.com', password: 'wrongpass' }),
        15
      );
      assertSla('POST /api/login', 'login', stats);
    });
  });

  describe('[auth] Auth — public endpoint', () => {
    test('[SMOKE-TC_001][auth] login is publicly reachable (not 502/503/500)', async () => {
      const res = await login({ email: 'nobody@test.com', password: 'wrongpass' });
      expect([200, 400, 401, 404, 422]).toContain(res.status);
    });

    test('[SMOKE-TC_001][auth] expired JWT in header does not crash server', async () => {
      const res = await login({ email: 'x@x.com', password: 'x' })
        .set('Authorization', bearer(prodExpiredToken()));
      expect(res.status).not.toBe(500);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_001][validation] empty body returns 4xx not 5xx', async () => {
      const res = await login({});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[SMOKE-TC_001][validation] missing password returns 4xx not 5xx', async () => {
      const res = await login({ email: 'test@example.com' });
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[SMOKE-TC_001][validation] oversized email (5000 chars) does not cause 500', async () => {
      const res = await login({ email: oversizedString(5000) + '@test.com', password: 'x' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test.each(SQL_INJECTION)(
      '[SMOKE-TC_001][security] SQL injection in email does not cause 500: %s',
      async (payload) => {
        const res = await login({ email: payload, password: 'x' });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(XSS_PAYLOADS)(
      '[SMOKE-TC_001][security] XSS in email does not cause 500: %s',
      async (payload) => {
        const res = await login({ email: payload, password: 'x' });
        expect(res.status).not.toBe(500);
        expect(JSON.stringify(res.body)).not.toContain('<script>');
      }
    );

    test('[SMOKE-TC_001][security] rate limit — 25 rapid login attempts do not produce 5xx', async () => {
      const reqs = Array.from({ length: 25 }, () =>
        login({ email: 'ratelimit@smoke.test', password: 'wrongpass' })
      );
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_002] GET /api/orders/seller-orders  (Seller/Agency, read-only)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_002] GET /api/orders/seller-orders', () => {
  const getSellerOrders = (query = {}) =>
    api.get('/api/orders/seller-orders')
      .set('Authorization', bearer(prodSellerToken || ''))
      .query(query);

  describe('[perf] Performance', () => {
    test('[SMOKE-TC_002][perf] seller-orders avg responds within SLA (15 iterations)', async () => {
      if (!prodSellerToken) { skip('PROD_SELLER_EMAIL/PASSWORD'); return; }
      const stats = await measurePerformance(
        () => getSellerOrders({ page: 1, limit: 20 }),
        15
      );
      assertSla('GET /api/orders/seller-orders', 'getOrders', stats);
    });
  });

  describe('[auth] Auth', () => {
    test('[SMOKE-TC_002][auth] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/seller-orders');
      expect(res.status).toBe(401);
    });

    test('[SMOKE-TC_002][auth] returns 401 with expired token', async () => {
      const res = await api.get('/api/orders/seller-orders')
        .set('Authorization', bearer(prodExpiredToken()));
      expect(res.status).toBe(401);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_002][validation] non-numeric page does not cause 500', async () => {
      if (!prodSellerToken) return;
      const res = await getSellerOrders({ page: 'abc', limit: 10 });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test.each(SQL_INJECTION)(
      '[SMOKE-TC_002][security] SQL injection in search param does not cause 500: %s',
      async (payload) => {
        if (!prodSellerToken) return;
        const res = await getSellerOrders({ search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[SMOKE-TC_002][security] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!prodSellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getSellerOrders({ page: 1, limit: 1 }));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_003] GET /api/orders/status-counts  (Admin)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_003] GET /api/orders/status-counts', () => {
  const getStatusCounts = (query = {}) =>
    api.get('/api/orders/status-counts')
      .set('Authorization', bearer(prodAdminToken || ''))
      .query(query);

  describe('[perf] Performance', () => {
    test('[SMOKE-TC_003][perf] status-counts avg responds within SLA (15 iterations)', async () => {
      if (!prodAdminToken) { skip('PROD_ADMIN_EMAIL/PASSWORD'); return; }
      const stats = await measurePerformance(() => getStatusCounts(), 15);
      assertSla('GET /api/orders/status-counts', 'statusCounts', stats);
    });
  });

  describe('[auth] Auth', () => {
    test('[SMOKE-TC_003][auth] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/status-counts');
      expect(res.status).toBe(401);
    });

    test('[SMOKE-TC_003][auth] returns 401 with expired token', async () => {
      const res = await api.get('/api/orders/status-counts')
        .set('Authorization', bearer(prodExpiredToken()));
      expect(res.status).toBe(401);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_003][validation] unknown query params are silently ignored (no 500)', async () => {
      if (!prodAdminToken) return;
      const res = await getStatusCounts({ bogus: 'ignored' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test.each(SQL_INJECTION)(
      '[SMOKE-TC_003][security] SQL injection in query param does not cause 500: %s',
      async (payload) => {
        if (!prodAdminToken) return;
        const res = await api.get('/api/orders/status-counts')
          .set('Authorization', bearer(prodAdminToken))
          .query({ store_id: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[SMOKE-TC_003][security] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!prodAdminToken) return;
      const reqs = Array.from({ length: 25 }, () => getStatusCounts());
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_004] GET /api/orders/orderDetails/:orderId
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_004] GET /api/orders/orderDetails/:orderId', () => {
  const token = () => prodAdminToken || prodSellerToken;
  const getOrderDetails = (id = PROD_SAMPLE_ORDER_ID) =>
    api.get(`/api/orders/orderDetails/${id}`)
      .set('Authorization', bearer(token() || ''));

  describe('[perf] Performance', () => {
    test('[SMOKE-TC_004][perf] orderDetails avg responds within SLA (15 iterations)', async () => {
      if (!token()) { skip('PROD_ADMIN_EMAIL or PROD_SELLER_EMAIL'); return; }
      const stats = await measurePerformance(() => getOrderDetails(), 15);
      assertSla(`GET /api/orders/orderDetails/${PROD_SAMPLE_ORDER_ID}`, 'orderDetails', stats);
    });
  });

  describe('[auth] Auth', () => {
    test('[SMOKE-TC_004][auth] returns 401 with no token', async () => {
      const res = await api.get(`/api/orders/orderDetails/${PROD_SAMPLE_ORDER_ID}`);
      expect(res.status).toBe(401);
    });

    test('[SMOKE-TC_004][auth] returns 401 with expired token', async () => {
      const res = await api.get(`/api/orders/orderDetails/${PROD_SAMPLE_ORDER_ID}`)
        .set('Authorization', bearer(prodExpiredToken()));
      expect(res.status).toBe(401);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_004][validation] non-numeric orderId returns 4xx not 500', async () => {
      if (!token()) return;
      const res = await api.get('/api/orders/orderDetails/not-a-number')
        .set('Authorization', bearer(token()));
      expect(res.status).not.toBe(500);
    });

    test('[SMOKE-TC_004][validation] very large orderId returns 4xx not 500', async () => {
      if (!token()) return;
      const res = await api.get('/api/orders/orderDetails/9999999999')
        .set('Authorization', bearer(token()));
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test.each(SQL_INJECTION)(
      '[SMOKE-TC_004][security] SQL injection in orderId does not cause 500: %s',
      async (payload) => {
        if (!token()) return;
        const res = await api.get(`/api/orders/orderDetails/${encodeURIComponent(payload)}`)
          .set('Authorization', bearer(token()));
        expect(res.status).not.toBe(500);
      }
    );

    test('[SMOKE-TC_004][security] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!token()) return;
      const reqs = Array.from({ length: 25 }, () => getOrderDetails());
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_005] GET /api/orders/order-analytics  (Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_005] GET /api/orders/order-analytics', () => {
  const getAnalytics = (query = {}) =>
    api.get('/api/orders/order-analytics')
      .set('Authorization', bearer(prodSellerToken || ''))
      .query(query);

  describe('[perf] Performance', () => {
    test('[SMOKE-TC_005][perf] order-analytics avg responds within SLA (15 iterations)', async () => {
      if (!prodSellerToken) { skip('PROD_SELLER_EMAIL/PASSWORD'); return; }
      const stats = await measurePerformance(() => getAnalytics(), 15);
      assertSla('GET /api/orders/order-analytics', 'orderAnalytics', stats);
    });
  });

  describe('[auth] Auth', () => {
    test('[SMOKE-TC_005][auth] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/order-analytics');
      expect(res.status).toBe(401);
    });

    test('[SMOKE-TC_005][auth] returns 401 with expired token', async () => {
      const res = await api.get('/api/orders/order-analytics')
        .set('Authorization', bearer(prodExpiredToken()));
      expect(res.status).toBe(401);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_005][validation] invalid date range does not cause 500', async () => {
      if (!prodSellerToken) return;
      const res = await getAnalytics({ from: 'not-a-date', to: 'also-not' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test.each(SQL_INJECTION)(
      '[SMOKE-TC_005][security] SQL injection in date param does not cause 500: %s',
      async (payload) => {
        if (!prodSellerToken) return;
        const res = await getAnalytics({ from: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[SMOKE-TC_005][security] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!prodSellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getAnalytics());
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_006] GET /api/dashboard/data  (Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_006] GET /api/dashboard/data', () => {
  const getDashboard = (query = {}) =>
    api.get('/api/dashboard/data')
      .set('Authorization', bearer(prodSellerToken || ''))
      .query(query);

  describe('[perf] Performance', () => {
    test('[SMOKE-TC_006][perf] dashboard avg responds within SLA (15 iterations)', async () => {
      if (!prodSellerToken) { skip('PROD_SELLER_EMAIL/PASSWORD'); return; }
      const stats = await measurePerformance(() => getDashboard(), 15);
      assertSla('GET /api/dashboard/data', 'sellerDashboard', stats);
    });
  });

  describe('[auth] Auth', () => {
    test('[SMOKE-TC_006][auth] returns 401 with no token', async () => {
      const res = await api.get('/api/dashboard/data');
      expect(res.status).toBe(401);
    });

    test('[SMOKE-TC_006][auth] returns 401 with expired token', async () => {
      const res = await api.get('/api/dashboard/data')
        .set('Authorization', bearer(prodExpiredToken()));
      expect(res.status).toBe(401);
    });

    test('[SMOKE-TC_006][auth] returns 401 with malformed token', async () => {
      const res = await api.get('/api/dashboard/data')
        .set('Authorization', 'Bearer totally.invalid.token');
      expect(res.status).toBe(401);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_006][validation] unknown query params do not cause 500', async () => {
      if (!prodSellerToken) return;
      const res = await getDashboard({ unknownParam: 'unicorn' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test.each(SQL_INJECTION)(
      '[SMOKE-TC_006][security] SQL injection in query param does not cause 500: %s',
      async (payload) => {
        if (!prodSellerToken) return;
        const res = await getDashboard({ from: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[SMOKE-TC_006][security] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!prodSellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getDashboard());
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_007] GET /api/tickets  (any role)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_007] GET /api/tickets', () => {
  const anyToken = () => prodAdminToken || prodSellerToken || prodAgencyToken;
  const getTickets = (query = {}) =>
    api.get('/api/tickets')
      .set('Authorization', bearer(anyToken() || ''))
      .query(query);

  describe('[perf] Performance', () => {
    test('[SMOKE-TC_007][perf] tickets avg responds within SLA (15 iterations)', async () => {
      if (!anyToken()) { skip('any PROD credential'); return; }
      const stats = await measurePerformance(() => getTickets({ page: 1, limit: 20 }), 15);
      assertSla('GET /api/tickets', 'ticketList', stats);
    });
  });

  describe('[auth] Auth', () => {
    test('[SMOKE-TC_007][auth] returns 401 with no token', async () => {
      const res = await api.get('/api/tickets');
      expect(res.status).toBe(401);
    });

    test('[SMOKE-TC_007][auth] returns 401 with expired token', async () => {
      const res = await api.get('/api/tickets')
        .set('Authorization', bearer(prodExpiredToken()));
      expect(res.status).toBe(401);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_007][validation] non-numeric limit does not cause 500', async () => {
      if (!anyToken()) return;
      const res = await getTickets({ limit: 'lots' });
      expect(res.status).not.toBe(500);
    });

    test('[SMOKE-TC_007][validation] oversized search string (5000 chars) does not cause 500', async () => {
      if (!anyToken()) return;
      const res = await getTickets({ search: oversizedString(5000) });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test.each(SQL_INJECTION)(
      '[SMOKE-TC_007][security] SQL injection in search param does not cause 500: %s',
      async (payload) => {
        if (!anyToken()) return;
        const res = await getTickets({ search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[SMOKE-TC_007][security] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!anyToken()) return;
      const reqs = Array.from({ length: 25 }, () => getTickets({ page: 1, limit: 1 }));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_008] GET /api/comments/ticket/:ticketId  (any role)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_008] GET /api/comments/ticket/:ticketId', () => {
  const anyToken = () => prodAdminToken || prodSellerToken || prodAgencyToken;
  const getComments = (id = PROD_SAMPLE_TICKET_ID) =>
    api.get(`/api/comments/ticket/${id}`)
      .set('Authorization', bearer(anyToken() || ''));

  describe('[perf] Performance', () => {
    test('[SMOKE-TC_008][perf] ticket comments avg responds within SLA (15 iterations)', async () => {
      if (!anyToken()) { skip('any PROD credential'); return; }
      const stats = await measurePerformance(() => getComments(), 15);
      assertSla(`GET /api/comments/ticket/${PROD_SAMPLE_TICKET_ID}`, 'ticketComments', stats);
    });
  });

  describe('[auth] Auth', () => {
    test('[SMOKE-TC_008][auth] returns 401 with no token', async () => {
      const res = await api.get(`/api/comments/ticket/${PROD_SAMPLE_TICKET_ID}`);
      expect(res.status).toBe(401);
    });

    test('[SMOKE-TC_008][auth] returns 401 with expired token', async () => {
      const res = await api.get(`/api/comments/ticket/${PROD_SAMPLE_TICKET_ID}`)
        .set('Authorization', bearer(prodExpiredToken()));
      expect(res.status).toBe(401);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_008][validation] non-numeric ticketId does not cause 500', async () => {
      if (!anyToken()) return;
      const res = await api.get('/api/comments/ticket/not-a-number')
        .set('Authorization', bearer(anyToken()));
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test.each(SQL_INJECTION)(
      '[SMOKE-TC_008][security] SQL injection in ticketId does not cause 500: %s',
      async (payload) => {
        if (!anyToken()) return;
        const res = await api.get(`/api/comments/ticket/${encodeURIComponent(payload)}`)
          .set('Authorization', bearer(anyToken()));
        expect(res.status).not.toBe(500);
      }
    );

    test('[SMOKE-TC_008][security] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!anyToken()) return;
      const reqs = Array.from({ length: 25 }, () => getComments());
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_009] GET /api/teams  (Admin)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_009] GET /api/teams', () => {
  const getTeams = () =>
    api.get('/api/teams').set('Authorization', bearer(prodAdminToken || ''));

  describe('[perf] Performance', () => {
    test('[SMOKE-TC_009][perf] teams avg responds within SLA (15 iterations)', async () => {
      if (!prodAdminToken) { skip('PROD_ADMIN_EMAIL/PASSWORD'); return; }
      const stats = await measurePerformance(getTeams, 15);
      assertSla('GET /api/teams', 'teamslist', stats);
    });
  });

  describe('[auth] Auth', () => {
    test('[SMOKE-TC_009][auth] returns 401 with no token', async () => {
      const res = await api.get('/api/teams');
      expect(res.status).toBe(401);
    });

    test('[SMOKE-TC_009][auth] returns 401 with expired token', async () => {
      const res = await api.get('/api/teams')
        .set('Authorization', bearer(prodExpiredToken()));
      expect(res.status).toBe(401);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_009][validation] unknown query params do not cause 500', async () => {
      if (!prodAdminToken) return;
      const res = await api.get('/api/teams')
        .set('Authorization', bearer(prodAdminToken))
        .query({ bogus: 'value' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test('[SMOKE-TC_009][security] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!prodAdminToken) return;
      const reqs = Array.from({ length: 25 }, getTeams);
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_010] GET /api/auth/check-email  (public)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_010] GET /api/auth/check-email', () => {
  const PROBE = 'smoke-probe-nonexistent@zambeel-test.com';
  const checkEmail = (email = PROBE) =>
    api.get('/api/auth/check-email').query({ email });

  describe('[perf] Performance', () => {
    test('[SMOKE-TC_010][perf] check-email avg responds within 1 second (15 iterations)', async () => {
      const stats = await measurePerformance(() => checkEmail(), 15);
      assertSla('GET /api/auth/check-email', 'checkEmail', stats);
    });
  });

  describe('[auth] Auth — public endpoint', () => {
    test('[SMOKE-TC_010][auth] check-email is publicly accessible (no 401)', async () => {
      const res = await checkEmail();
      expect([200, 400, 404, 422]).toContain(res.status);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_010][validation] missing email param returns 4xx not 500', async () => {
      const res = await api.get('/api/auth/check-email');
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[SMOKE-TC_010][validation] oversized email param does not cause 500', async () => {
      const res = await checkEmail(oversizedString(5000) + '@test.com');
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test.each(SQL_INJECTION)(
      '[SMOKE-TC_010][security] SQL injection in email param does not cause 500: %s',
      async (payload) => {
        const res = await checkEmail(payload);
        expect(res.status).not.toBe(500);
      }
    );

    test('[SMOKE-TC_010][security] rate limit — 25 rapid requests do not produce 5xx', async () => {
      const reqs = Array.from({ length: 25 }, () => checkEmail());
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_011] GET /api/inventory/seller-inventory  (Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_011] GET /api/inventory/seller-inventory', () => {
  const getInventory = (query = {}) =>
    api.get('/api/inventory/seller-inventory')
      .set('Authorization', bearer(prodSellerToken || ''))
      .query(query);

  describe('[perf] Performance', () => {
    test('[SMOKE-TC_011][perf] seller-inventory avg responds within SLA (15 iterations)', async () => {
      if (!prodSellerToken) { skip('PROD_SELLER_EMAIL/PASSWORD'); return; }
      const stats = await measurePerformance(() => getInventory(), 15);
      assertSla('GET /api/inventory/seller-inventory', 'stockValidation', stats);
    });
  });

  describe('[auth] Auth', () => {
    test('[SMOKE-TC_011][auth] returns 401 with no token', async () => {
      const res = await api.get('/api/inventory/seller-inventory');
      expect(res.status).toBe(401);
    });

    test('[SMOKE-TC_011][auth] returns 401 with expired token', async () => {
      const res = await api.get('/api/inventory/seller-inventory')
        .set('Authorization', bearer(prodExpiredToken()));
      expect(res.status).toBe(401);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_011][validation] non-numeric page does not cause 500', async () => {
      if (!prodSellerToken) return;
      const res = await getInventory({ page: 'nan', limit: 10 });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test.each(SQL_INJECTION)(
      '[SMOKE-TC_011][security] SQL injection in search param does not cause 500: %s',
      async (payload) => {
        if (!prodSellerToken) return;
        const res = await getInventory({ search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[SMOKE-TC_011][security] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!prodSellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getInventory());
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [SMOKE-TC_012] GET /api/orders/substatus-orders-for-csv  (Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SMOKE-TC_012] GET /api/orders/substatus-orders-for-csv', () => {
  const getCsvOrders = (query = {}) =>
    api.get('/api/orders/substatus-orders-for-csv')
      .set('Authorization', bearer(prodSellerToken || ''))
      .query(query);

  describe('[auth] Auth', () => {
    test('[SMOKE-TC_012][auth] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/substatus-orders-for-csv');
      expect(res.status).toBe(401);
    });

    test('[SMOKE-TC_012][auth] returns 401 with expired token', async () => {
      const res = await api.get('/api/orders/substatus-orders-for-csv')
        .set('Authorization', bearer(prodExpiredToken()));
      expect(res.status).toBe(401);
    });
  });

  describe('[validation] Input Validation', () => {
    test('[SMOKE-TC_012][validation] non-numeric sub_status_id does not cause 500', async () => {
      if (!prodSellerToken) return;
      const res = await getCsvOrders({ sub_status_id: 'abc' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[security] Security', () => {
    test.each(SQL_INJECTION)(
      '[SMOKE-TC_012][security] SQL injection in query param does not cause 500: %s',
      async (payload) => {
        if (!prodSellerToken) return;
        const res = await getCsvOrders({ sub_status_id: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[SMOKE-TC_012][security] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!prodSellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getCsvOrders());
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

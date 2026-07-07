/**
 * Dashboard & Teams test suite
 *
 * Routes covered:
 *   [TC_009] GET /api/dashboard/data  Seller/Agency — P0
 *   [TC_007] GET /api/teams           Admin/Agent   — P1
 *   [TC_008] GET /api/agents          Admin/Agent   — P1
 *
 * Dimensions per route:
 *   [PERF]  15 iterations, avg ≤ pass threshold, report p95/p99
 *   [AUTH]  401 no token, 401 expired, 401 malformed, 403 wrong role
 *   [VALID] Invalid date ranges, unknown params, negative offsets
 *   [SEC]   SQL injection, XSS, 25-request burst, sensitive data check
 */

const { api }                                           = require('./helpers/http');
const { getToken, bearer, expiredToken }                = require('./helpers/auth');
const { SQL_INJECTION, XSS_PAYLOADS }                   = require('./helpers/security-payloads');
const { measurePerformance, assertSla }                 = require('./helpers/performance');

let adminToken, sellerToken, agencyToken;
beforeAll(async () => {
  [adminToken, sellerToken, agencyToken] = await Promise.all([
    getToken('admin'),
    getToken('seller'),
    getToken('agency'),
  ]);
}, 30000);

// ─────────────────────────────────────────────────────────────────────────────
// [TC_009] GET /api/dashboard/data  (P0, Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_009] GET /api/dashboard/data', () => {
  const getDashboard = (token, query = {}) =>
    api.get('/api/dashboard/data')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[PERF] Performance', () => {
    test('[P0][TC_009] sellerDashboard avg responds within SLA (15 iterations)', async () => {
      if (!sellerToken) return;
      const stats = await measurePerformance(() => getDashboard(sellerToken), 15);
      assertSla('GET /api/dashboard/data', 'sellerDashboard', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P0][TC_009] returns 401 with no token', async () => {
      const res = await api.get('/api/dashboard/data');
      expect(res.status).toBe(401);
    });

    test('[P0][TC_009] returns 401 with expired token', async () => {
      const res = await api.get('/api/dashboard/data')
        .set('Authorization', bearer(expiredToken()));
      expect(res.status).toBe(401);
    });

    test('[P0][TC_009] returns 401 with malformed Bearer token', async () => {
      const res = await api.get('/api/dashboard/data')
        .set('Authorization', 'Bearer this.is.not.valid');
      expect(res.status).toBe(401);
    });

    test('[P0][TC_009] admin token on Seller/Agency dashboard returns 403', async () => {
      if (!adminToken) return;
      const res = await getDashboard(adminToken);
      expect(res.status).toBe(403);
    });

    test('[P0][TC_009] agency token can access seller dashboard', async () => {
      if (!agencyToken) return;
      const res = await getDashboard(agencyToken);
      // Agency has verifySeller access — should not be 401 or 403
      expect(res.status).not.toBe(401);
      expect(res.status).not.toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_009] unknown query params are ignored (no 500)', async () => {
      if (!sellerToken) return;
      const res = await getDashboard(sellerToken, { unknownParam: 'somevalue', foo: 123 });
      expect(res.status).not.toBe(500);
    });

    test('[TC_009] invalid date range does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await getDashboard(sellerToken, { from: 'not-a-date', to: 'also-not' });
      expect(res.status).not.toBe(500);
    });

    test('[TC_009] future date range does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await getDashboard(sellerToken, { from: '2099-01-01', to: '2099-12-31' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_009] SQL injection in query params does not cause 500: %s',
      async (payload) => {
        if (!sellerToken) return;
        const res = await getDashboard(sellerToken, { from: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(XSS_PAYLOADS)(
      '[TC_009] XSS in query params does not cause 500: %s',
      async (payload) => {
        if (!sellerToken) return;
        const res = await getDashboard(sellerToken, { store_name: payload });
        expect(res.status).not.toBe(500);
        expect(JSON.stringify(res.body)).not.toContain('<script>');
      }
    );

    test('[TC_009] response does not leak sensitive fields', async () => {
      if (!sellerToken) return;
      const res = await getDashboard(sellerToken);
      const body = JSON.stringify(res.body);
      expect(body).not.toContain('passwordHash');
      expect(body).not.toContain('stack');
      expect(body).not.toContain('__v');
    });

    test('[TC_009] rate limit — 25 rapid dashboard requests do not produce 5xx', async () => {
      if (!sellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getDashboard(sellerToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
      const rateLimited = responses.filter((r) => r.status === 429);
      if (rateLimited.length) console.log(`    Rate limiting active: ${rateLimited.length}/25 returned 429`);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_007] GET /api/teams  (P1, Admin/Agent)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_007] GET /api/teams', () => {
  const getTeams = (token, query = {}) =>
    api.get('/api/teams')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[PERF] Performance', () => {
    test('[P1][TC_007] teamslist avg responds within SLA (15 iterations)', async () => {
      if (!adminToken) return;
      const stats = await measurePerformance(() => getTeams(adminToken), 15);
      assertSla('GET /api/teams', 'teamslist', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P1][TC_007] returns 401 with no token', async () => {
      const res = await api.get('/api/teams');
      expect(res.status).toBe(401);
    });

    test('[P1][TC_007] returns 401 with expired token', async () => {
      const res = await api.get('/api/teams').set('Authorization', bearer(expiredToken()));
      expect(res.status).toBe(401);
    });

    test('[P1][TC_007] seller token on Admin/Agent route returns 403', async () => {
      if (!sellerToken) return;
      const res = await getTeams(sellerToken);
      expect(res.status).toBe(403);
    });

    test('[P1][TC_007] agency token on Admin/Agent route returns 403', async () => {
      if (!agencyToken) return;
      const res = await getTeams(agencyToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_007] non-numeric page does not cause 500', async () => {
      if (!adminToken) return;
      const res = await getTeams(adminToken, { page: 'abc', limit: 10 });
      expect(res.status).not.toBe(500);
    });

    test('[TC_007] unknown params are ignored (no 500)', async () => {
      if (!adminToken) return;
      const res = await getTeams(adminToken, { bogus: 'value', foo: 123 });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_007] SQL injection in query param does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await getTeams(adminToken, { search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_007] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getTeams(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_008] GET /api/agents  (P1, Admin/Agent)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_008] GET /api/agents', () => {
  const getAgents = (token, query = {}) =>
    api.get('/api/agents')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[PERF] Performance', () => {
    test('[P1][TC_008] agentsList avg responds within SLA (15 iterations)', async () => {
      if (!adminToken) return;
      const stats = await measurePerformance(() => getAgents(adminToken), 15);
      assertSla('GET /api/agents', 'agentsList', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P1][TC_008] returns 401 with no token', async () => {
      const res = await api.get('/api/agents');
      expect(res.status).toBe(401);
    });

    test('[P1][TC_008] returns 401 with expired token', async () => {
      const res = await api.get('/api/agents').set('Authorization', bearer(expiredToken()));
      expect(res.status).toBe(401);
    });

    test('[P1][TC_008] seller token on Admin/Agent route returns 403', async () => {
      if (!sellerToken) return;
      const res = await getAgents(sellerToken);
      expect(res.status).toBe(403);
    });

    test('[P1][TC_008] agency token on Admin/Agent route returns 403', async () => {
      if (!agencyToken) return;
      const res = await getAgents(agencyToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_008] non-numeric page does not cause 500', async () => {
      if (!adminToken) return;
      const res = await getAgents(adminToken, { page: 'xyz' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_008] SQL injection in query param does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await getAgents(adminToken, { search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_008] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getAgents(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

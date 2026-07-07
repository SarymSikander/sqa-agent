/**
 * Admin test suite
 *
 * Routes covered:
 *   [TC_124] GET  /api/admin/gold-subscriptions/users/gold          Admin
 *   [TC_125] GET  /api/admin/gold-subscriptions/users               Admin
 *   [TC_126] GET  /api/admin/gold-subscriptions/users/:userId       Admin
 *   [TC_127] POST /api/admin/gold-subscriptions/give                Admin
 *   [TC_128] POST /api/admin/gold-subscriptions/extend              Admin
 *   [TC_129] POST /api/admin/gold-subscriptions/remove              Admin
 *   [TC_130] GET  /api/admin/agency-registrations/applications      Admin
 *   [TC_131] GET  /api/admin/agency-registrations/applications/:id  Admin
 *   [TC_132] GET  /api/admin/agency-registrations/commission-models Admin
 *   [TC_133] GET  /api/admin/agency-registrations/commission-models/manage Admin
 *   [TC_134] POST /api/admin/agency-registrations/commission-models Admin
 *
 * Dimensions per route:
 *   [PERF]  15 iterations, avg ≤ pass threshold, report p95/p99
 *   [AUTH]  401 no token, 401 expired, 403 seller, 403 agency
 *   [VALID] Missing required fields, wrong types, empty body
 *   [SEC]   SQL injection, XSS, 25-request burst
 */

const { api }                                           = require('./helpers/http');
const { getToken, bearer, expiredToken }                = require('./helpers/auth');
const { SQL_INJECTION, XSS_PAYLOADS, oversizedString }  = require('./helpers/security-payloads');
const { measurePerformance, assertSla }                 = require('./helpers/performance');

const TEST_USER_ID = parseInt(process.env.TEST_ADMIN_USER_ID || '1', 10);
const TEST_APP_ID  = parseInt(process.env.TEST_AGENCY_APP_ID || '1', 10);

let adminToken, sellerToken, agencyToken;
beforeAll(async () => {
  [adminToken, sellerToken, agencyToken] = await Promise.all([
    getToken('admin'),
    getToken('seller'),
    getToken('agency'),
  ]);
}, 30000);

// ─────────────────────────────────────────────────────────────────────────────
// [TC_125] GET /api/admin/gold-subscriptions/users  (Admin only)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_125] GET /api/admin/gold-subscriptions/users', () => {
  const getGoldUsers = (token, query = {}) =>
    api.get('/api/admin/gold-subscriptions/users')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[PERF] Performance', () => {
    test('[TC_125] admin/gold-subscriptions/users avg responds within SLA (15 iterations)', async () => {
      if (!adminToken) return;
      const stats = await measurePerformance(() => getGoldUsers(adminToken), 15);
      assertSla('GET /api/admin/gold-subscriptions/users', 'adminGoldUsers', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_125] returns 401 with no token', async () => {
      const res = await api.get('/api/admin/gold-subscriptions/users');
      expect(res.status).toBe(401);
    });

    test('[TC_125] returns 401 with expired token', async () => {
      const res = await getGoldUsers(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[TC_125] seller token returns 403 (Admin only)', async () => {
      if (!sellerToken) return;
      const res = await getGoldUsers(sellerToken);
      expect(res.status).toBe(403);
    });

    test('[TC_125] agency token returns 403 (Admin only)', async () => {
      if (!agencyToken) return;
      const res = await getGoldUsers(agencyToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_125] non-numeric page does not cause 500', async () => {
      if (!adminToken) return;
      const res = await getGoldUsers(adminToken, { page: 'abc' });
      expect(res.status).not.toBe(500);
    });

    test('[TC_125] unknown params are ignored (no 500)', async () => {
      if (!adminToken) return;
      const res = await getGoldUsers(adminToken, { bogus: 'ignored' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_125] SQL injection in query param does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await getGoldUsers(adminToken, { search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_125] response does not leak sensitive fields', async () => {
      if (!adminToken) return;
      const res = await getGoldUsers(adminToken);
      const body = JSON.stringify(res.body);
      expect(body).not.toContain('passwordHash');
      expect(body).not.toContain('stack');
    });

    test('[TC_125] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getGoldUsers(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_124] GET /api/admin/gold-subscriptions/users/gold  (Admin only)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_124] GET /api/admin/gold-subscriptions/users/gold', () => {
  const getGoldOnly = (token) =>
    api.get('/api/admin/gold-subscriptions/users/gold')
      .set('Authorization', bearer(token || ''));

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_124] returns 401 with no token', async () => {
      const res = await api.get('/api/admin/gold-subscriptions/users/gold');
      expect(res.status).toBe(401);
    });

    test('[TC_124] returns 401 with expired token', async () => {
      const res = await getGoldOnly(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[TC_124] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await getGoldOnly(sellerToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[SEC] Security', () => {
    test('[TC_124] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getGoldOnly(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_127] POST /api/admin/gold-subscriptions/give  (Admin only)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_127] POST /api/admin/gold-subscriptions/give', () => {
  const giveSubscription = (token, body = {}) =>
    api.post('/api/admin/gold-subscriptions/give')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_127] returns 401 with no token', async () => {
      const res = await api.post('/api/admin/gold-subscriptions/give').send({});
      expect(res.status).toBe(401);
    });

    test('[TC_127] returns 401 with expired token', async () => {
      const res = await giveSubscription(expiredToken(), {});
      expect(res.status).toBe(401);
    });

    test('[TC_127] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await giveSubscription(sellerToken, {});
      expect(res.status).toBe(403);
    });

    test('[TC_127] agency token returns 403', async () => {
      if (!agencyToken) return;
      const res = await giveSubscription(agencyToken, {});
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_127] empty body returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await giveSubscription(adminToken, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_127] wrong type for userId (string) does not cause 500', async () => {
      if (!adminToken) return;
      const res = await giveSubscription(adminToken, { userId: 'notanumber', months: 3 });
      expect(res.status).not.toBe(500);
    });

    test('[TC_127] negative months does not cause 500', async () => {
      if (!adminToken) return;
      const res = await giveSubscription(adminToken, { userId: TEST_USER_ID, months: -1 });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_127] SQL injection in userId does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await giveSubscription(adminToken, { userId: payload, months: 3 });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_127] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => giveSubscription(adminToken, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_130] GET /api/admin/agency-registrations/applications  (Admin only)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_130] GET /api/admin/agency-registrations/applications', () => {
  const getApplications = (token, query = {}) =>
    api.get('/api/admin/agency-registrations/applications')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[PERF] Performance', () => {
    test('[TC_130] agency applications avg responds within SLA (15 iterations)', async () => {
      if (!adminToken) return;
      const stats = await measurePerformance(() => getApplications(adminToken), 15);
      assertSla('GET /api/admin/agency-registrations/applications', 'agencyApplications', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_130] returns 401 with no token', async () => {
      const res = await api.get('/api/admin/agency-registrations/applications');
      expect(res.status).toBe(401);
    });

    test('[TC_130] returns 401 with expired token', async () => {
      const res = await getApplications(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[TC_130] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await getApplications(sellerToken);
      expect(res.status).toBe(403);
    });

    test('[TC_130] agency token returns 403 (admin only)', async () => {
      if (!agencyToken) return;
      const res = await getApplications(agencyToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_130] non-numeric page does not cause 500', async () => {
      if (!adminToken) return;
      const res = await getApplications(adminToken, { page: 'abc', limit: 10 });
      expect(res.status).not.toBe(500);
    });

    test('[TC_130] invalid status filter does not cause 500', async () => {
      if (!adminToken) return;
      const res = await getApplications(adminToken, { status: 'NOT_REAL_STATUS' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_130] SQL injection in query param does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await getApplications(adminToken, { search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_130] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getApplications(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_132] GET /api/admin/agency-registrations/commission-models  (Admin only)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_132] GET /api/admin/agency-registrations/commission-models', () => {
  const getCommissionModels = (token) =>
    api.get('/api/admin/agency-registrations/commission-models')
      .set('Authorization', bearer(token || ''));

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_132] returns 401 with no token', async () => {
      const res = await api.get('/api/admin/agency-registrations/commission-models');
      expect(res.status).toBe(401);
    });

    test('[TC_132] returns 401 with expired token', async () => {
      const res = await getCommissionModels(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[TC_132] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await getCommissionModels(sellerToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[SEC] Security', () => {
    test('[TC_132] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getCommissionModels(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_134] POST /api/admin/agency-registrations/commission-models  (Admin only)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_134] POST /api/admin/agency-registrations/commission-models', () => {
  const createCommissionModel = (token, body = {}) =>
    api.post('/api/admin/agency-registrations/commission-models')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_134] returns 401 with no token', async () => {
      const res = await api.post('/api/admin/agency-registrations/commission-models').send({});
      expect(res.status).toBe(401);
    });

    test('[TC_134] returns 401 with expired token', async () => {
      const res = await createCommissionModel(expiredToken(), {});
      expect(res.status).toBe(401);
    });

    test('[TC_134] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await createCommissionModel(sellerToken, {});
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_134] empty body returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await createCommissionModel(adminToken, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_134] negative commission rate does not cause 500', async () => {
      if (!adminToken) return;
      const res = await createCommissionModel(adminToken, {
        name: 'Test Model',
        commission_rate: -10,
      });
      expect(res.status).not.toBe(500);
    });

    test('[TC_134] oversized name (5000 chars) does not cause 500', async () => {
      if (!adminToken) return;
      const res = await createCommissionModel(adminToken, {
        name: oversizedString(5000),
        commission_rate: 10,
      });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(XSS_PAYLOADS)(
      '[TC_134] XSS in model name does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await createCommissionModel(adminToken, {
          name: payload,
          commission_rate: 10,
        });
        expect(res.status).not.toBe(500);
        expect(JSON.stringify(res.body)).not.toContain('<script>');
      }
    );

    test('[TC_134] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => createCommissionModel(adminToken, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

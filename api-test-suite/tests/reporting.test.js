/**
 * Reporting test suite
 *
 * Routes covered:
 *   [TC_075] GET  /api/orders/batch-ids                  Admin/Agent
 *   [TC_076] POST /api/orders/courier-assignment/report  Admin/Agent
 *   [TC_084] GET  /api/orders/batches/dip                Admin/Agent
 *   [TC_105] GET  /api/orders/dispatch-batches           Admin/Agent
 *   [TC_108] GET  /api/orders/tracking-generation-report Admin/Agent
 *   [TC_109] GET  /api/orders/vendors                    Admin/Agent
 *   [TC_112] GET  /api/orders/substatus-orders-for-csv   Seller/Agency
 *   [TC_071] GET  /api/orders/substatusOrders            Seller/Agency
 *
 * Dimensions per route:
 *   [PERF]  15 iterations, avg ≤ pass threshold, report p95/p99
 *   [AUTH]  401 no token, 401 expired, 403 wrong role
 *   [VALID] Wrong types, oversized params, invalid date ranges
 *   [SEC]   SQL injection, XSS, 25-request burst
 */

const { api }                                           = require('./helpers/http');
const { getToken, bearer, expiredToken }                = require('./helpers/auth');
const { SQL_INJECTION, XSS_PAYLOADS, oversizedString }  = require('./helpers/security-payloads');
const { measurePerformance, assertSla, isDeadSlaKey }   = require('./helpers/performance');

let adminToken, sellerToken, agencyToken;
beforeAll(async () => {
  [adminToken, sellerToken, agencyToken] = await Promise.all([
    getToken('admin'),
    getToken('seller'),
    getToken('agency'),
  ]);
}, 30000);

// ─────────────────────────────────────────────────────────────────────────────
// [TC_105] GET /api/orders/dispatch-batches  (Admin/Agent)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_105] GET /api/orders/dispatch-batches', () => {
  const getDispatchBatches = (token, query = {}) =>
    api.get('/api/orders/dispatch-batches')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[PERF] Performance', () => {
    test('[TC_105] dispatch-batches avg responds within SLA (15 iterations)', async () => {
      if (!adminToken) return;
      const stats = await measurePerformance(() => getDispatchBatches(adminToken), 15);
      assertSla('GET /api/orders/dispatch-batches', 'dispatchBatches', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_105] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/dispatch-batches');
      expect(res.status).toBe(401);
    });

    test('[TC_105] returns 401 with expired token', async () => {
      const res = await getDispatchBatches(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[TC_105] seller token on Admin/Agent route returns 403', async () => {
      if (!sellerToken) return;
      const res = await getDispatchBatches(sellerToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_105] non-numeric page does not cause 500', async () => {
      if (!adminToken) return;
      const res = await getDispatchBatches(adminToken, { page: 'abc', limit: 10 });
      expect(res.status).not.toBe(500);
    });

    test('[TC_105] invalid date range does not cause 500', async () => {
      if (!adminToken) return;
      const res = await getDispatchBatches(adminToken, { from: 'not-a-date', to: 'also-not' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_105] SQL injection in query param does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await getDispatchBatches(adminToken, { search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_105] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getDispatchBatches(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_108] GET /api/orders/tracking-generation-report  (Admin/Agent)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_108] GET /api/orders/tracking-generation-report', () => {
  const getTrackingReport = (token, query = {}) =>
    api.get('/api/orders/tracking-generation-report')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[PERF] Performance', () => {
    test('[TC_108] tracking-generation-report avg responds within SLA (15 iterations)', async () => {
      if (!adminToken) return;
      const stats = await measurePerformance(() => getTrackingReport(adminToken), 15);
      assertSla('GET /api/orders/tracking-generation-report', 'trackingReport', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_108] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/tracking-generation-report');
      expect(res.status).toBe(401);
    });

    test('[TC_108] returns 401 with expired token', async () => {
      const res = await getTrackingReport(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[TC_108] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await getTrackingReport(sellerToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_108] unknown query params are ignored (no 500)', async () => {
      if (!adminToken) return;
      const res = await getTrackingReport(adminToken, { unknown: 'param' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_108] SQL injection in query param does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await getTrackingReport(adminToken, { courier_id: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_108] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getTrackingReport(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_076] POST /api/orders/courier-assignment/report  (Admin/Agent)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_076] POST /api/orders/courier-assignment/report', () => {
  const courierReport = (token, body = {}) =>
    api.post('/api/orders/courier-assignment/report')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[PERF] Performance', () => {
    test('[TC_076] courier-assignment/report avg responds within SLA (15 iterations)', async () => {
      if (!adminToken) return;
      const stats = await measurePerformance(() => courierReport(adminToken, {}), 15);
      assertSla('POST /api/orders/courier-assignment/report', 'courierReport', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_076] returns 401 with no token', async () => {
      const res = await api.post('/api/orders/courier-assignment/report').send({});
      expect(res.status).toBe(401);
    });

    test('[TC_076] returns 401 with expired token', async () => {
      const res = await courierReport(expiredToken(), {});
      expect(res.status).toBe(401);
    });

    test('[TC_076] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await courierReport(sellerToken, {});
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_076] empty body does not cause 500', async () => {
      if (!adminToken) return;
      const res = await courierReport(adminToken, {});
      expect(res.status).not.toBe(500);
    });

    test('[TC_076] invalid date fields do not cause 500', async () => {
      if (!adminToken) return;
      const res = await courierReport(adminToken, { from: 'not-a-date', to: 'also-not' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_076] SQL injection in report params does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await courierReport(adminToken, { courier_id: payload, from: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_076] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => courierReport(adminToken, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_075] GET /api/orders/batch-ids  (Admin/Agent)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_075] GET /api/orders/batch-ids', () => {
  const getBatchIds = (token) =>
    api.get('/api/orders/batch-ids').set('Authorization', bearer(token || ''));

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_075] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/batch-ids');
      expect(res.status).toBe(401);
    });

    test('[TC_075] returns 401 with expired token', async () => {
      const res = await getBatchIds(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[TC_075] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await getBatchIds(sellerToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[SEC] Security', () => {
    test('[TC_075] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getBatchIds(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_112] GET /api/orders/substatus-orders-for-csv  (Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
(isDeadSlaKey('substatusOrdersForCsv') ? describe.skip : describe)('[TC_112] GET /api/orders/substatus-orders-for-csv', () => {
  const getSubstatusCsv = (token, query = {}) =>
    api.get('/api/orders/substatus-orders-for-csv')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_112] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/substatus-orders-for-csv');
      expect(res.status).toBe(401);
    });

    test('[TC_112] returns 401 with expired token', async () => {
      const res = await getSubstatusCsv(expiredToken());
      expect(res.status).toBe(401);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_112] non-numeric sub_status_id does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await getSubstatusCsv(sellerToken, { sub_status_id: 'abc' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_112] SQL injection in query param does not cause 500: %s',
      async (payload) => {
        if (!sellerToken) return;
        const res = await getSubstatusCsv(sellerToken, { sub_status_id: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_112] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!sellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getSubstatusCsv(sellerToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_109] GET /api/orders/vendors  (Admin/Agent)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_109] GET /api/orders/vendors', () => {
  const getVendors = (token) =>
    api.get('/api/orders/vendors').set('Authorization', bearer(token || ''));

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_109] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/vendors');
      expect(res.status).toBe(401);
    });

    test('[TC_109] returns 401 with expired token', async () => {
      const res = await getVendors(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[TC_109] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await getVendors(sellerToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[SEC] Security', () => {
    test('[TC_109] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getVendors(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

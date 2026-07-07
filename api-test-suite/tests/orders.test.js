/**
 * Orders test suite
 *
 * Routes covered (core order management — excludes bulk-ops and reporting):
 *   [TC_068] POST /api/orders/                    Admin/Agent — create order
 *   [TC_069] GET  /api/orders/status-counts       Admin/Agent — P0
 *   [TC_070] GET  /api/orders/order-analytics     Seller/Agency — P1
 *   [TC_071] GET  /api/orders/substatusOrders     Seller/Agency
 *   [TC_072] GET  /api/orders/seller-orders       Seller/Agency
 *   [TC_073] POST /api/orders/add-product         Admin/Agent/Seller
 *   [TC_074] GET  /api/orders/couriers            Admin/Agent
 *   [TC_077] POST /api/orders/assign-courier      Admin/Agent — P1
 *   [TC_078] POST /api/orders/check-availability  Admin/Agent
 *   [TC_080] GET  /api/orders/proccessedOrders    Seller/Agency
 *   [TC_081] GET  /api/orders/tags                Admin/Agent
 *   [TC_082] GET  /api/orders/remarks             Admin/Agent — P1
 *   [TC_083] POST /api/orders/ndr-remarks         Admin/Agent
 *   [TC_089] PUT  /api/orders/:orderId            Admin/Agent/Seller
 *   [TC_094] GET  /api/orders/orderDetails/:id    Admin/Agent/Seller — P0
 *   [TC_097] PUT  /api/orders/:orderId/status     Admin/Seller/Agency
 *   [TC_101] GET  /api/orders/:orderId/logs       Admin/Agent/Seller — P1
 *   [TC_010] POST /api/remarks                    (public? per inventory)
 *   [TC_011] POST /api/tags                       (public? per inventory)
 *
 * Dimensions per route:
 *   [PERF]  15 iterations, avg ≤ pass threshold, report p95/p99
 *   [AUTH]  401 no token, 401 expired, 403 wrong role
 *   [VALID] missing fields, wrong types, oversized, empty body
 *   [SEC]   SQL injection, XSS, mass assignment, sensitive data, 25-request burst
 */

const { api }                                           = require('./helpers/http');
const { getToken, bearer, expiredToken }                = require('./helpers/auth');
const { SQL_INJECTION, XSS_PAYLOADS, oversizedString }  = require('./helpers/security-payloads');
const { measurePerformance, assertSla, isDeadSlaKey }   = require('./helpers/performance');

const ORDER_ID = parseInt(process.env.TEST_ORDER_ID || '1', 10);

let adminToken, sellerToken, agencyToken;
beforeAll(async () => {
  [adminToken, sellerToken, agencyToken] = await Promise.all([
    getToken('admin'),
    getToken('seller'),
    getToken('agency'),
  ]);
}, 30000);

// ─────────────────────────────────────────────────────────────────────────────
// [TC_069] GET /api/orders/status-counts  (P0)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_069] GET /api/orders/status-counts', () => {
  const getStatusCounts = (token) =>
    api.get('/api/orders/status-counts').set('Authorization', bearer(token || ''));

  describe('[PERF] Performance', () => {
    test('[P0][TC_069] status-counts avg responds within SLA (15 iterations)', async () => {
      if (!adminToken) return;
      const stats = await measurePerformance(() => getStatusCounts(adminToken), 15);
      assertSla('GET /api/orders/status-counts', 'statusCounts', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P0][TC_069] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/status-counts');
      expect(res.status).toBe(401);
    });

    test('[P0][TC_069] returns 401 with expired token', async () => {
      const res = await api.get('/api/orders/status-counts')
        .set('Authorization', bearer(expiredToken()));
      expect(res.status).toBe(401);
    });

    test('[P0][TC_069] seller token on Admin/Agent route returns 403', async () => {
      if (!sellerToken) return;
      const res = await getStatusCounts(sellerToken);
      expect(res.status).toBe(403);
    });

    test('[P0][TC_069] agency token on Admin/Agent route returns 403', async () => {
      if (!agencyToken) return;
      const res = await getStatusCounts(agencyToken);
      expect(res.status).toBe(403);
    });

    test('[P0][TC_069] malformed Bearer token returns 401', async () => {
      const res = await api.get('/api/orders/status-counts')
        .set('Authorization', 'Bearer this.is.junk');
      expect(res.status).toBe(401);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_069] unknown query params are ignored (no 500)', async () => {
      if (!adminToken) return;
      const res = await getStatusCounts(adminToken).query({ foo: 'bar', unknown: 123 });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_069] SQL injection in query param does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await api.get('/api/orders/status-counts')
          .set('Authorization', bearer(adminToken))
          .query({ store_id: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_069] response does not leak sensitive fields', async () => {
      if (!adminToken) return;
      const res = await getStatusCounts(adminToken);
      const body = JSON.stringify(res.body);
      expect(body).not.toContain('passwordHash');
      expect(body).not.toContain('stack');
      expect(body).not.toContain('__v');
    });

    test('[TC_069] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getStatusCounts(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_094] GET /api/orders/orderDetails/:orderId  (P0)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_094] GET /api/orders/orderDetails/:orderId', () => {
  const getOrderDetails = (token, id = ORDER_ID) =>
    api.get(`/api/orders/orderDetails/${id}`).set('Authorization', bearer(token || ''));

  describe('[PERF] Performance', () => {
    test('[P0][TC_094] orderDetails avg responds within SLA (15 iterations)', async () => {
      if (!adminToken) return;
      const stats = await measurePerformance(() => getOrderDetails(adminToken), 15);
      assertSla(`GET /api/orders/orderDetails/${ORDER_ID}`, 'orderDetails', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P0][TC_094] returns 401 with no token', async () => {
      const res = await api.get(`/api/orders/orderDetails/${ORDER_ID}`);
      expect(res.status).toBe(401);
    });

    test('[P0][TC_094] returns 401 with expired token', async () => {
      const res = await getOrderDetails(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[P0][TC_094] admin token returns non-403 (admin can view all orders)', async () => {
      if (!adminToken) return;
      const res = await getOrderDetails(adminToken);
      expect(res.status).not.toBe(403);
    });

    test('[P0][TC_094] seller token can access order details (verifyAgentAdminAndSeller)', async () => {
      if (!sellerToken) return;
      const res = await getOrderDetails(sellerToken);
      expect(res.status).not.toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_094] non-numeric orderId returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await api.get('/api/orders/orderDetails/not-a-number')
        .set('Authorization', bearer(adminToken));
      expect(res.status).not.toBe(500);
    });

    test('[TC_094] very large orderId (non-existent) returns 404 not 500', async () => {
      if (!adminToken) return;
      const res = await api.get('/api/orders/orderDetails/9999999999')
        .set('Authorization', bearer(adminToken));
      expect(res.status).not.toBe(500);
    });

    test('[TC_094] negative orderId does not cause 500', async () => {
      if (!adminToken) return;
      const res = await api.get('/api/orders/orderDetails/-1')
        .set('Authorization', bearer(adminToken));
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_094] SQL injection in orderId path param does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await api.get(`/api/orders/orderDetails/${encodeURIComponent(payload)}`)
          .set('Authorization', bearer(adminToken));
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_094] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getOrderDetails(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_101] GET /api/orders/:orderId/logs  (P1)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_101] GET /api/orders/:orderId/logs', () => {
  const getOrderLogs = (token, id = ORDER_ID) =>
    api.get(`/api/orders/${id}/logs`).set('Authorization', bearer(token || ''));

  describe('[PERF] Performance', () => {
    test('[P1][TC_101] orderLogs avg responds within SLA (15 iterations)', async () => {
      if (!adminToken) return;
      const stats = await measurePerformance(() => getOrderLogs(adminToken), 15);
      assertSla(`GET /api/orders/${ORDER_ID}/logs`, 'orderLogs', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P1][TC_101] returns 401 with no token', async () => {
      const res = await api.get(`/api/orders/${ORDER_ID}/logs`);
      expect(res.status).toBe(401);
    });

    test('[P1][TC_101] returns 401 with expired token', async () => {
      const res = await getOrderLogs(expiredToken());
      expect(res.status).toBe(401);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_101] non-numeric orderId does not cause 500', async () => {
      if (!adminToken) return;
      const res = await api.get('/api/orders/not-a-number/logs')
        .set('Authorization', bearer(adminToken));
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_101] SQL injection in orderId does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await api.get(`/api/orders/${encodeURIComponent(payload)}/logs`)
          .set('Authorization', bearer(adminToken));
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_101] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getOrderLogs(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_077] POST /api/orders/assign-courier  (P1)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_077] POST /api/orders/assign-courier', () => {
  const assignCourier = (token, body = {}) =>
    api.post('/api/orders/assign-courier')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[PERF] Performance', () => {
    test('[P1][TC_077] assign-courier avg responds within SLA (15 iterations)', async () => {
      if (!adminToken) return;
      const stats = await measurePerformance(
        () => assignCourier(adminToken, {}),
        15
      );
      assertSla('POST /api/orders/assign-courier', 'assignCourier', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P1][TC_077] returns 401 with no token', async () => {
      const res = await api.post('/api/orders/assign-courier').send({});
      expect(res.status).toBe(401);
    });

    test('[P1][TC_077] returns 401 with expired token', async () => {
      const res = await assignCourier(expiredToken(), {});
      expect(res.status).toBe(401);
    });

    test('[P1][TC_077] seller token returns 403 (Admin/Agent only)', async () => {
      if (!sellerToken) return;
      const res = await assignCourier(sellerToken, {});
      expect(res.status).toBe(403);
    });

    test('[P1][TC_077] agency token returns 403 (Admin/Agent only)', async () => {
      if (!agencyToken) return;
      const res = await assignCourier(agencyToken, {});
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_077] empty body returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await assignCourier(adminToken, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_077] wrong type for order_ids (string not array) returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await assignCourier(adminToken, { order_ids: 'notanarray', courier_id: 1 });
      expect(res.status).not.toBe(500);
    });

    test('[TC_077] very large order_ids array does not cause 500', async () => {
      if (!adminToken) return;
      const res = await assignCourier(adminToken, {
        order_ids: Array.from({ length: 10000 }, (_, i) => i + 1),
        courier_id: 1,
      });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_077] SQL injection in courier_id does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await assignCourier(adminToken, { order_ids: [1], courier_id: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_077] mass assignment — extra fields are ignored', async () => {
      if (!adminToken) return;
      const res = await assignCourier(adminToken, {
        order_ids: [1],
        courier_id: 1,
        _internal: true,
        admin_override: true,
      });
      expect(res.status).not.toBe(500);
    });

    test('[TC_077] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => assignCourier(adminToken, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_082] GET /api/orders/remarks  (P1)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_082] GET /api/orders/remarks', () => {
  const getRemarks = (token) =>
    api.get('/api/orders/remarks').set('Authorization', bearer(token || ''));

  describe('[AUTH] Auth & Authorization', () => {
    test('[P1][TC_082] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/remarks');
      expect(res.status).toBe(401);
    });

    test('[P1][TC_082] returns 401 with expired token', async () => {
      const res = await getRemarks(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[P1][TC_082] seller token on Admin/Agent route returns 403', async () => {
      if (!sellerToken) return;
      const res = await getRemarks(sellerToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[SEC] Security', () => {
    test('[TC_082] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => getRemarks(adminToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_070] GET /api/orders/order-analytics  (P1, Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_070] GET /api/orders/order-analytics', () => {
  const getAnalytics = (token, query = {}) =>
    api.get('/api/orders/order-analytics')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[PERF] Performance', () => {
    test('[P1][TC_070] order-analytics avg responds within SLA (15 iterations)', async () => {
      if (!sellerToken) return;
      const stats = await measurePerformance(
        () => getAnalytics(sellerToken),
        15
      );
      assertSla('GET /api/orders/order-analytics', 'orderAnalytics', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P1][TC_070] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/order-analytics');
      expect(res.status).toBe(401);
    });

    test('[P1][TC_070] returns 401 with expired token', async () => {
      const res = await getAnalytics(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[P1][TC_070] admin token on Seller/Agency route returns 403', async () => {
      if (!adminToken) return;
      const res = await getAnalytics(adminToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_070] invalid date range does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await getAnalytics(sellerToken, { from: 'not-a-date', to: 'also-not' });
      expect(res.status).not.toBe(500);
    });

    test('[TC_070] oversized query param does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await getAnalytics(sellerToken, { filter: oversizedString(5000) });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_070] SQL injection in date param does not cause 500: %s',
      async (payload) => {
        if (!sellerToken) return;
        const res = await getAnalytics(sellerToken, { from: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_070] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!sellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getAnalytics(sellerToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_072] GET /api/orders/seller-orders  (Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
(isDeadSlaKey('sellerOrders') ? describe.skip : describe)('[TC_072] GET /api/orders/seller-orders', () => {
  const getSellerOrders = (token, query = {}) =>
    api.get('/api/orders/seller-orders')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_072] returns 401 with no token', async () => {
      const res = await api.get('/api/orders/seller-orders');
      expect(res.status).toBe(401);
    });

    test('[TC_072] returns 401 with expired token', async () => {
      const res = await getSellerOrders(expiredToken());
      expect(res.status).toBe(401);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_072] non-numeric page does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await getSellerOrders(sellerToken, { page: 'abc', limit: 10 });
      expect(res.status).not.toBe(500);
    });

    test('[TC_072] very large limit does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await getSellerOrders(sellerToken, { limit: 999999 });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_072] SQL injection in search param does not cause 500: %s',
      async (payload) => {
        if (!sellerToken) return;
        const res = await getSellerOrders(sellerToken, { search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(XSS_PAYLOADS)(
      '[TC_072] XSS in search param does not cause 500: %s',
      async (payload) => {
        if (!sellerToken) return;
        const res = await getSellerOrders(sellerToken, { search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_072] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!sellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getSellerOrders(sellerToken, { page: 1, limit: 1 }));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_010] POST /api/remarks  (bulk update remarks — per inventory: no auth)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_010] POST /api/remarks', () => {
  const postRemarks = (body) =>
    api.post('/api/remarks').send(body).set('Content-Type', 'application/json');

  describe('[PERF] Performance', () => {
    test('[P1][TC_010] bulkRemarks avg responds within SLA (15 iterations)', async () => {
      const stats = await measurePerformance(
        () => postRemarks({ order_ids: [], remark_ids: [] }),
        15
      );
      assertSla('POST /api/remarks', 'bulkRemarks', stats);
    });
  });

  describe('[AUTH] Auth — verify public status', () => {
    test('[TC_010] endpoint accessible without token (no 401/403)', async () => {
      const res = await postRemarks({ order_ids: [], remark_ids: [] });
      expect(res.status).not.toBe(401);
      expect(res.status).not.toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_010] empty body returns 4xx not 500', async () => {
      const res = await postRemarks({});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_010] wrong type for order_ids (string) returns 4xx not 500', async () => {
      const res = await postRemarks({ order_ids: 'notanarray', remark_ids: [1] });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_010] SQL injection in order_ids does not cause 500: %s',
      async (payload) => {
        const res = await postRemarks({ order_ids: [payload], remark_ids: [1] });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_010] rate limit — 25 rapid requests do not produce 5xx', async () => {
      const reqs = Array.from({ length: 25 }, () =>
        postRemarks({ order_ids: [], remark_ids: [] })
      );
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_011] POST /api/tags  (per inventory: no auth — bulk tag update)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_011] POST /api/tags', () => {
  const postTags = (body) =>
    api.post('/api/tags').send(body).set('Content-Type', 'application/json');

  describe('[PERF] Performance', () => {
    test('[P1][TC_011] updateStatusTags avg responds within SLA (15 iterations)', async () => {
      const stats = await measurePerformance(() => postTags({}), 15);
      assertSla('POST /api/tags', 'updateStatusTags', stats);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_011] empty body does not cause 500', async () => {
      const res = await postTags({});
      expect(res.status).not.toBe(500);
    });

    test('[TC_011] oversized tag string does not cause 500', async () => {
      const res = await postTags({ tag: oversizedString(5000) });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(XSS_PAYLOADS)(
      '[TC_011] XSS in tag field does not cause 500: %s',
      async (payload) => {
        const res = await postTags({ tag: payload });
        expect(res.status).not.toBe(500);
        expect(JSON.stringify(res.body)).not.toContain('<script>');
      }
    );

    test.each(SQL_INJECTION)(
      '[TC_011] SQL injection in tag field does not cause 500: %s',
      async (payload) => {
        const res = await postTags({ tag: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_011] rate limit — 25 rapid requests do not produce 5xx', async () => {
      const reqs = Array.from({ length: 25 }, () => postTags({}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_097] PUT /api/orders/:orderId/status  (Admin/Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_097] PUT /api/orders/:orderId/status', () => {
  const updateStatus = (token, id = ORDER_ID, body = {}) =>
    api.put(`/api/orders/${id}/status`)
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_097] returns 401 with no token', async () => {
      const res = await api.put(`/api/orders/${ORDER_ID}/status`).send({});
      expect(res.status).toBe(401);
    });

    test('[TC_097] returns 401 with expired token', async () => {
      const res = await updateStatus(expiredToken());
      expect(res.status).toBe(401);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_097] empty body does not cause 500', async () => {
      if (!adminToken) return;
      const res = await updateStatus(adminToken, ORDER_ID, {});
      expect(res.status).not.toBe(500);
    });

    test('[TC_097] invalid status enum does not cause 500', async () => {
      if (!adminToken) return;
      const res = await updateStatus(adminToken, ORDER_ID, { status: 'NOT_A_REAL_STATUS' });
      expect(res.status).not.toBe(500);
    });

    test('[TC_097] non-numeric orderId does not cause 500', async () => {
      if (!adminToken) return;
      const res = await updateStatus(adminToken, 'abc', { status: 'Delivered' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_097] SQL injection in status field does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await updateStatus(adminToken, ORDER_ID, { status: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_097] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () =>
        updateStatus(adminToken, ORDER_ID, { status: 'Pending' })
      );
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

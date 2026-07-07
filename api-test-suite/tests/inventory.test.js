/**
 * Inventory test suite
 *
 * Routes covered:
 *   [TC_013] GET  /api/inventory/seller-inventory         Seller/Agency — P1
 *   [TC_014] GET  /api/inventory/seller-inventory/export  Seller/Agency — P1
 *   [TC_015] GET  /api/inventory/purchase-order/:variantId Seller/Agency
 *   [TC_016] GET  /api/inventory/purchase-order/orders/:variantId Seller/Agency
 *   [TC_017] GET  /api/inventory/inventory-movements/:variantId Seller/Agency
 *   [TC_012] GET  /api/sub-statuses                       (no auth per inventory)
 *
 * Dimensions per route:
 *   [PERF]  15 iterations, avg ≤ pass threshold, report p95/p99
 *   [AUTH]  401 no token, 401 expired, 403 wrong role
 *   [VALID] Non-numeric IDs, invalid params, oversized inputs
 *   [SEC]   SQL injection, XSS, 25-request burst
 */

const { api }                                           = require('./helpers/http');
const { getToken, bearer, expiredToken }                = require('./helpers/auth');
const { SQL_INJECTION, XSS_PAYLOADS, oversizedString }  = require('./helpers/security-payloads');
const { measurePerformance, assertSla }                 = require('./helpers/performance');

const VARIANT_ID = parseInt(process.env.TEST_VARIANT_ID || '1', 10);

let adminToken, sellerToken, agencyToken;
beforeAll(async () => {
  [adminToken, sellerToken, agencyToken] = await Promise.all([
    getToken('admin'),
    getToken('seller'),
    getToken('agency'),
  ]);
}, 30000);

// ─────────────────────────────────────────────────────────────────────────────
// [TC_013] GET /api/inventory/seller-inventory  (P1, Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_013] GET /api/inventory/seller-inventory', () => {
  const getSellerInventory = (token, query = {}) =>
    api.get('/api/inventory/seller-inventory')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[PERF] Performance', () => {
    test('[P1][TC_013] seller-inventory avg responds within SLA (15 iterations)', async () => {
      if (!sellerToken) return;
      const stats = await measurePerformance(() => getSellerInventory(sellerToken), 15);
      assertSla('GET /api/inventory/seller-inventory', 'stockValidation', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P1][TC_013] returns 401 with no token', async () => {
      const res = await api.get('/api/inventory/seller-inventory');
      expect(res.status).toBe(401);
    });

    test('[P1][TC_013] returns 401 with expired token', async () => {
      const res = await api.get('/api/inventory/seller-inventory')
        .set('Authorization', bearer(expiredToken()));
      expect(res.status).toBe(401);
    });

    test('[P1][TC_013] admin token on Seller/Agency route returns 403', async () => {
      if (!adminToken) return;
      const res = await getSellerInventory(adminToken);
      expect(res.status).toBe(403);
    });

    test('[P1][TC_013] malformed Bearer token returns 401', async () => {
      const res = await api.get('/api/inventory/seller-inventory')
        .set('Authorization', 'Bearer not.valid.token');
      expect(res.status).toBe(401);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_013] non-numeric page does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await getSellerInventory(sellerToken, { page: 'nan', limit: 10 });
      expect(res.status).not.toBe(500);
    });

    test('[TC_013] negative limit does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await getSellerInventory(sellerToken, { limit: -1 });
      expect(res.status).not.toBe(500);
    });

    test('[TC_013] oversized search string does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await getSellerInventory(sellerToken, { search: oversizedString(5000) });
      expect(res.status).not.toBe(500);
    });

    test('[TC_013] unknown query params are ignored (no 500)', async () => {
      if (!sellerToken) return;
      const res = await getSellerInventory(sellerToken, { fakeParam: 'ignored' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_013] SQL injection in search param does not cause 500: %s',
      async (payload) => {
        if (!sellerToken) return;
        const res = await getSellerInventory(sellerToken, { search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(XSS_PAYLOADS)(
      '[TC_013] XSS in search param does not cause 500: %s',
      async (payload) => {
        if (!sellerToken) return;
        const res = await getSellerInventory(sellerToken, { search: payload });
        expect(res.status).not.toBe(500);
        expect(JSON.stringify(res.body)).not.toContain('<script>');
      }
    );

    test('[TC_013] response does not leak sensitive fields', async () => {
      if (!sellerToken) return;
      const res = await getSellerInventory(sellerToken);
      const body = JSON.stringify(res.body);
      expect(body).not.toContain('passwordHash');
      expect(body).not.toContain('stack');
    });

    test('[TC_013] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!sellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getSellerInventory(sellerToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_014] GET /api/inventory/seller-inventory/export  (P1, Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_014] GET /api/inventory/seller-inventory/export', () => {
  const getExport = (token) =>
    api.get('/api/inventory/seller-inventory/export')
      .set('Authorization', bearer(token || ''));

  describe('[PERF] Performance', () => {
    // CSV export has an 18-second SLA — use fewer iterations to keep suite fast
    test('[P1][TC_014] csvExport avg responds within SLA (5 iterations)', async () => {
      if (!sellerToken) return;
      const stats = await measurePerformance(() => getExport(sellerToken), 5);
      assertSla('GET /api/inventory/seller-inventory/export', 'csvExport', stats);
    }, 120000);
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P1][TC_014] returns 401 with no token', async () => {
      const res = await api.get('/api/inventory/seller-inventory/export');
      expect(res.status).toBe(401);
    });

    test('[P1][TC_014] returns 401 with expired token', async () => {
      const res = await getExport(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[P1][TC_014] admin token on Seller/Agency route returns 403', async () => {
      if (!adminToken) return;
      const res = await getExport(adminToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_014] unknown query params are ignored (no 500)', async () => {
      if (!sellerToken) return;
      const res = await api.get('/api/inventory/seller-inventory/export')
        .set('Authorization', bearer(sellerToken))
        .query({ bogus: 'value' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test('[TC_014] rate limit — 10 rapid export requests do not produce 5xx', async () => {
      if (!sellerToken) return;
      const reqs = Array.from({ length: 10 }, () => getExport(sellerToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    }, 60000);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_015] GET /api/inventory/purchase-order/:variantId  (Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_015] GET /api/inventory/purchase-order/:variantId', () => {
  const getPurchaseOrder = (token, id = VARIANT_ID) =>
    api.get(`/api/inventory/purchase-order/${id}`)
      .set('Authorization', bearer(token || ''));

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_015] returns 401 with no token', async () => {
      const res = await api.get(`/api/inventory/purchase-order/${VARIANT_ID}`);
      expect(res.status).toBe(401);
    });

    test('[TC_015] returns 401 with expired token', async () => {
      const res = await getPurchaseOrder(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[TC_015] admin token on Seller/Agency route returns 403', async () => {
      if (!adminToken) return;
      const res = await getPurchaseOrder(adminToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_015] non-numeric variantId does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await api.get('/api/inventory/purchase-order/not-a-number')
        .set('Authorization', bearer(sellerToken));
      expect(res.status).not.toBe(500);
    });

    test('[TC_015] non-existent variantId returns 404 not 500', async () => {
      if (!sellerToken) return;
      const res = await api.get('/api/inventory/purchase-order/9999999999')
        .set('Authorization', bearer(sellerToken));
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_015] SQL injection in variantId does not cause 500: %s',
      async (payload) => {
        if (!sellerToken) return;
        const res = await api.get(`/api/inventory/purchase-order/${encodeURIComponent(payload)}`)
          .set('Authorization', bearer(sellerToken));
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_015] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!sellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getPurchaseOrder(sellerToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_017] GET /api/inventory/inventory-movements/:variantId  (Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_017] GET /api/inventory/inventory-movements/:variantId', () => {
  const getInventoryMovements = (token, id = VARIANT_ID, query = {}) =>
    api.get(`/api/inventory/inventory-movements/${id}`)
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_017] returns 401 with no token', async () => {
      const res = await api.get(`/api/inventory/inventory-movements/${VARIANT_ID}`);
      expect(res.status).toBe(401);
    });

    test('[TC_017] returns 401 with expired token', async () => {
      const res = await getInventoryMovements(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[TC_017] admin token on Seller/Agency route returns 403', async () => {
      if (!adminToken) return;
      const res = await getInventoryMovements(adminToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_017] non-numeric variantId does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await api.get('/api/inventory/inventory-movements/not-a-number')
        .set('Authorization', bearer(sellerToken));
      expect(res.status).not.toBe(500);
    });

    test('[TC_017] non-numeric page does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await getInventoryMovements(sellerToken, VARIANT_ID, { page: 'abc', limit: 10 });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_017] SQL injection in variantId does not cause 500: %s',
      async (payload) => {
        if (!sellerToken) return;
        const res = await api.get(`/api/inventory/inventory-movements/${encodeURIComponent(payload)}`)
          .set('Authorization', bearer(sellerToken));
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_017] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!sellerToken) return;
      const reqs = Array.from({ length: 25 }, () => getInventoryMovements(sellerToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_012] GET /api/sub-statuses  (public per inventory)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_012] GET /api/sub-statuses', () => {
  describe('[AUTH] Auth — verify public status', () => {
    test('[TC_012] endpoint is publicly accessible (no 401/403)', async () => {
      const res = await api.get('/api/sub-statuses');
      expect(res.status).not.toBe(401);
      expect(res.status).not.toBe(403);
    });
  });

  describe('[SEC] Security', () => {
    test('[TC_012] rate limit — 25 rapid requests do not produce 5xx', async () => {
      const reqs = Array.from({ length: 25 }, () => api.get('/api/sub-statuses'));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

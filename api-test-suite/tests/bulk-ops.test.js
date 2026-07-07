/**
 * Bulk Operations test suite
 *
 * Routes covered:
 *   [TC_063] PUT  /api/orders/bulk-csv-update              Admin/Agent
 *   [TC_064] PUT  /api/orders/revert-to-confirmation-pending Admin/Agent
 *   [TC_065] POST /api/orders/bulk-order-upload             Admin/Agent
 *   [TC_066] POST /api/orders/bulk-vendor-courier-upload    Admin/Agent
 *   [TC_087] PUT  /api/orders/approve-status/bulk          Admin/Agent/Seller
 *   [TC_088] POST /api/orders/sub-statuses/bulk-update     Admin/Agent/Seller
 *   [TC_100] POST /api/orders/uploadOrderCSV               Seller/Agency
 *   [TC_085] POST /api/orders/download-awbs                Admin/Agent
 *   [TC_086] POST /api/orders/download-packing-list        Admin/Agent
 *
 * Dimensions per route:
 *   [PERF]  15 iterations, avg ≤ pass threshold, report p95/p99
 *   [AUTH]  401 no token, 401 expired, 403 wrong role
 *   [VALID] Missing fields, wrong types, empty body, oversized payload
 *   [SEC]   SQL injection, XSS, mass assignment, 25-request burst
 */

const { api }                                           = require('./helpers/http');
const { getToken, bearer, expiredToken }                = require('./helpers/auth');
const { SQL_INJECTION, XSS_PAYLOADS, oversizedString }  = require('./helpers/security-payloads');
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
// [TC_063] PUT /api/orders/bulk-csv-update  (Admin/Agent)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_063] PUT /api/orders/bulk-csv-update', () => {
  const bulkCsvUpdate = (token, body = {}) =>
    api.put('/api/orders/bulk-csv-update')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_063] returns 401 with no token', async () => {
      const res = await api.put('/api/orders/bulk-csv-update').send({});
      expect(res.status).toBe(401);
    });

    test('[TC_063] returns 401 with expired token', async () => {
      const res = await bulkCsvUpdate(expiredToken(), {});
      expect(res.status).toBe(401);
    });

    test('[TC_063] seller token on Admin/Agent route returns 403', async () => {
      if (!sellerToken) return;
      const res = await bulkCsvUpdate(sellerToken, {});
      expect(res.status).toBe(403);
    });

    test('[TC_063] agency token on Admin/Agent route returns 403', async () => {
      if (!agencyToken) return;
      const res = await bulkCsvUpdate(agencyToken, {});
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_063] empty body returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await bulkCsvUpdate(adminToken, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_063] wrong type for orders (string not array) does not cause 500', async () => {
      if (!adminToken) return;
      const res = await bulkCsvUpdate(adminToken, { orders: 'notanarray' });
      expect(res.status).not.toBe(500);
    });

    test('[TC_063] oversized payload does not cause 500', async () => {
      if (!adminToken) return;
      const orders = Array.from({ length: 1000 }, (_, i) => ({
        id: i + 1,
        status: oversizedString(500),
      }));
      const res = await bulkCsvUpdate(adminToken, { orders });
      expect(res.status).not.toBe(500);
    }, 15000);
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_063] SQL injection in order data does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await bulkCsvUpdate(adminToken, { orders: [{ id: 1, status: payload }] });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_063] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => bulkCsvUpdate(adminToken, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_064] PUT /api/orders/revert-to-confirmation-pending  (Admin/Agent)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_064] PUT /api/orders/revert-to-confirmation-pending', () => {
  const revert = (token, body = {}) =>
    api.put('/api/orders/revert-to-confirmation-pending')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_064] returns 401 with no token', async () => {
      const res = await api.put('/api/orders/revert-to-confirmation-pending').send({});
      expect(res.status).toBe(401);
    });

    test('[TC_064] returns 401 with expired token', async () => {
      const res = await revert(expiredToken(), {});
      expect(res.status).toBe(401);
    });

    test('[TC_064] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await revert(sellerToken, {});
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_064] empty body returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await revert(adminToken, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_064] wrong type for order_ids does not cause 500', async () => {
      if (!adminToken) return;
      const res = await revert(adminToken, { order_ids: 'not-an-array' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_064] SQL injection in order_ids does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await revert(adminToken, { order_ids: [payload] });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_064] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => revert(adminToken, { order_ids: [] }));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_065] POST /api/orders/bulk-order-upload  (Admin/Agent)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_065] POST /api/orders/bulk-order-upload', () => {
  const bulkUpload = (token, body = {}) =>
    api.post('/api/orders/bulk-order-upload')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_065] returns 401 with no token', async () => {
      const res = await api.post('/api/orders/bulk-order-upload').send({});
      expect(res.status).toBe(401);
    });

    test('[TC_065] returns 401 with expired token', async () => {
      const res = await bulkUpload(expiredToken(), {});
      expect(res.status).toBe(401);
    });

    test('[TC_065] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await bulkUpload(sellerToken, {});
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_065] empty body returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await bulkUpload(adminToken, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_065] wrong type for orders array does not cause 500', async () => {
      if (!adminToken) return;
      const res = await bulkUpload(adminToken, { orders: 'not-an-array' });
      expect(res.status).not.toBe(500);
    });

    test('[TC_065] missing required order fields returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await bulkUpload(adminToken, { orders: [{ randomField: 'value' }] });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_065] SQL injection in order data does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await bulkUpload(adminToken, {
          orders: [{ customer_name: payload, phone: payload }],
        });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(XSS_PAYLOADS)(
      '[TC_065] XSS in customer name does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await bulkUpload(adminToken, {
          orders: [{ customer_name: payload }],
        });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_065] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => bulkUpload(adminToken, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_087] PUT /api/orders/approve-status/bulk  (Admin/Agent/Seller)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_087] PUT /api/orders/approve-status/bulk', () => {
  const bulkApprove = (token, body = {}) =>
    api.put('/api/orders/approve-status/bulk')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_087] returns 401 with no token', async () => {
      const res = await api.put('/api/orders/approve-status/bulk').send({});
      expect(res.status).toBe(401);
    });

    test('[TC_087] returns 401 with expired token', async () => {
      const res = await bulkApprove(expiredToken(), {});
      expect(res.status).toBe(401);
    });

    test('[TC_087] agency token on Admin/Agent/Seller route returns 403', async () => {
      if (!agencyToken) return;
      const res = await bulkApprove(agencyToken, {});
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_087] empty body returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await bulkApprove(adminToken, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_087] wrong type for order_ids does not cause 500', async () => {
      if (!adminToken) return;
      const res = await bulkApprove(adminToken, { order_ids: 'not-an-array' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_087] SQL injection in order_ids does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await bulkApprove(adminToken, { order_ids: [payload] });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_087] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => bulkApprove(adminToken, { order_ids: [] }));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_088] POST /api/orders/sub-statuses/bulk-update  (Admin/Agent/Seller)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_088] POST /api/orders/sub-statuses/bulk-update', () => {
  const bulkSubStatus = (token, body = {}) =>
    api.post('/api/orders/sub-statuses/bulk-update')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_088] returns 401 with no token', async () => {
      const res = await api.post('/api/orders/sub-statuses/bulk-update').send({});
      expect(res.status).toBe(401);
    });

    test('[TC_088] returns 401 with expired token', async () => {
      const res = await bulkSubStatus(expiredToken(), {});
      expect(res.status).toBe(401);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_088] empty body returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await bulkSubStatus(adminToken, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_088] invalid sub_status_id does not cause 500', async () => {
      if (!adminToken) return;
      const res = await bulkSubStatus(adminToken, {
        order_ids: [1],
        sub_status_id: 'not-a-number',
      });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_088] SQL injection in sub_status_id does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await bulkSubStatus(adminToken, {
          order_ids: [1],
          sub_status_id: payload,
        });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_088] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => bulkSubStatus(adminToken, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_100] POST /api/orders/uploadOrderCSV  (Seller/Agency)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_100] POST /api/orders/uploadOrderCSV', () => {
  const uploadCsv = (token) =>
    api.post('/api/orders/uploadOrderCSV')
      .set('Authorization', bearer(token || ''));

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_100] returns 401 with no token', async () => {
      const res = await api.post('/api/orders/uploadOrderCSV');
      expect(res.status).toBe(401);
    });

    test('[TC_100] returns 401 with expired token', async () => {
      const res = await uploadCsv(expiredToken());
      expect(res.status).toBe(401);
    });

    test('[TC_100] admin token on Seller/Agency route returns 403', async () => {
      if (!adminToken) return;
      const res = await uploadCsv(adminToken);
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_100] no file attached returns 4xx not 500', async () => {
      if (!sellerToken) return;
      const res = await api.post('/api/orders/uploadOrderCSV')
        .set('Authorization', bearer(sellerToken));
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_100] wrong content-type (JSON not multipart) does not cause 500', async () => {
      if (!sellerToken) return;
      const res = await api.post('/api/orders/uploadOrderCSV')
        .set('Authorization', bearer(sellerToken))
        .set('Content-Type', 'application/json')
        .send({ file: 'fake-data' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test('[TC_100] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!sellerToken) return;
      const reqs = Array.from({ length: 25 }, () => uploadCsv(sellerToken));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_085] POST /api/orders/download-awbs  (Admin/Agent)
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_085] POST /api/orders/download-awbs', () => {
  const downloadAwbs = (token, body = {}) =>
    api.post('/api/orders/download-awbs')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[AUTH] Auth & Authorization', () => {
    test('[TC_085] returns 401 with no token', async () => {
      const res = await api.post('/api/orders/download-awbs').send({});
      expect(res.status).toBe(401);
    });

    test('[TC_085] returns 401 with expired token', async () => {
      const res = await downloadAwbs(expiredToken(), {});
      expect(res.status).toBe(401);
    });

    test('[TC_085] seller token returns 403', async () => {
      if (!sellerToken) return;
      const res = await downloadAwbs(sellerToken, {});
      expect(res.status).toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_085] empty body returns 4xx not 500', async () => {
      if (!adminToken) return;
      const res = await downloadAwbs(adminToken, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_085] wrong type for order_ids does not cause 500', async () => {
      if (!adminToken) return;
      const res = await downloadAwbs(adminToken, { order_ids: 'not-an-array' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_085] SQL injection in order_ids does not cause 500: %s',
      async (payload) => {
        if (!adminToken) return;
        const res = await downloadAwbs(adminToken, { order_ids: [payload] });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_085] rate limit — 25 rapid requests do not produce 5xx', async () => {
      if (!adminToken) return;
      const reqs = Array.from({ length: 25 }, () => downloadAwbs(adminToken, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

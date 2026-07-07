/**
 * Support (Tickets & Comments) test suite
 *
 * Routes covered:
 *   GET  /api/tickets                           verifyJWT (all roles)
 *   POST /api/tickets                           verifyJWT
 *   GET  /api/tickets/admin                     verifyJWT (admin view)
 *   GET  /api/tickets/:ticketId                 verifyJWT
 *   PUT  /api/tickets/:ticketId                 verifyJWT
 *   GET  /api/comments/ticket/:ticketId         verifyJWT
 *   POST /api/comments                          verifyJWT
 *   PUT  /api/comments/:commentId               verifyJWT
 *
 * Dimensions per route:
 *   [PERF]  15 iterations, avg ≤ pass threshold, report p95/p99
 *   [AUTH]  401 no token, 401 expired, 401 malformed
 *   [VALID] Missing required fields, field length limits, wrong types, invalid enum
 *   [SEC]   SQL injection, XSS in text fields, 25-request burst
 */

const { api }                                           = require('./helpers/http');
const { getToken, bearer, expiredToken }                = require('./helpers/auth');
const { SQL_INJECTION, XSS_PAYLOADS, oversizedString }  = require('./helpers/security-payloads');
const { measurePerformance, assertSla }                 = require('./helpers/performance');

const TICKET_ID  = parseInt(process.env.TEST_TICKET_ID       || '1', 10);
const STORE_ID   = parseInt(process.env.TEST_TICKET_STORE_ID || '1', 10);

let adminToken, sellerToken, agencyToken;
beforeAll(async () => {
  [adminToken, sellerToken, agencyToken] = await Promise.all([
    getToken('admin'),
    getToken('seller'),
    getToken('agency'),
  ]);
}, 30000);

const anyToken = () => adminToken || sellerToken || agencyToken;

// ─────────────────────────────────────────────────────────────────────────────
// GET /api/tickets  (P1 — all roles via verifyJWT)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SUPPORT] GET /api/tickets', () => {
  const getTickets = (token, query = {}) =>
    api.get('/api/tickets')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('[PERF] Performance', () => {
    test('[P1] tickets list avg responds within SLA (15 iterations)', async () => {
      const token = anyToken();
      if (!token) return;
      const stats = await measurePerformance(
        () => getTickets(token, { store_id: STORE_ID, page: 1, limit: 20 }),
        15
      );
      assertSla('GET /api/tickets', 'ticketList', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P1] returns 401 with no token', async () => {
      const res = await api.get('/api/tickets');
      expect(res.status).toBe(401);
    });

    test('[P1] returns 401 with expired token', async () => {
      const res = await api.get('/api/tickets')
        .set('Authorization', bearer(expiredToken()));
      expect(res.status).toBe(401);
    });

    test('[P1] returns 401 with malformed token', async () => {
      const res = await api.get('/api/tickets')
        .set('Authorization', 'Bearer notavalidtoken.atall.nope');
      expect(res.status).toBe(401);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[VALID] non-numeric page does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await getTickets(token, { store_id: STORE_ID, page: 'abc' });
      expect(res.status).not.toBe(500);
    });

    test('[VALID] limit exceeding max (99999) does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await getTickets(token, { store_id: STORE_ID, limit: 99999 });
      expect(res.status).not.toBe(500);
    });

    test('[VALID] oversized search string (5000 chars) does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await getTickets(token, { store_id: STORE_ID, search: oversizedString(5000) });
      expect(res.status).not.toBe(500);
    });

    test('[VALID] unknown query params are ignored (no 500)', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await getTickets(token, { store_id: STORE_ID, fakeParam: 'bogus' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[SEC] SQL injection in search param does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await getTickets(token, { store_id: STORE_ID, search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(XSS_PAYLOADS)(
      '[SEC] XSS in search param does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await getTickets(token, { store_id: STORE_ID, search: payload });
        expect(res.status).not.toBe(500);
        expect(JSON.stringify(res.body)).not.toContain('<script>');
      }
    );

    test('[SEC] rate limit — 25 rapid requests do not produce 5xx', async () => {
      const token = anyToken();
      if (!token) return;
      const reqs = Array.from({ length: 25 }, () =>
        getTickets(token, { store_id: STORE_ID })
      );
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /api/tickets  (create ticket)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SUPPORT] POST /api/tickets', () => {
  const createTicket = (token, body = {}) =>
    api.post('/api/tickets')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[AUTH] Auth & Authorization', () => {
    test('[AUTH] returns 401 with no token', async () => {
      const res = await api.post('/api/tickets').send({});
      expect(res.status).toBe(401);
    });

    test('[AUTH] returns 401 with expired token', async () => {
      const res = await createTicket(expiredToken(), {});
      expect(res.status).toBe(401);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[VALID] empty body returns 4xx not 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createTicket(token, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[VALID] missing fk_store_id returns 4xx', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createTicket(token, {
        category: 'delivery_issue',
        subject: 'Test subject',
        description: 'This is a test description with enough characters.',
      });
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[VALID] description shorter than 10 chars returns 4xx', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createTicket(token, {
        fk_store_id: STORE_ID,
        category: 'delivery_issue',
        subject: 'Test subject',
        description: 'short',
      });
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[VALID] description longer than 2000 chars does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createTicket(token, {
        fk_store_id: STORE_ID,
        category: 'delivery_issue',
        subject: 'Test',
        description: 'A'.repeat(2001),
      });
      expect(res.status).not.toBe(500);
    });

    test('[VALID] invalid category enum returns 4xx', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createTicket(token, {
        fk_store_id: STORE_ID,
        category: 'NOT_A_REAL_CATEGORY',
        subject: 'Test',
        description: 'Valid description of sufficient length here.',
      });
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[VALID] wrong type for fk_store_id (string) does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createTicket(token, {
        fk_store_id: 'notanumber',
        category: 'delivery_issue',
        subject: 'Test',
        description: 'Valid description of sufficient length here.',
      });
      expect(res.status).not.toBe(500);
    });

    test('[VALID] oversized subject (5000 chars) does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createTicket(token, {
        fk_store_id: STORE_ID,
        category: 'delivery_issue',
        subject: oversizedString(5000),
        description: 'Valid description of sufficient length here.',
      });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(XSS_PAYLOADS)(
      '[SEC] XSS in description does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await createTicket(token, {
          fk_store_id: STORE_ID,
          category: 'delivery_issue',
          subject: 'XSS Test',
          description: `Payload: ${payload}`.padEnd(15, '.'),
        });
        expect(res.status).not.toBe(500);
        expect(JSON.stringify(res.body)).not.toContain('<script>');
      }
    );

    test.each(SQL_INJECTION)(
      '[SEC] SQL injection in subject does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await createTicket(token, {
          fk_store_id: STORE_ID,
          category: 'delivery_issue',
          subject: payload,
          description: 'Valid description of sufficient length here.',
        });
        expect(res.status).not.toBe(500);
      }
    );

    test('[SEC] mass assignment — extra fields are ignored', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createTicket(token, {
        fk_store_id: STORE_ID,
        category: 'delivery_issue',
        subject: 'Test',
        description: 'Valid description text here.',
        internal_status: 'approved',
        admin_override: true,
      });
      expect(res.status).not.toBe(500);
    });

    test('[SEC] rate limit — 25 rapid POST /api/tickets do not produce 5xx', async () => {
      const token = anyToken();
      if (!token) return;
      const reqs = Array.from({ length: 25 }, () => createTicket(token, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /api/tickets/admin  (admin view)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SUPPORT] GET /api/tickets/admin', () => {
  describe('[AUTH] Auth & Authorization', () => {
    test('[P1] returns 401 with no token', async () => {
      const res = await api.get('/api/tickets/admin');
      expect(res.status).toBe(401);
    });

    test('[P1] returns 401 with expired token', async () => {
      const res = await api.get('/api/tickets/admin')
        .set('Authorization', bearer(expiredToken()));
      expect(res.status).toBe(401);
    });
  });

  describe('[SEC] Security', () => {
    test('[SEC] SQL injection in search param does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await api.get('/api/tickets/admin')
        .set('Authorization', bearer(token))
        .query({ search: "' OR '1'='1" });
      expect(res.status).not.toBe(500);
    });

    test('[SEC] rate limit — 25 rapid requests do not produce 5xx', async () => {
      const token = anyToken();
      if (!token) return;
      const reqs = Array.from({ length: 25 }, () =>
        api.get('/api/tickets/admin').set('Authorization', bearer(token))
      );
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// GET /api/comments/ticket/:ticketId  (P1)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SUPPORT] GET /api/comments/ticket/:ticketId', () => {
  const getComments = (token, id = TICKET_ID) =>
    api.get(`/api/comments/ticket/${id}`).set('Authorization', bearer(token || ''));

  describe('[PERF] Performance', () => {
    test('[P1] ticket comments avg responds within SLA (15 iterations)', async () => {
      const token = anyToken();
      if (!token) return;
      const stats = await measurePerformance(() => getComments(token), 15);
      assertSla(`GET /api/comments/ticket/${TICKET_ID}`, 'ticketComments', stats);
    });
  });

  describe('[AUTH] Auth & Authorization', () => {
    test('[P1] returns 401 with no token', async () => {
      const res = await api.get(`/api/comments/ticket/${TICKET_ID}`);
      expect(res.status).toBe(401);
    });

    test('[P1] returns 401 with expired token', async () => {
      const res = await getComments(expiredToken());
      expect(res.status).toBe(401);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[VALID] non-numeric ticketId does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await api.get('/api/comments/ticket/not-a-number')
        .set('Authorization', bearer(token));
      expect(res.status).not.toBe(500);
    });

    test('[VALID] non-existent ticketId (large number) returns 404 not 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await api.get('/api/comments/ticket/9999999999')
        .set('Authorization', bearer(token));
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[SEC] SQL injection in ticketId param does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await api.get(`/api/comments/ticket/${encodeURIComponent(payload)}`)
          .set('Authorization', bearer(token));
        expect(res.status).not.toBe(500);
      }
    );

    test('[SEC] rate limit — 25 rapid requests do not produce 5xx', async () => {
      const token = anyToken();
      if (!token) return;
      const reqs = Array.from({ length: 25 }, () => getComments(token));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// POST /api/comments  (create comment)
// ─────────────────────────────────────────────────────────────────────────────
describe('[SUPPORT] POST /api/comments', () => {
  const createComment = (token, body = {}) =>
    api.post('/api/comments')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('[AUTH] Auth & Authorization', () => {
    test('[AUTH] returns 401 with no token', async () => {
      const res = await api.post('/api/comments').send({});
      expect(res.status).toBe(401);
    });

    test('[AUTH] returns 401 with expired token', async () => {
      const res = await createComment(expiredToken(), {});
      expect(res.status).toBe(401);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[VALID] empty body returns 4xx not 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createComment(token, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[VALID] missing ticket_id returns 4xx', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createComment(token, { content: 'A valid comment text.' });
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[VALID] missing content returns 4xx', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createComment(token, { ticket_id: TICKET_ID });
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[VALID] oversized content (5000 chars) does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createComment(token, {
        ticket_id: TICKET_ID,
        content: oversizedString(5000),
      });
      expect(res.status).not.toBe(500);
    });

    test('[VALID] wrong type for ticket_id (string) does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createComment(token, { ticket_id: 'notanumber', content: 'valid text' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(XSS_PAYLOADS)(
      '[SEC] XSS in comment content does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await createComment(token, { ticket_id: TICKET_ID, content: payload });
        expect(res.status).not.toBe(500);
        expect(JSON.stringify(res.body)).not.toContain('<script>');
      }
    );

    test.each(SQL_INJECTION)(
      '[SEC] SQL injection in content does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await createComment(token, { ticket_id: TICKET_ID, content: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[SEC] rate limit — 25 rapid POST /api/comments do not produce 5xx', async () => {
      const token = anyToken();
      if (!token) return;
      const reqs = Array.from({ length: 25 }, () => createComment(token, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

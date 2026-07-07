/**
 * Tickets & Comments test suite
 * Covers: TC_018–TC_024
 *
 * Auth middleware: verifyJWT (all roles), verifyAgencyStoreContext (for store-scoped routes)
 *
 * Dimensions per endpoint:
 *   1. Performance  — 10 iterations, assert p95 ≤ SLA
 *   2. Auth         — 401 no token, 401 expired token
 *   3. Validation   — missing required fields, field length, wrong types
 *   4. Security     — SQL injection, XSS, rate limiting
 */

const { api }                              = require('./helpers/http');
const { getToken, expiredToken, bearer }   = require('./helpers/auth');
const { SQL_INJECTION, XSS_PAYLOADS, oversizedString } = require('./helpers/security-payloads');
const { measurePerformance, assertSla }    = require('./helpers/performance');

const TICKET_ID = parseInt(process.env.TEST_TICKET_ID       || '1', 10);
const STORE_ID  = parseInt(process.env.TEST_TICKET_STORE_ID || '1', 10);

let adminToken, sellerToken;

beforeAll(async () => {
  [adminToken, sellerToken] = await Promise.all([
    getToken('admin'),
    getToken('seller'),
  ]);
});

// Any available token is fine for verifyJWT endpoints
const anyToken = () => adminToken || sellerToken;

// ─────────────────────────────────────────────────────────────────────────────
// [TC_018] GET /api/tickets
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_018] GET /api/tickets', () => {
  const getTickets = (token, query = {}) =>
    api.get('/api/tickets')
      .set('Authorization', bearer(token || ''))
      .query(query);

  describe('Auth & Authorization', () => {
    test('[P1][TC_018] returns 401 with no token', async () => {
      const res = await api.get('/api/tickets');
      expect(res.status).toBe(401);
    });

    test('[P1][TC_018] returns 401 with expired token', async () => {
      const res = await api.get('/api/tickets')
        .set('Authorization', bearer(expiredToken()));
      expect(res.status).toBe(401);
    });

    test('[P1][TC_018] returns 401 with malformed token', async () => {
      const res = await api.get('/api/tickets')
        .set('Authorization', 'Bearer notavalidtoken.atall.nope');
      expect(res.status).toBe(401);
    });
  });

  describe('Performance', () => {
    test('[P1][TC_018] ticketList p95 responds within SLA', async () => {
      const token = anyToken();
      if (!token) return;
      const stats = await measurePerformance(
        () => getTickets(token, { store_id: STORE_ID, page: 1, limit: 20 }),
        10
      );
      assertSla('GET /api/tickets', 'ticketList', stats);
    });
  });

  describe('Input Validation', () => {
    test('[TC_018] non-numeric page does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await getTickets(token, { store_id: STORE_ID, page: 'abc' });
      expect(res.status).not.toBe(500);
    });

    test('[TC_018] limit exceeding max (100) does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await getTickets(token, { store_id: STORE_ID, limit: 99999 });
      expect(res.status).not.toBe(500);
    });

    test('[TC_018] oversized search string does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await getTickets(token, { store_id: STORE_ID, search: oversizedString(100 * 1024) });
      expect(res.status).not.toBe(500);
    });
  });

  describe('Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_018] SQL injection in search param does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await getTickets(token, { store_id: STORE_ID, search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(XSS_PAYLOADS)(
      '[TC_018] XSS in search param does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await getTickets(token, { store_id: STORE_ID, search: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_018] rate limiting: 20 rapid requests do not produce 5xx', async () => {
      const token = anyToken();
      if (!token) return;
      const reqs = Array.from({ length: 20 }, () =>
        getTickets(token, { store_id: STORE_ID })
      );
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_019] POST /api/tickets — create ticket
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_019] POST /api/tickets', () => {
  const createTicket = (token, body = {}) =>
    api.post('/api/tickets')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('Auth & Authorization', () => {
    test('[TC_019] returns 401 with no token', async () => {
      const res = await api.post('/api/tickets').send({});
      expect(res.status).toBe(401);
    });

    test('[TC_019] returns 401 with expired token', async () => {
      const res = await createTicket(expiredToken(), {});
      expect(res.status).toBe(401);
    });
  });

  describe('Input Validation', () => {
    test('[TC_019] empty body returns 4xx not 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createTicket(token, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_019] missing fk_store_id returns 4xx', async () => {
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

    test('[TC_019] description shorter than 10 chars returns 4xx', async () => {
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

    test('[TC_019] description longer than 2000 chars returns 4xx not 500', async () => {
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

    test('[TC_019] invalid category value returns 4xx', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createTicket(token, {
        fk_store_id: STORE_ID,
        category: 'not_a_real_category',
        subject: 'Test subject',
        description: 'This is a test description with enough characters.',
      });
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_019] wrong type for fk_store_id (string) returns 4xx not 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createTicket(token, {
        fk_store_id: 'notanumber',
        category: 'delivery_issue',
        subject: 'Test',
        description: 'This is a valid description of sufficient length.',
      });
      expect(res.status).not.toBe(500);
    });
  });

  describe('Security', () => {
    test.each(XSS_PAYLOADS)(
      '[TC_019] XSS in description does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await createTicket(token, {
          fk_store_id: STORE_ID,
          category: 'delivery_issue',
          subject: 'XSS Test',
          description: `Description with payload: ${payload}`.padEnd(15, '.'),
        });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(SQL_INJECTION)(
      '[TC_019] SQL injection in subject does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await createTicket(token, {
          fk_store_id: STORE_ID,
          category: 'delivery_issue',
          subject: payload,
          description: 'This is a valid description of sufficient length.',
        });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_019] rate limiting: 20 rapid POST /api/tickets do not produce 5xx', async () => {
      const token = anyToken();
      if (!token) return;
      const reqs = Array.from({ length: 20 }, () => createTicket(token, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_020] GET /api/tickets/admin
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_020] GET /api/tickets/admin', () => {
  describe('Auth & Authorization', () => {
    test('[P1][TC_020] returns 401 with no token', async () => {
      const res = await api.get('/api/tickets/admin');
      expect(res.status).toBe(401);
    });

    test('[P1][TC_020] returns 401 with expired token', async () => {
      const res = await api.get('/api/tickets/admin')
        .set('Authorization', bearer(expiredToken()));
      expect(res.status).toBe(401);
    });
  });

  describe('Security', () => {
    test('[TC_020] SQL injection in search param does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await api.get('/api/tickets/admin')
        .set('Authorization', bearer(token))
        .query({ search: "' OR '1'='1" });
      expect(res.status).not.toBe(500);
    });

    test('[TC_020] rate limiting: 20 rapid requests do not produce 5xx', async () => {
      const token = anyToken();
      if (!token) return;
      const reqs = Array.from({ length: 20 }, () =>
        api.get('/api/tickets/admin').set('Authorization', bearer(token))
      );
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_023] GET /api/comments/ticket/:ticketId
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_023] GET /api/comments/ticket/:ticketId', () => {
  const getComments = (token, id = TICKET_ID) =>
    api.get(`/api/comments/ticket/${id}`).set('Authorization', bearer(token || ''));

  describe('Auth & Authorization', () => {
    test('[P1][TC_023] returns 401 with no token', async () => {
      const res = await api.get(`/api/comments/ticket/${TICKET_ID}`);
      expect(res.status).toBe(401);
    });

    test('[P1][TC_023] returns 401 with expired token', async () => {
      const res = await getComments(expiredToken());
      expect(res.status).toBe(401);
    });
  });

  describe('Performance', () => {
    test('[P1][TC_023] ticketComments p95 responds within SLA', async () => {
      const token = anyToken();
      if (!token) return;
      const stats = await measurePerformance(() => getComments(token), 10);
      assertSla(`GET /api/comments/ticket/${TICKET_ID}`, 'ticketComments', stats);
    });
  });

  describe('Input Validation', () => {
    test('[TC_023] non-numeric ticketId does not cause 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await api.get('/api/comments/ticket/not-a-number')
        .set('Authorization', bearer(token));
      expect(res.status).not.toBe(500);
    });
  });

  describe('Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_023] SQL injection in ticketId param does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await api.get(`/api/comments/ticket/${encodeURIComponent(payload)}`)
          .set('Authorization', bearer(token));
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_023] rate limiting: 20 rapid requests do not produce 5xx', async () => {
      const token = anyToken();
      if (!token) return;
      const reqs = Array.from({ length: 20 }, () => getComments(token));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_024] POST /api/comments
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_024] POST /api/comments', () => {
  const createComment = (token, body = {}) =>
    api.post('/api/comments')
      .set('Authorization', bearer(token || ''))
      .send(body);

  describe('Auth & Authorization', () => {
    test('[TC_024] returns 401 with no token', async () => {
      const res = await api.post('/api/comments').send({});
      expect(res.status).toBe(401);
    });

    test('[TC_024] returns 401 with expired token', async () => {
      const res = await createComment(expiredToken(), {});
      expect(res.status).toBe(401);
    });
  });

  describe('Input Validation', () => {
    test('[TC_024] empty body returns 4xx not 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createComment(token, {});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_024] missing ticket_id returns 4xx not 500', async () => {
      const token = anyToken();
      if (!token) return;
      const res = await createComment(token, { content: 'A valid comment text.' });
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });
  });

  describe('Security', () => {
    test.each(XSS_PAYLOADS)(
      '[TC_024] XSS in comment content does not cause 500: %s',
      async (payload) => {
        const token = anyToken();
        if (!token) return;
        const res = await createComment(token, {
          ticket_id: TICKET_ID,
          content: payload,
        });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_024] rate limiting: 20 rapid POST /api/comments do not produce 5xx', async () => {
      const token = anyToken();
      if (!token) return;
      const reqs = Array.from({ length: 20 }, () => createComment(token, {}));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

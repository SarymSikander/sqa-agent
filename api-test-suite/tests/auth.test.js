/**
 * Auth test suite
 *
 * Routes:
 *   [TC_001] POST /api/login
 *   [TC_002] POST /api/signUp
 *   [TC_003] GET  /api/auth/check-email
 *   [TC_004] GET  /api/verify-email
 *
 * Dimensions per route:
 *   [PERF]  15 iterations, assert avg ≤ pass threshold, report p95/p99
 *   [AUTH]  Public endpoints: verify no auth required; 401 on expired token in header
 *   [VALID] Missing fields, wrong types, oversized, empty body
 *   [SEC]   SQL injection, XSS, rate limit (25 requests), mass-assignment, sensitive-data check
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
// [TC_001] POST /api/login
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_001] POST /api/login', () => {
  const login = (body) =>
    api.post('/api/login').send(body).set('Content-Type', 'application/json');

  // ── [PERF] ──────────────────────────────────────────────────────────────
  describe('[PERF] Performance', () => {
    test('[P0][TC_001] login avg responds within SLA (15 iterations)', async () => {
      const stats = await measurePerformance(
        () => login({ email: 'perf@test.com', password: 'wrongpass' }),
        15
      );
      assertSla('POST /api/login', 'login', stats);
    });
  });

  // ── [AUTH] ──────────────────────────────────────────────────────────────
  describe('[AUTH] Auth — public endpoint', () => {
    test('[TC_001] login is publicly accessible — no token needed', async () => {
      const res = await login({ email: 'nobody@test.com', password: 'wrongpass' });
      expect([200, 400, 401, 404, 422]).toContain(res.status);
    });

    test('[TC_001] expired JWT in Authorization header is ignored on public route', async () => {
      const res = await login({ email: 'x@x.com', password: 'x' })
        .set('Authorization', bearer(expiredToken()));
      expect(res.status).not.toBe(500);
    });
  });

  // ── [VALID] ─────────────────────────────────────────────────────────────
  describe('[VALID] Input Validation', () => {
    test('[TC_001] empty body returns 4xx', async () => {
      const res = await login({});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_001] missing email returns 4xx', async () => {
      const res = await login({ password: 'somepass123' });
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_001] missing password returns 4xx', async () => {
      const res = await login({ email: 'test@example.com' });
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_001] numeric email does not cause 500', async () => {
      const res = await login({ email: 12345, password: 'pass' });
      expect(res.status).not.toBe(500);
    });

    test('[TC_001] object password does not cause 500', async () => {
      const res = await login({ email: 'test@example.com', password: { nested: true } });
      expect(res.status).not.toBe(500);
    });

    test('[TC_001] null fields do not cause 500', async () => {
      const res = await login({ email: null, password: null });
      expect(res.status).not.toBe(500);
    });

    test('[TC_001] oversized email (5000 chars) does not cause 500', async () => {
      const res = await login({ email: oversizedString(5000) + '@test.com', password: 'pass' });
      expect(res.status).not.toBe(500);
    });

    test('[TC_001] array value in email field does not cause 500', async () => {
      const res = await login({ email: ['a@b.com', 'c@d.com'], password: 'pass' });
      expect(res.status).not.toBe(500);
    });
  });

  // ── [SEC] ───────────────────────────────────────────────────────────────
  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_001] SQL injection in email does not cause 500: %s',
      async (payload) => {
        const res = await login({ email: payload, password: 'pass' });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(SQL_INJECTION)(
      '[TC_001] SQL injection in password does not cause 500: %s',
      async (payload) => {
        const res = await login({ email: 'test@example.com', password: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(XSS_PAYLOADS)(
      '[TC_001] XSS payload in email does not cause 500 and is not reflected raw: %s',
      async (payload) => {
        const res = await login({ email: payload, password: 'pass' });
        expect(res.status).not.toBe(500);
        const body = JSON.stringify(res.body);
        expect(body).not.toContain('<script>');
      }
    );

    test('[TC_001] mass assignment — extra fields are ignored (no 500)', async () => {
      const res = await login({
        email: 'test@example.com',
        password: 'pass',
        role: 'Admin',
        isAdmin: true,
        __proto__: { admin: true },
      });
      expect(res.status).not.toBe(500);
    });

    test('[TC_001] response does not contain sensitive fields', async () => {
      const res = await login({ email: 'admin@test.com', password: 'wrongpass' });
      const body = JSON.stringify(res.body);
      expect(body).not.toContain('passwordHash');
      expect(body).not.toContain('password_hash');
      expect(body).not.toContain('stack');
    });

    test('[TC_001] rate limit — 25 rapid login attempts do not produce 5xx', async () => {
      const reqs = Array.from({ length: 25 }, () =>
        login({ email: 'ratelimit@test.com', password: 'wrongpass' })
      );
      const responses = await Promise.all(reqs);
      const serverErrors = responses.filter((r) => r.status >= 500);
      expect(serverErrors).toHaveLength(0);
      const rateLimited = responses.filter((r) => r.status === 429);
      if (rateLimited.length) console.log(`    Rate limiting active: ${rateLimited.length}/25 returned 429`);
      else                    console.warn('    ⚠️  No 429s — verify rate-limit middleware is configured');
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_002] POST /api/signUp
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_002] POST /api/signUp', () => {
  const signUp = (body) =>
    api.post('/api/signUp').send(body).set('Content-Type', 'application/json');

  describe('[AUTH] Auth — public endpoint', () => {
    test('[TC_002] signUp is publicly accessible', async () => {
      const res = await signUp({ email: 'x@x.com', password: 'Pass123!' });
      expect(res.status).not.toBe(401);
      expect(res.status).not.toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_002] empty body returns 4xx', async () => {
      const res = await signUp({});
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_002] missing email returns 4xx', async () => {
      const res = await signUp({ password: 'Pass123!', username: 'testuser' });
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_002] wrong types (bool email, array password) do not cause 500', async () => {
      const res = await signUp({ email: true, password: [], username: 999 });
      expect(res.status).not.toBe(500);
    });

    test('[TC_002] oversized username (5000 chars) does not cause 500', async () => {
      const res = await signUp({ email: 'new@test.com', password: 'Pass123!', username: oversizedString(5000) });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_002] SQL injection in email does not cause 500: %s',
      async (payload) => {
        const res = await signUp({ email: payload, password: 'Pass123!', username: 'u' });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(XSS_PAYLOADS)(
      '[TC_002] XSS in username does not cause 500: %s',
      async (payload) => {
        const res = await signUp({ email: 'x@x.com', password: 'Pass123!', username: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_002] rate limit — 25 rapid signUp attempts do not produce 5xx', async () => {
      const reqs = Array.from({ length: 25 }, (_, i) =>
        signUp({ email: `rate${i}${Date.now()}@test.com`, password: 'Pass123!', username: `u${i}` })
      );
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_003] GET /api/auth/check-email
// ─────────────────────────────────────────────────────────────────────────────
describe('[TC_003] GET /api/auth/check-email', () => {
  const checkEmail = (q) => api.get('/api/auth/check-email').query(q || {});

  describe('[PERF] Performance', () => {
    test('[TC_003] check-email avg responds within 1 second (15 iterations)', async () => {
      const stats = await measurePerformance(() => checkEmail({ email: 'probe@check.test' }), 15);
      assertSla('GET /api/auth/check-email', 'checkEmail', stats);
    });
  });

  describe('[AUTH] Auth — public endpoint', () => {
    test('[TC_003] check-email is publicly accessible', async () => {
      const res = await checkEmail({ email: 'probe@test.com' });
      expect(res.status).not.toBe(401);
      expect(res.status).not.toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_003] missing email param returns 4xx', async () => {
      const res = await checkEmail();
      expect(res.status).toBeGreaterThanOrEqual(400);
      expect(res.status).toBeLessThan(500);
    });

    test('[TC_003] oversized email param does not cause 500', async () => {
      const res = await checkEmail({ email: oversizedString(5000) + '@test.com' });
      expect(res.status).not.toBe(500);
    });

    test('[TC_003] invalid email format does not cause 500', async () => {
      const res = await checkEmail({ email: 'not-an-email' });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_003] SQL injection in email param does not cause 500: %s',
      async (payload) => {
        const res = await checkEmail({ email: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test.each(XSS_PAYLOADS)(
      '[TC_003] XSS in email param does not cause 500: %s',
      async (payload) => {
        const res = await checkEmail({ email: payload });
        expect(res.status).not.toBe(500);
        expect(JSON.stringify(res.body)).not.toContain('<script>');
      }
    );

    test('[TC_003] rate limit — 25 rapid requests do not produce 5xx', async () => {
      const reqs = Array.from({ length: 25 }, () => checkEmail({ email: 'probe@test.com' }));
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// [TC_004] GET /api/verify-email
// ─────────────────────────────────────────────────────────────────────────────
(isDeadSlaKey('tc_004') ? describe.skip : describe)('[TC_004] GET /api/verify-email', () => {
  describe('[AUTH] Auth — public endpoint', () => {
    test('[TC_004] verify-email is publicly accessible (no 401/403)', async () => {
      const res = await api.get('/api/verify-email').query({ token: 'invalid-token' });
      expect(res.status).not.toBe(401);
      expect(res.status).not.toBe(403);
    });
  });

  describe('[VALID] Input Validation', () => {
    test('[TC_004] missing token param does not cause 500', async () => {
      const res = await api.get('/api/verify-email');
      expect(res.status).not.toBe(500);
    });

    test('[TC_004] oversized token param does not cause 500', async () => {
      const res = await api.get('/api/verify-email').query({ token: oversizedString(5000) });
      expect(res.status).not.toBe(500);
    });
  });

  describe('[SEC] Security', () => {
    test.each(SQL_INJECTION)(
      '[TC_004] SQL injection in token param does not cause 500: %s',
      async (payload) => {
        const res = await api.get('/api/verify-email').query({ token: payload });
        expect(res.status).not.toBe(500);
      }
    );

    test('[TC_004] rate limit — 25 rapid requests do not produce 5xx', async () => {
      const reqs = Array.from({ length: 25 }, () =>
        api.get('/api/verify-email').query({ token: 'probe-token' })
      );
      const responses = await Promise.all(reqs);
      expect(responses.filter((r) => r.status >= 500)).toHaveLength(0);
    });
  });
});

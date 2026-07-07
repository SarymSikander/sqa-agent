/**
 * Autonomous auth helper — Firebase-first login.
 *
 * Flow for every role:
 *   1. POST Firebase signInWithPassword → idToken
 *   2. POST /api/login with { idToken } → Zambeel JWT
 *   3. Cache the Zambeel JWT; re-auth automatically when idToken is >50 min old
 *   4. Auto-refresh: clearToken() + retry once on any 401 (via withAuth)
 *
 * Staging env vars:
 *   FIREBASE_API_KEY
 *   ADMIN_EMAIL  / ADMIN_PASSWORD
 *   SELLER_EMAIL / SELLER_PASSWORD
 *   AGENCY_EMAIL / AGENCY_PASSWORD
 *
 * Production smoke (PROD_ prefix):
 *   PROD_FIREBASE_API_KEY        (may equal FIREBASE_API_KEY if one project)
 *   PROD_ADMIN_EMAIL  / PROD_ADMIN_PASSWORD
 *   PROD_SELLER_EMAIL / PROD_SELLER_PASSWORD
 *   PROD_AGENCY_EMAIL / PROD_AGENCY_PASSWORD
 */

require('dotenv').config({ path: require('path').resolve(__dirname, '../../.env') });
const https     = require('https');
const supertest = require('supertest');
const jwt       = require('jsonwebtoken');

const BASE_URL      = (process.env.BASE_URL      || 'http://localhost:3000').replace(/\/$/, '');
const PROD_BASE_URL = (process.env.PROD_BASE_URL || 'https://api.myzambeel.com').replace(/\/$/, '');
const JWT_SECRET    = process.env.JWT_SECRET || 'fallback-dev-secret';

const FIREBASE_SIGN_IN_HOST = 'identitytoolkit.googleapis.com';
const FIREBASE_SIGN_IN_PATH = '/v1/accounts:signInWithPassword';
const FIREBASE_TTL_MS       = 50 * 60 * 1000; // re-auth at 50 min; idTokens expire at 60 min

// { 'staging:admin': { token: '...', issuedAt: <ms> }, ... }
const tokenCache = {};

// ── Firebase REST call (plain https — no extra deps) ──────────────────────────
function firebaseSignIn(apiKey, email, password) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ email, password, returnSecureToken: true });
    const req  = https.request({
      hostname: FIREBASE_SIGN_IN_HOST,
      path:     `${FIREBASE_SIGN_IN_PATH}?key=${apiKey}`,
      method:   'POST',
      headers:  {
        'Content-Type':   'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
    }, res => {
      let d = '';
      res.on('data', c => { d += c; });
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(d) }); }
        catch (e) { reject(new Error(`Firebase response parse error: ${e.message}`)); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// ── Step 1: email+password → Firebase idToken ─────────────────────────────────
async function getFirebaseIdToken(role, env = 'staging') {
  const prefix   = env === 'prod' ? 'PROD_' : '';
  const apiKey   = process.env[`${prefix}FIREBASE_API_KEY`];
  const emailVar = `${prefix}${role.toUpperCase()}_EMAIL`;
  const passVar  = `${prefix}${role.toUpperCase()}_PASSWORD`;
  const email    = process.env[emailVar];
  const password = process.env[passVar];

  if (!apiKey) {
    throw new Error(
      `${prefix}FIREBASE_API_KEY is not set. ` +
      `Find it in Firebase console > Project Settings > General > Web API Key.`
    );
  }
  if (!email || !password) {
    throw new Error(`${emailVar} or ${passVar} is not set in .env`);
  }

  const res = await firebaseSignIn(apiKey, email, password);
  if (!res.body.idToken) {
    const reason = res.body.error?.message || `HTTP ${res.status}`;
    throw new Error(`Firebase sign-in failed for role=${role} (${email}): ${reason}`);
  }

  return res.body.idToken;
}

// ── Step 2 + cache: idToken → Zambeel JWT ─────────────────────────────────────
async function getToken(role, env = 'staging') {
  const cacheKey = `${env}:${role}`;
  const cached   = tokenCache[cacheKey];

  if (cached && (Date.now() - cached.issuedAt) < FIREBASE_TTL_MS) {
    return cached.token;
  }

  let idToken;
  try {
    idToken = await getFirebaseIdToken(role, env);
  } catch (err) {
    console.warn(`\n⚠️  Firebase auth failed for role=${role}: ${err.message}\n`);
    return null;
  }

  const baseUrl = env === 'prod' ? PROD_BASE_URL : BASE_URL;
  const api     = supertest(baseUrl);

  let res;
  try {
    res = await api
      .post('/api/login')
      .send({ idToken })
      .set('Content-Type', 'application/json');
  } catch (err) {
    console.warn(`\n⚠️  Zambeel login request failed for role=${role}: ${err.message}\n`);
    return null;
  }

  if (res.status !== 200) {
    console.warn(
      `\n⚠️  POST /api/login returned ${res.status} for role=${role} — auth tests may skip\n`
    );
    return null;
  }

  const token = res.body?.token || res.body?.accessToken || res.body?.access_token
    || res.body?.data?.token || res.body?.result?.token || null;

  if (!token) {
    console.warn(
      `\n⚠️  No JWT in Zambeel login response for role=${role}. ` +
      `Keys: ${Object.keys(res.body || {}).join(', ')}\n`
    );
    return null;
  }

  tokenCache[cacheKey] = { token, issuedAt: Date.now() };
  return token;
}

// ── Cache eviction (forces full re-auth on next getToken call) ────────────────
function clearToken(role, env = 'staging') {
  delete tokenCache[`${env}:${role}`];
}

// ── One automatic 401 refresh ─────────────────────────────────────────────────
async function withAuth(role, requestFn, env = 'staging') {
  let token = await getToken(role, env);
  let res   = await requestFn(token);
  if (res.status === 401 && token) {
    clearToken(role, env);
    token = await getToken(role, env);
    res   = await requestFn(token);
  }
  return res;
}

function bearer(token) {
  return `Bearer ${token || ''}`;
}

function expiredToken(secret = JWT_SECRET) {
  return jwt.sign(
    { sub: 9999, role: 'Admin', email: 'expired@test.com' },
    secret,
    { expiresIn: '-1s', algorithm: 'HS256' }
  );
}

function prodExpiredToken() {
  const secret = process.env.PROD_JWT_SECRET || process.env.JWT_SECRET || 'fallback-dev-secret';
  return expiredToken(secret);
}

module.exports = {
  getToken,
  getFirebaseIdToken,
  clearToken,
  withAuth,
  bearer,
  expiredToken,
  prodExpiredToken,
};

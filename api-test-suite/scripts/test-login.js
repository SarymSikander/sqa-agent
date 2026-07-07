require('dotenv').config();
const https = require('https');

const email          = process.env.ADMIN_EMAIL;
const password       = process.env.ADMIN_PASSWORD;
const firebaseApiKey = process.env.FIREBASE_API_KEY;
const host           = (process.env.BASE_URL || '').replace('https://','').replace('http://','');

if (!email || !password)       { console.error('❌  ADMIN_EMAIL or ADMIN_PASSWORD not set'); process.exit(1); }
if (!firebaseApiKey)           { console.error('❌  FIREBASE_API_KEY not set'); process.exit(1); }
if (!host)                     { console.error('❌  BASE_URL not set'); process.exit(1); }

console.log('Step 1 — Firebase sign-in with:', email);

// ── Step 1: Firebase REST → idToken ──────────────────────────────────────────
function post(hostname, path, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req  = https.request({
      hostname,
      path,
      method:  'POST',
      headers: {
        'Content-Type':   'application/json',
        'Content-Length': Buffer.byteLength(data),
      },
    }, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(d) }));
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

(async () => {
  // Firebase sign-in
  const fbRes = await post(
    'identitytoolkit.googleapis.com',
    `/v1/accounts:signInWithPassword?key=${firebaseApiKey}`,
    { email, password, returnSecureToken: true }
  );

  if (!fbRes.body.idToken) {
    console.error('❌  Firebase sign-in failed:', fbRes.body.error?.message || JSON.stringify(fbRes.body));
    process.exit(1);
  }

  const idToken = fbRes.body.idToken;
  console.log('✅ Firebase idToken obtained:', idToken.slice(0, 40) + '...');

  // Step 2: Zambeel login
  console.log('\nStep 2 — Zambeel POST /api/login with idToken');
  const zbRes = await post(host, '/api/login', { idToken });

  if (zbRes.body.token) {
    console.log('✅ Login works. Token:', zbRes.body.token.slice(0, 30) + '...');
  } else {
    console.log('❌ Login failed:', zbRes.body.message);
    console.log('Full response:', JSON.stringify(zbRes.body, null, 2));
  }
})().catch(err => {
  console.error('❌ Fatal:', err.message);
  process.exit(1);
});

/**
 * Payloads for security testing dimensions.
 * All payloads are safe to send — they test that the server rejects or sanitises
 * them without crashing (no 500s) or leaking data.
 */

const SQL_INJECTION = [
  "' OR '1'='1",
  "'; DROP TABLE orders; --",
  "1 UNION SELECT 1,2,3,4,5 --",
  "' OR 1=1 --",
  "admin'--",
  "1; EXEC xp_cmdshell('dir'); --",
];

const XSS_PAYLOADS = [
  '<script>alert(document.cookie)</script>',
  '"><img src=x onerror=alert(1)>',
  "javascript:alert(1)",
  '<svg/onload=alert(1)>',
  '{{7*7}}',
  '<iframe src="javascript:alert(1)">',
];

/** Returns a string of `byteCount` bytes (approx) */
function oversizedString(byteCount = 1024 * 1024) {
  return 'A'.repeat(byteCount);
}

module.exports = { SQL_INJECTION, XSS_PAYLOADS, oversizedString };

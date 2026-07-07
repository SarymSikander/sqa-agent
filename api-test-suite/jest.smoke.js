/**
 * Jest configuration for the production smoke test suite.
 *
 * ONLY runs files inside tests/smoke/ — every file there must carry
 * the JSDoc tag "@readonly" at the top to signal it performs no mutations.
 *
 * Enforcement rules baked into the smoke test files:
 *   • Only GET requests OR POST /api/login are permitted.
 *   • No CSV uploads, no order creation, no status mutations, no bulk ops.
 *   • All auth tests use PROD_JWT_SECRET to generate expired tokens — the
 *     PROD_TOKEN itself must NEVER be written to assertions or logs.
 *
 * Usage:
 *   jest --config jest.smoke.js --ci --json --outputFile=reports/smoke-results.json
 */

module.exports = {
  testEnvironment: 'node',

  // 30 s default; CSV export smoke test overrides to 60 s inline
  testTimeout: 30000,

  // Only files in the smoke directory are picked up by this config
  testMatch: ['**/tests/smoke/**/*.test.js'],

  reporters: [
    'default',
    [
      'jest-html-reporter',
      {
        pageTitle: 'Zambeel Production — Smoke Test Report',
        outputPath: 'reports/smoke-report.html',
        includeFailureMsg: true,
        includeSuiteFailure: true,
        theme: 'defaultTheme',
        dateFormat: 'yyyy-mm-dd HH:MM:ss',
        sort: 'status',
      },
    ],
  ],
};

module.exports = {
  testEnvironment: 'node',

  // 15 iterations × ~2s per request + 5s buffer = 35s minimum.
  // CSV export tests override inline to 120s.
  testTimeout: 60000,

  testMatch: ['**/tests/**/*.test.js'],
  // Exclude smoke tests from the main suite (they have their own jest.smoke.js)
  testPathIgnorePatterns: ['/node_modules/', '/tests/smoke/'],

  randomize: false,

  reporters: [
    'default',
    [
      'jest-html-reporter',
      {
        pageTitle:           'Zambeel API Test Report',
        outputPath:          'reports/test-report.html',
        includeFailureMsg:   true,
        includeSuiteFailure: true,
        theme:               'defaultTheme',
        dateFormat:          'yyyy-mm-dd HH:MM:ss',
        sort:                'status',
      },
    ],
  ],
};

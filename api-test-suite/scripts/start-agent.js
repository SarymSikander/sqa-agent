/**
 * PM2 ecosystem file for the Zambeel SQA Agent.
 *
 * Usage:
 *   pm2 start scripts/start-agent.js   # start
 *   pm2 stop  zambeel-sqa-agent        # stop
 *   pm2 logs  zambeel-sqa-agent        # tail logs
 *   pm2 save                           # persist across reboots
 *   pm2 startup                        # install system service
 *
 * The .env file at the project root is loaded automatically by slack-agent.js
 * via dotenv. PM2's own env block below is a fallback / explicit override path
 * for production deployments where .env may not be present.
 */

module.exports = {
  apps: [
    {
      name:              'zambeel-sqa-agent',
      script:            'scripts/slack-agent.js',
      cwd:               require('path').resolve(__dirname, '..'),
      interpreter:       'node',

      // Restart on crash; give it up to 5 seconds to gracefully stop
      restart_delay:     5000,
      max_restarts:      10,
      kill_timeout:      5000,
      watch:             false,

      // Log to project-local files so logs ship with artifacts
      out_file:          'logs/agent-out.log',
      error_file:        'logs/agent-err.log',
      merge_logs:        true,
      log_date_format:   'YYYY-MM-DD HH:mm:ss',

      // Environment variables — values here are used when .env is absent.
      // For local dev: set these in .env instead so they're not in source.
      env: {
        NODE_ENV:            'production',
        AGENT_TEST_TIMEOUT_MS: '600000',
        // SLACK_BOT_TOKEN and SLACK_APP_TOKEN must come from .env or system env
      },
    },
  ],
};

import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './smoke',
  use: { baseURL: 'http://127.0.0.1:5175', channel: process.env.PLAYWRIGHT_CHANNEL },
  webServer: [
    {
      command: 'uv run --project ../backend --locked python ../backend/tests/serve_sample.py',
      url: 'http://127.0.0.1:8011/api/health',
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --port 5175',
      env: { UAS_API_URL: 'http://127.0.0.1:8011' },
      url: 'http://127.0.0.1:5175',
      reuseExistingServer: false,
    },
  ],
})

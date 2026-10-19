// Headless smoke test against a regtest node. See README.md.
//   LOTUSD=/path/to/lotusd npm run smoke
// PW_CHANNEL selects the browser: "chrome" (installed Google Chrome, default),
// "chromium" (Playwright's own build: run `npx playwright install chromium`).

import { defineConfig } from '@playwright/test';

const channel = process.env.PW_CHANNEL ?? 'chrome';

export default defineConfig({
  testDir: '.',
  testMatch: /.*\.spec\.mjs$/,
  timeout: 180_000,
  expect: { timeout: 20_000 },
  workers: 1,
  fullyParallel: false,
  reporter: [['list']],
  outputDir: process.env.NODE_PWA_SMOKE_OUT ?? '../../test-results',
  use: {
    headless: true,
    ...(channel === 'chromium' ? {} : { channel }),
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
});

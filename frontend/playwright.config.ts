import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/browser",
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:4173",
    channel: process.platform === "win32" ? "msedge" : "chromium",
    screenshot: "only-on-failure",
  },
  webServer: [{
    command: "npm run preview -- --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
  }, {
    command: 'python -m gridmind.api',
    env: { PYTHONPATH: '../src' },
    url: 'http://127.0.0.1:8000/api/health',
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  }],
  projects: [
    { name: "laptop", use: { viewport: { width: 1366, height: 768 } } },
    { name: "mobile", use: { viewport: { width: 390, height: 844 } } },
  ],
});

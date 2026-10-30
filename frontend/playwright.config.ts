import { defineConfig, devices } from "@playwright/test";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const frontend = dirname(fileURLToPath(import.meta.url));
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45000,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:18300",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "desktop-chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1000 },
      },
    },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command: ".venv/bin/python -m scripts.browser_api",
      cwd: resolve(frontend, ".."),
      url: "http://127.0.0.1:18400/health",
      reuseExistingServer: false,
      timeout: 30000,
      env: {
        DERMA_E2E: "1",
        DERMA_API_TOKEN: "isolated-browser-test-token-not-a-real-secret",
      },
    },
    {
      command: "npm run dev -- --port 18300",
      cwd: frontend,
      url: "http://127.0.0.1:18300",
      reuseExistingServer: false,
      timeout: 60000,
      env: { API_URL: "http://127.0.0.1:18400" },
    },
  ],
});

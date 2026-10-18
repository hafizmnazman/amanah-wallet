import { defineConfig, devices } from "@playwright/test";
import { generatePrivateKey } from "viem/accounts";

const PORT = 5174;

/**
 * Browser checks against the dev server in mock mode (task D5). The pinned @playwright/test 1.56.1 uses
 * Chromium build 1194; set PLAYWRIGHT_BROWSERS_PATH if your browsers live elsewhere. The dev trustee key
 * is generated fresh for every run, so no key is ever committed.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: true,
  reporter: [["list"]],
  use: { baseURL: `http://127.0.0.1:${PORT}`, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npx vite --host 127.0.0.1 --port ${PORT} --strictPort`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      VITE_MOCK_API: "1",
      VITE_MOCK_LATENCY_MS: "50",
      VITE_DEV_SIGNING: "1",
      VITE_DEV_TRUSTEE_KEY: generatePrivateKey(),
      VITE_CHAIN_ID: "84532",
      VITE_VAULT_ADDRESS: "",
    },
  },
});

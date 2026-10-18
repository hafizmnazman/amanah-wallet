import { defineConfig, devices } from "@playwright/test";
import { toHex } from "viem";
import { mnemonicToAccount } from "viem/accounts";

import { ANVIL_PORT, API_PORT, MNEMONIC, STACK_RPC, STACK_VAULT, WEB_PORT } from "./e2e-stack/stack";

/**
 * Browser checks against the real stack, not the mock: `scripts/dev_up.sh` starts Anvil with lane A's
 * fixture, the auditor, the sentinel and the API in dry-run, and Vite serves the app against it.
 *
 *   npx playwright test --config playwright.stack.config.ts
 *
 * PYTHON picks the backend's interpreter; the default is .venv/bin/python at the repository root. The
 * ports differ from the dev defaults, so a running dev stack is not disturbed. The dev trustee key is
 * Anvil's account 5, a public test key that the fixture registers as trustee 1. It is derived here,
 * never written down.
 */
const trusteeKey = toHex(mnemonicToAccount(MNEMONIC, { addressIndex: 5 }).getHdKey().privateKey!);

export default defineConfig({
  testDir: "./e2e-stack",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: `http://127.0.0.1:${WEB_PORT}`, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `bash ../scripts/dev_up.sh --anvil-port ${ANVIL_PORT} --api-port ${API_PORT} --auditor-port 8401 --sentinel-port 8402 --cors http://127.0.0.1:${WEB_PORT}`,
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      reuseExistingServer: false,
      timeout: 180_000,
      env: { PYTHON: process.env.PYTHON ?? "" },
    },
    {
      command: `npx vite --host 127.0.0.1 --port ${WEB_PORT} --strictPort`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        VITE_MOCK_API: "0",
        VITE_API_URL: `http://127.0.0.1:${API_PORT}`,
        VITE_CHAIN_ID: "31337",
        VITE_VAULT_ADDRESS: STACK_VAULT,
        VITE_RPC_URL: STACK_RPC,
        VITE_EXPLORER_URL: "http://anvil.local",
        VITE_DEV_SIGNING: "1",
        VITE_DEV_TRUSTEE_KEY: trusteeKey,
      },
    },
  ],
});

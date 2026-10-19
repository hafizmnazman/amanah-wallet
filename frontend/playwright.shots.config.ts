import { defineConfig } from "@playwright/test";

import stack from "./playwright.stack.config";

/**
 * The README's screenshots, taken from the real stack that playwright.stack.config.ts starts: Anvil with
 * lane A's fixture, the auditor, the sentinel and the API, with dry-run models.
 *
 *   npx playwright test --config playwright.shots.config.ts
 *
 * They are written to .github/readme/shots/ at the repository root.
 */
export default defineConfig({ ...stack, testDir: "./e2e-shots" });

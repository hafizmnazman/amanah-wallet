import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";
import { createWalletClient, http, parseAbi } from "viem";
import { mnemonicToAccount } from "viem/accounts";
import { foundry } from "viem/chains";

import { MNEMONIC, STACK_RPC, STACK_VAULT } from "../e2e-stack/stack";

// The README's screenshots, along the same path as e2e-stack/stack.spec.ts: one chain, in order.
const SHOTS = fileURLToPath(new URL("../../.github/readme/shots/", import.meta.url));
test.describe.configure({ mode: "serial" });
test.use({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });

async function say(page: Page, text: string) {
  await page.getByLabel("Message").fill(text);
  await page.getByRole("button", { name: "Send" }).click();
}

async function shot(page: Page, name: string) {
  await page.waitForTimeout(400); // let the last render settle
  await page.screenshot({ path: `${SHOTS}${name}.png` });
}

test("the officer's batch: a question, a correction, and 11 payouts through the checkers", async ({ page }) => {
  await page.goto("/officer");
  await expect(page.getByTestId("scheduled-drafts").getByTestId("plan-row")).toHaveCount(12, { timeout: 15_000 });
  await say(page, "Pay October's aid for Ipoh.");
  await expect(page.getByTestId("clarification")).toContainText("two batches for Ipoh");
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); // the question and its answers
  await shot(page, "clarify");

  await page.getByRole("button", { name: "Zakat monthly aid" }).click();
  await expect(page.getByTestId("chat-log").getByTestId("plan-card").last().getByTestId("plan-row")).toHaveCount(12);
  await say(page, "Leave out household 12, they moved.");
  const updated = page.getByTestId("chat-log").getByTestId("plan-card").last();
  await expect(updated.getByTestId("plan-row")).toHaveCount(11);
  await updated.getByRole("button", { name: "Confirm 11 payouts" }).click();
  const results = page.getByTestId("chat-log").getByTestId("payout-result");
  await expect(results).toHaveCount(11, { timeout: 45_000 });
  for (const row of await results.all()) await expect(row).toContainText("Paid");
  await results.first().scrollIntoViewIfNeeded();
  await shot(page, "officer");
});

test("an elevated payout waits, and the trustee checks the summary against the signed fields", async ({ page }) => {
  const oracle = createWalletClient({ account: mnemonicToAccount(MNEMONIC, { addressIndex: 4 }), chain: foundry,
                                      transport: http(STACK_RPC) });
  await oracle.writeContract({ address: STACK_VAULT, abi: parseAbi(["function raisePosture(uint8 level, bytes32 reportHash)"]),
                               functionName: "raisePosture", args: [1, `0x${"ab".repeat(32)}`] });
  await page.goto("/officer");
  await expect(page.getByTestId("posture-banner")).toContainText("level 1");
  await say(page, "Pay household ZKT-H14 this month.");
  const card = page.getByTestId("chat-log").getByTestId("plan-card").last();
  await expect(card.getByTestId("tier-preview")).toContainText("Elevated");
  await card.getByRole("button", { name: /Confirm/ }).click();
  await expect(page.getByTestId("payout-result").last()).toContainText("Waiting for a trustee", { timeout: 30_000 });
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await shot(page, "posture");

  await page.getByLabel("Role").selectOption("trustee");
  await page.goto("/trustee");
  const pending = page.getByTestId("pending-payout");
  await expect(pending.getByTestId("checks-ok")).toBeVisible();
  await shot(page, "trustee");
  await pending.getByRole("button", { name: "Sign with local trustee key" }).click();
  await expect(page.getByTestId("sign-result")).toContainText("paid");

  await page.getByLabel("Role").selectOption("finance_officer");
  await page.goto("/proof");
  await expect(page.getByTestId("proof-row")).toHaveCount(12);
  await shot(page, "proof");
});

test("the public page of how each fund was used", async ({ page }) => {
  await page.goto("/usage");
  await expect(page.getByTestId("usage-programme").first()).toContainText("12 paid on-chain");
  await shot(page, "usage");
});

test("the story, the red team and the design system", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("sweet-talked");
  await shot(page, "home");
  await page.goto("/redteam");
  await expect(page.getByTestId("redteam-row")).toHaveCount(44);
  await shot(page, "redteam");
  await page.goto("/brand");
  await expect(page.getByTestId("brand-poses")).toBeVisible();
  await shot(page, "brand");
});

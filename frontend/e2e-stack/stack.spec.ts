import { expect, test, type Page } from "@playwright/test";
import { createWalletClient, http, parseAbi } from "viem";
import { mnemonicToAccount } from "viem/accounts";
import { foundry } from "viem/chains";

import { MNEMONIC, STACK_RPC, STACK_VAULT } from "./stack";

// One chain for the whole file: the tests run in order and build on each other.
test.describe.configure({ mode: "serial" });

async function say(page: Page, text: string) {
  await page.getByLabel("Message").fill(text);
  await page.getByRole("button", { name: "Send" }).click();
}

test("the scripted conversation pays 11 households through the real checkers and the vault", async ({ page }) => {
  await page.goto("/officer");
  await expect(page.getByTestId("mock-badge")).toHaveCount(0);
  // The API's schedule loop drafted October's zakat batch at start (plan task B11); it waits, unconfirmed
  const scheduled = page.getByTestId("scheduled-drafts");
  await expect(scheduled.getByTestId("plan-row")).toHaveCount(12, { timeout: 15_000 });
  await expect(scheduled.getByTestId("payout-result")).toHaveCount(0);

  await say(page, "Pay October's aid for Ipoh.");
  await expect(page.getByTestId("clarification")).toContainText("two batches for Ipoh");
  await page.getByRole("button", { name: "Zakat monthly aid" }).click();

  const card = page.getByTestId("chat-log").getByTestId("plan-card").last();
  await expect(card.getByTestId("plan-row")).toHaveCount(12);
  await expect(card.getByTestId("plan-total")).toHaveText("1,810.00");
  await expect(card.getByTestId("tier-preview")).toContainText("Routine");

  await say(page, "Leave out household 12, they moved.");
  const updated = page.getByTestId("chat-log").getByTestId("plan-card").last();
  await expect(updated.getByTestId("plan-row")).toHaveCount(11);
  await expect(updated.getByTestId("plan-total")).toHaveText("1,650.00");

  await updated.getByRole("button", { name: "Confirm 11 payouts" }).click();
  const results = page.getByTestId("chat-log").getByTestId("payout-result");
  await expect(results).toHaveCount(11, { timeout: 45_000 });
  for (const row of await results.all()) await expect(row).toContainText("Paid");
  await expect(results.first().getByTestId("verdict-card")).toHaveCount(3);
  await expect(results.first()).toContainText("Auditor (Qwen)");
  await expect(page.locator('a[href^="http://anvil.local/tx/0x"]')).toHaveCount(11);
});

test("with the posture raised, a payout waits for a trustee and turns to paid once signed", async ({ page }) => {
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
  const row = page.getByTestId("payout-result").last();
  await expect(row).toContainText("Waiting for a trustee", { timeout: 30_000 });

  await page.getByLabel("Role").selectOption("trustee");
  await page.goto("/trustee");
  const pending = page.getByTestId("pending-payout");
  await expect(pending).toHaveCount(1);
  await expect(pending.getByTestId("summary-text")).toContainText("Pay 160.00 USDC");
  await expect(pending.getByTestId("checks-ok")).toBeVisible();
  await pending.getByRole("button", { name: "Sign with local trustee key" }).click();
  await expect(page.getByTestId("sign-result")).toContainText("paid");
  await expect(page.getByText("Nothing is waiting for a trustee.")).toBeVisible();

  await page.getByLabel("Role").selectOption("finance_officer");
  await page.goto("/proof");
  await expect(page.getByTestId("proof-row")).toHaveCount(12);
});

test("the public fund use page counts the payouts the vault made", async ({ page }) => {
  await page.goto("/usage");
  await expect(page.getByTestId("usage-fund")).toHaveCount(3);
  // The first test paid 11 zakat households on-chain, and the second paid one more
  await expect(page.getByTestId("usage-programme").first()).toContainText("12 paid on-chain");
  await expect(page.locator("body")).not.toContainText(/0x[0-9a-fA-F]{40}/);
});

import { expect, test } from "@playwright/test";

test("the trustee sees decoded fields beside the summary and signs with the local key", async ({ page }) => {
  await page.goto("/trustee");
  const card = page.getByTestId("pending-payout");
  await expect(card).toHaveCount(1);
  await expect(card.getByTestId("summary-text")).toContainText("1,200.00 USDC");
  await expect(card.getByTestId("field-amount")).toHaveText("1,200.00 USDC (1200000000 base units)");
  await expect(card.getByTestId("field-beneficiary")).toHaveText(/^0x[0-9a-fA-F]{40}$/);
  await expect(card.getByTestId("field-deadline")).toContainText("UTC");
  await expect(card.getByTestId("checks-ok")).toBeVisible();
  await expect(card.getByRole("button", { name: "Sign in MetaMask" })).toBeEnabled();

  await card.getByRole("button", { name: "Sign with local trustee key" }).click();
  const result = page.getByTestId("sign-result");
  await expect(result).toContainText("paid (mock; signed by 0x");
  await expect(result).toContainText("(mock)");
  await expect(page.getByTestId("pending-payout")).toHaveCount(0);
  await expect(page.getByText("Nothing is waiting for a trustee.")).toBeVisible();
});

test("the wallet panel offers MetaMask when no wallet is connected", async ({ page }) => {
  await page.goto("/trustee");
  await expect(page.getByTestId("wallet-panel")).toContainText("Connect the trustee wallet");
});

import { expect, test } from "@playwright/test";

test("the proof page lists the 16 scenarios, marked as mock data", async ({ page }) => {
  await page.goto("/proof");
  const rows = page.getByTestId("proof-row");
  await expect(rows).toHaveCount(16);
  await expect(rows.nth(9)).toContainText("NotAllowlisted");
  await expect(rows.nth(9)).toContainText("reverted");
  await expect(page.getByTestId("mock-badge").first()).toBeVisible();
  await expect(page.locator('a[href*="basescan"]')).toHaveCount(0);
});

test("a raised posture shows the banner on every page, and the queue lists a held payout", async ({ page }) => {
  await page.goto("/proof");
  await expect(page.getByTestId("posture-banner")).toHaveCount(0);
  await page.getByTestId("mock-posture-toggle").click();
  await expect(page.getByTestId("posture-banner")).toContainText("raised to level 1");

  await page.getByRole("link", { name: "Queue" }).click();
  await expect(page.getByTestId("posture-banner")).toBeVisible();
  await expect(page.getByTestId("queue-item")).toHaveCount(1);
  await expect(page.getByTestId("queue-item")).toContainText("Auditor unavailable");

  await page.getByRole("link", { name: "Officer" }).click();
  await expect(page.getByTestId("posture-banner")).toBeVisible();
});

test("the role switcher changes who the app acts as", async ({ page }) => {
  await page.goto("/queue");
  await expect(page.getByText("This page is for trustees.")).toBeVisible();
  await page.getByLabel("Role").selectOption("trustee");
  await expect(page.getByText("This page is for trustees.")).toHaveCount(0);
});

test("the fund use page shows totals by programme and no wallet", async ({ page }) => {
  await page.goto("/usage");
  await expect(page.getByTestId("usage-fund")).toHaveCount(3);
  await expect(page.getByTestId("usage-total").first()).toHaveText("5,850.00 USDC");
  await expect(page.getByTestId("usage-source")).toContainText("the vault's PayoutExecuted events");
  await expect(page.locator("body")).not.toContainText(/0x[0-9a-fA-F]{40}/);
});

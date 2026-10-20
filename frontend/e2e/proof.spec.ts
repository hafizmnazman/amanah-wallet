import { expect, test } from "@playwright/test";

test("the proof page lists the 16 scenarios, marked as mock data", async ({ page }) => {
  await page.goto("/proof");
  const rows = page.getByTestId("proof-row");
  await expect(rows).toHaveCount(16);
  await expect(rows.nth(9)).toContainText("NotAllowlisted");
  await expect(rows.nth(9).getByText("Reverted", { exact: true })).toBeVisible();
  await expect(page.getByTestId("mock-badge").first()).toBeVisible();
  // Mock hashes never link; the one explorer link on the page is the real anchor of the action log
  await expect(rows.locator('a[href*="basescan"], a[href*="blockscout"]')).toHaveCount(0);
  await expect(page.locator('a[href*="basescan"], a[href*="blockscout"]')).toHaveCount(1);
});

test("the proof page verifies the 19 October run's action log in the browser and offers it for download", async ({ page }) => {
  await page.goto("/proof");
  const log = page.getByTestId("action-log");
  await expect(log).toContainText("19 October Base Sepolia run");
  await expect(log.getByTestId("action-log-count")).toHaveText("88");
  await expect(log.getByTestId("action-log-head")).toHaveText("487218f0aba40a763bef66a8275480f6ada1990bfe1ce6d6a85a797a2a9ec212");
  await expect(log.getByTestId("anchor-link")).toHaveAttribute(
    "href",
    "https://base-sepolia.blockscout.com/tx/0x904b8f9db00c81ee403703780d77b01f15e88fce2b0698f7b2f1791365d5b605",
  );
  await log.getByRole("button", { name: "Verify in Your Browser" }).click();
  await expect(log.getByTestId("action-log-check")).toHaveText("88 of 88 links verified. The head matches the hash shown above.");

  const [csv] = await Promise.all([page.waitForEvent("download"), log.getByRole("button", { name: "Download CSV" }).click()]);
  expect(csv.suggestedFilename()).toBe("action-log.csv");
  const [jsonl] = await Promise.all([page.waitForEvent("download"), log.getByRole("button", { name: "Download JSONL" }).click()]);
  expect(jsonl.suggestedFilename()).toBe("action-log.jsonl");
});

test("the queue page lists the store's alerts, newest first", async ({ page }) => {
  await page.goto("/queue");
  await page.getByLabel("Role").selectOption("trustee");
  const alerts = page.getByTestId("alert");
  await expect(alerts).toHaveCount(6);
  await expect(alerts.first()).toContainText("Queued");
  await expect(alerts.first()).toContainText("The auditor service did not answer");
  await expect(alerts.nth(1)).toContainText("Trustee Needed");
  await expect(alerts.nth(2)).toContainText("Refused on Retry");
  await expect(alerts.nth(2)).toContainText("was refused on retry: The vault reverted it: Expired. Nothing was paid.");
  await expect(alerts.nth(3)).toContainText("Queued payout went through after a retry.");
  await expect(alerts.last()).toContainText("the RPC endpoint did not answer");
});

test("a raised posture shows the banner on every page, and the queue lists a held payout", async ({ page }) => {
  await page.goto("/proof");
  await expect(page.getByTestId("posture-banner")).toHaveCount(0);
  await page.getByTestId("mock-posture-toggle").click();
  await expect(page.getByTestId("posture-banner")).toContainText("raised to level 1");

  await page.getByRole("link", { name: "Queue" }).click();
  await expect(page.getByTestId("posture-banner")).toBeVisible();
  await expect(page.getByTestId("queue-item")).toHaveCount(1);
  await expect(page.getByTestId("queue-item")).toContainText("Auditor Unavailable");

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

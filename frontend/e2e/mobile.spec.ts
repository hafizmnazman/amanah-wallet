import { expect, test, type Page } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 } });

async function expectNoSideScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

test("the officer page fits a 390 px phone, with a plan card open", async ({ page }) => {
  await page.goto("/officer");
  await expectNoSideScroll(page);
  await page.getByLabel("Message").fill("Pay October's monthly aid for the Ipoh fakir programme");
  await page.getByRole("button", { name: "Send" }).click();
  await page.getByRole("button", { name: "Zakat monthly aid" }).click();
  const chat = page.getByTestId("chat-log");
  await expect(chat.getByTestId("plan-row")).toHaveCount(12);
  await expectNoSideScroll(page);
  await expect(chat.getByRole("button", { name: "Confirm 12 payouts" })).toBeVisible();
  // The message box stays on screen while the long plan card scrolls under it
  await expect(page.getByLabel("Message")).toBeInViewport();
  // Under 640 px the wallet column hides, and a short hash stays in the beneficiary cell
  await expect(chat.getByTestId("plan-row").first().getByText(/^0x[0-9a-fA-F]{4}\.\.\.[0-9a-fA-F]{4}$/)).toBeVisible();
});

test("the proof page fits a 390 px phone, with the action log", async ({ page }) => {
  await page.goto("/proof");
  await expect(page.getByTestId("proof-row")).toHaveCount(16);
  await expect(page.getByTestId("action-log-head")).toBeVisible();
  await expectNoSideScroll(page);
});

test("the trustee page fits a 390 px phone", async ({ page }) => {
  await page.goto("/trustee");
  await expect(page.getByTestId("pending-payout")).toHaveCount(1);
  await expectNoSideScroll(page);
  await expect(page.getByTestId("field-amount")).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign with local trustee key" })).toBeVisible();
});

test("the fund use page fits a 390 px phone", async ({ page }) => {
  await page.goto("/usage");
  await expect(page.getByTestId("usage-fund")).toHaveCount(3);
  await expectNoSideScroll(page);
});

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
});

test("the trustee page fits a 390 px phone", async ({ page }) => {
  await page.goto("/trustee");
  await expect(page.getByTestId("pending-payout")).toHaveCount(1);
  await expectNoSideScroll(page);
  await expect(page.getByTestId("field-amount")).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign with local trustee key" })).toBeVisible();
});

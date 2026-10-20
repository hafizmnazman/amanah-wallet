import { expect, test } from "@playwright/test";

/** The officer desk as a judge first meets it, in mock mode. */

test("the payout chips plan one household from the books, then the emergency grant the trustee holds", async ({ page }) => {
  await page.goto("/officer");
  const chat = page.getByTestId("chat-log");
  await page.getByRole("button", { name: "Pay household ZKT-H14 this month." }).click();
  const card = chat.getByTestId("plan-card").last();
  await expect(card.getByTestId("plan-row")).toHaveCount(1);
  await expect(card.getByTestId("plan-row")).toContainText("ZKT-H14");
  await expect(card.getByTestId("plan-total")).toHaveText("160.00");
  await expect(card.getByRole("button", { name: "Confirm 1 Payout · 160.00 USDC" })).toBeVisible();

  await page.getByRole("button", { name: "Start Over" }).click();
  await page.getByTestId("start-over-confirm").getByRole("button", { name: "Drop" }).click();
  await page.getByRole("button", { name: "Pay the flood relief emergency grant." }).click();
  const grant = chat.getByTestId("plan-card").last();
  await expect(grant.getByTestId("tier-preview")).toContainText("Elevated");
  await expect(grant.getByTestId("plan-total")).toHaveText("1,200.00");
  await expect(grant.getByTestId("plan-row")).toContainText("REL-H01");
  await grant.getByRole("button", { name: "Confirm 1 Payout · 1,200.00 USDC" }).click();
  await expect(chat.getByTestId("payout-result")).toContainText("Waiting for a Trustee");
  const happened = chat.getByTestId("what-happened");
  await expect(happened).toContainText("The vault held 1 for a trustee to co-sign.");
  await happened.getByRole("link", { name: "Open the Trustee Page" }).click();
  // The same grant, not a second copy of it
  await expect(page.getByTestId("pending-payout")).toHaveCount(1);
  await expect(page.getByTestId("summary-text")).toContainText("household REL-H01");
});

test("the Chinese trick is refused in Chinese and English, and the line says who stopped it", async ({ page }) => {
  await page.goto("/officer");
  await page.getByRole("button", { name: "用中文试试" }).click();
  const reply = page.getByTestId("agent-message").last();
  await expect(reply).toContainText("我不能向账簿之外的钱包付款。");
  await expect(reply).toContainText("(I can't send money to a wallet that is not in the books.");
  await expect(page.getByTestId("what-happened")).toContainText("Stopped by the planner");
  await expect(page.getByTestId("chat-log").getByTestId("plan-card")).toHaveCount(0);
});

test("Start Over asks before it drops an unconfirmed plan", async ({ page }) => {
  await page.goto("/officer");
  const chat = page.getByTestId("chat-log");
  await page.getByRole("button", { name: "Pay household ZKT-H14 this month." }).click();
  await expect(chat.getByTestId("plan-card")).toHaveCount(1);

  await page.getByRole("button", { name: "Start Over" }).click();
  const ask = page.getByTestId("start-over-confirm");
  await expect(ask).toContainText("Drop the unconfirmed plan? Nothing was paid.");
  await ask.getByRole("button", { name: "Keep" }).click();
  await expect(ask).toHaveCount(0);
  await expect(chat.getByTestId("plan-card")).toHaveCount(1);

  await page.getByRole("button", { name: "Start Over" }).click();
  await page.getByTestId("start-over-confirm").getByRole("button", { name: "Drop" }).click();
  await expect(chat.getByTestId("plan-card")).toHaveCount(0);
  await expect(page.getByText("Try a Payout")).toBeVisible();
});

test("a document that is empty or over 1 MB is refused before it is sent", async ({ page }) => {
  await page.goto("/officer");
  const input = page.getByTestId("document-input");
  await expect(input).toHaveAttribute("accept", ".txt,.md,text/plain");
  await input.setInputFiles({ name: "empty.txt", mimeType: "text/plain", buffer: Buffer.from("") });
  await expect(page.getByTestId("file-error")).toHaveText("Attach a plain-text file under 1 MB.");
  await input.setInputFiles({ name: "big.txt", mimeType: "text/plain", buffer: Buffer.alloc(1_000_001, 97) });
  await expect(page.getByTestId("file-error")).toHaveText("Attach a plain-text file under 1 MB.");
  await expect(page.getByTestId("reader-fields")).toHaveCount(0);

  await input.setInputFiles({ name: "note.txt", mimeType: "text/plain", buffer: Buffer.from("Applicant: EDU-A-08, 2026-10-06.") });
  await expect(page.getByTestId("reader-fields")).toContainText("note.txt");
  await expect(page.getByTestId("file-error")).toHaveCount(0);
});

test("the first-visit steps can be dismissed, and stay dismissed", async ({ page }) => {
  await page.goto("/officer");
  const steps = page.getByTestId("first-visit");
  await expect(steps).toContainText("Confirm the batch");
  await expect(steps).toContainText("Try a trick");
  await expect(steps.getByRole("link", { name: "See the red team" })).toHaveAttribute("href", "/redteam");
  await steps.getByRole("button", { name: "Hide These Steps" }).click();
  await expect(steps).toHaveCount(0);
  await page.reload();
  await expect(page.getByTestId("chat-log")).toBeVisible();
  await expect(page.getByTestId("first-visit")).toHaveCount(0);
});

test("the posture button says what it does, and the chat input shows its focus", async ({ page }) => {
  await page.goto("/officer");
  await expect(page.getByTestId("mock-posture-toggle")).toHaveAttribute("title", /as the red team's oracle would/);
  await page.getByLabel("Message").focus();
  // --color-sky, #2f6fe4
  await expect(page.locator("form .chunky")).toHaveCSS("border-top-color", "rgb(47, 111, 228)");
});

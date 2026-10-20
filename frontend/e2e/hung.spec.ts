import { expect, test, type Page } from "@playwright/test";

/**
 * A backend that hangs. The mock answers after its 50 ms latency (playwright.config.ts), so this shim holds
 * those timers until the test lets them go, and lets the chat's 20-second wait pass in a moment.
 */
function holdMockReplies() {
  const realTimeout = window.setTimeout.bind(window);
  const held: (() => void)[] = [];
  let holding = false;
  Object.assign(window, {
    holdMock(on: boolean) {
      holding = on;
      if (!on) for (const reply of held.splice(0)) reply();
    },
  });
  window.setTimeout = ((handler: TimerHandler, ms?: number, ...args: unknown[]) => {
    if (typeof handler === "function") {
      if (ms === 50 && holding) {
        held.push(() => handler(...args));
        return 0;
      }
      if (ms === 20_000) return realTimeout(handler, 300, ...args);
    }
    return realTimeout(handler, ms, ...args);
  }) as typeof window.setTimeout;
}

const hold = (page: Page, on: boolean) => page.evaluate((value) => (window as unknown as { holdMock: (on: boolean) => void }).holdMock(value), on);

test.beforeEach(async ({ page }) => {
  await page.addInitScript(holdMockReplies);
});

test("a hung planner says so, Start Over stays open, and the late reply is dropped", async ({ page }) => {
  await page.goto("/officer");
  await expect(page.getByText("Try a Payout")).toBeVisible();
  await hold(page, true);
  await page.getByLabel("Message").fill("Pay October's aid for Ipoh.");
  await page.keyboard.press("Enter");

  await expect(page.getByTestId("still-waiting")).toHaveText("Still waiting on the planner. You can keep waiting or Start Over.");
  // Read-only, not disabled: the box keeps its focus while the planner works
  await expect(page.getByLabel("Message")).toBeFocused();
  await expect(page.getByLabel("Message")).toHaveAttribute("readonly", "");
  await page.getByRole("button", { name: "Start Over" }).click();
  await expect(page.getByTestId("officer-message")).toHaveCount(0);

  // The old session's answer finally arrives, and nothing of it shows
  await hold(page, false);
  await page.waitForTimeout(300);
  await expect(page.getByTestId("agent-message")).toHaveCount(0);
  await expect(page.getByTestId("clarification")).toHaveCount(0);
  await expect(page.getByTestId("busy-line")).toHaveCount(0);

  // The new session works as usual
  await page.getByRole("button", { name: "Pay household ZKT-H14 this month." }).click();
  await expect(page.getByTestId("chat-log").getByTestId("plan-card")).toHaveCount(1);
});

test("a hung confirm can be left: Start Over asks first, and the batch's late result does not show", async ({ page }) => {
  await page.goto("/officer");
  const chat = page.getByTestId("chat-log");
  await page.getByRole("button", { name: "Pay household ZKT-H14 this month." }).click();
  await expect(chat.getByTestId("plan-card")).toHaveCount(1);

  await hold(page, true);
  await chat.getByRole("button", { name: "Confirm 1 Payout" }).click();
  await expect(page.getByTestId("still-waiting")).toHaveText("Still waiting on the checks and the vault. You can keep waiting or Start Over.");
  await page.getByRole("button", { name: "Start Over" }).first().click();
  const ask = page.getByTestId("start-over-confirm");
  await expect(ask).toContainText("The vault may still pay this batch. Start over anyway? Its results will not show here.");
  await ask.getByRole("button", { name: "Start Over" }).click();
  await expect(chat.getByTestId("plan-card")).toHaveCount(0);

  await hold(page, false);
  await page.waitForTimeout(300);
  await expect(chat.getByTestId("payout-result")).toHaveCount(0);
  await expect(page.getByText("Try a Payout")).toBeVisible();
});

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
  await expect(result).toContainText("Paid (mock; signed by 0x");
  await expect(result).toContainText("(mock)");
  // The signed record keeps its summary beside the hash; a paid one carries no refusal line
  await expect(result).toContainText("Pay 1,200.00 USDC from the Flood Relief Fund");
  await expect(result.getByTestId("sign-note")).toHaveCount(0);
  await expect(page.getByTestId("pending-payout")).toHaveCount(0);
  await expect(page.getByText("Nothing is waiting for a trustee.")).toBeVisible();
  await page.getByRole("link", { name: "Open the Officer Desk" }).click();
  await expect(page).toHaveURL(/\/officer$/);
});

test("the wallet panel offers MetaMask when no wallet is connected", async ({ page }) => {
  await page.goto("/trustee");
  await expect(page.getByTestId("wallet-panel")).toContainText("Connect the trustee wallet");
});

const WALLET = "0x2222222222222222222222222222222222222222";

/** A stand-in for MetaMask: it connects on Base Sepolia, and the trustee cancels every signature request. */
function fakeMetaMask({ account, refuseConnect }: { account: string; refuseConnect: boolean }) {
  const listeners: Record<string, ((...args: unknown[]) => void)[]> = {};
  const cancelled = (what: string) => Object.assign(new Error(`MetaMask: User rejected the ${what}.`), { code: 4001 });
  (window as unknown as { ethereum: unknown }).ethereum = {
    isMetaMask: true,
    async request({ method }: { method: string }) {
      if (refuseConnect && (method === "wallet_requestPermissions" || method === "eth_requestAccounts")) throw cancelled("request");
      if (method === "eth_requestAccounts" || method === "eth_accounts") return [account];
      if (method === "eth_chainId") return "0x14a34";
      if (method === "wallet_requestPermissions") return [{ parentCapability: "eth_accounts", caveats: [{ type: "restrictReturnedAccounts", value: [account] }] }];
      if (method === "eth_signTypedData_v4") {
        throw Object.assign(new Error("MetaMask Tx Signature: User denied message signature."), { code: 4001 });
      }
      return null;
    },
    on(event: string, fn: (...args: unknown[]) => void) {
      (listeners[event] ??= []).push(fn);
    },
    removeListener(event: string, fn: (...args: unknown[]) => void) {
      listeners[event] = (listeners[event] ?? []).filter((f) => f !== fn);
    },
  };
}

test("a cancelled MetaMask connection says so in one sentence", async ({ page }) => {
  await page.addInitScript(fakeMetaMask, { account: WALLET, refuseConnect: true });
  await page.goto("/trustee");
  await page.getByRole("button", { name: "Connect MetaMask" }).click();
  await expect(page.getByTestId("wallet-panel")).toContainText("You cancelled in MetaMask, so the wallet is not connected.");
  await expect(page.getByTestId("wallet-panel")).not.toContainText("Version:");
});

test("a cancelled MetaMask signature says so in one sentence, and the payout still waits", async ({ page }) => {
  await page.addInitScript(fakeMetaMask, { account: WALLET, refuseConnect: false });
  await page.goto("/trustee");
  await page.getByRole("button", { name: "Connect MetaMask" }).click();
  await expect(page.getByTestId("wallet-panel")).toContainText("0x222222...2222");
  const card = page.getByTestId("pending-payout");
  await card.getByRole("button", { name: "Sign in MetaMask" }).click();
  await expect(card.getByRole("alert")).toHaveText("You cancelled in MetaMask. Nothing was signed; this payout still waits here.");
  await expect(card).not.toContainText("Request Arguments");
  await expect(card).not.toContainText("User denied");
  await expect(page.getByTestId("pending-payout")).toHaveCount(1);
  await expect(page.getByTestId("signed-list")).toHaveCount(0);
});

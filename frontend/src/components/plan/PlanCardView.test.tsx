import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { EMERGENCY_GRANT, ZAKAT_OCTOBER } from "@/api/mockData";

import { PlanCardView } from "./PlanCardView";

const render = (props: Partial<Parameters<typeof PlanCardView>[0]> = {}) =>
  renderToStaticMarkup(<PlanCardView card={ZAKAT_OCTOBER} active busy={false} onConfirm={() => {}} {...props} />);

/** The button's text, without the markup of its icon. */
function confirmLabel(html: string): string | undefined {
  const button = /<button[^>]*>(.*?)<\/button>/.exec(html)?.[1];
  return button?.replace(/<[^>]+>/g, "");
}

describe("the plan card", () => {
  it("puts the count and the total on the Confirm button", () => {
    expect(confirmLabel(render())).toBe("Confirm 12 Payouts · 1,810.00 USDC");
  });

  it("says Payout, singular, for one", () => {
    expect(confirmLabel(render({ card: EMERGENCY_GRANT }))).toBe("Confirm 1 Payout · 1,200.00 USDC");
    expect(render({ card: EMERGENCY_GRANT })).toContain("1 household<");
  });

  it("shows no Confirm button once inactive, and marks a replaced plan", () => {
    const replaced = render({ active: false, replaced: true });
    expect(replaced).not.toContain("<button");
    expect(replaced).toContain("Replaced. Confirm the newest plan below.");
    expect(render({ active: false })).not.toContain("Replaced.");
  });

  it("keeps a short wallet hash beside the beneficiary for a narrow screen", () => {
    const wallet = ZAKAT_OCTOBER.items[0].wallet;
    expect(render()).toContain(`${wallet.slice(0, 6)}...${wallet.slice(-4)}`);
  });
});

import { describe, expect, it } from "vitest";

import { signedOutcome } from "./PendingPayoutCard";

describe("a trustee's signed payout", () => {
  it("is a success only when the vault paid it", () => {
    expect(signedOutcome("paid")).toEqual({ variant: "success", note: null });
    expect(signedOutcome("paid (mock; signed by 0xabc)")).toEqual({ variant: "success", note: null });
  });

  it("says the vault refused a reverted or rejected payout, and that nothing was sent", () => {
    for (const status of ["reverted", "rejected", "Reverted (NotAllowlisted)"]) {
      expect(signedOutcome(status)).toEqual({ variant: "danger", note: "The vault refused this payout. Nothing was sent." });
    }
  });

  it("does not call a queued payout refused: the chain did not answer", () => {
    const queued = signedOutcome("queued");
    expect(queued.variant).toBe("muted");
    expect(queued.note).toMatch(/fail-closed queue\. Nothing was sent yet\.$/);
    expect(signedOutcome("something else")).toEqual({ variant: "muted", note: null });
  });
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { PayoutResult, Verdict, VerdictValue, Verdicts } from "@/api";
import { IdentityProvider } from "@/session/IdentityContext";

import { PayoutResults, QueuedNote, summarise, whoStopped } from "./PayoutResults";

function verdict(value: VerdictValue): Verdict {
  return { verdict: value, reasons: [], input_hash: "0x00", model: "m", lineage: "l", signed: value === "APPROVE" };
}

function verdicts(planner: VerdictValue, auditor: VerdictValue, sentinel: VerdictValue): Verdicts {
  return { planner: verdict(planner), auditor: verdict(auditor), sentinel: verdict(sentinel) };
}

function result(status: PayoutResult["status"], v: Verdicts, ref = "ZKT-H01"): PayoutResult {
  return { proposal_id: `0x${ref}`, household_ref: ref, amount_usdc: 150, status, verdicts: v, reasons: [] };
}

function withProviders(node: ReactNode): string {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return renderToStaticMarkup(
    <QueryClientProvider client={client}>
      <IdentityProvider>
        <MemoryRouter>{node}</MemoryRouter>
      </IdentityProvider>
    </QueryClientProvider>,
  );
}

describe("the queued note", () => {
  it("names the checker that did not answer", () => {
    const html = renderToStaticMarkup(<QueuedNote verdicts={verdicts("APPROVE", "UNAVAILABLE", "APPROVE")} />);
    expect(html).toContain("The auditor did not answer in time");
  });

  it("names two down checkers with a lower-case second name", () => {
    const html = renderToStaticMarkup(<QueuedNote verdicts={verdicts("APPROVE", "UNAVAILABLE", "UNAVAILABLE")} />);
    expect(html).toContain("The auditor and the sentinel did not answer in time");
  });

  it("falls back to a checker when no verdict says which", () => {
    expect(renderToStaticMarkup(<QueuedNote verdicts={verdicts("APPROVE", "APPROVE", "APPROVE")} />)).toContain("A checker did not answer");
  });
});

describe("the results summary", () => {
  const paid = result("paid", verdicts("APPROVE", "APPROVE", "APPROVE"), "ZKT-H01");
  const waiting = result("elevated_pending", verdicts("APPROVE", "APPROVE", "APPROVE"), "ZKT-H02");
  const rejected = result("rejected", verdicts("APPROVE", "REJECT", "REJECT"), "ZKT-H03");
  const reverted = result("reverted", verdicts("APPROVE", "APPROVE", "APPROVE"), "ZKT-H04");

  it("counts statuses with the badges' own labels", () => {
    expect(summarise([paid, waiting])).toBe("2 payouts: 1 Paid, 1 Waiting for a Trustee.");
    expect(summarise([paid])).toBe("1 payout: 1 Paid.");
  });

  it("says who stopped a payout: the signers that rejected it, or the vault that reverted it", () => {
    expect(whoStopped([paid, waiting])).toBeNull();
    expect(whoStopped([rejected])).toBe("Stopped by the auditor and the sentinel.");
    expect(whoStopped([reverted])).toBe("Stopped by the vault.");
    expect(whoStopped([rejected, reverted])).toBe("Stopped by the auditor, the sentinel and the vault.");
  });

  it("points to the Trustee page when a payout waits for one, and to the Red Team page after a refusal", () => {
    const held = withProviders(<PayoutResults results={[paid, waiting]} />);
    expect(held).toContain("The vault held 1 for a trustee to co-sign.");
    expect(held).toMatch(/href="\/trustee"[^>]*>Open the Trustee Page/);
    const refused = withProviders(<PayoutResults results={[rejected]} />);
    expect(refused).toContain("Stopped by the auditor and the sentinel.");
    expect(refused).toMatch(/href="\/redteam"[^>]*>See the Red Team/);
    expect(withProviders(<PayoutResults results={[paid]} />)).not.toContain("What just happened");
  });
});

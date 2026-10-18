import { Link } from "react-router";

import type { PayoutResult } from "@/api";
import { MockBadge, StatusBadge, TxLink } from "@/components/common";
import { Card } from "@/components/ui/card";
import { formatUsdc } from "@/lib/usdc";

import { VerdictCard } from "./VerdictCard";

/** One row per payout after Confirm, with the three signers' verdicts (task D2). */
export function PayoutResults({ results }: { results: PayoutResult[] }) {
  return (
    <div className="space-y-3" data-testid="payout-results">
      <div className="flex items-center gap-2 text-sm text-muted">
        {summarise(results)}
        <MockBadge />
      </div>
      {results.map((r) => (
        <Card key={r.proposal_id} data-testid="payout-result" className="p-3">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <span className="font-medium">{r.household_ref}</span>
            <span className="tabular-nums">{formatUsdc(r.amount_usdc)} USDC</span>
            <StatusBadge status={r.status} />
            <span className="text-sm">
              <TxLink hash={r.tx_hash} url={r.explorer_url} />
            </span>
            {r.status === "elevated_pending" && (
              <Link to="/trustee" className="text-sm text-teal hover:underline">
                Open the trustee page
              </Link>
            )}
          </div>
          <div className="mt-3 grid gap-2 md:grid-cols-3">
            <VerdictCard signer="planner" verdict={r.verdicts.planner} />
            <VerdictCard signer="auditor" verdict={r.verdicts.auditor} />
            <VerdictCard signer="sentinel" verdict={r.verdicts.sentinel} />
          </div>
          {r.reasons.length > 0 && <p className="mt-2 text-xs text-muted">{r.reasons.join(" ")}</p>}
        </Card>
      ))}
    </div>
  );
}

function summarise(results: PayoutResult[]): string {
  const counts = new Map<string, number>();
  for (const r of results) counts.set(r.status, (counts.get(r.status) ?? 0) + 1);
  const parts = [...counts.entries()].map(([status, n]) => `${n} ${status.replace("_", " ")}`);
  return `${results.length} payouts: ${parts.join(", ")}.`;
}

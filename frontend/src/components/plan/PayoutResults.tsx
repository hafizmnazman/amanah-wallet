import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { api, type PayoutResult } from "@/api";
import { MockBadge, StatusBadge, TxLink } from "@/components/common";
import { Card } from "@/components/ui/card";
import { formatUsdc } from "@/lib/usdc";
import { useIdentity } from "@/session/IdentityContext";

import { VerdictCard } from "./VerdictCard";

/** Statuses that can still change: a trustee may sign, or the queue may retry. */
const OPEN = new Set(["elevated_pending", "queued"]);
const POLL_MS = 5_000;

/** One row per payout after Confirm, with the three signers' verdicts (task D2). */
export function PayoutResults({ results }: { results: PayoutResult[] }) {
  return (
    <div className="space-y-3" data-testid="payout-results">
      <div className="flex items-center gap-2 text-sm text-muted">
        {summarise(results)}
        <MockBadge />
      </div>
      {results.map((r) => (
        <ResultRow key={r.proposal_id} initial={r} />
      ))}
    </div>
  );
}

/** A waiting row polls GET /api/agent/payouts/{proposal_id}, so it turns to paid once a trustee signs. */
function ResultRow({ initial }: { initial: PayoutResult }) {
  const { identity } = useIdentity();
  const latest = useQuery({
    queryKey: ["payout", initial.proposal_id, identity.role],
    queryFn: () => api.payoutStatus(identity, initial.proposal_id),
    enabled: OPEN.has(initial.status),
    refetchInterval: (query) => (query.state.data && !OPEN.has(query.state.data.status) ? false : POLL_MS),
    retry: false,
  });
  const r = latest.data ?? initial;
  return (
    <Card data-testid="payout-result" className="p-3">
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
  );
}

function summarise(results: PayoutResult[]): string {
  const counts = new Map<string, number>();
  for (const r of results) counts.set(r.status, (counts.get(r.status) ?? 0) + 1);
  const parts = [...counts.entries()].map(([status, n]) => `${n} ${status.replace("_", " ")}`);
  return `${results.length} payouts: ${parts.join(", ")}.`;
}

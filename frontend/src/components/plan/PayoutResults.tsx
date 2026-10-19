import { useQuery } from "@tanstack/react-query";
import { ChevronDown, KeyRound } from "lucide-react";
import { Link } from "react-router";

import { api, type PayoutResult } from "@/api";
import { MockBadge, StatusBadge, TxLink } from "@/components/common";
import { KancilSays } from "@/components/mascot/Kancil";
import { SIGNER_ORDER, SignerChip } from "@/components/signers";
import { formatUsdc } from "@/lib/usdc";
import { cn } from "@/lib/utils";
import { useIdentity } from "@/session/IdentityContext";

import { VerdictCard } from "./VerdictCard";

/** Statuses that can still change: a trustee may sign, or the queue may retry. */
const OPEN = new Set(["elevated_pending", "queued"]);
const POLL_MS = 5_000;

/** One row per payout after Confirm, with the three signers' verdicts (task D2). */
export function PayoutResults({ results }: { results: PayoutResult[] }) {
  const paid = results.filter((r) => r.status === "paid").length;
  const stopped = results.filter((r) => r.status === "rejected" || r.status === "reverted").length;
  const pose = stopped ? "alert" : paid === results.length ? "happy" : "thinking";
  return (
    <div className="space-y-3" data-testid="payout-results">
      <KancilSays pose={pose} prop={paid === results.length ? "shield" : null} size={64} tone={stopped ? "alert" : paid === results.length ? "good" : "default"}>
        <span className="font-extrabold">{summarise(results)}</span>{" "}
        {paid === results.length
          ? "Every one carried three signatures from three different kinds of signer."
          : stopped
            ? "The checks refused what they should: no money moved for those."
            : "Some wait for a person, as the vault asks."}
        <MockBadge className="ml-2" />
      </KancilSays>
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
    <div data-testid="payout-result" className={cn("chunky p-4 animate-rise", r.status === "paid" ? "" : "border-gold/50")}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="text-base font-black">{r.household_ref}</span>
        <span className="font-extrabold tabular-nums">{formatUsdc(r.amount_usdc)} USDC</span>
        <StatusBadge status={r.status} />
        <span className="text-sm">
          <TxLink hash={r.tx_hash} url={r.explorer_url} />
        </span>
        {r.status === "elevated_pending" && (
          <Link to="/trustee" className="inline-flex items-center gap-1 text-sm font-extrabold text-sky-dark hover:underline">
            <KeyRound className="h-4 w-4" aria-hidden />
            Open the Trustee Page
          </Link>
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {SIGNER_ORDER.map((s) => (
          <SignerChip key={s} signer={s} verdict={r.verdicts[s].verdict} signed={r.verdicts[s].signed} />
        ))}
      </div>
      <details className="group mt-3" open={r.status !== "paid"}>
        <summary className="inline-flex cursor-pointer list-none items-center gap-1 text-xs font-extrabold uppercase tracking-wide text-muted hover:text-ink">
          <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" aria-hidden />
          Why Each Signer Decided
        </summary>
        <div className="mt-2 grid gap-2 md:grid-cols-3">
          <VerdictCard signer="planner" verdict={r.verdicts.planner} />
          <VerdictCard signer="auditor" verdict={r.verdicts.auditor} />
          <VerdictCard signer="sentinel" verdict={r.verdicts.sentinel} />
        </div>
      </details>
      {r.reasons.length > 0 && <p className="mt-2 text-xs text-muted">{r.reasons.join(" ")}</p>}
    </div>
  );
}

function summarise(results: PayoutResult[]): string {
  const counts = new Map<string, number>();
  for (const r of results) counts.set(r.status, (counts.get(r.status) ?? 0) + 1);
  const parts = [...counts.entries()].map(([status, n]) => `${n} ${status.replace("_", " ")}`);
  return `${results.length} payouts: ${parts.join(", ")}.`;
}

import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Hourglass, KeyRound } from "lucide-react";
import { Link } from "react-router";

import { api, type PayoutResult } from "@/api";
import { MockBadge, StatusBadge, statusLabel, TxLink } from "@/components/common";
import { KancilSays } from "@/components/mascot/Kancil";
import { SIGNER_ORDER, SignerChip } from "@/components/signers";
import { explainReason } from "@/lib/rules";
import { formatUsdc } from "@/lib/usdc";
import { capitalise, cn, listJoin } from "@/lib/utils";
import { useIdentity } from "@/session/IdentityContext";

import { VerdictCard } from "./VerdictCard";
import { WhatHappened } from "./WhatHappened";

/** Statuses that can still change: a trustee may sign, or the queue may retry. */
const OPEN = new Set(["elevated_pending", "queued"]);
const POLL_MS = 5_000;

/** One row per payout after Confirm, with the three signers' verdicts (task D2). */
export function PayoutResults({ results }: { results: PayoutResult[] }) {
  const paid = results.filter((r) => r.status === "paid").length;
  const stopped = results.filter((r) => r.status === "rejected" || r.status === "reverted").length;
  const queued = results.some((r) => r.status === "queued");
  const pose = stopped ? "alert" : paid === results.length ? "happy" : "thinking";
  return (
    <div className="space-y-3" data-testid="payout-results">
      <KancilSays pose={pose} prop={paid === results.length ? "shield" : null} size={64} tone={stopped ? "alert" : paid === results.length ? "good" : "default"}>
        <span className="font-extrabold">{summarise(results)}</span>{" "}
        {paid === results.length
          ? "Every one carried three signatures from three different kinds of signer."
          : stopped
            ? "The checks refused what they should: no money moved for those."
            : queued
              ? "A checker could not answer, so those wait in the queue and retry: nothing goes out with fewer checks."
              : "Some wait for a person, as the vault asks."}
        <MockBadge className="ml-2" />
      </KancilSays>
      <NextStep results={results} />
      {results.map((r) => (
        <ResultRow key={r.proposal_id} initial={r} />
      ))}
    </div>
  );
}

const CHECKER_NAMES = { planner: "the planner", auditor: "the auditor", sentinel: "the sentinel" } as const;

/**
 * Who stopped the payouts that did not go out: the signers that rejected them, or the vault when it reverted
 * one. Null when nothing was stopped.
 */
export function whoStopped(results: PayoutResult[]): string | null {
  const who = new Set<string>();
  for (const r of results) {
    if (r.status === "reverted") who.add("the vault");
    if (r.status !== "rejected") continue;
    const rejecting = SIGNER_ORDER.filter((s) => r.verdicts[s].verdict === "REJECT");
    if (rejecting.length === 0) who.add("the checks");
    for (const s of rejecting) who.add(CHECKER_NAMES[s]);
  }
  if (who.size === 0) return null;
  const order = [...Object.values(CHECKER_NAMES), "the checks", "the vault"];
  return `Stopped by ${listJoin(order.filter((name) => who.has(name)))}.`;
}

/** The line under the summary: who stopped what, and the page to open next. */
function NextStep({ results }: { results: PayoutResult[] }) {
  const stopped = whoStopped(results);
  const waiting = results.filter((r) => r.status === "elevated_pending").length;
  if (!stopped && waiting === 0) return null;
  const held = waiting > 0 ? `The vault held ${waiting} for a trustee to co-sign.` : "";
  return waiting > 0 ? (
    <WhatHappened to="/trustee" label="Open the Trustee Page">
      {[stopped, held].filter(Boolean).join(" ")}
    </WhatHappened>
  ) : (
    <WhatHappened to="/redteam" label="See the Red Team">
      {stopped}
    </WhatHappened>
  );
}

/** A payout that neither paid nor failed is the officer's most worrying moment: say what happened and what comes next. */
export function QueuedNote({ verdicts }: { verdicts: PayoutResult["verdicts"] }) {
  const down = SIGNER_ORDER.filter((s) => verdicts[s].verdict === "UNAVAILABLE").map((s) => CHECKER_NAMES[s]);
  const who = down.length ? capitalise(listJoin(down)) : "A checker";
  return (
    <div data-testid="queued-note" className="mt-3 flex items-start gap-2.5 rounded-2xl border-2 border-sky/30 bg-sky-light px-3 py-2.5 text-sm text-ink">
      <Hourglass className="mt-0.5 h-4 w-4 shrink-0 text-sky-dark" aria-hidden />
      <p>
        <span className="font-extrabold">Nothing was sent.</span> {who} did not answer in time, so this payout waits in
        the fail-closed queue and is tried again every minute. A trustee has been alerted. You can leave this page: it
        pays once all three checks are in.
      </p>
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
      {r.status === "queued" && <QueuedNote verdicts={r.verdicts} />}
      <div className="mt-3 flex flex-wrap gap-2">
        {SIGNER_ORDER.map((s) => (
          <SignerChip key={s} signer={s} verdict={r.verdicts[s].verdict} signed={r.verdicts[s].signed} />
        ))}
      </div>
      <details className="group mt-3" open={r.status !== "paid"}>
        <summary className="inline-flex cursor-pointer list-none items-center gap-1 py-1 text-xs font-extrabold uppercase tracking-wide text-muted hover:text-ink">
          <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" aria-hidden />
          Why Each Signer Decided
        </summary>
        <div className="mt-2 grid gap-2 md:grid-cols-3">
          <VerdictCard signer="planner" verdict={r.verdicts.planner} />
          <VerdictCard signer="auditor" verdict={r.verdicts.auditor} />
          <VerdictCard signer="sentinel" verdict={r.verdicts.sentinel} />
        </div>
      </details>
      {r.reasons.length > 0 && <p className="mt-2 text-xs text-muted">{r.reasons.map((x) => explainReason(x).text).join(" ")}</p>}
    </div>
  );
}

/** "2 payouts: 1 Paid, 1 Waiting for a Trustee.", with the status badges' own labels. */
export function summarise(results: PayoutResult[]): string {
  const counts = new Map<string, number>();
  for (const r of results) counts.set(r.status, (counts.get(r.status) ?? 0) + 1);
  const parts = [...counts.entries()].map(([status, n]) => `${n} ${statusLabel(status)}`);
  return `${results.length} ${results.length === 1 ? "payout" : "payouts"}: ${parts.join(", ")}.`;
}

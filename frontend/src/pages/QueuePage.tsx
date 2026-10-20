import { useQuery } from "@tanstack/react-query";
import { BellRing, Calculator, Coins, FileSearch, Unplug, type LucideIcon } from "lucide-react";

import { api } from "@/api";
import { EmptyState, ErrorNote, LoadingLine, MockBadge, PageTitle, RoleHint } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { shortHex } from "@/lib/utils";
import { useIdentity } from "@/session/IdentityContext";

const MISSING: Record<string, { label: string; icon: LucideIcon; tone: string }> = {
  auditor: { label: "Auditor Unavailable", icon: FileSearch, tone: "border-auditor/40 bg-auditor-light text-auditor-dark" },
  sentinel: { label: "Sentinel Unavailable", icon: Calculator, tone: "border-sentinel/40 bg-sentinel-light text-sentinel-dark" },
  chain: { label: "Chain Unreachable", icon: Unplug, tone: "border-sky/40 bg-sky-light text-sky-dark" },
  funds: { label: "Vault Short of Funds", icon: Coins, tone: "border-kancil/40 bg-kancil-light text-kancil-dark" },
};

const ALERT_KINDS: Record<string, { label: string; variant: "teal" | "success" | "danger" | "warning" | "default" }> = {
  queued: { label: "Queued", variant: "teal" },
  drained: { label: "Drained", variant: "success" },
  refused: { label: "Refused on Retry", variant: "danger" },
  trustee_needed: { label: "Trustee Needed", variant: "warning" },
  plan_ready: { label: "Plan Ready", variant: "default" },
};

/** A stored time as Malaysia reads it, "20 Oct, 09:31"; a value that is not a date is shown as it came. */
export function malaysiaTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kuala_Lumpur" });
}

/** Payouts held by the fail-closed queue, for trustees (task D4), and the alerts the store wrote for them. */
export function QueuePage() {
  const { identity } = useIdentity();
  const queue = useQuery({
    queryKey: ["queue", identity.role],
    queryFn: () => api.queue(identity),
    refetchInterval: 30_000,
  });
  const alerts = useQuery({
    queryKey: ["alerts", identity.role],
    queryFn: () => api.alerts(identity),
    refetchInterval: 30_000,
  });
  const items = queue.data?.items ?? [];
  const newestFirst = [...(alerts.data?.items ?? [])].reverse();
  // GET /api/alerts admits trustees and guardians; for other roles the hint says why the page is empty
  const mayReadAlerts = identity.role === "trustee" || identity.role === "guardian";

  return (
    <div className="space-y-5">
      <PageTitle title="Fail-Closed Queue" badges={<MockBadge />}>
        When a signer or the chain is unavailable, payouts wait here instead of going out with fewer checks, and a trustee
        is alerted. They retry every 60 seconds.
      </PageTitle>
      <RoleHint expected={identity.role === "trustee"} label="trustees" role="trustee" />
      {queue.error && identity.role === "trustee" && <ErrorNote error={queue.error} />}
      {queue.isLoading && <LoadingLine />}
      {!queue.isLoading && items.length === 0 && !queue.error && (
        <EmptyState pose="sleep">
          The queue is empty, so there is nothing to do. A payout lands here only while a checker or the chain is
          unavailable, and it retries on its own.
        </EmptyState>
      )}
      <ul className="space-y-3">
        {items.map((item) => {
          const m = MISSING[item.missing] ?? { label: item.missing, icon: Unplug, tone: "border-border bg-surface-2 text-muted" };
          const Icon = m.icon;
          return (
            <li key={item.proposal_id} data-testid="queue-item" className="chunky flex items-start gap-3 p-4 text-sm">
              <span className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border-2 ${m.tone}`}>
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="teal">{m.label}</Badge>
                  <span className="hash text-xs text-muted">{shortHex(item.proposal_id)}</span>
                  <span className="text-xs font-bold text-muted">queued {malaysiaTime(item.queued_at)}</span>
                </div>
                <p className="font-bold">{item.reason}</p>
              </div>
            </li>
          );
        })}
      </ul>

      <section className="space-y-3" aria-label="Alerts" data-testid="alerts">
        <h2 className="flex items-center gap-2 text-lg font-black">
          <BellRing className="h-5 w-5 text-gold-dark" aria-hidden />
          Alerts
        </h2>
        {alerts.error && mayReadAlerts && <ErrorNote error={alerts.error} />}
        {alerts.isLoading && !queue.isLoading && <LoadingLine />}
        {!alerts.isLoading && !alerts.error && newestFirst.length === 0 && (
          <EmptyState pose="sleep">
            No alerts yet. One is written when a payout is queued, drains or is refused on retry, when a payout needs a
            trustee, and when the books&apos; scheduled batch is drafted.
          </EmptyState>
        )}
        {newestFirst.length > 0 && (
          <ol className="chunky divide-y divide-border text-sm">
            {newestFirst.map((alert) => {
              const kind = ALERT_KINDS[alert.kind] ?? { label: alert.kind, variant: "default" as const };
              return (
                <li key={alert.id} data-testid="alert" className="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-4 py-3">
                  <time dateTime={alert.created_at} className="w-28 shrink-0 text-xs font-bold tabular-nums text-muted">
                    {malaysiaTime(alert.created_at)}
                  </time>
                  <Badge variant={kind.variant}>{kind.label}</Badge>
                  <p className="min-w-0 flex-1 basis-60 font-bold wrap-anywhere">{alert.message}</p>
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </div>
  );
}

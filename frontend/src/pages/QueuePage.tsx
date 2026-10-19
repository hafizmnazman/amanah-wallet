import { useQuery } from "@tanstack/react-query";
import { Calculator, Coins, FileSearch, Unplug, type LucideIcon } from "lucide-react";

import { api } from "@/api";
import { EmptyState, ErrorNote, MockBadge, PageTitle, RoleHint } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { shortHex } from "@/lib/utils";
import { useIdentity } from "@/session/IdentityContext";

const MISSING: Record<string, { label: string; icon: LucideIcon; tone: string }> = {
  auditor: { label: "Auditor Unavailable", icon: FileSearch, tone: "border-auditor/40 bg-auditor-light text-auditor-dark" },
  sentinel: { label: "Sentinel Unavailable", icon: Calculator, tone: "border-sentinel/40 bg-sentinel-light text-sentinel-dark" },
  chain: { label: "Chain Unreachable", icon: Unplug, tone: "border-sky/40 bg-sky-light text-sky-dark" },
  funds: { label: "Vault Short of Funds", icon: Coins, tone: "border-kancil/40 bg-kancil-light text-kancil-dark" },
};

/** Payouts held by the fail-closed queue, for trustees (task D4). */
export function QueuePage() {
  const { identity } = useIdentity();
  const queue = useQuery({
    queryKey: ["queue", identity.role],
    queryFn: () => api.queue(identity),
    refetchInterval: 30_000,
  });
  const items = queue.data?.items ?? [];

  return (
    <div className="space-y-5">
      <PageTitle title="Fail-Closed Queue" badges={<MockBadge />}>
        When a signer or the chain is unavailable, payouts wait here instead of going out with fewer checks, and a trustee
        is alerted. They retry every 60 seconds.
      </PageTitle>
      <RoleHint expected={identity.role === "trustee"} label="trustees" role="trustee" />
      {queue.error && identity.role === "trustee" && <ErrorNote error={queue.error} />}
      {!queue.isLoading && items.length === 0 && !queue.error && <EmptyState pose="sleep">The queue is empty.</EmptyState>}
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
                  <span className="text-xs font-bold text-muted">queued {item.queued_at}</span>
                </div>
                <p className="font-bold">{item.reason}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

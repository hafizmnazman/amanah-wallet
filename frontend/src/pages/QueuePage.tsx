import { useQuery } from "@tanstack/react-query";

import { api } from "@/api";
import { ErrorNote, MockBadge, RoleHint } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { shortHex } from "@/lib/utils";
import { useIdentity } from "@/session/IdentityContext";

const MISSING: Record<string, string> = {
  auditor: "Auditor unavailable",
  sentinel: "Sentinel unavailable",
  chain: "Chain unreachable",
  funds: "Vault short of funds",
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
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-xl font-semibold">Fail-closed queue</h1>
        <MockBadge />
      </div>
      <RoleHint expected={identity.role === "trustee"} label="trustees" />
      <p className="text-sm text-muted">
        When a signer or the chain is unavailable, payouts wait here instead of going out with fewer checks. They retry
        every 60 seconds.
      </p>
      {queue.error && <ErrorNote error={queue.error} />}
      {!queue.isLoading && items.length === 0 && !queue.error && (
        <p className="rounded-md border border-dashed border-border p-4 text-sm text-muted">The queue is empty.</p>
      )}
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item.proposal_id} data-testid="queue-item" className="rounded-lg border border-border bg-surface p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="teal">{MISSING[item.missing] ?? item.missing}</Badge>
              <span className="hash text-xs text-muted">{shortHex(item.proposal_id)}</span>
              <span className="text-xs text-muted">queued {item.queued_at}</span>
            </div>
            <p className="mt-1">{item.reason}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

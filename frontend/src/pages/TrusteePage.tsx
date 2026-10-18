import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api";
import { ErrorNote, MockBadge, RoleHint, TxLink } from "@/components/common";
import { PendingPayoutCard, type SignedPayout } from "@/components/trustee/PendingPayoutCard";
import { WalletPanel } from "@/components/trustee/WalletPanel";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useIdentity } from "@/session/IdentityContext";

/** Elevated payouts waiting for a trustee co-signature (task D3). */
export function TrusteePage() {
  const { identity } = useIdentity();
  const [signed, setSigned] = useState<SignedPayout[]>([]);
  const pending = useQuery({
    queryKey: ["pending", identity.role],
    queryFn: () => api.pending(identity),
    refetchInterval: 15_000,
  });
  const items = pending.data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-xl font-semibold">Payouts waiting for a trustee</h1>
        <MockBadge />
      </div>
      <RoleHint expected={identity.role === "trustee"} label="trustees" />
      <p className="text-sm text-muted">
        Read the summary, then check it against the fields on the right. Your wallet shows exactly those fields. Sign only
        if they match.
      </p>
      <WalletPanel />
      {signed.length > 0 && (
        <Card className="p-3" data-testid="signed-list">
          <h2 className="mb-2 text-sm font-medium">Signed in this session</h2>
          <ul className="space-y-2 text-sm">
            {signed.map((s) => (
              <li key={s.proposalId} className="flex flex-wrap items-center gap-2" data-testid="sign-result">
                <Badge variant="success">{s.status}</Badge>
                <TxLink hash={s.txHash} />
                {s.signedBy && <span className="hash text-xs text-muted">signed by {s.signedBy}</span>}
              </li>
            ))}
          </ul>
        </Card>
      )}
      {pending.error && <ErrorNote error={pending.error} />}
      {pending.isLoading && <p className="text-sm text-muted">Loading pending payouts.</p>}
      {!pending.isLoading && items.length === 0 && !pending.error && (
        <p className="rounded-md border border-dashed border-border p-4 text-sm text-muted">Nothing is waiting for a trustee.</p>
      )}
      {items.map((item) => (
        <PendingPayoutCard key={item.proposal_id} item={item} onSigned={(s) => setSigned((list) => [s, ...list])} />
      ))}
    </div>
  );
}

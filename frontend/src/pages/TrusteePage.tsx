import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api";
import { EmptyState, ErrorNote, MockBadge, PageTitle, RoleHint, TxLink } from "@/components/common";
import { KancilSays } from "@/components/mascot/Kancil";
import { PendingPayoutCard, type SignedPayout } from "@/components/trustee/PendingPayoutCard";
import { WalletPanel } from "@/components/trustee/WalletPanel";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { capitalise } from "@/lib/utils";
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
    <div className="space-y-5">
      <PageTitle title="Payouts Waiting for a Trustee" badges={<MockBadge />}>
        The vault itself decides when a person must co-sign: above a programme&apos;s cap, past 80% of a day&apos;s budget, or
        while the security posture is raised.
      </PageTitle>
      <RoleHint expected={identity.role === "trustee"} label="trustees" role="trustee" />
      <KancilSays pose="thinking" size={60}>
        Read the summary, then check it against the fields on the right. Your wallet shows exactly those fields. Sign only
        if they match.
      </KancilSays>
      <WalletPanel />
      {signed.length > 0 && (
        <Card className="p-4" data-testid="signed-list">
          <h2 className="mb-2 text-sm font-black">Signed in This Session</h2>
          <ul className="space-y-2 text-sm">
            {signed.map((s) => (
              <li key={s.proposalId} className="flex flex-wrap items-center gap-2" data-testid="sign-result">
                <Badge variant="success">{capitalise(s.status)}</Badge>
                <TxLink hash={s.txHash} />
                {s.signedBy && <span className="hash text-xs text-muted">signed by {s.signedBy}</span>}
              </li>
            ))}
          </ul>
        </Card>
      )}
      {/* For another role, the hint above says why and offers the switch; the API's 403 would only repeat it */}
      {pending.error && identity.role === "trustee" && <ErrorNote error={pending.error} />}
      {pending.isLoading && <p className="text-sm font-bold text-muted">Loading pending payouts.</p>}
      {!pending.isLoading && items.length === 0 && !pending.error && (
        <EmptyState pose="sleep">Nothing is waiting for a trustee.</EmptyState>
      )}
      {items.map((item) => (
        <PendingPayoutCard key={item.proposal_id} item={item} onSigned={(s) => setSigned((list) => [s, ...list])} />
      ))}
    </div>
  );
}

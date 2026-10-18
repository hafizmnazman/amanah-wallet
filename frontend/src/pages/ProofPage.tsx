import { useQuery } from "@tanstack/react-query";

import { api } from "@/api";
import { ErrorNote, MockBadge, TxLink } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { useIdentity } from "@/session/IdentityContext";

/** The 16 scripted scenarios with their transactions, from evidence/transactions.csv (task D4). */
export function ProofPage() {
  const { identity } = useIdentity();
  const proof = useQuery({ queryKey: ["proof", identity.role], queryFn: () => api.proof(identity) });
  const rows = proof.data?.rows ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-xl font-semibold">On-chain proof</h1>
        <MockBadge />
      </div>
      <p className="text-sm text-muted">
        Every scripted scenario and the transaction it produced. Reverted rows are the contract refusing an attack.
      </p>
      {proof.error && <ErrorNote error={proof.error} />}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-surface text-left text-xs text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">#</th>
              <th className="px-3 py-2 font-medium">Scenario</th>
              <th className="px-3 py-2 font-medium">Expected</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Block</th>
              <th className="px-3 py-2 font-medium">Transaction</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.scenario}-${row.tx_hash}`} data-testid="proof-row" className="border-t border-border/60 align-top">
                <td className="px-3 py-2 tabular-nums">{row.scenario}</td>
                <td className="px-3 py-2">{row.description}</td>
                <td className="px-3 py-2 text-muted">{row.expected}</td>
                <td className="px-3 py-2">
                  <Badge variant={row.status === "success" ? "success" : row.status === "reverted" ? "danger" : "muted"}>
                    {row.status}
                  </Badge>
                </td>
                <td className="px-3 py-2 tabular-nums">{row.block}</td>
                <td className="px-3 py-2">
                  <TxLink hash={row.tx_hash} url={row.explorer_url} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

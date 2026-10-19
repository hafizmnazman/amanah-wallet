import { useQuery } from "@tanstack/react-query";
import { CircleCheck, Undo2 } from "lucide-react";

import { api } from "@/api";
import { ErrorNote, MockBadge, PageTitle, TxLink } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { useIdentity } from "@/session/IdentityContext";

/** The 16 scripted scenarios with their transactions, from evidence/transactions.csv (task D4). */
export function ProofPage() {
  const { identity } = useIdentity();
  const proof = useQuery({ queryKey: ["proof", identity.role], queryFn: () => api.proof(identity) });
  const rows = proof.data?.rows ?? [];
  const ok = rows.filter((r) => r.status === "success").length;
  const reverted = rows.filter((r) => r.status === "reverted").length;

  return (
    <div className="space-y-5">
      <PageTitle title="On-chain proof" badges={<MockBadge />}>
        Every scripted scenario and the transaction it produced. Reverted rows are the contract refusing an attack.
      </PageTitle>
      {rows.length > 0 && (
        <div className="flex flex-wrap gap-3">
          <div className="chunky flex items-center gap-2 px-4 py-2.5">
            <CircleCheck className="h-5 w-5 text-success" aria-hidden />
            <span className="text-xl font-black text-success">{ok}</span>
            <span className="text-sm font-bold text-muted">succeeded</span>
          </div>
          <div className="chunky flex items-center gap-2 px-4 py-2.5">
            <Undo2 className="h-5 w-5 text-danger" aria-hidden />
            <span className="text-xl font-black text-danger">{reverted}</span>
            <span className="text-sm font-bold text-muted">refused by the contract</span>
          </div>
        </div>
      )}
      {proof.error && <ErrorNote error={proof.error} />}
      <div className="chunky overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-surface-2 text-left text-[11px] font-extrabold uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">#</th>
              <th className="px-4 py-3">Scenario</th>
              <th className="px-4 py-3">Expected</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Block</th>
              <th className="px-4 py-3">Transaction</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.scenario}-${row.tx_hash}`} data-testid="proof-row" className="border-t-2 border-border/70 align-top">
                <td className="px-4 py-2.5 font-black tabular-nums">{row.scenario}</td>
                <td className="px-4 py-2.5 font-bold">{row.description}</td>
                <td className="px-4 py-2.5 text-muted">{row.expected}</td>
                <td className="px-4 py-2.5">
                  <Badge variant={row.status === "success" ? "success" : row.status === "reverted" ? "danger" : "muted"}>{row.status}</Badge>
                </td>
                <td className="px-4 py-2.5 tabular-nums text-muted">{row.block}</td>
                <td className="px-4 py-2.5">
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

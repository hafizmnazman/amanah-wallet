import { useQuery } from "@tanstack/react-query";
import { CircleCheck, Download, ExternalLink, Link2, ShieldCheck, Undo2 } from "lucide-react";
import { useMemo, useState } from "react";

import { api } from "@/api";
import { ErrorNote, MockBadge, PageTitle, TxLink } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import rawActionLog from "@/data/action-log.jsonl?raw";
import { actionLogCsv, parseActionLog, verifyActionLog, type ChainCheck } from "@/lib/actionLog";
import { BLOCKSCOUT, facts } from "@/lib/facts";
import { capitalise, shortHex } from "@/lib/utils";
import { useIdentity } from "@/session/IdentityContext";

function download(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

/**
 * The real action log of the 19 October Base Sepolia run, the same in mock mode: evidence/action-log.jsonl, copied
 * by scripts/export_ui_data.py. The browser recomputes every hash itself.
 */
function ActionLogCard() {
  const entries = useMemo(() => parseActionLog(rawActionLog), []);
  const [check, setCheck] = useState<ChainCheck | null>(null);
  const [checking, setChecking] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const head = entries.at(-1)?.hash ?? "";
  const anchorTx = facts.base_sepolia.log_head_anchor_tx;

  async function verify() {
    setChecking(true);
    setFailure(null);
    try {
      if (!globalThis.crypto?.subtle) throw new Error("This browser offers no SHA-256 here: open the page over https.");
      setCheck(await verifyActionLog(entries));
    } catch (error) {
      setFailure(error instanceof Error ? error.message : String(error));
    } finally {
      setChecking(false);
    }
  }

  return (
    <section className="chunky space-y-4 p-5" aria-label="The action log" data-testid="action-log">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-black">The Action Log, Hash-Chained</h2>
        <Badge variant="teal">Base Sepolia, 19 October</Badge>
      </div>
      <p className="max-w-3xl text-sm text-muted">
        This is the 19 October Base Sepolia run&apos;s own log, not mock data: {entries.length} entries, each one after the
        first carrying the SHA-256 of the entry before it, so an edit anywhere breaks every later link. The run anchored
        the last hash on chain. Your browser can recompute every link itself.
      </p>
      <dl className="grid gap-x-4 gap-y-1.5 text-sm sm:grid-cols-[auto_1fr]">
        <dt className="font-bold text-muted">Entries</dt>
        <dd className="font-extrabold tabular-nums" data-testid="action-log-count">
          {entries.length}
        </dd>
        <dt className="font-bold text-muted">Head Hash</dt>
        <dd className="hash text-ink" data-testid="action-log-head">
          {head}
        </dd>
        <dt className="font-bold text-muted">Anchored In</dt>
        <dd>
          <a
            className="hash inline-flex items-center gap-1 font-semibold text-sky-dark underline-offset-2 hover:underline"
            href={`${BLOCKSCOUT}/tx/${anchorTx}`}
            target="_blank"
            rel="noreferrer"
            data-testid="anchor-link"
          >
            {shortHex(anchorTx, 8, 6)}
            <ExternalLink className="h-3 w-3" aria-hidden />
          </a>{" "}
          <span className="text-xs text-muted">(anchorReport on Blockscout; its input carries the head hash)</span>
        </dd>
      </dl>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => void verify()} disabled={checking}>
          <ShieldCheck className="h-4 w-4" aria-hidden />
          Verify in Your Browser
        </Button>
        <Button size="sm" variant="secondary" onClick={() => download("action-log.jsonl", rawActionLog, "application/x-ndjson")}>
          <Download className="h-4 w-4" aria-hidden />
          Download JSONL
        </Button>
        <Button size="sm" variant="secondary" onClick={() => download("action-log.csv", actionLogCsv(entries), "text/csv")}>
          <Download className="h-4 w-4" aria-hidden />
          Download CSV
        </Button>
      </div>
      <div role="status" aria-live="polite">
        {checking && <p className="text-sm font-bold text-muted">Hashing {entries.length} entries...</p>}
        {failure && <ErrorNote error={failure} />}
        {check && !checking && (
          <p
            data-testid="action-log-check"
            className={
              check.ok
                ? "flex items-center gap-2 rounded-2xl border-2 border-success/40 bg-success-light px-4 py-2.5 text-sm font-extrabold text-success"
                : "flex items-center gap-2 rounded-2xl border-2 border-danger/30 bg-danger-light px-4 py-2.5 text-sm font-extrabold text-danger"
            }
          >
            <Link2 className="h-4 w-4 shrink-0" aria-hidden />
            {check.ok
              ? `${check.verified} of ${check.total} links verified. The head matches the hash shown above.`
              : `Broken at entry ${check.brokenAt}: ${check.problem}. ${check.verified} of ${check.total} links verified before it.`}
          </p>
        )}
      </div>
    </section>
  );
}

/** The 16 scripted scenarios with their transactions, from evidence/transactions.csv (task D4). */
export function ProofPage() {
  const { identity } = useIdentity();
  const proof = useQuery({ queryKey: ["proof", identity.role], queryFn: () => api.proof(identity) });
  const rows = proof.data?.rows ?? [];
  const ok = rows.filter((r) => r.status === "success").length;
  const reverted = rows.filter((r) => r.status === "reverted").length;

  return (
    <div className="space-y-5">
      <PageTitle title="On-Chain Proof" badges={<MockBadge />}>
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
                  <Badge variant={row.status === "success" ? "success" : row.status === "reverted" ? "danger" : "muted"}>{capitalise(row.status)}</Badge>
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
      <ActionLogCard />
    </div>
  );
}

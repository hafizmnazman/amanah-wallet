import type { Verdict } from "@/api";
import { VerdictBadge } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { shortHex } from "@/lib/utils";

export const SIGNER_LABELS = {
  planner: "Planner (Claude)",
  auditor: "Auditor (Qwen)",
  sentinel: "Sentinel (rules)",
} as const;

/** One signer's verdict: what it decided, why, and whether it signed. */
export function VerdictCard({ signer, verdict }: { signer: keyof typeof SIGNER_LABELS; verdict: Verdict }) {
  return (
    <div data-testid="verdict-card" className="rounded-md border border-border bg-background/60 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">{SIGNER_LABELS[signer]}</span>
        <VerdictBadge verdict={verdict.verdict} />
        <Badge variant={verdict.signed ? "teal" : "muted"}>{verdict.signed ? "Signed" : "Not signed"}</Badge>
      </div>
      {verdict.reasons.length > 0 && (
        <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs text-muted">
          {verdict.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
      <p className="hash mt-2 text-[11px] text-muted/80">
        {verdict.model}, {verdict.lineage}, input {shortHex(verdict.input_hash)}
      </p>
    </div>
  );
}

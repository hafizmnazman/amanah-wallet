import type { Verdict } from "@/api";
import { VerdictBadge } from "@/components/common";
import { SIGNERS, SignerAvatar } from "@/components/signers";
import { Badge } from "@/components/ui/badge";
import { explainReason } from "@/lib/rules";
import { cn, shortHex } from "@/lib/utils";

export const SIGNER_LABELS = {
  planner: SIGNERS.planner.label,
  auditor: SIGNERS.auditor.label,
  sentinel: SIGNERS.sentinel.label,
} as const;

/** One signer's verdict: what it decided, why, and whether it signed. */
export function VerdictCard({ signer, verdict }: { signer: keyof typeof SIGNER_LABELS; verdict: Verdict }) {
  const s = SIGNERS[signer];
  return (
    <div data-testid="verdict-card" className={cn("rounded-2xl border-2 p-3", s.ring, s.light)}>
      <div className="flex flex-wrap items-center gap-2">
        <SignerAvatar signer={signer} size={26} />
        <span className={cn("text-sm font-black", s.text)}>{SIGNER_LABELS[signer]}</span>
        <VerdictBadge verdict={verdict.verdict} />
        <Badge variant={verdict.signed ? "teal" : "muted"}>{verdict.signed ? "Signed" : "Not Signed"}</Badge>
      </div>
      {verdict.reasons.length > 0 && (
        <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs text-ink/80">
          {verdict.reasons.map((reason) => {
            const { text, rule } = explainReason(reason);
            return (
              <li key={reason}>
                {text}
                {rule && <span className="hash ml-1.5 text-[11px] text-muted">{rule}</span>}
              </li>
            );
          })}
        </ul>
      )}
      <p className="hash mt-2 text-[11px] text-muted">
        {verdict.model}, {verdict.lineage}, input {shortHex(verdict.input_hash)}
      </p>
    </div>
  );
}

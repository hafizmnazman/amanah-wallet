import { Check, ExternalLink, X } from "lucide-react";

import { PageTitle } from "@/components/common";
import { KancilSays } from "@/components/mascot/Kancil";
import { SignerAvatar } from "@/components/signers";
import { Badge } from "@/components/ui/badge";
import { ARM_LABELS, ARMS, facts, rateOf, REPORT_URL, type RedTeamCase } from "@/lib/facts";
import { cn } from "@/lib/utils";

const COLUMNS = [
  { key: "planner", label: "Planner", sub: "Claude", avatar: "planner" as const },
  { key: "auditor_qwen", label: "Auditor", sub: "Qwen", avatar: "auditor" as const },
  { key: "auditor_claude", label: "Control", sub: "Claude", avatar: null },
  { key: "auditor_gpt", label: "Third", sub: "GPT", avatar: null },
  { key: "sentinel", label: "Sentinel", sub: "Rules", avatar: "sentinel" as const },
];

const CLASS_NAMES: Record<string, string> = {
  authority: "Authority Impersonation",
  data_extraction: "Data Extraction",
  direct_injection: "Direct Injection",
  document_injection: "Injection Through Documents",
  encoded: "Encoded Payloads",
  induced_transfer: "Induced Transfer",
  privilege_escalation: "Privilege Escalation",
  stored_injection: "Stored Injection in the Books",
  structuring: "Splitting Under the Cap",
  urgency: "Urgency",
};

type VariantArm = { n: number; successes: number; upper95: number; seeds_with_a_success: number };
type VariantsFacts = { population: number; pooled: { n: number; n_transfer: number; arms: Record<string, VariantArm> } };
// Present once a stage of redteam/protocol-variants.md has run and scripts/export_ui_data.py has read it
const variants = (facts as unknown as { variants?: VariantsFacts }).variants;
const PROTOCOL_URL = `${REPORT_URL.split("/blob/")[0]}/blob/main/redteam/protocol-variants.md`;

/** The random sample of code-made variants: the planner alone against the full quorum and the vault. */
function RandomVariants({ v }: { v: VariantsFacts }) {
  const alone = v.pooled.arms.S1;
  const amanah = v.pooled.arms.S5;
  if (!alone || !amanah) return null;
  const percent = (x: number) => `${(x * 100).toFixed(1)}%`;
  return (
    <section className="chunky space-y-3 p-5" aria-label="Random variants" data-testid="random-variants">
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 className="text-xl font-black">Then {v.pooled.n} More, Drawn at Random</h2>
        <a href={PROTOCOL_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-bold text-sky-dark hover:underline">
          How the draw was made <ExternalLink className="h-3.5 w-3.5" aria-hidden />
        </a>
      </div>
      <p className="max-w-3xl text-sm text-muted">
        Code rewrote the attacks above into {v.population.toLocaleString()} variants: new personas, urgency, wrappers,
        hidden characters and fresh wallets. {v.pooled.n} were drawn at random, with a seed from a public block mined
        after the plan was published, so no one could pick the easy ones.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className={cn("rounded-2xl border-2 p-4", alone.successes > 0 ? "border-danger/30" : "border-success/40")}>
          <p className="text-xs font-extrabold uppercase tracking-wide text-muted">One Model Alone</p>
          <p className={cn("font-display text-3xl font-black", alone.successes > 0 ? "text-danger" : "text-success")}>
            {alone.successes}/{alone.n}
          </p>
          <p className="text-xs text-muted">attacks it fell for</p>
        </div>
        <div className="rounded-2xl border-2 border-success/40 p-4">
          <p className="text-xs font-extrabold uppercase tracking-wide text-muted">Through Amanah</p>
          <p className={cn("font-display text-3xl font-black", amanah.successes > 0 ? "text-danger" : "text-success")}>
            {amanah.successes}/{amanah.n}
          </p>
          <p className="text-xs text-muted">
            payment attacks moved funds; at 95% confidence the true rate is under {percent(amanah.upper95)}
          </p>
        </div>
      </div>
    </section>
  );
}

/** The red team's final run as a grid: every attack, who fell for it, and which set-ups it beat. */
export function RedTeamPage() {
  const rt = facts.redteam;
  const attacks = rt.cases.filter((c) => c.attack);
  const legit = rt.cases.filter((c) => !c.attack);
  const classes = [...new Set(attacks.map((c) => c.class))].sort();
  const refused = legit.filter((c) => c.success.S3 === false);

  return (
    <div className="space-y-8">
      <PageTitle title={`Red Team: We Tried to Trick It ${rt.n_attacks} Ways`} badges={<Badge variant="muted">Protocol ffa0490</Badge>}>
        Every attack ran against five set-ups, from one model holding the key up to the full quorum and the vault, with
        the live models, on 19 October 2026. The protocol was committed before the run.
      </PageTitle>

      <KancilSays pose="alert" size={64} className="max-w-3xl">
        Here is every trick we tried and who fell for it. A <b className="text-danger">red</b> mark means that signer was
        fooled; the quorum only fails if every signer it needs is fooled at once.
      </KancilSays>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5" aria-label="Results by set-up">
        {ARMS.map((arm) => {
          const won = rateOf(rt.attack_success_transfer[arm]);
          const fr = rateOf(rt.false_refusal[arm]);
          const bad = (won?.k ?? 0) > 0;
          return (
            <div key={arm} className={cn("chunky space-y-1 p-4", bad ? "border-danger/30" : "border-success/40")}>
              <p className="text-xs font-extrabold uppercase tracking-wide text-muted">{arm}</p>
              <p className="text-sm font-black leading-tight">{ARM_LABELS[arm].short}</p>
              <p className={cn("font-display text-3xl font-black", bad ? "text-danger" : "text-success")}>
                {won ? `${won.k}/${won.n}` : "n/a"}
              </p>
              <p className="text-xs text-muted">payment attacks got through</p>
              <p className="pt-1 text-xs font-bold text-ink/80">{fr ? `${fr.k} of ${fr.n} sound payouts held back` : ""}</p>
            </div>
          );
        })}
      </section>

      {variants && <RandomVariants v={variants} />}

      <section className="space-y-3" aria-label="Every attack">
        <h2 className="text-xl font-black">Every Attack, Signer by Signer</h2>
        <div className="chunky overflow-x-auto">
          <table className="w-full min-w-[860px] text-sm">
            <thead>
              <tr className="border-b-2 border-border text-left">
                <th className="px-3 py-3 text-xs font-extrabold uppercase tracking-wide text-muted">Attack</th>
                {COLUMNS.map((c) => (
                  <th key={c.key} className="px-1 py-3 text-center">
                    <span className="flex flex-col items-center gap-1">
                      {c.avatar ? <SignerAvatar signer={c.avatar} size={26} /> : <span className="h-[26px] w-[26px] rounded-full border-2 border-border bg-surface-2" aria-hidden />}
                      <span className="text-[11px] font-extrabold leading-none">{c.label}</span>
                      <span className="text-[10px] font-bold leading-none text-muted">{c.sub}</span>
                    </span>
                  </th>
                ))}
                {ARMS.map((a) => (
                  <th key={a} className="px-1 py-3 text-center text-[11px] font-extrabold text-muted" title={ARM_LABELS[a].long}>
                    {a}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {classes.map((cls) => (
                <ClassRows key={cls} name={CLASS_NAMES[cls] ?? cls} cases={attacks.filter((c) => c.class === cls)} />
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted">
          Signer columns: was this signer fooled by the attack. S1 to S5: did the attack get every signature that set-up
          needs (and, in S5, move funds). The control and third columns are measurements only; they sign nothing.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="chunky space-y-3 p-5">
          <h2 className="text-lg font-black">Sound Payouts, Held Back by Mistake</h2>
          <p className="text-sm text-ink/85">
            {refused.length} of {legit.length} legitimate payouts were escalated to a trustee by the Qwen auditor, which
            misread its own rules: {refused.map((c) => c.id).join(" and ")}, both first flood-relief payouts under the cap.
            An escalation waits for a person; nothing is paid wrongly. We did not tune the prompt to these cases.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {legit.map((c) => (
              <span
                key={c.id}
                title={c.says}
                className={cn(
                  "rounded-full border-2 px-2 py-0.5 text-[11px] font-extrabold",
                  c.success.S3 === false ? "border-gold/50 bg-gold-light text-warning" : "border-success/30 bg-success-light text-success",
                )}
              >
                {c.id}
              </span>
            ))}
          </div>
        </div>
        <div className="chunky space-y-3 p-5">
          <h2 className="text-lg font-black">How to Read It</h2>
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-ink/85">
            <li>
              The planner alone signed {rateOf(rt.attack_success_transfer.S1)?.k ?? 0} payment attacks; with the Qwen auditor and
              the vault, none moved funds.
            </li>
            <li>
              S3&apos;s edge over S2 rests on one case, with a McNemar p of 1.0, and the escalation that stopped it is the
              misreading above. We do not claim Qwen judges better than Claude.
            </li>
            <li>The planner and the Qwen auditor were never fooled together: joint failure 0.0%.</li>
          </ul>
          <a className="inline-flex items-center gap-1 text-sm font-extrabold text-sky-dark hover:underline" href={REPORT_URL} target="_blank" rel="noreferrer">
            The Full Report, with Its Two Deviations <ExternalLink className="h-3.5 w-3.5" aria-hidden />
          </a>
        </div>
      </section>
    </div>
  );
}

function ClassRows({ name, cases }: { name: string; cases: RedTeamCase[] }) {
  return (
    <>
      <tr className="bg-surface-2">
        <td colSpan={1 + COLUMNS.length + ARMS.length} className="px-3 py-1.5 text-xs font-extrabold uppercase tracking-wide text-muted">
          {name}
        </td>
      </tr>
      {cases.map((c) => (
        <tr key={c.id} className="border-t border-border align-top" data-testid="redteam-row">
          <td className="max-w-[340px] px-3 py-2">
            <p className="text-xs font-extrabold text-ink">{c.id}</p>
            <p className="line-clamp-2 text-xs text-muted" title={c.says}>
              {c.says}
            </p>
          </td>
          {COLUMNS.map((col) => {
            const fooled = (c.fooled as Record<string, boolean>)[col.key];
            return (
              <td key={col.key} className="px-1 py-2 text-center">
                {fooled === undefined ? (
                  <span className="text-muted">-</span>
                ) : (
                  <span
                    className={cn("mx-auto block h-3.5 w-3.5 rounded-full border-2", fooled ? "border-danger-dark bg-danger-fill" : "border-primary-dark bg-primary")}
                    title={fooled ? "fooled" : "held"}
                    aria-label={fooled ? "fooled" : "held"}
                  />
                )}
              </td>
            );
          })}
          {ARMS.map((a) => {
            const won = (c.success as Record<string, boolean>)[a];
            return (
              <td key={a} className="px-1 py-2 text-center">
                {won ? (
                  <X className="mx-auto h-4 w-4 text-danger" strokeWidth={3.5} aria-label="got through" />
                ) : (
                  <Check className="mx-auto h-4 w-4 text-success" strokeWidth={3.5} aria-label="stopped" />
                )}
              </td>
            );
          })}
        </tr>
      ))}
    </>
  );
}

import { Calculator, Check, FileSearch, Minus, Sparkles, X, type LucideIcon } from "lucide-react";

import type { VerdictValue } from "@/api";
import { cn } from "@/lib/utils";

/**
 * The three signers, each built to fail differently: a different model lineage, a different view of the
 * evidence, a different way of reasoning. One colour each, used everywhere a signer appears.
 */
export type SignerKey = "planner" | "auditor" | "sentinel";

export const SIGNERS: Record<
  SignerKey,
  { label: string; role: string; who: string; sees: string; never: string; icon: LucideIcon; fill: string; text: string; light: string; ring: string }
> = {
  planner: {
    label: "Planner (Claude)",
    role: "Planner",
    who: "Claude, by Anthropic",
    sees: "the officer's chat and the books",
    never: "raw documents or personal data",
    icon: Sparkles,
    fill: "bg-planner",
    text: "text-planner-dark",
    light: "bg-planner-light",
    ring: "border-planner/40",
  },
  auditor: {
    label: "Auditor (Qwen)",
    role: "Auditor",
    who: "Qwen, by Alibaba",
    sees: "a typed case file rebuilt from the books",
    never: "the chat, the planner's reasoning, any free text",
    icon: FileSearch,
    fill: "bg-auditor",
    text: "text-auditor-dark",
    light: "bg-auditor-light",
    ring: "border-auditor/40",
  },
  sentinel: {
    label: "Sentinel (Rules)",
    role: "Sentinel",
    who: "8 Rules, No Model",
    sees: "numbers only",
    never: "any text at all",
    icon: Calculator,
    fill: "bg-sentinel",
    text: "text-sentinel-dark",
    light: "bg-sentinel-light",
    ring: "border-sentinel/40",
  },
};

export const SIGNER_ORDER: SignerKey[] = ["planner", "auditor", "sentinel"];

export function SignerAvatar({ signer, size = 36, className }: { signer: SignerKey; size?: number; className?: string }) {
  const s = SIGNERS[signer];
  const Icon = s.icon;
  return (
    <span
      className={cn("inline-flex shrink-0 items-center justify-center rounded-full border-2 border-white text-white shadow-[0_2px_0_rgba(0,0,0,0.12)]", s.fill, className)}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <Icon style={{ width: size * 0.5, height: size * 0.5 }} strokeWidth={2.6} />
    </span>
  );
}

const VERDICT_WORDS: Record<VerdictValue, string> = {
  APPROVE: "approved",
  REJECT: "rejected",
  ESCALATE: "escalated to a trustee",
  UNAVAILABLE: "did not answer",
};

/** A signer and its verdict in one pill: green tick, red cross, amber dash. A screen reader hears it in words. */
export function SignerChip({ signer, verdict, signed }: { signer: SignerKey; verdict: VerdictValue; signed: boolean }) {
  const s = SIGNERS[signer];
  const ok = verdict === "APPROVE" && signed;
  const no = verdict === "REJECT";
  const Mark = ok ? Check : no ? X : Minus;
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 rounded-full border-2 py-0.5 pl-0.5 pr-2.5 text-xs font-extrabold", s.ring, s.light, s.text)}
      title={`${s.label}: ${verdict}${signed ? ", signed" : ", not signed"}`}
    >
      <SignerAvatar signer={signer} size={22} />
      <span aria-hidden>{s.role}</span>
      <Mark className={cn("h-3.5 w-3.5", ok ? "text-success" : no ? "text-danger" : "text-warning")} strokeWidth={3.5} aria-hidden />
      <span className="sr-only">
        {s.label}: {VERDICT_WORDS[verdict] ?? verdict}, {signed ? "signed" : "not signed"}
      </span>
    </span>
  );
}

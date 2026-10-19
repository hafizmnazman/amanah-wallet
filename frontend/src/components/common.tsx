import { CircleAlert, CircleCheck, Clock3, ExternalLink, FlaskConical, Hourglass, ShieldX, Undo2 } from "lucide-react";
import type { ReactNode } from "react";

import { api, type PayoutStatus, type VerdictValue } from "@/api";
import { Kancil } from "@/components/mascot/Kancil";
import { Badge } from "@/components/ui/badge";
import { txUrl } from "@/lib/explorer";
import { shortHex } from "@/lib/utils";

/** Shown on every screen fed by the in-browser mock, so a recording never passes off fake hashes as real. */
export function MockBadge({ className }: { className?: string }) {
  if (!api.isMock) return null;
  return (
    <Badge variant="warning" className={className} data-testid="mock-badge">
      <FlaskConical className="h-3 w-3" aria-hidden />
      Mock data
    </Badge>
  );
}

const STATUS: Record<
  PayoutStatus,
  { label: string; variant: "success" | "warning" | "danger" | "teal" | "muted"; icon: typeof CircleCheck }
> = {
  paid: { label: "Paid", variant: "success", icon: CircleCheck },
  elevated_pending: { label: "Waiting for a trustee", variant: "warning", icon: Clock3 },
  rejected: { label: "Rejected", variant: "danger", icon: ShieldX },
  escalated: { label: "Escalated", variant: "warning", icon: CircleAlert },
  queued: { label: "Queued", variant: "teal", icon: Hourglass },
  reverted: { label: "Reverted", variant: "danger", icon: Undo2 },
};

export function StatusBadge({ status }: { status: PayoutStatus }) {
  const s = STATUS[status] ?? { label: status, variant: "muted" as const, icon: CircleAlert };
  const Icon = s.icon;
  return (
    <Badge variant={s.variant}>
      <Icon className="h-3.5 w-3.5" strokeWidth={3} aria-hidden />
      {s.label}
    </Badge>
  );
}

export function VerdictBadge({ verdict }: { verdict: VerdictValue }) {
  const variant = verdict === "APPROVE" ? "success" : verdict === "REJECT" ? "danger" : "warning";
  return <Badge variant={variant}>{verdict}</Badge>;
}

/**
 * A transaction hash with its explorer link. Mock hashes are never linked: they would open a page
 * for a transaction that does not exist.
 */
export function TxLink({ hash, url }: { hash?: string; url?: string }) {
  if (!hash) return <span className="text-muted">No transaction</span>;
  if (api.isMock) {
    return (
      <span className="hash text-muted" title="Mock hash, not on any chain">
        {shortHex(hash, 8, 6)} (mock)
      </span>
    );
  }
  return (
    <a
      className="hash inline-flex items-center gap-1 font-semibold text-sky-dark underline-offset-2 hover:underline"
      href={url || txUrl(hash)}
      target="_blank"
      rel="noreferrer"
    >
      {shortHex(hash, 8, 6)}
      <ExternalLink className="h-3 w-3" aria-hidden />
    </a>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <p role="alert" className="rounded-2xl border-2 border-danger/30 bg-danger-light px-4 py-2.5 text-sm font-bold text-danger">
      {message}
    </p>
  );
}

export function RoleHint({ expected, label }: { expected: boolean; label: string }) {
  if (expected) return null;
  return (
    <div className="flex items-center gap-3 rounded-2xl border-2 border-sentinel/40 bg-sentinel-light px-4 py-2.5">
      <Kancil pose="thinking" size={40} title="Kancil, wondering" />
      <p className="text-sm font-bold text-warning">This page is for {label}. Switch the role in the header to act as one.</p>
    </div>
  );
}

/** A page title with a short line under it, and room for badges. */
export function PageTitle({ title, children, badges }: { title: string; children?: ReactNode; badges?: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-2xl font-black tracking-tight sm:text-3xl">{title}</h1>
        {badges}
      </div>
      {children && <p className="max-w-3xl text-sm text-muted sm:text-base">{children}</p>}
    </div>
  );
}

/** An empty state with Kancil, so a blank list still says something useful. */
export function EmptyState({ pose = "sleep", children }: { pose?: "sleep" | "happy" | "calm"; children: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-3xl border-2 border-dashed border-border-strong bg-surface px-6 py-8 text-center">
      <Kancil pose={pose} size={96} />
      <p className="max-w-md text-sm font-bold text-muted">{children}</p>
    </div>
  );
}

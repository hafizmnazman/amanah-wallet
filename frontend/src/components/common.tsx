import { ExternalLink, FlaskConical } from "lucide-react";

import { api, type PayoutStatus, type VerdictValue } from "@/api";
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

const STATUS: Record<PayoutStatus, { label: string; variant: "success" | "warning" | "danger" | "teal" | "muted" }> = {
  paid: { label: "Paid", variant: "success" },
  elevated_pending: { label: "Waiting for a trustee", variant: "warning" },
  rejected: { label: "Rejected", variant: "danger" },
  escalated: { label: "Escalated", variant: "warning" },
  queued: { label: "Queued", variant: "teal" },
  reverted: { label: "Reverted", variant: "danger" },
};

export function StatusBadge({ status }: { status: PayoutStatus }) {
  const s = STATUS[status] ?? { label: status, variant: "muted" as const };
  return <Badge variant={s.variant}>{s.label}</Badge>;
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
    <a className="hash inline-flex items-center gap-1 text-teal hover:underline" href={url || txUrl(hash)} target="_blank" rel="noreferrer">
      {shortHex(hash, 8, 6)}
      <ExternalLink className="h-3 w-3" aria-hidden />
    </a>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
      {message}
    </p>
  );
}

export function RoleHint({ expected, label }: { expected: boolean; label: string }) {
  if (expected) return null;
  return (
    <p className="rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-warning">
      This page is for {label}. Switch the role in the header to act as one.
    </p>
  );
}

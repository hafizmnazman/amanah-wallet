import { FileText } from "lucide-react";

import type { DocumentResponse } from "@/api";
import { MockBadge } from "@/components/common";
import { Kancil } from "@/components/mascot/Kancil";
import { Card } from "@/components/ui/card";
import { formatUsdc } from "@/lib/usdc";
import { shortHex } from "@/lib/utils";

/** What the quarantined reader took from an uploaded document: typed fields only (task D1). */
export function ReaderFieldsCard({ name, response }: { name: string; response: DocumentResponse }) {
  const f = response.fields;
  const rows: [string, string][] = [
    ["Applicant", f.applicant_ref ?? "not found"],
    ["Requested Amount", f.requested_amount_usdc !== undefined ? `${formatUsdc(f.requested_amount_usdc)} USDC (advisory)` : "not found"],
    ["Programme", f.programme_code ?? "not found"],
    ["Dates", f.dates.length ? f.dates.join(", ") : "none"],
    ["Free Text Present", f.free_text_present ? "yes, kept out of every model" : "no"],
  ];
  return (
    <Card data-testid="reader-fields" className="p-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl border-2 border-border bg-surface-2">
          <FileText className="h-4 w-4 text-muted" aria-hidden />
        </span>
        <span className="font-extrabold">{name}</span>
        <span className="hash text-xs text-muted">{shortHex(response.document_id)}</span>
        <MockBadge />
      </div>
      {response.injection_flag && (
        <div
          role="alert"
          data-testid="injection-warning"
          className="mt-3 flex items-center gap-3 rounded-2xl border-2 border-danger/30 bg-danger-light px-3 py-2.5 text-sm font-bold text-danger"
        >
          <Kancil pose="alert" size={44} title="Kancil spotted a trick" />
          <span>
            Instruction-like text found in this document. It was quarantined: only the typed fields below reach the
            planner, and the flag is logged.
          </span>
        </div>
      )}
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="font-bold text-muted">{label}</dt>
            <dd className="font-bold">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-muted">The planner takes amounts from the books, never from a document.</p>
    </Card>
  );
}

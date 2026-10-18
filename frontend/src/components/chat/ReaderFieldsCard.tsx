import { FileText, TriangleAlert } from "lucide-react";

import type { DocumentResponse } from "@/api";
import { MockBadge } from "@/components/common";
import { Card } from "@/components/ui/card";
import { formatUsdc } from "@/lib/usdc";
import { shortHex } from "@/lib/utils";

/** What the quarantined reader took from an uploaded document: typed fields only (task D1). */
export function ReaderFieldsCard({ name, response }: { name: string; response: DocumentResponse }) {
  const f = response.fields;
  const rows: [string, string][] = [
    ["Applicant", f.applicant_ref ?? "not found"],
    ["Requested amount", f.requested_amount_usdc !== undefined ? `${formatUsdc(f.requested_amount_usdc)} USDC (advisory)` : "not found"],
    ["Programme", f.programme_code ?? "not found"],
    ["Dates", f.dates.length ? f.dates.join(", ") : "none"],
    ["Free text present", f.free_text_present ? "yes, kept out of every model" : "no"],
  ];
  return (
    <Card data-testid="reader-fields" className="p-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <FileText className="h-4 w-4 text-muted" aria-hidden />
        <span className="font-medium">{name}</span>
        <span className="hash text-xs text-muted">{shortHex(response.document_id)}</span>
        <MockBadge />
      </div>
      {response.injection_flag && (
        <p
          role="alert"
          data-testid="injection-warning"
          className="mt-2 flex gap-2 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger"
        >
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          Instruction-like text found in this document. It was quarantined: only the typed fields below reach the
          planner, and the flag is logged.
        </p>
      )}
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-muted">{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-xs text-muted">The planner takes amounts from the books, never from a document.</p>
    </Card>
  );
}

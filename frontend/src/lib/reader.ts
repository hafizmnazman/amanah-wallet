import type { ReaderFields } from "@/api/types";

import { formatUsdc } from "./usdc";

/** The reader's typed fields as rows to show. The API sends null for a field the reader did not find. */
export function readerRows(f: ReaderFields): [string, string][] {
  const amount = f.requested_amount_usdc;
  return [
    ["Applicant", f.applicant_ref ?? "not found"],
    ["Requested Amount", amount == null ? "not found" : `${formatUsdc(amount)} USDC (advisory)`],
    ["Programme", f.programme_code ?? "not found"],
    ["Dates", f.dates.length ? f.dates.join(", ") : "none"],
    ["Free Text Present", f.free_text_present ? "yes, kept out of every model" : "no"],
  ];
}

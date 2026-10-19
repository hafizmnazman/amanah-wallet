import { describe, expect, it } from "vitest";

import { readerRows } from "./reader";

describe("readerRows", () => {
  it("shows an amount the reader found as advisory", () => {
    const rows = readerRows({ applicant_ref: "EDU-A-07", requested_amount_usdc: "2500", programme_code: "EDU-BURSARY-S1",
                              dates: ["2026-10-05"], free_text_present: true });
    expect(rows).toContainEqual(["Requested Amount", "2,500.00 USDC (advisory)"]);
    expect(rows).toContainEqual(["Free Text Present", "yes, kept out of every model"]);
  });

  it("says not found for the nulls the API sends, as for a letter that names no amount", () => {
    const rows = readerRows({ applicant_ref: "ZKT-H07", requested_amount_usdc: null, programme_code: null,
                              dates: [], free_text_present: true });
    expect(rows).toContainEqual(["Requested Amount", "not found"]);
    expect(rows).toContainEqual(["Programme", "not found"]);
    expect(rows).toContainEqual(["Dates", "none"]);
  });
});

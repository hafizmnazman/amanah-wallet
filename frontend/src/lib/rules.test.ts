import { describe, expect, it } from "vitest";

import { explainReason, SENTINEL_RULES } from "./rules";

// The ids in backend/app/agentwallet/sentinel/rules.py RULES, in order
const BACKEND_RULES = ["beneficiary_known", "eligibility_current", "no_duplicate_in_batch", "within_hard_ceiling",
  "daily_budget", "frequency", "threshold_structuring", "amount_vs_history"];

describe("explainReason", () => {
  it("has plain words for every one of the sentinel's eight rules", () => {
    for (const rule of BACKEND_RULES) expect(explainReason(rule)).toEqual({ text: SENTINEL_RULES[rule], rule });
  });

  it("leaves an auditor's own sentence as it is, and says all rules passed without a rule id", () => {
    expect(explainReason("The wallet is not registered for programme REL-PERAK-FLOOD.")).toEqual({
      text: "The wallet is not registered for programme REL-PERAK-FLOOD.", rule: null });
    expect(explainReason("all rules passed")).toEqual({ text: "All eight rules passed.", rule: null });
  });
});

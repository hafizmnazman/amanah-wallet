/**
 * The sentinel's eight rules in plain words, for the reasons it gives: a failed rule's id, or "all rules passed".
 * They follow backend/app/agentwallet/sentinel/rules.py, where each id names the check that failed.
 */
export const SENTINEL_RULES: Record<string, string> = {
  beneficiary_known: "The wallet is not a registered beneficiary of this programme.",
  eligibility_current: "The household's eligibility is not current.",
  no_duplicate_in_batch: "The same payout appears twice in this batch.",
  within_hard_ceiling: "The amount is above the programme's hard ceiling.",
  daily_budget: "It would take the programme past today's budget.",
  frequency: "This household was paid less than 25 days ago.",
  threshold_structuring: "It looks like one payment split up to stay under a limit.",
  amount_vs_history: "The amount is far above this household's last payout.",
  "all rules passed": "All eight rules passed.",
};

// backend/app/agentwallet/checkers.py: "<service> unavailable: <the HTTP client's error>"
const UNAVAILABLE = /^(\w+) unavailable: (\w+)$/;

/** A reason in plain words, and the rule or error code when it was one, so the code stays visible beside it. */
export function explainReason(reason: string): { text: string; rule: string | null } {
  const down = UNAVAILABLE.exec(reason);
  if (down) {
    const [, service, error] = down;
    const what = /Timeout/.test(error) ? "did not answer in time" : /Connect/.test(error) ? "could not be reached" : "was not available";
    return { text: `The ${service} ${what}.`, rule: error };
  }
  const text = SENTINEL_RULES[reason];
  if (text === undefined) return { text: reason, rule: null };
  return { text, rule: reason === "all rules passed" ? null : reason };
}

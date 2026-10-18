import type { DecodedPayout } from "./typedData";
import { formatBaseUnits, parseUsdc } from "./usdc";

/**
 * Compares the plain-words summary with the fields the wallet will sign. A summary that names a different
 * amount or wallet is the blind-signing failure the trustee screen exists to catch.
 */
export function checkSummary(summary: string, payout: DecodedPayout): { ok: boolean; problems: string[] } {
  const problems: string[] = [];
  const amounts = Array.from(summary.matchAll(/([\d,]+(?:\.\d+)?)\s*USDC/gi), (m) => m[1]);
  const signedAmount = formatBaseUnits(payout.amount);
  if (amounts.length === 0) {
    problems.push("The summary names no amount.");
  } else {
    // The first amount is the payout; later ones (a cap, a budget) are context.
    let first: bigint | null = null;
    try {
      first = parseUsdc(amounts[0]);
    } catch {
      problems.push(`The summary's amount "${amounts[0]}" cannot be read.`);
    }
    if (first !== null && first !== payout.amount) {
      problems.push(`The summary says ${amounts[0]} USDC, but the signed amount is ${signedAmount} USDC.`);
    }
  }
  const wallets = Array.from(summary.matchAll(/0x[0-9a-fA-F]{40}/g), (m) => m[0].toLowerCase());
  if (wallets.length > 0 && !wallets.includes(payout.beneficiary.toLowerCase())) {
    problems.push(`The summary names wallet ${wallets[0]}, but the signed beneficiary is ${payout.beneficiary}.`);
  }
  return { ok: problems.length === 0, problems };
}

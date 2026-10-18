import { getAddress, keccak256, stringToHex } from "viem";

import { PROGRAMMES, type Programme } from "@/lib/programmes";

import type { PlanCard, ProofRow, QueuedPayout, UsageReport, Verdict, Verdicts } from "./types";

/**
 * Demo data for mock mode. Every hash here is visibly fake (zero-padded counters) and every wallet is
 * derived from a label; nothing in this file is a real transaction or a real person.
 */

export function mockHash(n: number): `0x${string}` {
  return `0x${n.toString(16).padStart(64, "0")}`;
}

export function labelHash(label: string): `0x${string}` {
  return keccak256(stringToHex(`amanah.mock.${label}`));
}

export function mockWallet(label: string): `0x${string}` {
  return getAddress(`0x${labelHash(label).slice(-40)}`);
}

export const MOCK_VAULT = "0xa3A1000000000000000000000000000000000001";


function batch(
  programme: Programme,
  batchId: string,
  prefix: string,
  amounts: number[],
  tier: PlanCard["tier_preview"],
  notes: string[],
): PlanCard {
  const items = amounts.map((amount, i) => {
    const n = String(i + 1).padStart(2, "0");
    return {
      household_ref: `H-${n}`,
      beneficiary_ref: `${prefix}-B${n}`,
      wallet: mockWallet(`${prefix}-B${n}`),
      amount_usdc: amount,
    };
  });
  return {
    batch_id: batchId,
    programme_code: programme.code,
    programme_name: programme.name,
    fund_name: programme.fund,
    items,
    total_usdc: amounts.reduce((a, b) => a + b, 0),
    tier_preview: tier,
    notes,
  };
}

/** 12 households; without household 12 the total is 1,650 USDC, inside the window scenario 13 needs. */
export const ZAKAT_OCTOBER = batch(
  PROGRAMMES[0],
  "ZKT-2026-10",
  "ZKT",
  [150, 150, 140, 160, 150, 155, 145, 150, 150, 150, 150, 160],
  "routine",
  ["Amounts come from the books, one payout per household.", "Every amount is under the 200.00 USDC cap."],
);

export const FLOOD_OCTOBER = batch(
  PROGRAMMES[1],
  "REL-2026-10",
  "REL",
  [300, 300, 250, 300, 300],
  "routine",
  ["Amounts come from the books, one payout per household."],
);

export const BURSARY_S1 = batch(
  PROGRAMMES[2],
  "EDU-2026-S1",
  "EDU",
  [500, 500, 450, 400],
  "elevated",
  ["The batch passes 80% of the programme's 2,000.00 USDC daily budget, so a trustee must co-sign."],
);

function verdict(lineage: string, model: string, reasons: string[], value: Verdict["verdict"] = "APPROVE"): Verdict {
  return {
    verdict: value,
    reasons,
    input_hash: labelHash(`input.${lineage}.${reasons.join("|")}`),
    model,
    lineage,
    signed: value === "APPROVE",
  };
}

export function approvals(householdRef: string, amount: string, programmeCode: string): Verdicts {
  return {
    planner: verdict("anthropic/claude", "mock planner", [
      `Amount ${amount} USDC taken from the books for ${householdRef}.`,
      `Beneficiary is allowlisted for ${programmeCode}.`,
    ]),
    auditor: verdict("alibaba/qwen", "mock auditor", [
      "Strongest reason against: none found in the case file.",
      "Eligibility is current and the last payout was 30 days ago.",
    ]),
    sentinel: verdict("symbolic/rules", "rules", [
      "known_beneficiary",
      "eligibility_current",
      "within_cap",
      "frequency_ok",
      "daily_budget_ok",
    ]),
  };
}

/** Plan section 10's 16 scenarios, with fake hashes. */
export const PROOF_ROWS: ProofRow[] = [
  ["Deploy and verify AmanahVault", "Verified source; the deployer holds no role", "success"],
  ["Two trustees register planner, auditor, sentinel and posture oracle", "Registry events", "success"],
  ["Two trustees set the three mandates", "Mandate events", "success"],
  ["Two trustees add beneficiaries, 10-minute cooling-off", "Beneficiary events", "success"],
  ["Donor deposit, matched to a receipt in the books", "Transfer in", "success"],
  ["Routine batch: 11 households of ZKT-IPOH-FAKIR-M", "Paid with no human", "success"],
  ["Above-cap emergency grant from REL-PERAK-FLOOD", "Elevated; a trustee co-signs; paid", "success"],
  ["Induced transfer from a chairman message", "Rejected; decision anchored", "success"],
  ["Prompt injection in an uploaded letter", "Rejected; decision anchored", "success"],
  ["Forced attack: three machine signatures to an unlisted wallet", "Reverted with NotAllowlisted", "reverted"],
  ["Same-lineage quorum: two Claude keys", "Reverted with SameLineage", "reverted"],
  ["Planner key calls addBeneficiary with its own signature", "Reverted with NotTrustee", "reverted"],
  ["Structuring: 199 USDC payouts to one beneficiary", "Elevated at the 80% line, then BeneficiaryCapExceeded", "reverted"],
  ["Immune loop: report anchored, posture raised", "The next routine payout needs a trustee", "success"],
  ["Override of an anchored auditor rejection", "Planner and two trustees sign; paid", "success"],
  ["Guardian pauses; two trustees unpause", "A payout reverts while paused", "success"],
].map(([description, expected, status], i) => ({
  scenario: i + 1,
  description,
  expected,
  tx_hash: mockHash(0x5c000 + i + 1),
  status,
  block: 30_000_000 + i * 7,
  explorer_url: "",
}));

export const QUEUE_ITEMS: QueuedPayout[] = [
  {
    proposal_id: labelHash("queued-proposal"),
    reason: "The auditor service did not answer, so the payout is held and a trustee was alerted.",
    queued_at: "2026-10-20T09:31:00+08:00",
    missing: "auditor",
  },
];

/** The same totals the backend's /api/usage gives for the generated books (redteam/data/books.json). */
export const USAGE: UsageReport = {
  generated_at: "2026-10-18T12:00:00+08:00",
  institution: "Amanah Demo Institution",
  synthetic: true,
  min_cell: 3,
  source: "the books and the vault's PayoutExecuted events",
  funds: [
    {
      fund_code: "ZKT",
      fund_name: "Zakat Fund",
      total_usdc: "5850.00",
      donations_recorded_usdc: "5000.00",
      programmes: [
        {
          programme_code: "ZKT-IPOH-FAKIR-M",
          programme_name: "Ipoh fakir monthly aid",
          payouts: 39,
          households: 13,
          total_usdc: "5850.00",
          paid_on_chain: 0,
          by_month: [
            { month: "2026-07", payouts: 13, total_usdc: "1950.00" },
            { month: "2026-08", payouts: 13, total_usdc: "1950.00" },
            { month: "2026-09", payouts: 13, total_usdc: "1950.00" },
          ],
        },
      ],
    },
    {
      fund_code: "REL",
      fund_name: "Flood Relief Fund",
      total_usdc: "0.00",
      donations_recorded_usdc: "0.00",
      programmes: [
        { programme_code: "REL-PERAK-FLOOD", programme_name: "Perak flood relief", payouts: 0, households: 0, total_usdc: "0.00", paid_on_chain: 0, by_month: [] },
      ],
    },
    {
      fund_code: "EDU",
      fund_name: "Education Bursary Fund",
      total_usdc: "4500.00",
      donations_recorded_usdc: "0.00",
      programmes: [
        {
          programme_code: "EDU-BURSARY-S1",
          programme_name: "Semester bursary",
          payouts: 10,
          households: 10,
          total_usdc: "4500.00",
          paid_on_chain: 0,
          by_month: [{ month: "2026-03", payouts: 10, total_usdc: "4500.00" }],
        },
      ],
    },
  ],
};

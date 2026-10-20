import { getAddress, keccak256, stringToHex } from "viem";

import { PROGRAMMES, type Programme } from "@/lib/programmes";

import type { Alert, PlanCard, ProofRow, QueuedPayout, UsageReport, Verdict, Verdicts } from "./types";

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


/** Households and beneficiaries are named as the books name them (redteam/data/books.json): ZKT-H01 with ZKT-B01. */
function batch(
  programme: Programme,
  batchId: string,
  prefix: string,
  amounts: number[],
  tier: PlanCard["tier_preview"],
  notes: string[],
  first = 1,
): PlanCard {
  const items = amounts.map((amount, i) => {
    const n = String(i + first).padStart(2, "0");
    return {
      household_ref: `${prefix}-H${n}`,
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

/** Each zakat household's monthly aid in the books, ZKT-H01 to ZKT-H15. */
export const ZAKAT_MONTHLY_USDC = [150, 150, 140, 160, 150, 155, 145, 150, 150, 150, 150, 160, 140, 160, 140];

/**
 * The books' October batch: 12 households, 1,810 USDC. Without household 12 it is 11 and 1,650 USDC, the
 * routine batch the Base Sepolia run paid (scenario 6).
 */
export const ZAKAT_OCTOBER = batch(
  PROGRAMMES[0],
  "ZKT-2026-10",
  "ZKT",
  ZAKAT_MONTHLY_USDC.slice(0, 12),
  "routine",
  ["Amounts come from the books, one payout per household.", "Every amount is under the 200.00 USDC cap."],
);

/** One zakat household's monthly aid on its own, as "Pay household ZKT-H14 this month" asks. Null if not in the books. */
export function zakatHousehold(ref: string): PlanCard | null {
  const n = Number(/^ZKT-H(\d{2})$/i.exec(ref)?.[1]);
  const amount = ZAKAT_MONTHLY_USDC[n - 1];
  if (!amount) return null;
  const card = batch(PROGRAMMES[0], `ZKT-2026-10-H${String(n).padStart(2, "0")}`, "ZKT", [amount], "routine", [], n);
  card.notes = [`The amount is ${card.items[0].household_ref}'s monthly aid in the books.`, "It is under the 200.00 USDC cap."];
  return card;
}

/** The books' October flood relief batch: REL-H02 to REL-H09 at 250 USDC each, under the 300.00 USDC cap. */
export const FLOOD_OCTOBER = batch(
  PROGRAMMES[1],
  "REL-2026-10",
  "REL",
  [250, 250, 250, 250, 250, 250, 250, 250],
  "routine",
  ["Amounts come from the books, one payout per household.", "Every amount is under the 300.00 USDC cap."],
  2,
);

/**
 * Request REQ-REL-0001 in the books: 1,200 USDC for household REL-H01, above the 300.00 USDC cap, so the vault
 * asks a trustee to co-sign (scenario 7). It is the payout the mock's Trustee page holds.
 */
export const EMERGENCY_GRANT: PlanCard = {
  ...batch(PROGRAMMES[1], "REQ-REL-0001", "REL", [1200], "elevated", []),
  notes: [
    "Request REQ-REL-0001 in the books, approved by the officer: an emergency grant for household REL-H01.",
    "1,200.00 USDC is above the programme's 300.00 USDC cap, so the vault requires a trustee to co-sign.",
  ],
};

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
    // What the backend's sentinel says when it approves (sentinel/rules.py). A rule id is only ever a failure:
    // listing "eligibility_current" here showed an approving sentinel saying the eligibility was not current.
    sentinel: verdict("symbolic/rules", "rules", ["all rules passed"]),
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
  ["Override of an anchored auditor refusal", "Planner and two trustees sign; paid", "success"],
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

/**
 * The alerts the store writes, oldest first, in the backend's own words (queue.py): a payout queued while the
 * chain did not answer and refused on a retry an hour later, its signatures expired; another queued while the
 * auditor timed out and drained on the retry; the emergency grant waiting for a trustee; and the payout still in
 * the queue above. The backend writes no alert when the posture rises, so neither does the mock.
 */
export const ALERTS: Alert[] = [
  {
    id: 1,
    created_at: "2026-10-20T07:55:05+08:00",
    kind: "queued",
    proposal_id: labelHash("refused-proposal"),
    message: "Payout queued, chain missing: the RPC endpoint did not answer (ReadTimeout)",
    read: 0,
  },
  {
    id: 2,
    created_at: "2026-10-20T08:58:12+08:00",
    kind: "queued",
    proposal_id: labelHash("drained-proposal"),
    message: "Payout queued, auditor missing: auditor unavailable: ReadTimeout",
    read: 0,
  },
  {
    id: 3,
    created_at: "2026-10-20T08:59:12+08:00",
    kind: "drained",
    proposal_id: labelHash("drained-proposal"),
    message: "Queued payout went through after a retry.",
    read: 0,
  },
  {
    id: 4,
    created_at: "2026-10-20T09:02:05+08:00",
    kind: "refused",
    proposal_id: labelHash("refused-proposal"),
    message: "Queued payout of 150 USDC to ZKT-H01 was refused on retry: The vault reverted it: Expired. Nothing was paid.",
    read: 0,
  },
  {
    id: 5,
    created_at: "2026-10-20T09:14:40+08:00",
    kind: "trustee_needed",
    proposal_id: labelHash("proposal.rel-emergency-grant"),
    message: "An elevated payout needs a trustee's signature.",
    read: 0,
  },
  {
    id: 6,
    created_at: QUEUE_ITEMS[0].queued_at,
    kind: "queued",
    proposal_id: QUEUE_ITEMS[0].proposal_id,
    message: `Payout queued, auditor missing: ${QUEUE_ITEMS[0].reason}`,
    read: 0,
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

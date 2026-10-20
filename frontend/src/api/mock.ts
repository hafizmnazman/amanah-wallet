import { recoverTypedDataAddress } from "viem";

import { config } from "@/config";
import { PROGRAMMES } from "@/lib/programmes";
import { formatUsdc, parseUsdc } from "@/lib/usdc";
import { toSignable } from "@/lib/typedData";

import {
  ALERTS,
  BURSARY_S1,
  EMERGENCY_GRANT,
  FLOOD_OCTOBER,
  MOCK_VAULT,
  PROOF_ROWS,
  QUEUE_ITEMS,
  USAGE,
  ZAKAT_OCTOBER,
  approvals,
  labelHash,
  mockHash,
  mockWallet,
  zakatHousehold,
} from "./mockData";
import type {
  AmanahApi,
  ChatResponse,
  DocumentResponse,
  PayoutResult,
  PendingPayout,
  PlanCard,
  PostureResponse,
  ReaderFields,
} from "./types";

/**
 * An in-browser stand-in for lane B's backend that plays the scripted demo. It keeps state in memory
 * for the life of the page. Every screen fed by it shows a "Mock data" badge.
 */

interface Session {
  awaitingBatchChoice: boolean;
  card: PlanCard | null;
}

// "Urgent" alone is not an attack: an officer may well say it about a real batch
const ATTACK = /chairman|new wallet|0x[0-9a-f]{40}/i;
const EXTRACTION = /export|ic number|identity number|home address/i;
const ESCALATION = /new admin|i am the admin|add .*beneficiar|raise the cap/i;
const INJECTION = /SYSTEM:|ignore (all|previous|the above)|you are now|approve this applicant|as the admin/i;
/** A wallet address of any length: the mock never plans a payout to a wallet named in the chat. */
const ADDRESS = /\b0x[0-9a-f]*/i;
/** Money-moving words, for the refusal of anything that asks to pay and matches no request the books know. */
const MOVES_MONEY = /\b(send|transfer|wire)\b|\bpay to\b|\busdc\b/i;
const HOUSEHOLD = /\bZKT-H\d{2}\b/i;
/** Chinese text (CJK ideographs) that asks to transfer, pay or send money, or names a wallet or USDC. */
const CHINESE = /[\u3400-\u9fff]/;
const CHINESE_MONEY = /转账|转钱|转给|付款|支付|汇款|打款|打钱|发送|发给|钱包|USDC/i;

export const NOT_IN_BOOKS =
  "I can't send money to a wallet that is not in the books. Every payout needs the planner, the auditor and the sentinel, " +
  "and the vault pays only beneficiaries the trustees registered.";
export const NOT_IN_BOOKS_ZH = "我不能向账簿之外的钱包付款。每一笔付款都需要规划者、审计者和规则哨兵的签名，金库只付给受托人登记过的受益人。";

function delay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, config.mockLatencyMs));
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function recount(card: PlanCard): PlanCard {
  const total = card.items.reduce((sum, item) => sum + Number(item.amount_usdc), 0);
  return { ...card, total_usdc: total };
}

export interface MockControls {
  setPosture(level: number): void;
}

export function createMockApi(): AmanahApi & { controls: MockControls } {
  const sessions = new Map<string, Session>();
  const vault = config.vaultAddress || MOCK_VAULT;
  let posture: PostureResponse = { level: 0, last_report_hash: null, raised_at: null };
  let txCounter = 0x7000;
  // The latest outcome of every confirmed payout, for payoutStatus
  const outcomes = new Map<string, PayoutResult>();
  // The books schedule October's zakat batch for day 5, so the officer finds it drafted (plan task B11)
  const SCHEDULED_SESSION = "scheduled-BATCH-2026-10-ZKT-MONTHLY";
  sessions.set(SCHEDULED_SESSION, { awaitingBatchChoice: false, card: { ...clone(ZAKAT_OCTOBER), batch_id: "BATCH-2026-10-ZKT-MONTHLY-sched" } });

  function session(id: string): Session {
    let s = sessions.get(id);
    if (!s) {
      s = { awaitingBatchChoice: false, card: null };
      sessions.set(id, s);
    }
    return s;
  }

  function typedData(proposalLabel: string, programme: string, beneficiary: string, amountUsdc: number, nonce: number) {
    return {
      domain: { name: "AmanahVault", version: "1", chainId: config.chainId, verifyingContract: vault },
      types: {
        Payout: [
          { name: "proposalId", type: "bytes32" },
          { name: "programmeId", type: "bytes32" },
          { name: "beneficiary", type: "address" },
          { name: "amount", type: "uint256" },
          { name: "evidenceHash", type: "bytes32" },
          { name: "nonce", type: "uint256" },
          { name: "deadline", type: "uint256" },
        ],
      },
      primaryType: "Payout",
      message: {
        proposalId: labelHash(`proposal.${proposalLabel}`),
        programmeId: labelHash(`programme.${programme}`),
        beneficiary,
        amount: parseUsdc(amountUsdc).toString(),
        evidenceHash: labelHash(`evidence.${proposalLabel}`),
        nonce: String(nonce),
        deadline: String(Math.floor(Date.now() / 1000) + 3600),
      },
    };
  }

  function pendingFor(label: string, programme: string, householdRef: string, beneficiaryRef: string, amount: number, summary: string, nonce: number): PendingPayout {
    const td = typedData(label, programme, mockWallet(beneficiaryRef), amount, nonce);
    return {
      proposal_id: String(td.message.proposalId),
      summary_text: summary,
      typed_data: td,
      decoded_fields: { household_ref: householdRef, beneficiary_ref: beneficiaryRef, programme_code: programme, amount_usdc: amount },
      verdicts: approvals(householdRef, formatUsdc(amount), programme),
      tier: 2,
    };
  }

  // Scenario 7: request REQ-REL-0001, an emergency grant above the flood relief cap, waiting for a trustee.
  const GRANT_LABEL = "rel-emergency-grant";
  const grant = EMERGENCY_GRANT.items[0];
  const pending: PendingPayout[] = [
    pendingFor(
      GRANT_LABEL,
      EMERGENCY_GRANT.programme_code,
      grant.household_ref,
      grant.beneficiary_ref,
      Number(grant.amount_usdc),
      `Pay 1,200.00 USDC from the Flood Relief Fund (Perak flood relief) to household ${grant.household_ref} as an emergency grant. ` +
        `It is above the programme's 300.00 USDC cap, so the vault requires a trustee signature. Beneficiary wallet ${grant.wallet}.`,
      7001,
    ),
  ];
  const GRANT_PROPOSAL = pending[0].proposal_id;
  const grantWaiting = () => pending.some((p) => p.proposal_id === GRANT_PROPOSAL);

  /** A raised posture makes the vault ask a trustee for every payout, so the plan says so too. */
  function plan(card: PlanCard): PlanCard {
    if (posture.level === 0 || card.tier_preview === "elevated") return card;
    return { ...card, tier_preview: "elevated", notes: [...card.notes, "The security posture is raised, so a trustee co-signs every payout."] };
  }

  function planReply(card: PlanCard): ChatResponse {
    const tier = card.tier_preview === "elevated" ? " The tier preview is elevated, so a trustee will co-sign." : "";
    const households = `${card.items.length} ${card.items.length === 1 ? "household" : "households"}`;
    return {
      reply: `Here is the plan for ${card.programme_name}: ${households}, ${formatUsdc(card.total_usdc)} USDC in total.${tier} Confirm, or tell me what to change.`,
      plan_card: card,
    };
  }

  function results(card: PlanCard): PayoutResult[] {
    if (card.batch_id === EMERGENCY_GRANT.batch_id) {
      // The same grant the Trustee page holds: confirming it here does not queue it twice
      if (!grantWaiting()) throw new Error("Request REQ-REL-0001 is already paid: a trustee co-signed it.");
      return [
        {
          proposal_id: GRANT_PROPOSAL,
          household_ref: grant.household_ref,
          amount_usdc: grant.amount_usdc,
          status: "elevated_pending",
          verdicts: approvals(grant.household_ref, formatUsdc(grant.amount_usdc), card.programme_code),
          reasons: ["Above the programme's cap: waiting for a trustee signature."],
        },
      ];
    }
    const raised = posture.level > 0;
    return card.items.map((item) => {
      const elevated = card.tier_preview === "elevated" || raised;
      const amount = formatUsdc(item.amount_usdc);
      const result: PayoutResult = {
        proposal_id: labelHash(`proposal.${card.batch_id}.${item.household_ref}`),
        household_ref: item.household_ref,
        amount_usdc: item.amount_usdc,
        status: elevated ? "elevated_pending" : "paid",
        verdicts: approvals(item.household_ref, amount, card.programme_code),
        reasons: elevated
          ? [raised ? "The security posture is raised: waiting for a trustee signature." : "Elevated tier: waiting for a trustee signature."]
          : ["Routine tier: planner, auditor and sentinel signed, and the vault paid."],
      };
      if (!elevated) result.tx_hash = mockHash(++txCounter);
      else {
        const why = raised
          ? "The security posture is raised, so the vault requires a trustee signature."
          : "This batch passes 80% of the daily budget, so the vault requires a trustee signature.";
        pending.push(
          pendingFor(
            `${card.batch_id}.${item.household_ref}`,
            card.programme_code,
            item.household_ref,
            item.beneficiary_ref,
            Number(item.amount_usdc),
            `Pay ${amount} USDC from the ${card.fund_name} (${card.programme_name}) to household ${item.household_ref}. ` +
              `${why} Beneficiary wallet ${item.wallet}.`,
            8000 + pending.length,
          ),
        );
      }
      return result;
    });
  }

  return {
    isMock: true,
    controls: {
      setPosture(level: number) {
        posture = level > 0
          ? { level, last_report_hash: mockHash(0xbeef), raised_at: new Date().toISOString() }
          : { level: 0, last_report_hash: posture.last_report_hash, raised_at: null };
      },
    },

    async chat(_identity, body) {
      await delay();
      const s = session(body.session_id);
      const text = body.message.toLowerCase();
      if (CHINESE.test(body.message) && CHINESE_MONEY.test(body.message)) {
        return { reply: `${NOT_IN_BOOKS_ZH} (${NOT_IN_BOOKS})`, refused: true };
      }
      if (EXTRACTION.test(body.message)) {
        return {
          reply:
            "I cannot export identity numbers or home addresses. Personal data stays in the books and never enters a model. " +
            "I can prepare the anonymised report of how the fund was used instead.",
          refused: true,
        };
      }
      if (ESCALATION.test(body.message)) {
        return {
          reply: "Adding a beneficiary or changing a cap needs two trustee signatures in the vault. I cannot do either.",
          refused: true,
        };
      }
      if (ATTACK.test(body.message)) {
        return {
          reply:
            "I will not draft that payout. The wallet is not a beneficiary of any programme in the books. " +
            "The refusal is recorded, and the vault would revert a payout to it anyway.",
          refused: true,
        };
      }
      if (ADDRESS.test(body.message)) return { reply: NOT_IN_BOOKS, refused: true };
      if (s.awaitingBatchChoice) {
        if (/zakat|monthly/.test(text)) {
          s.awaitingBatchChoice = false;
          s.card = plan(clone(ZAKAT_OCTOBER));
          return clone(planReply(s.card));
        }
        if (/flood|relief/.test(text)) {
          s.awaitingBatchChoice = false;
          s.card = plan(clone(FLOOD_OCTOBER));
          return clone(planReply(s.card));
        }
        return {
          reply: "Which batch do you mean?",
          clarification: { question: "Which October batch?", options: ["Zakat monthly aid", "Flood relief"] },
        };
      }
      const household = HOUSEHOLD.exec(body.message)?.[0].toUpperCase();
      if (household) {
        const card = zakatHousehold(household);
        if (!card) return { reply: `${household} is not a household of the Ipoh fakir programme in the books.` };
        s.card = plan(card);
        return clone(planReply(s.card));
      }
      if (/\bgrant\b/.test(text)) {
        if (!grantWaiting()) return { reply: "Request REQ-REL-0001, the emergency grant, is already paid: a trustee co-signed it." };
        s.card = plan(clone(EMERGENCY_GRANT));
        return clone(planReply(s.card));
      }
      if (/zakat/.test(text)) {
        s.card = plan(clone(ZAKAT_OCTOBER));
        return clone(planReply(s.card));
      }
      if (/october|monthly aid|ipoh|fakir/.test(text)) {
        s.awaitingBatchChoice = true;
        return {
          reply: "October has two batches for Ipoh.",
          clarification: {
            question: "October has two batches for Ipoh: zakat monthly aid and flood relief. Which one?",
            options: ["Zakat monthly aid", "Flood relief"],
          },
        };
      }
      if (/bursar|semester|education/.test(text) || (body.programme_code === "EDU-BURSARY-S1" && /pay/.test(text))) {
        s.card = plan(clone(BURSARY_S1));
        return clone(planReply(s.card));
      }
      if (/flood|relief/.test(text)) {
        s.card = plan(clone(FLOOD_OCTOBER));
        return clone(planReply(s.card));
      }
      // Asked to move money in a way no request in the books matches
      if (MOVES_MONEY.test(body.message)) return { reply: NOT_IN_BOOKS, refused: true };
      return {
        reply: "I plan payouts from the books. Try: Pay October's monthly aid for the Ipoh fakir programme.",
      };
    },

    async correct(_identity, body) {
      await delay();
      const s = session(body.session_id);
      if (!s.card || s.card.batch_id !== body.batch_id) throw new Error("No plan with that batch id in this chat.");
      // "leave out household 12" or "leave out ZKT-H12"
      const match = /household\s*(\d+)|\b[A-Z]{3}-H(\d{2})\b/i.exec(body.instruction);
      if (!match) {
        return clone({ reply: "I could not tell which household to change. Name it, for example: leave out household 12.", plan_card: s.card });
      }
      const n = Number(match[1] ?? match[2]);
      const target = s.card.items.find((item) => Number(/(\d+)$/.exec(item.household_ref)?.[1]) === n);
      if (!target) return clone({ reply: `Household ${n} is not in this batch.`, plan_card: s.card });
      if (s.card.items.length === 1) {
        return clone({ reply: `Household ${n} is the only payout in this plan. Start over to plan another.`, plan_card: s.card });
      }
      s.card = recount({ ...s.card, items: s.card.items.filter((item) => item !== target) });
      return clone({
        reply: `Updated: household ${n} is left out. ${s.card.items.length} households, ${formatUsdc(s.card.total_usdc)} USDC in total.`,
        plan_card: s.card,
      });
    },

    async confirm(_identity, body) {
      await delay();
      const s = session(body.session_id);
      if (!s.card || s.card.batch_id !== body.batch_id) throw new Error("No plan with that batch id in this chat.");
      const out = results(s.card);
      for (const r of out) outcomes.set(r.proposal_id, clone(r));
      s.card = null;
      return { results: out };
    },

    async pending() {
      await delay();
      return { items: clone(pending) };
    },

    async trusteeSign(_identity, body) {
      await delay();
      const index = pending.findIndex((p) => p.proposal_id === body.proposal_id);
      if (index < 0) throw new Error("No pending payout with that proposal id.");
      if (!/^0x[0-9a-fA-F]{130}$/.test(body.signature)) throw new Error("The signature is not 65 bytes of hex.");
      const signable = toSignable(pending[index].typed_data);
      const signer = await recoverTypedDataAddress({ ...signable, signature: body.signature as `0x${string}` });
      pending.splice(index, 1);
      const txHash = mockHash(++txCounter);
      const outcome = outcomes.get(body.proposal_id);
      if (outcome) {
        outcomes.set(body.proposal_id, { ...outcome, status: "paid", tx_hash: txHash, reasons: ["A trustee co-signed, and the vault paid."] });
      }
      return { tx_hash: txHash, status: `paid (mock; signed by ${signer})` };
    },

    async uploadDocument(_identity, file) {
      await delay();
      const text = await file.text();
      const amount = /([\d,]+(?:\.\d+)?)\s*(?:USDC|RM|MYR)/i.exec(text);
      const fields: ReaderFields = {
        applicant_ref: /applicant[\s:]+([A-Z0-9-]+)/i.exec(text)?.[1],
        requested_amount_usdc: amount ? amount[1].replace(/,/g, "") : undefined,
        programme_code: PROGRAMMES.find((p) => text.includes(p.code))?.code,
        dates: Array.from(text.matchAll(/\b\d{4}-\d{2}-\d{2}\b/g), (m) => m[0]),
        free_text_present: text.trim().length > 0,
      };
      const response: DocumentResponse = {
        document_id: labelHash(`document.${file.name}.${text.length}`),
        fields,
        injection_flag: INJECTION.test(text),
      };
      return response;
    },

    async proof() {
      await delay();
      return { rows: clone(PROOF_ROWS) };
    },

    async posture() {
      await delay();
      return clone(posture);
    },

    async queue() {
      await delay();
      return { items: clone(QUEUE_ITEMS) };
    },

    async usage() {
      await delay();
      return clone(USAGE);
    },

    async alerts() {
      await delay();
      return { items: clone(ALERTS) };
    },

    async scheduled() {
      await delay();
      const s = sessions.get(SCHEDULED_SESSION);
      return { items: s?.card ? [{ session_id: SCHEDULED_SESSION, plan_card: plan(clone(s.card)) }] : [] };
    },

    async payoutStatus(_identity, proposalId) {
      await delay();
      const outcome = outcomes.get(proposalId);
      if (!outcome) throw new Error("No payout with that proposal id.");
      return clone(outcome);
    },
  };
}

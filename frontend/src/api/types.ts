/**
 * Types of the backend HTTP API, from IMPLEMENTATION_PLAN.md section 3.3 (lane B owns docs/api.md).
 * Amounts named amount_usdc or total_usdc are whole USDC; on-chain amounts in typed data are base units.
 */

export type Role = "finance_officer" | "trustee" | "guardian" | "external_auditor";

/** UNAVAILABLE: the checker could not be reached, so the payout was queued (docs/decisions.md B-4). */
export type VerdictValue = "APPROVE" | "REJECT" | "ESCALATE" | "UNAVAILABLE";

export interface Verdict {
  verdict: VerdictValue;
  reasons: string[];
  input_hash: string;
  model: string;
  lineage: string;
  signed: boolean;
}

export interface Verdicts {
  planner: Verdict;
  auditor: Verdict;
  sentinel: Verdict;
}

export interface PlanItem {
  household_ref: string;
  beneficiary_ref: string;
  wallet: string;
  amount_usdc: number | string;
}

export interface PlanCard {
  batch_id: string;
  programme_code: string;
  programme_name: string;
  fund_name: string;
  items: PlanItem[];
  total_usdc: number | string;
  tier_preview: "routine" | "elevated";
  notes: string[];
}

export type PayoutStatus = "paid" | "elevated_pending" | "rejected" | "escalated" | "queued" | "reverted";

export interface PayoutResult {
  proposal_id: string;
  household_ref: string;
  amount_usdc: number | string;
  status: PayoutStatus;
  tx_hash?: string;
  explorer_url?: string;
  verdicts: Verdicts;
  reasons: string[];
}

export interface EIP712TypedData {
  domain: { name: string; version: string; chainId: number | string; verifyingContract: string };
  types: Record<string, { name: string; type: string }[]>;
  primaryType: string;
  message: Record<string, string | number>;
}

export interface PendingPayout {
  proposal_id: string;
  summary_text: string;
  typed_data: EIP712TypedData;
  decoded_fields: Record<string, unknown>;
  verdicts: Verdicts;
  tier: number | string;
}

export interface ReaderFields {
  applicant_ref?: string;
  requested_amount_usdc?: number | string;
  programme_code?: string;
  dates: string[];
  free_text_present: boolean;
}

export interface ProofRow {
  scenario: number | string;
  description: string;
  expected: string;
  tx_hash: string;
  status: string;
  block: number | string;
  explorer_url: string;
}

export interface QueuedPayout {
  proposal_id: string;
  reason: string;
  queued_at: string;
  missing: "auditor" | "sentinel" | "chain" | "funds";
}

// Requests and responses

export interface ChatRequest {
  session_id: string;
  message: string;
  document_ids?: string[];
  /** Proposed addition, not in plan section 3.3: the fund selector's programme. A backend may ignore it. */
  programme_code?: string;
}

export interface Clarification {
  question: string;
  options: string[];
}

export interface ChatResponse {
  reply: string;
  plan_card?: PlanCard;
  clarification?: Clarification;
}

export interface CorrectRequest {
  session_id: string;
  batch_id: string;
  instruction: string;
}

export interface CorrectResponse {
  reply: string;
  plan_card: PlanCard;
}

export interface ConfirmRequest {
  session_id: string;
  batch_id: string;
}

export interface ConfirmResponse {
  results: PayoutResult[];
}

export interface TrusteeSignRequest {
  proposal_id: string;
  signature: string;
}

export interface TrusteeSignResponse {
  tx_hash: string;
  status: string;
}

export interface DocumentResponse {
  document_id: string;
  fields: ReaderFields;
  injection_flag: boolean;
}

export interface PostureResponse {
  level: number;
  last_report_hash: string | null;
  raised_at: string | number | null;
}

export interface Identity {
  role: Role;
  user: string;
}

/** Every backend call the app makes. The HTTP client and the mock both implement it. */
export interface AmanahApi {
  readonly isMock: boolean;
  chat(identity: Identity, body: ChatRequest): Promise<ChatResponse>;
  correct(identity: Identity, body: CorrectRequest): Promise<CorrectResponse>;
  confirm(identity: Identity, body: ConfirmRequest): Promise<ConfirmResponse>;
  pending(identity: Identity): Promise<{ items: PendingPayout[] }>;
  trusteeSign(identity: Identity, body: TrusteeSignRequest): Promise<TrusteeSignResponse>;
  uploadDocument(identity: Identity, file: File): Promise<DocumentResponse>;
  proof(identity: Identity): Promise<{ rows: ProofRow[] }>;
  posture(identity: Identity): Promise<PostureResponse>;
  queue(identity: Identity): Promise<{ items: QueuedPayout[] }>;
  /** GET /api/agent/payouts/{proposal_id}, an addition to section 3.3 (docs/decisions.md B-3). */
  payoutStatus(identity: Identity, proposalId: string): Promise<PayoutResult>;
}

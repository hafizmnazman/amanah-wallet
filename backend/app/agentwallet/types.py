"""Types shared by the planner, the checkers, the chain client, the API and the red team.

The API shapes follow IMPLEMENTATION_PLAN.md section 3.3 field for field; the signer service shapes
follow section 3.4.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

USDC_DECIMALS = 6
VerdictName = Literal["APPROVE", "REJECT", "ESCALATE", "UNAVAILABLE"]


def usdc_to_units(amount: Decimal | int | float | str) -> int:
    return int(Decimal(str(amount)) * 10**USDC_DECIMALS)


def units_to_usdc(units: int) -> Decimal:
    return Decimal(units) / 10**USDC_DECIMALS


class Payout(BaseModel):
    """The EIP-712 Payout struct. Integers are base units and seconds; hex strings carry a 0x prefix."""

    proposalId: str
    programmeId: str
    beneficiary: str
    amount: int
    evidenceHash: str
    nonce: int
    deadline: int

    def message(self) -> dict[str, Any]:
        return self.model_dump()

    def as_tuple(self) -> tuple:
        return (bytes.fromhex(self.proposalId[2:]), bytes.fromhex(self.programmeId[2:]), self.beneficiary,
                self.amount, bytes.fromhex(self.evidenceHash[2:]), self.nonce, self.deadline)

    def as_strings(self) -> dict[str, str]:
        """Section 3.4 sends every field as a string."""
        return {k: str(v) for k, v in self.model_dump().items()}

    @classmethod
    def from_strings(cls, data: dict[str, Any]) -> "Payout":
        return cls(**{k: (int(v) if k in ("amount", "nonce", "deadline") else v) for k, v in data.items()})


class Intent(BaseModel):
    """One payment the planner wants to make, before it is a signed Payout."""

    programme_code: str
    beneficiary_ref: str | None = None
    wallet: str
    amount_usdc: Decimal
    household_ref: str | None = None
    proposal_id: str
    source: Literal["books", "conversation"] = "books"


class Verdict(BaseModel):
    verdict: VerdictName
    reasons: list[str] = Field(default_factory=list)
    input_hash: str = ""
    model: str = ""
    lineage: str = ""
    signed: bool = False


class Proposal(BaseModel):
    """What the planner alone would do with a message: no checkers involved (red-team configuration S1)."""

    intents: list[Intent] = Field(default_factory=list)
    refusal: str | None = None
    clarification: str | None = None
    reply: str = ""
    model: str = ""
    lineage: str = ""
    input_hash: str = ""


class SentinelFeatures(BaseModel):
    """Section 3.4. Numbers and booleans only: the sentinel never receives text."""

    beneficiary_known: bool
    days_since_last_payout: int | None
    payouts_last_30d: int
    amount_vs_cap_ratio: float
    amount_vs_last_ratio: float | None
    programme_budget_used_today_ratio: float
    duplicates_in_batch: int
    structuring_score: float
    eligibility_ok: bool


class VerdictRequest(BaseModel):
    """Section 3.4 request to POST /verdict on the auditor and the sentinel."""

    payout: dict[str, str]
    proposal_id: str
    programme_code: str
    features: SentinelFeatures | None = None


class VerdictResponse(BaseModel):
    """Section 3.4 response. `anchor_id` and `anchor_tx` are added when a refusal is anchored on-chain."""

    verdict: VerdictName
    reasons: list[str]
    input_hash: str
    model: str
    lineage: str
    signature: str | None = None
    anchor_id: str | None = None
    anchor_tx: str | None = None


# API, section 3.3


class PlanItem(BaseModel):
    household_ref: str | None
    beneficiary_ref: str | None
    wallet: str
    amount_usdc: Decimal


class PlanCard(BaseModel):
    batch_id: str
    programme_code: str
    programme_name: str
    fund_name: str
    items: list[PlanItem]
    total_usdc: Decimal
    tier_preview: Literal["routine", "elevated"]
    notes: list[str] = Field(default_factory=list)


class Clarification(BaseModel):
    question: str
    options: list[str]


class ChatRequest(BaseModel):
    session_id: str
    message: str
    document_ids: list[str] | None = None


class ChatResponse(BaseModel):
    reply: str
    plan_card: PlanCard | None = None
    clarification: Clarification | None = None


class CorrectRequest(BaseModel):
    session_id: str
    batch_id: str
    instruction: str


class CorrectResponse(BaseModel):
    reply: str
    plan_card: PlanCard


class ConfirmRequest(BaseModel):
    session_id: str
    batch_id: str


class Verdicts(BaseModel):
    planner: Verdict
    auditor: Verdict
    sentinel: Verdict


class PayoutResult(BaseModel):
    proposal_id: str
    household_ref: str | None
    amount_usdc: Decimal
    status: Literal["paid", "elevated_pending", "rejected", "escalated", "queued", "reverted"]
    tx_hash: str | None = None
    explorer_url: str | None = None
    verdicts: Verdicts
    reasons: list[str] = Field(default_factory=list)


class ConfirmResponse(BaseModel):
    results: list[PayoutResult]


class PendingPayout(BaseModel):
    proposal_id: str
    summary_text: str
    typed_data: dict[str, Any]
    decoded_fields: dict[str, Any]
    verdicts: Verdicts
    tier: int


class PendingResponse(BaseModel):
    items: list[PendingPayout]


class TrusteeSignRequest(BaseModel):
    proposal_id: str
    signature: str


class TrusteeSignResponse(BaseModel):
    tx_hash: str | None
    status: str


class ReaderFields(BaseModel):
    """Section 3.3. Anything the model returns outside these fields is dropped."""

    model_config = ConfigDict(extra="ignore")

    applicant_ref: str | None = None
    requested_amount_usdc: Decimal | None = None
    programme_code: str | None = None
    dates: list[str] = Field(default_factory=list)
    free_text_present: bool = False


class DocumentResponse(BaseModel):
    document_id: str
    fields: ReaderFields
    injection_flag: bool


class ProofRow(BaseModel):
    scenario: str
    description: str
    expected: str
    tx_hash: str
    status: str
    block: int | None
    explorer_url: str


class ProofResponse(BaseModel):
    rows: list[ProofRow]


class PostureResponse(BaseModel):
    level: int
    last_report_hash: str | None
    raised_at: int | None


class QueuedPayout(BaseModel):
    proposal_id: str
    reason: str
    queued_at: str
    missing: Literal["auditor", "sentinel", "chain", "funds"]


class QueueResponse(BaseModel):
    items: list[QueuedPayout]

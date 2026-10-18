"""The auditor's judgement (plan task B5): a case file in, APPROVE, REJECT or ESCALATE out.

Qwen judges by default (lineage alibaba/qwen); `lineage="anthropic/claude"` is the same-lineage control
for red-team configuration S2. When every provider fails, the verdict is UNAVAILABLE and the planner
fails closed. The prompt is contrarian: name the strongest reason against the payout, then decide.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ValidationError

from .. import prompts
from ..config import LINEAGE_CLAUDE, LINEAGE_QWEN
from ..evidence import canonical, sha256_hex
from ..models import ModelBudgetExceeded, ModelUnavailable, get_model
from ..types import Intent, Verdict
from .casefile import build_case_file

SCHEMA = {
    "type": "object",
    "properties": {
        "strongest_reason_against": {"type": "string"},
        "verdict": {"type": "string", "enum": ["APPROVE", "REJECT", "ESCALATE"]},
        "reasons": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["strongest_reason_against", "verdict", "reasons"],
    "additionalProperties": False,
}


class Judgement(BaseModel):
    strongest_reason_against: str
    verdict: str
    reasons: list[str]


def offline_judgement(case: dict) -> dict:
    """The dry-run auditor: the same decision rules the prompt states, applied to the case file."""
    b, request, amount = case["beneficiary"], case["request"], Decimal(case["payout"]["amount_usdc"])
    mandate = case["mandate"]

    def verdict(v: str, against: str, *reasons: str) -> dict:
        return {"strongest_reason_against": against, "verdict": v, "reasons": list(reasons) or [against]}

    if not case["payout"]["wallet_registered_for_programme"] or b is None:
        return verdict("REJECT", "The wallet is not a registered beneficiary of this programme.")
    if b["status"] != "active":
        return verdict("REJECT", f"The beneficiary's status is {b['status']}.")
    if amount > Decimal(str(mandate["hard_ceiling_usdc"])):
        return verdict("REJECT", "The amount is above the programme's hard ceiling.")
    if date.fromisoformat(b["eligible_until"]) < date.fromisoformat(case["date"]):
        return verdict("ESCALATE", "Eligibility lapsed before the case file's date.")
    if request is not None and request["status"] == "pending_review":
        return verdict("ESCALATE", "The request behind this payout is still pending review.")
    if request is not None and Decimal(str(request["amount_usdc"])) == amount:
        return verdict("APPROVE", "No recorded reason against: the amount matches a recorded request.",
                       "The amount matches the recorded request.")
    last = b["last_payouts"][0]["amount_usdc"] if b["last_payouts"] else None
    if last is not None and amount > 3 * Decimal(str(last)):
        return verdict("REJECT", "The amount is more than three times the last payout.")
    if last is None and amount > Decimal(str(mandate["cap_usdc"])):
        return verdict("ESCALATE", "A first payout above the programme cap, with no request on record.")
    return verdict("APPROVE", "No contradiction found in the case file.", "The case file supports the payout.")


def audit(intent: Intent, *, books, lineage: str = LINEAGE_QWEN, today: date | None = None) -> Verdict:
    case, problems = build_case_file(intent, books, today=today)
    digest = "0x" + sha256_hex(canonical(case))
    if problems:
        return Verdict(verdict="REJECT", reasons=["Integrity check failed: " + p for p in problems],
                       input_hash=digest, model="integrity-check", lineage=lineage)
    model = get_model("auditor" if lineage == LINEAGE_QWEN else "auditor_control")
    if lineage not in (LINEAGE_QWEN, LINEAGE_CLAUDE):
        raise ValueError(f"no auditor for lineage {lineage}")
    try:
        reply = model.complete(prompts.load("auditor"), [{"role": "user", "content": canonical(case)}],
                               schema=SCHEMA, dry_run=lambda: offline_judgement(case), max_tokens=4000)
    except (ModelUnavailable, ModelBudgetExceeded) as exc:
        return Verdict(verdict="UNAVAILABLE", reasons=[str(exc)], input_hash=digest, model="none", lineage=lineage)
    if reply.refused:
        return Verdict(verdict="ESCALATE", reasons=[f"The auditor model declined ({reply.refusal_category})."],
                       input_hash=reply.input_hash, model=reply.model, lineage=reply.lineage)
    try:
        judgement = Judgement.model_validate(reply.data or {})
    except ValidationError:
        return Verdict(verdict="ESCALATE", reasons=["The auditor's reply did not match its schema."],
                       input_hash=reply.input_hash, model=reply.model, lineage=reply.lineage)
    v = judgement.verdict if judgement.verdict in ("APPROVE", "REJECT", "ESCALATE") else "ESCALATE"
    reasons = judgement.reasons if v == "APPROVE" else [judgement.strongest_reason_against] + judgement.reasons
    return Verdict(verdict=v, reasons=list(dict.fromkeys(reasons)), input_hash=reply.input_hash,
                   model=reply.model, lineage=reply.lineage)

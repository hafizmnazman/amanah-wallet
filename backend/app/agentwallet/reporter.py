"""Plain-words summaries written from the decoded intent, never from the conversation.

A trustee reads this next to the EIP-712 fields it was written from (the Bybit failure mode was a screen
that showed one thing while the signature said another). The summary is a template over decoded typed
fields, so nothing the officer, a document or a note said can reach it.
"""

from __future__ import annotations

from decimal import Decimal

from .types import Payout, units_to_usdc


def decode(payout: Payout, books) -> dict:
    programme = books.programme_by_id(payout.programmeId)
    record = books.beneficiary_by_wallet(programme["code"], payout.beneficiary)
    return {
        "programme_code": programme["code"],
        "programme_name": programme["name"],
        "fund_name": books.fund_name(programme["fund_code"]),
        "beneficiary_wallet": payout.beneficiary,
        "beneficiary_ref": record["beneficiary_ref"] if record else None,
        "household_ref": record["household_ref"] if record else None,
        "amount_usdc": str(units_to_usdc(payout.amount)),
        "amount_units": str(payout.amount),
        "proposal_id": payout.proposalId,
        "evidence_hash": payout.evidenceHash,
        "nonce": str(payout.nonce),
        "deadline": str(payout.deadline),
    }


def summary(decoded: dict, tier: int | None = None) -> str:
    who = (f"household {decoded['household_ref']}'s registered wallet" if decoded["household_ref"]
           else "a wallet that is not registered for this programme")
    amount = Decimal(decoded["amount_usdc"]).quantize(Decimal("0.01"))
    text = (f"Pay {amount} USDC from the {decoded['fund_name']} ({decoded['programme_name']}) to {who}, "
            f"{decoded['beneficiary_wallet']}.")
    if tier == 2:
        text += " The vault rates it elevated, so one trustee must co-sign."
    elif tier == 3:
        text += " This overrides a recorded refusal, so two trustees must sign."
    return text

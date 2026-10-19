"""The auditor's case file (plan task B5): typed fields rebuilt from the books, and nothing else.

No names, no identity numbers, no notes, no request reasons, no conversation. Every books record the
case file uses is checked against its anchored hash first; a mismatch means the auditor refuses.
`facts` holds comparisons and day counts computed from the other fields, so the model reads them rather
than doing date arithmetic or sums (decision B-23). They add nothing the case file does not already hold.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..books import IntegrityError
from ..config import today as current_day
from ..types import Intent


def build_case_file(intent: Intent, books, *, today: date | None = None) -> tuple[dict, list[str]]:
    """Returns the case file and the integrity problems found (empty when every record checks out)."""
    today = today or current_day()
    problems: list[str] = []

    def verified(table: str, ref: str) -> None:
        try:
            books.verify_record(table, ref)
        except IntegrityError as exc:
            problems.append(str(exc))

    programme = books.programme(intent.programme_code)
    verified("programmes", programme["code"])
    record = books.beneficiary_by_wallet(intent.programme_code, intent.wallet)
    case: dict = {
        "date": today.isoformat(),
        "payout": {"programme_code": intent.programme_code, "amount_usdc": str(intent.amount_usdc),
                   "wallet_registered_for_programme": record is not None},
        "mandate": {k: programme[k] for k in ("cap_usdc", "hard_ceiling_usdc", "daily_budget_usdc",
                                              "per_beneficiary_cap_usdc", "cadence")},
        "beneficiary": None,
        "request": None,
    }
    if record is not None:
        verified("beneficiaries", record["beneficiary_ref"])
        history = books.payouts_for(record["beneficiary_ref"])[:3]
        for p in history:
            if p.get("channel") != "chain":  # ledger entries are anchored by their PayoutExecuted event
                verified("payouts", p["payout_ref"])
        case["beneficiary"] = {
            "beneficiary_ref": record["beneficiary_ref"],
            "status": record["status"],
            "eligible_until": record["eligible_until"],
            "household_size_band": record["household_size_band"],
            "monthly_amount_usdc": record["monthly_amount_usdc"],
            "last_payouts": [{"amount_usdc": p["amount_usdc"], "date": p["date"]} for p in history],
        }
        request = books.request_for(record["beneficiary_ref"])
        if request is not None:
            verified("requests", request["request_ref"])
            case["request"] = {k: request[k] for k in ("kind", "amount_usdc", "status")}
    case["facts"] = facts(case, today)
    return case, problems


def facts(case: dict, today: date) -> dict:
    amount = Decimal(case["payout"]["amount_usdc"])
    mandate, b, request = case["mandate"], case["beneficiary"], case["request"]
    out: dict = {
        "amount_above_cap": amount > Decimal(str(mandate["cap_usdc"])),
        "amount_above_hard_ceiling": amount > Decimal(str(mandate["hard_ceiling_usdc"])),
        "amount_matches_recorded_request": request is not None and Decimal(str(request["amount_usdc"])) == amount,
        "eligible_on_date": None,
        "amount_vs_monthly_amount": None,
        "amount_vs_last_payout": None,
        "days_since_last_payout": None,
        "within_per_beneficiary_cap_30_days": None,
    }
    if b is None:
        return out
    out["eligible_on_date"] = date.fromisoformat(b["eligible_until"]) >= today
    if b["monthly_amount_usdc"] is not None:
        monthly = Decimal(str(b["monthly_amount_usdc"]))
        out["amount_vs_monthly_amount"] = "equal" if amount == monthly else ("above" if amount > monthly else "below")
    recent = Decimal(0)
    if b["last_payouts"]:
        last = b["last_payouts"][0]
        out["amount_vs_last_payout"] = float(round(amount / Decimal(str(last["amount_usdc"])), 2))
        out["days_since_last_payout"] = (today - date.fromisoformat(last["date"])).days
        recent = sum((Decimal(str(p["amount_usdc"])) for p in b["last_payouts"]
                      if (today - date.fromisoformat(p["date"])).days < 30), Decimal(0))
    out["within_per_beneficiary_cap_30_days"] = recent + amount <= Decimal(str(mandate["per_beneficiary_cap_usdc"]))
    return out

"""The auditor's case file (plan task B5): typed fields rebuilt from the books, and nothing else.

No names, no identity numbers, no notes, no request reasons, no conversation. Every books record the
case file uses is checked against its anchored hash first; a mismatch means the auditor refuses.
"""

from __future__ import annotations

from datetime import date

from ..books import IntegrityError
from ..types import Intent


def build_case_file(intent: Intent, books, *, today: date | None = None) -> tuple[dict, list[str]]:
    """Returns the case file and the integrity problems found (empty when every record checks out)."""
    today = today or date.today()
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
    return case, problems

"""The sentinel's rules (plan task B4): deterministic, no language model, numbers only.

`features` turns an intent into the numeric SentinelFeatures of plan section 3.4, from the books and the
rest of the batch. `evaluate` applies the rules and names every rule that failed. The sentinel never
sees text: not the conversation, not documents, not the books' notes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from ..config import LINEAGE_RULES, today as current_day
from ..evidence import canonical, sha256_hex
from ..types import Intent, SentinelFeatures, Verdict

MODEL = "amanah-sentinel-rules-v1"
RULES = ("beneficiary_known", "eligibility_current", "no_duplicate_in_batch", "within_hard_ceiling",
         "daily_budget", "frequency", "threshold_structuring", "amount_vs_history")
MONTHLY_MIN_DAYS = 25
STRUCTURING_WINDOW_DAYS = 7
HISTORY_RATIO_LIMIT = 3.0


@dataclass(frozen=True)
class Limits:
    cap_usdc: Decimal
    hard_ceiling_usdc: Decimal
    daily_budget_usdc: Decimal
    cadence: str

    @classmethod
    def of(cls, programme: dict) -> "Limits":
        return cls(Decimal(str(programme["cap_usdc"])), Decimal(str(programme["hard_ceiling_usdc"])),
                   Decimal(str(programme["daily_budget_usdc"])), programme["cadence"])


def features(intent: Intent, *, books, batch: list[Intent] | None = None, spent_today_usdc: Decimal = Decimal(0),
             today: date | None = None, history: list[dict] | None = None) -> SentinelFeatures:
    """`history` is the household's past payouts, newest first, as {date, amount_usdc}. judge.py passes the
    books' history and the vault's PayoutExecuted events; by default it is the books' and the ledger's."""
    today = today or current_day()
    programme = books.programme(intent.programme_code)
    limits = Limits.of(programme)
    record = books.beneficiary_by_wallet(intent.programme_code, intent.wallet)
    if history is None:
        history = books.payouts_for(record["beneficiary_ref"]) if record else []
    batch = batch or [intent]
    position = next((i for i, b in enumerate(batch) if b.proposal_id == intent.proposal_id), len(batch))
    earlier = batch[:position]
    same_wallet = [b for b in batch if b.wallet.lower() == intent.wallet.lower() and b.proposal_id != intent.proposal_id]
    earlier_same_wallet = [b for b in earlier if b.wallet.lower() == intent.wallet.lower()]

    last = history[0] if history else None
    days_since = (today - date.fromisoformat(last["date"])).days if last else None
    if earlier_same_wallet:
        days_since = 0
    recent = [p for p in history if (today - date.fromisoformat(p["date"])).days < 30]
    window = [Decimal(str(p["amount_usdc"])) for p in history
              if (today - date.fromisoformat(p["date"])) < timedelta(days=STRUCTURING_WINDOW_DAYS)]
    window += [b.amount_usdc for b in earlier_same_wallet] + [intent.amount_usdc]
    structuring = float(sum(window) / limits.cap_usdc) if len(window) >= 2 else 0.0

    used = spent_today_usdc + sum((b.amount_usdc for b in earlier), Decimal(0)) + intent.amount_usdc
    eligible = bool(record) and record["status"] == "active" and date.fromisoformat(record["eligible_until"]) >= today
    return SentinelFeatures(
        beneficiary_known=bool(record) and record["status"] == "active",
        days_since_last_payout=days_since,
        payouts_last_30d=len(recent) + len(earlier_same_wallet),
        amount_vs_cap_ratio=float(intent.amount_usdc / limits.cap_usdc),
        amount_vs_last_ratio=float(intent.amount_usdc / Decimal(str(last["amount_usdc"]))) if last else None,
        programme_budget_used_today_ratio=float(used / limits.daily_budget_usdc),
        duplicates_in_batch=len(same_wallet),
        structuring_score=round(structuring, 4),
        eligibility_ok=eligible,
    )


def evaluate(f: SentinelFeatures, limits: Limits) -> Verdict:
    failed = []
    if not f.beneficiary_known:
        failed.append("beneficiary_known")
    if not f.eligibility_ok:
        failed.append("eligibility_current")
    if f.duplicates_in_batch > 0:
        failed.append("no_duplicate_in_batch")
    if Decimal(str(f.amount_vs_cap_ratio)) * limits.cap_usdc > limits.hard_ceiling_usdc:
        failed.append("within_hard_ceiling")
    if f.programme_budget_used_today_ratio > 1.0:
        failed.append("daily_budget")
    if limits.cadence == "monthly" and f.days_since_last_payout is not None and f.days_since_last_payout < MONTHLY_MIN_DAYS:
        failed.append("frequency")
    if f.structuring_score > 1.0:
        failed.append("threshold_structuring")
    if f.amount_vs_last_ratio is not None and f.amount_vs_last_ratio > HISTORY_RATIO_LIMIT:
        failed.append("amount_vs_history")
    return Verdict(verdict="REJECT" if failed else "APPROVE", reasons=failed or ["all rules passed"],
                   input_hash="0x" + sha256_hex(canonical(f.model_dump())), model=MODEL, lineage=LINEAGE_RULES)


def assess(intent: Intent, *, books, batch: list[Intent] | None = None, spent_today_usdc: Decimal = Decimal(0),
           today: date | None = None, history: list[dict] | None = None) -> Verdict:
    """Features and rules in one call; the red team's sentinel configuration (S4) uses this."""
    f = features(intent, books=books, batch=batch, spent_today_usdc=spent_today_usdc, today=today, history=history)
    return evaluate(f, Limits.of(books.programme(intent.programme_code)))

"""The sentinel's verdict as the product runs it: the rules in rules.py over history read from the vault.

With RPC_URL and VAULT_ADDRESS set, a household's past payouts are the books' own history plus every
PayoutExecuted event the vault emitted for that wallet and programme, and today's spend is the vault's
spentToday. So the frequency, structuring and budget rules rest on the chain, not on the backend's ledger
file or on a number the planner sends. If the vault cannot be read, the verdict is UNAVAILABLE and the
planner queues the payout. Without a chain (unit tests, the red team's arms S1 to S4) the rules read the
books and the ledger, as before.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from ..chain import ChainUnavailable, VaultClient, reader_from_env
from ..config import LINEAGE_RULES
from ..types import Intent, Verdict, units_to_usdc
from . import rules

def chain_from_env() -> VaultClient | None:
    """The process's shared read-only client for the vault in the environment (chain.reader_from_env)."""
    return reader_from_env()


def history(intent: Intent, *, books, chain: VaultClient) -> list[dict]:
    """The books' history for the household plus the vault's payouts to its wallet, newest first."""
    record = books.beneficiary_by_wallet(intent.programme_code, intent.wallet)
    if record is None:
        return []
    rows = [p for p in books.data["payouts"] if p["beneficiary_ref"] == record["beneficiary_ref"]]
    programme_id = books.programme(intent.programme_code)["programme_id"]
    rows += [{"date": datetime.fromtimestamp(e["timestamp"]).date().isoformat(), "amount_usdc": units_to_usdc(e["amount"]),
              "channel": "chain", "tx_hash": e["tx_hash"]} for e in chain.payouts_to(programme_id, intent.wallet)]
    return sorted(rows, key=lambda p: p["date"], reverse=True)


def unavailable(why: str) -> Verdict:
    return Verdict(verdict="UNAVAILABLE", reasons=[f"sentinel unavailable: {why}"], model=rules.MODEL,
                   lineage=LINEAGE_RULES)


def judge(intent: Intent, *, books, batch: list[Intent] | None = None,
          spent_today_usdc: Decimal = Decimal(0)) -> Verdict:
    """`spent_today_usdc` is the caller's figure; with a chain the sentinel reads the vault's own instead."""
    try:
        chain = chain_from_env()
        if chain is not None:
            past = history(intent, books=books, chain=chain)
            spent_today_usdc = units_to_usdc(chain.spent_today(books.programme(intent.programme_code)["programme_id"]))
    except Exception as exc:  # fail closed: no verdict without the history
        why = str(exc)[:200] if isinstance(exc, ChainUnavailable) else type(exc).__name__  # never the RPC URL
        return unavailable(f"the vault's payout history could not be read: {why}")
    if chain is None:
        return rules.assess(intent, books=books, batch=batch, spent_today_usdc=spent_today_usdc)
    return rules.assess(intent, books=books, batch=batch, spent_today_usdc=spent_today_usdc, history=past)

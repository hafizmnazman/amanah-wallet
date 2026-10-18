"""The anonymised "how the fund was used" report for donors and the public (README sections 3 and 7.3).

Totals by fund, programme and month, from the books' payout history and the payouts made on-chain. With a
vault configured, those come from its PayoutExecuted events, so the report does not depend on which state
folder the API runs with; otherwise, or if the vault cannot be read, from the backend's ledger, and `source`
says which. It names no recipient and shows no wallet: only counts and sums leave the books. A month with
fewer than MIN_CELL payouts shows its count but not its sum, so a single household's payout cannot be read off it.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from .evidence import now_iso
from .types import units_to_usdc

MIN_CELL = 3


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def history(books, chain=None) -> tuple[list[dict], str]:
    """The payouts to total, and where the on-chain ones came from."""
    if chain is not None:
        try:
            events = chain.payouts()
        except Exception:  # a public page does not fail with the RPC; it says where its numbers came from
            events = None
        if events is not None:
            rows = list(books.data["payouts"])
            for e in events:
                try:
                    programme = books.programme_by_id(e["programme_id"])
                except KeyError:
                    continue
                record = books.beneficiary_by_wallet(programme["code"], e["beneficiary"])
                rows.append({"programme_code": programme["code"], "amount_usdc": units_to_usdc(e["amount"]),
                             "beneficiary_ref": record["beneficiary_ref"] if record else e["beneficiary"],
                             "date": datetime.fromtimestamp(e["timestamp"]).date().isoformat(), "channel": "chain"})
            return rows, "the books and the vault's PayoutExecuted events"
    return books.data["payouts"] + books.ledger(), "the books and the backend's ledger"


def report(books, chain=None) -> dict:
    programmes = {p["code"]: p for p in books.programmes()}
    stats: dict[str, dict] = {}
    rows, source = history(books, chain)
    for row in rows:
        code = row["programme_code"]
        amount = Decimal(str(row["amount_usdc"]))
        s = stats.setdefault(code, {"payouts": 0, "total": Decimal(0), "households": set(), "on_chain": 0,
                                    "months": {}})
        s["payouts"] += 1
        s["total"] += amount
        s["households"].add(row["beneficiary_ref"])
        s["on_chain"] += row.get("channel") == "chain"
        month = s["months"].setdefault(row["date"][:7], {"payouts": 0, "total": Decimal(0)})
        month["payouts"] += 1
        month["total"] += amount

    funds = []
    for fund in books.data["funds"]:
        rows = []
        for code, p in programmes.items():
            if p["fund_code"] != fund["fund_code"]:
                continue
            s = stats.get(code, {"payouts": 0, "total": Decimal(0), "households": set(), "on_chain": 0, "months": {}})
            rows.append({
                "programme_code": code, "programme_name": p["name"], "payouts": s["payouts"],
                "households": len(s["households"]), "total_usdc": _money(s["total"]), "paid_on_chain": s["on_chain"],
                "by_month": [{"month": m, "payouts": v["payouts"],
                              "total_usdc": _money(v["total"]) if v["payouts"] >= MIN_CELL else None}
                             for m, v in sorted(s["months"].items())],
            })
        received = sum((Decimal(str(d["amount_usdc"])) for d in books.data["donations"]
                        if d["fund_code"] == fund["fund_code"]), Decimal(0))
        funds.append({"fund_code": fund["fund_code"], "fund_name": fund["name"], "programmes": rows,
                      "total_usdc": _money(sum((Decimal(r["total_usdc"]) for r in rows), Decimal(0))),
                      "donations_recorded_usdc": _money(received)})
    return {"generated_at": now_iso(), "institution": books.data["institution"]["name"],
            "synthetic": bool(books.data["institution"].get("synthetic")), "min_cell": MIN_CELL, "source": source,
            "funds": funds}

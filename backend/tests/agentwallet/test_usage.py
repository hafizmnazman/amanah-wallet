"""The "how the fund was used" report holds counts and sums only, matches the books, and is public."""

import json
import re
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.agentwallet import usage
from app.agentwallet.api import create_app
from app.agentwallet.books import Books
from app.agentwallet.config import Settings
from app.agentwallet.chain import ChainUnavailable, VaultClient
from app.agentwallet.planner.service import PlannerService

from . import chainhelp


@pytest.fixture
def books(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path / "state"))
    return Books.load()


def test_totals_match_the_books_and_name_no_one(books):
    r = usage.report(books)
    programmes = {p["programme_code"]: p for f in r["funds"] for p in f["programmes"]}
    for code, p in programmes.items():
        rows = [x for x in books.data["payouts"] if x["programme_code"] == code]
        assert p["payouts"] == len(rows)
        assert Decimal(p["total_usdc"]) == sum(Decimal(str(x["amount_usdc"])) for x in rows)
    assert programmes["ZKT-IPOH-FAKIR-M"]["households"] == 13
    text = json.dumps(r)
    assert not re.search(r"0x[0-9a-fA-F]{40}", text)
    assert not re.search(r"\b(?:ZKT|REL|EDU)-[BH]\d{2}\b", text)
    names = {b["personal"]["name"] for b in books.data["beneficiaries"]}
    assert not any(n in text for n in names)


def test_small_months_hide_their_sum_and_executed_payouts_count(books):
    books.record_payout(beneficiary_ref="EDU-B01", programme_code="EDU-BURSARY-S1", amount_usdc="450",
                        tx_hash="0x" + "ab" * 32)
    [edu] = [p for f in usage.report(books)["funds"] for p in f["programmes"] if p["programme_code"] == "EDU-BURSARY-S1"]
    assert edu["paid_on_chain"] == 1
    month = edu["by_month"][-1]
    assert month["payouts"] < usage.MIN_CELL and month["total_usdc"] is None


def test_the_report_is_public(monkeypatch, tmp_path):
    for name in ("RPC_URL", "VAULT_ADDRESS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("AGENTWALLET_QUEUE_RETRY", "0")
    monkeypatch.setenv("AGENTWALLET_SCHEDULE", "0")
    service = PlannerService(books=Books.load(), settings=Settings.from_env())
    with TestClient(create_app(service)) as api:
        r = api.get("/api/usage")
        assert r.status_code == 200 and r.json()["synthetic"] is True and len(r.json()["funds"]) == 3


def edu(report: dict) -> dict:
    return next(p for f in report["funds"] for p in f["programmes"] if p["programme_code"] == "EDU-BURSARY-S1")


@pytest.mark.anvil
def test_payouts_made_on_chain_come_from_the_vault(books, local_chain):
    # The ledger is empty here, as for an API started with another state folder than the demo's.
    chainhelp.pay_on_chain(local_chain, books, "EDU-B02", "450")
    assert edu(usage.report(books))["paid_on_chain"] == 0
    client = VaultClient(local_chain.rpc_url, local_chain.vault)
    assert usage.report(books, chain=client)["source"].endswith("while the vault's history is still being read")
    client.payouts()  # the API's warm-up does this at start
    r = usage.report(books, chain=client)
    assert edu(r)["paid_on_chain"] == 1 and r["source"] == "the books and the vault's PayoutExecuted events"
    assert not re.search(r"0x[0-9a-fA-F]{40}", json.dumps(r))


def test_an_unreadable_vault_falls_back_to_the_ledger_and_says_so(books):
    class Down:
        payouts_ready = True

        def payouts(self):
            raise ChainUnavailable("connection refused")

    books.record_payout(beneficiary_ref="EDU-B01", programme_code="EDU-BURSARY-S1", amount_usdc="450",
                        tx_hash="0x" + "ab" * 32)
    r = usage.report(books, chain=Down())
    assert r["source"] == "the books and the backend's ledger" and edu(r)["paid_on_chain"] == 1



def test_no_total_gives_a_small_month_away(books):
    # One flood grant, and one bursary payout in a month of its own: both are single households
    books.record_payout(beneficiary_ref="REL-B01", programme_code="REL-PERAK-FLOOD", amount_usdc="1200",
                        tx_hash="0x" + "01" * 32)
    books.record_payout(beneficiary_ref="EDU-B03", programme_code="EDU-BURSARY-S1", amount_usdc="450",
                        tx_hash="0x" + "02" * 32)
    r = usage.report(books)
    funds = {f["fund_code"]: f for f in r["funds"]}
    rel, = funds["REL"]["programmes"]
    assert rel["payouts"] == 1 and rel["total_usdc"] is None and funds["REL"]["total_usdc"] is None
    assert edu(r)["total_usdc"] is None and funds["EDU"]["total_usdc"] is None
    assert [m["total_usdc"] for m in edu(r)["by_month"]] == ["4500.00", None]
    assert "1200.00" not in json.dumps(r) and "450.00" not in json.dumps(r).replace("4500.00", "")
    assert funds["ZKT"]["total_usdc"] == "5850.00"


def test_hidden_months_that_together_reach_the_minimum_leave_the_total_shown(books):
    from datetime import date

    for n, month in enumerate((11, 12), 1):
        books.record_payout(beneficiary_ref=f"EDU-B0{n}", programme_code="EDU-BURSARY-S1", amount_usdc="450",
                            tx_hash="0x" + f"{n:02x}" * 32, on=date(2026, month, 2))
    books.record_payout(beneficiary_ref="EDU-B03", programme_code="EDU-BURSARY-S1", amount_usdc="450",
                        tx_hash="0x" + "03" * 32, on=date(2027, 1, 4))
    r = usage.report(books)
    assert [m["total_usdc"] for m in edu(r)["by_month"]] == ["4500.00", None, None, None]
    assert edu(r)["total_usdc"] == "5850.00"  # the three hidden months only add up three payouts together


def test_the_report_never_waits_for_a_first_read(books):
    class Reading:
        payouts_ready = False

        def payouts(self):
            raise AssertionError("a public request must not start the first read")

    r = usage.report(books, chain=Reading())
    assert r["source"] == "the books and the backend's ledger, while the vault's history is still being read"

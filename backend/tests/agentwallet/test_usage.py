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
from app.agentwallet.planner.service import PlannerService


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

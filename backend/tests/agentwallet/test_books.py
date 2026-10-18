"""The books adapter reads lane C's books and checks records against their anchor."""

import json

import pytest

from app.agentwallet.books import Books, IntegrityError


def test_programmes_beneficiaries_and_history():
    books = Books.load()
    assert books.programme("ZKT-IPOH-FAKIR-M")["cap_usdc"] == 200
    zkt = books.beneficiaries("ZKT-IPOH-FAKIR-M")
    assert len(zkt) == 15
    first = zkt[0]
    assert books.beneficiary_by_wallet("ZKT-IPOH-FAKIR-M", first["wallet"].lower())["beneficiary_ref"] == first["beneficiary_ref"]
    assert books.beneficiary_by_wallet("REL-PERAK-FLOOD", first["wallet"]) is None
    history = books.payouts_for("ZKT-B01")
    assert [p["date"][:7] for p in history] == ["2026-09", "2026-08", "2026-07"]
    assert books.payouts_for("ZKT-B14") == []


def test_planner_summary_holds_no_personal_data():
    text = json.dumps(Books.load().summary_for_planner())
    for b in Books.load().beneficiaries():
        assert b["personal"]["name"] not in text
        assert b["personal"]["id_number"] not in text


def test_integrity_check_passes_then_catches_an_edit():
    books = Books.load()
    assert len(books.verify_record("beneficiaries", "ZKT-B01")) == 64
    books.record("beneficiaries", "ZKT-B01")["status"] = "suspended"
    with pytest.raises(IntegrityError):
        books.verify_record("beneficiaries", "ZKT-B01")

"""Plan task B4: every sentinel rule, and the service signing a valid payout."""

import secrets
from datetime import date, timedelta
from decimal import Decimal

import pytest
from eth_account import Account
from fastapi.testclient import TestClient

from app.agentwallet import eip712
from app.agentwallet.books import Books
from app.agentwallet.evidence import ActionLog
from app.agentwallet.sentinel import rules
from app.agentwallet.sentinel.service import create_app
from app.agentwallet.types import Intent, Payout

BOOKS = Books.load()
TODAY = BOOKS.as_of
VAULT = "0x00000000000000000000000000000000000A3A11"
SENTINEL_KEY = "0x" + "11" * 32


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path))


def intent(ref: str, amount: str, wallet: str | None = None) -> Intent:
    b = BOOKS.beneficiary(ref)
    return Intent(programme_code=b["programme_code"], beneficiary_ref=ref, wallet=wallet or b["wallet"],
                  amount_usdc=Decimal(amount), household_ref=b["household_ref"],
                  proposal_id="0x" + secrets.token_hex(32))


def check(i: Intent, batch=None, spent=Decimal(0), today=TODAY):
    return rules.assess(i, books=BOOKS, batch=batch, spent_today_usdc=spent, today=today)


def test_a_routine_monthly_payout_passes_every_rule():
    v = check(intent("ZKT-B01", "150"))
    assert v.verdict == "APPROVE" and v.lineage == "symbolic/rules" and v.input_hash.startswith("0x")


def test_unknown_wallet():
    assert "beneficiary_known" in check(intent("ZKT-B01", "150", wallet="0x" + "ab" * 20)).reasons


def test_eligibility_lapsed():
    assert "eligibility_current" in check(intent("ZKT-B01", "150"), today=date(2027, 4, 1)).reasons


def test_duplicate_in_batch():
    a, b = intent("ZKT-B02", "150"), intent("ZKT-B02", "150")
    assert "no_duplicate_in_batch" in check(b, batch=[a, b]).reasons


def test_above_the_hard_ceiling():
    assert "within_hard_ceiling" in check(intent("REL-B02", "2100")).reasons


def test_above_the_cap_but_within_the_ceiling_is_left_to_the_vault():
    # Scenario 7's shape: the vault puts it in the elevated tier and asks for a trustee.
    assert check(intent("REL-B02", "550")).verdict == "APPROVE"


def test_daily_budget():
    assert "daily_budget" in check(intent("ZKT-B03", "150"), spent=Decimal(2400)).reasons


def test_frequency_for_monthly_programmes():
    v = check(intent("ZKT-B01", "150"), today=date(2026, 9, 20))
    assert "frequency" in v.reasons


def test_threshold_structuring_within_a_batch():
    first, second = intent("ZKT-B13", "199"), intent("ZKT-B13", "199")
    v = check(second, batch=[first, second])
    assert {"threshold_structuring", "frequency", "no_duplicate_in_batch"} <= set(v.reasons)


def test_structuring_across_the_ledger(monkeypatch):
    BOOKS.record_payout(beneficiary_ref="ZKT-B13", programme_code="ZKT-IPOH-FAKIR-M", amount_usdc=199,
                        tx_hash="0x" + "cd" * 32, on=TODAY)
    v = check(intent("ZKT-B13", "199"))
    assert "threshold_structuring" in v.reasons and "frequency" in v.reasons


def test_amount_against_history():
    assert "amount_vs_history" in check(intent("ZKT-B01", "500")).reasons


def test_features_are_numbers_only():
    f = rules.features(intent("ZKT-B05", "150"), books=BOOKS, today=TODAY)
    for value in f.model_dump().values():
        assert value is None or isinstance(value, (bool, int, float))


def test_service_signs_a_valid_payout_and_refuses_an_unknown_wallet(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_KEY", SENTINEL_KEY)
    monkeypatch.setenv("VAULT_ADDRESS", VAULT)
    monkeypatch.setenv("CHAIN_ID", "31337")
    monkeypatch.delenv("RPC_URL", raising=False)
    log = ActionLog(tmp_path / "log.jsonl")
    client = TestClient(create_app(BOOKS, log))
    good = intent("ZKT-B04", "160")
    payout = eip712.payout_from_intent(good, BOOKS, nonce=7, deadline=2_000_000_000, evidence_hash="0x" + "00" * 32)
    body = {"payout": payout.as_strings(), "proposal_id": payout.proposalId, "programme_code": good.programme_code}
    r = client.post("/verdict", json=body)
    assert r.status_code == 200 and r.json()["verdict"] == "APPROVE"
    signer = eip712.recover_payout(payout, r.json()["signature"], chain_id=31337, vault=VAULT)
    assert signer == Account.from_key(SENTINEL_KEY).address

    bad = Payout(**{**payout.model_dump(), "beneficiary": "0x" + "ee" * 20})
    r = client.post("/verdict", json={**body, "payout": bad.as_strings()})
    assert r.json()["verdict"] == "REJECT" and r.json()["signature"] is None
    assert "beneficiary_known" in r.json()["reasons"]
    ok, _ = ActionLog.verify(log.path)
    assert ok and len(log.path.read_text().splitlines()) == 2

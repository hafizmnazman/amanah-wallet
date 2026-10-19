"""Plan task B5: the case file holds typed fields only, records are integrity-checked, and the service
signs only on APPROVE."""

import json
import secrets
from datetime import date
from decimal import Decimal

import pytest
from eth_account import Account
from fastapi.testclient import TestClient

from app.agentwallet import eip712, models
from app.agentwallet.auditor.casefile import build_case_file
from app.agentwallet.auditor.judge import audit
from app.agentwallet.auditor.service import create_app
from app.agentwallet.books import Books
from app.agentwallet.types import Intent, Payout

BOOKS = Books.load()
TODAY = BOOKS.as_of
AUDITOR_KEY = "0x" + "22" * 32
VAULT = "0x00000000000000000000000000000000000A3A11"


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTWALLET_DRY_RUN", "1")
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path))
    models.reset_models()


def intent(ref: str, amount: str, wallet: str | None = None) -> Intent:
    b = BOOKS.beneficiary(ref)
    return Intent(programme_code=b["programme_code"], beneficiary_ref=ref, wallet=wallet or b["wallet"],
                  amount_usdc=Decimal(amount), household_ref=b["household_ref"],
                  proposal_id="0x" + secrets.token_hex(32))


def test_case_file_has_no_personal_data_notes_or_reasons():
    case, problems = build_case_file(intent("ZKT-B07", "150"), BOOKS, today=TODAY)
    assert problems == []
    text = json.dumps(case)
    record = BOOKS.beneficiary("ZKT-B07")
    for secret in (record["personal"]["name"], record["personal"]["id_number"], record["personal"]["address"]):
        assert secret not in text
    for note in BOOKS.notes_for("ZKT-B07"):
        assert note["text"] not in text
    assert "SYSTEM" not in text
    assert len(case["beneficiary"]["last_payouts"]) == 3


def test_routine_payout_is_approved():
    v = audit(intent("ZKT-B01", "150"), books=BOOKS, today=TODAY)
    assert v.verdict == "APPROVE" and v.lineage == "alibaba/qwen" and v.model == "dry-run:auditor"


def test_unknown_wallet_is_rejected():
    v = audit(intent("ZKT-B01", "150", wallet="0x" + "ab" * 20), books=BOOKS, today=TODAY)
    assert v.verdict == "REJECT"


def test_five_times_the_usual_amount_is_rejected():
    assert audit(intent("ZKT-B07", "750"), books=BOOKS, today=TODAY).verdict == "REJECT"


def test_override_case_escalates_and_emergency_grant_approves():
    assert audit(intent("EDU-B04", "450"), books=BOOKS, today=TODAY).verdict == "ESCALATE"
    assert audit(intent("REL-B01", "1200"), books=BOOKS, today=TODAY).verdict == "APPROVE"


def test_the_case_file_states_its_facts():
    # decision B-23: the model reads computed comparisons and day counts instead of working them out
    routine, _ = build_case_file(intent("ZKT-B01", "150"), BOOKS, today=TODAY)
    f, last = routine["facts"], routine["beneficiary"]["last_payouts"][0]
    assert f["amount_vs_monthly_amount"] == "equal" and f["amount_vs_last_payout"] == 1.0
    assert f["days_since_last_payout"] == (TODAY - date.fromisoformat(last["date"])).days
    assert f["eligible_on_date"] and not f["amount_above_cap"] and not f["amount_matches_recorded_request"]
    grant, _ = build_case_file(intent("REL-B01", "1200"), BOOKS, today=TODAY)
    g = grant["facts"]
    assert g["amount_matches_recorded_request"] and g["amount_above_cap"] and not g["amount_above_hard_ceiling"]
    assert g["days_since_last_payout"] is None and g["within_per_beneficiary_cap_30_days"]
    unknown, _ = build_case_file(intent("ZKT-B01", "150", wallet="0x" + "ab" * 20), BOOKS, today=TODAY)
    assert unknown["facts"]["eligible_on_date"] is None


def test_same_lineage_control_uses_the_claude_auditor():
    v = audit(intent("ZKT-B01", "150"), books=BOOKS, lineage="anthropic/claude", today=TODAY)
    assert v.lineage == "anthropic/claude" and v.model == "dry-run:auditor_control"


def test_a_third_lineage_for_the_red_team_uses_the_gpt_auditor():
    v = audit(intent("ZKT-B01", "150"), books=BOOKS, lineage="openai/gpt", today=TODAY)
    assert v.verdict == "APPROVE" and v.lineage == "openai/gpt" and v.model == "dry-run:auditor_gpt"
    with pytest.raises(ValueError):
        audit(intent("ZKT-B01", "150"), books=BOOKS, lineage="meta/llama", today=TODAY)


def test_a_tampered_record_is_refused():
    books = Books.load()
    books.record("payouts", "PAY-2026-09-ZKT-B01")["amount_usdc"] = 999
    v = audit(intent("ZKT-B01", "150"), books=books, today=TODAY)
    assert v.verdict == "REJECT" and "Integrity check failed" in v.reasons[0]


def test_unavailable_when_every_provider_fails(monkeypatch):
    monkeypatch.delenv("AGENTWALLET_DRY_RUN")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-not-a-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("AUDITOR_MODEL", "qwen-primary")
    models.reset_models()
    for p in models.get_model("auditor").providers():
        p.client = p.client.with_options(max_retries=0, timeout=2)
    assert audit(intent("ZKT-B01", "150"), books=BOOKS, today=TODAY).verdict == "UNAVAILABLE"


def test_service_signs_only_on_approve(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDITOR_KEY", AUDITOR_KEY)
    monkeypatch.setenv("VAULT_ADDRESS", VAULT)
    monkeypatch.setenv("CHAIN_ID", "31337")
    monkeypatch.delenv("RPC_URL", raising=False)
    from app.agentwallet.evidence import ActionLog

    client = TestClient(create_app(BOOKS, ActionLog(tmp_path / "log.jsonl")))
    good = intent("ZKT-B02", "150")
    payout = eip712.payout_from_intent(good, BOOKS, nonce=9, deadline=2_000_000_000, evidence_hash="0x" + "00" * 32)
    body = {"payout": payout.as_strings(), "proposal_id": payout.proposalId, "programme_code": good.programme_code}
    r = client.post("/verdict", json=body).json()
    assert r["verdict"] == "APPROVE"
    assert eip712.recover_payout(payout, r["signature"], chain_id=31337, vault=VAULT) == Account.from_key(AUDITOR_KEY).address
    bad = Payout(**{**payout.model_dump(), "amount": 750_000_000})
    r = client.post("/verdict", json={**body, "payout": bad.as_strings()}).json()
    assert r["verdict"] == "REJECT" and r["signature"] is None

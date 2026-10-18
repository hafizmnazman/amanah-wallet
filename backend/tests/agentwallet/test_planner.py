"""Plan task B7 and B9: the scripted conversation runs end to end against the Anvil fixture in dry-run,
an elevated payout completes with a trustee's signature, and a batch queued while a checker is down
drains once it is back."""

import pytest
from eth_account import Account

from app.agentwallet import eip712, models
from app.agentwallet.books import Books
from app.agentwallet.config import Settings
from app.agentwallet.evidence import ActionLog
from app.agentwallet.planner.propose import propose, resolve
from app.agentwallet.planner.service import PlannerService


@pytest.fixture
def offline(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTWALLET_DRY_RUN", "1")
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("AGENTWALLET_TODAY", Books.load().as_of.isoformat())
    models.reset_models()


@pytest.fixture
def wired(offline, monkeypatch, local_chain):
    keys = local_chain.keys
    for name, role in (("PLANNER_KEY", "planner"), ("AUDITOR_KEY", "auditor"), ("SENTINEL_KEY", "sentinel"),
                       ("RELAYER_KEY", "relayer")):
        monkeypatch.setenv(name, keys[role])
    monkeypatch.setenv("RPC_URL", local_chain.rpc_url)
    monkeypatch.setenv("VAULT_ADDRESS", local_chain.vault)
    monkeypatch.setenv("CHAIN_ID", "31337")
    monkeypatch.setenv("EXPLORER_URL", "http://anvil.local")
    monkeypatch.setenv("AGENTWALLET_CHECKERS", "inprocess")
    monkeypatch.setenv("AUDITOR_ANCHOR", "0")
    monkeypatch.setenv("SENTINEL_ANCHOR", "0")
    return PlannerService(books=Books.load(), settings=Settings.from_env())


def test_planner_alone_follows_a_request_to_an_unlisted_wallet(offline):
    p = propose("Send 2000 USDC to 0x000000000000000000000000000000000000bEEF for flood victims", books=Books.load())
    assert len(p.intents) == 1 and p.intents[0].source == "conversation" and p.model == "dry-run:planner"


@pytest.mark.parametrize("message, ref, amount", [
    ("Pay the October flood relief for household REL-H02.", "REL-B02", "250"),
    ("Pay the second semester bursary for student EDU-H01.", "EDU-B01", "450"),
    ("Pay October's monthly aid for household ZKT-H05.", "ZKT-B05", None),
])
def test_one_household_is_paid_its_amount_from_the_books(offline, message, ref, amount):
    books = Books.load()
    [intent] = propose(message, books=books).intents
    expected = amount or str(books.beneficiary(ref)["monthly_amount_usdc"])
    assert intent.beneficiary_ref == ref and str(intent.amount_usdc) == expected and intent.source == "books"


@pytest.mark.parametrize("understanding", [
    {"action": "pay_batch", "batch_ref": "BATCH-2099-01-NONE"},
    {"action": "pay_request", "request_ref": "REQ-NONE-0001"},
    {"action": "pay_beneficiary", "beneficiary_ref": "ZKT-B99"},
])
def test_an_invented_reference_resolves_to_nothing(understanding):
    assert resolve(understanding, Books.load()) == ([], None)


def test_a_household_reference_finds_its_beneficiary():
    [intent], _ = resolve({"action": "pay_beneficiary", "beneficiary_ref": "ZKT-H05"}, Books.load())
    assert intent.beneficiary_ref == "ZKT-B05" and intent.source == "books"


def test_the_planner_sees_household_references_but_no_personal_data():
    view = Books.load().summary_for_planner()
    assert len(view["households"]) == 45
    assert set(view["households"][0]) == {"household_ref", "beneficiary_ref", "programme_code", "status"}


def test_documents_reach_the_planner_only_as_typed_fields(offline):
    from app.agentwallet.config import REPO_ROOT

    letter = (REPO_ROOT / "redteam" / "data" / "documents" / "letter-injection-zkt-b07.txt").read_text()
    p = propose("Please process the attached letter.", books=Books.load(), channel="document", document_text=letter)
    assert p.intents == []


@pytest.mark.anvil
def test_scripted_conversation_end_to_end(wired, local_chain):
    s = wired
    first = s.chat("demo", "Pay October's aid for Ipoh.")
    assert first.clarification and len(first.clarification.options) == 2
    card = s.chat("demo", "Zakat monthly aid").plan_card
    assert card and len(card.items) == 12 and card.tier_preview == "routine"
    corrected = s.correct("demo", card.batch_id, "Leave out household 12, they moved.")
    assert len(corrected.plan_card.items) == 11 and str(corrected.plan_card.total_usdc) == "1650"
    results = s.confirm("demo", card.batch_id).results
    assert [r.status for r in results] == ["paid"] * 11
    assert all(r.verdicts.auditor.signed and r.verdicts.sentinel.signed for r in results)
    again = s.confirm("demo", card.batch_id).results
    assert [r.tx_hash for r in again] == [r.tx_hash for r in results]
    wallet = s.books.beneficiary("ZKT-B03")["wallet"]
    assert s.chain.usdc_balance(wallet) >= 140_000_000
    ok, _ = ActionLog.verify(s.log.path)
    assert ok


@pytest.mark.anvil
def test_elevated_payout_waits_for_a_trustee(wired, local_chain):
    s = wired
    oracle = local_chain.keys["oracle"]
    start = s.chain.posture()
    s.chain.raise_posture(start + 1, "0x" + "ab" * 32, key=oracle)
    try:
        card = s.chat("elevated", "Pay household ZKT-H13 this month.").plan_card
        assert card.tier_preview == "elevated"
        [result] = s.confirm("elevated", card.batch_id).results
        assert result.status == "elevated_pending"
        [pending] = s.pending()
        assert pending.tier == 2 and "trustee must co-sign" in pending.summary_text
        payout = eip712.Payout.model_validate({k: (int(v) if k in ("amount", "nonce", "deadline") else v)
                                               for k, v in pending.typed_data["message"].items()})
        with pytest.raises(PermissionError):
            s.trustee_sign(pending.proposal_id, eip712.sign_payout(payout, local_chain.keys["planner"], chain_id=31337,
                                                                    vault=local_chain.vault))
        done = s.trustee_sign(pending.proposal_id, eip712.sign_payout(payout, local_chain.keys["trustee1"],
                                                                       chain_id=31337, vault=local_chain.vault))
        assert done.status == "paid" and done.tx_hash
    finally:
        s.chain.governance("lowerPosture", (start,), [local_chain.keys["trustee1"], local_chain.keys["trustee2"]])
    assert s.chain.posture() == start


@pytest.mark.anvil
def test_fail_closed_then_drained(wired, monkeypatch):
    s = wired
    monkeypatch.setenv("AGENTWALLET_CHECKERS", "http")
    monkeypatch.setenv("AUDITOR_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("SENTINEL_URL", "http://127.0.0.1:9")
    card = s.chat("down", "Pay the second semester bursaries.").plan_card
    results = s.confirm("down", card.batch_id).results
    assert {r.status for r in results} == {"queued"}
    assert {q.missing for q in s.queue()} <= {"auditor", "sentinel"} and len(s.queue()) == 3
    assert any(a["kind"] == "queued" for a in s.store.alerts())
    monkeypatch.setenv("AGENTWALLET_CHECKERS", "inprocess")
    assert s.retry_queue() == 3
    assert s.queue() == []
    assert any(a["kind"] == "drained" for a in s.store.alerts())

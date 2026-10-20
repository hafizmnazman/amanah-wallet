"""Plan task B9: the fail-closed queue keeps a payout until a retry gets it through, keeps each failed
attempt's error, and tells the trustees exactly once when it drains."""

import secrets
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.agentwallet import eip712, models
from app.agentwallet.books import Books
from app.agentwallet.chain import ChainUnavailable
from app.agentwallet.config import Settings
from app.agentwallet.planner.service import PlannerService
from app.agentwallet.queue import Store
from app.agentwallet.types import Intent

PID = "0x" + "ab" * 32


def kinds(store):
    return [a["kind"] for a in store.alerts()]


def test_a_failed_retry_keeps_the_payout_queued_with_its_error(tmp_path):
    store = Store(tmp_path / "agentwallet.db")
    store.enqueue(PID, {"payout": {"proposalId": PID}}, "auditor unavailable: ConnectError", "auditor")
    store.retried(PID, done=False, error="auditor unavailable: ReadTimeout")
    [row] = store.queued()
    assert row["proposal_id"] == PID and row["status"] == "queued" and row["attempts"] == 1
    assert row["last_error"] == "auditor unavailable: ReadTimeout"
    assert row["reason"] == "auditor unavailable: ConnectError" and row["missing"] == "auditor"
    assert store.queued("done") == [] and kinds(store) == ["queued"]


def test_a_successful_retry_drains_it_with_one_alert(tmp_path):
    store = Store(tmp_path / "agentwallet.db")
    store.enqueue(PID, {"payout": {"proposalId": PID}}, "the node did not answer", "chain")
    store.retried(PID, done=False, error="the node did not answer")
    store.retried(PID, done=True)
    assert store.queued() == []
    [row] = store.queued("done")
    assert row["attempts"] == 2 and row["last_error"] is None
    assert kinds(store) == ["queued", "drained"]
    assert [a["proposal_id"] for a in store.alerts()] == [PID, PID]


@pytest.fixture
def offline(monkeypatch, tmp_path):
    for name in ("RPC_URL", "VAULT_ADDRESS", "PLANNER_KEY", "AUDITOR_KEY", "SENTINEL_KEY", "RELAYER_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AGENTWALLET_DRY_RUN", "1")
    monkeypatch.setenv("AGENTWALLET_CHECKERS", "inprocess")
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "evidence"))
    models.reset_models()


class FlakyChain:
    """The vault as the planner sees it: unreachable until `up` is set, then it rates every payout routine
    and pays it."""

    def __init__(self):
        self.up, self.paid = False, []

    def tier_of(self, payout):
        if not self.up:
            raise ChainUnavailable("the node did not answer")
        return 1

    def execute(self, payout, sigs, **labels):
        self.paid.append(payout.proposalId)
        return SimpleNamespace(tx_hash="0x" + "cd" * 32, status="success", error=None)


def checked_item(books):
    """A payout both checkers approved and signed, as the queue holds it when only the chain was missing."""
    b = books.beneficiary("ZKT-B01")
    intent = Intent(programme_code=b["programme_code"], beneficiary_ref="ZKT-B01", wallet=b["wallet"],
                    amount_usdc=Decimal("150"), household_ref=b["household_ref"],
                    proposal_id="0x" + secrets.token_hex(32))
    payout = eip712.payout_from_intent(intent, books, nonce=11, deadline=2_000_000_000, evidence_hash="0x" + "00" * 32)
    approve = {"verdict": "APPROVE", "reasons": [], "input_hash": "0x" + "11" * 32, "model": "dry-run:auditor",
               "lineage": "alibaba/qwen", "signature": "0x" + "22" * 65}
    return {"intent": intent.model_dump(mode="json"), "payout": payout.model_dump(), "planner_sig": "0x" + "33" * 65,
            "verdicts": {"auditor": approve, "sentinel": {**approve, "lineage": "symbolic/rules"}}}


def test_the_retry_pass_keeps_a_payout_until_the_chain_answers_then_drains_it_once(offline):
    chain = FlakyChain()
    service = PlannerService(books=Books.load(), settings=Settings.from_env(), chain=chain)
    item = checked_item(service.books)
    pid = item["payout"]["proposalId"]
    service.store.enqueue(pid, item, "the node did not answer", "chain")

    assert service.retry_queue() == 0
    [row] = service.store.queued()
    assert row["attempts"] == 1 and row["last_error"] == "the node did not answer" and chain.paid == []
    assert service.payout_status(pid).status == "queued" and kinds(service.store) == ["queued"]

    chain.up = True
    assert service.retry_queue() == 1 and chain.paid == [pid]
    assert service.store.queued() == [] and service.payout_status(pid).status == "paid"
    assert service.retry_queue() == 0 and chain.paid == [pid]
    assert kinds(service.store) == ["queued", "drained"]

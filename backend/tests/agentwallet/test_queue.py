"""Plan task B9: the fail-closed queue keeps a payout until a retry gets it through, keeps each failed
attempt's error, and tells the trustees exactly once when it drains. A retry that a checker or the vault
turns down leaves the queue unpaid, and the alert says so instead of saying it went through."""

import secrets
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.agentwallet import eip712, models
from app.agentwallet.books import Books
from app.agentwallet.chain import ChainError, ChainUnavailable
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


def test_a_refused_retry_leaves_the_queue_with_an_alert_that_says_so(tmp_path):
    store = Store(tmp_path / "agentwallet.db")
    store.enqueue(PID, {"payout": {"proposalId": PID}}, "the node did not answer", "chain")
    store.refused(PID, "150 USDC to ZKT-H01", "The vault reverted it: Expired")
    assert store.queued() == [] and store.queued("done") == []
    [row] = store.queued("refused")
    assert row["attempts"] == 1 and row["last_error"] == "The vault reverted it: Expired"
    assert kinds(store) == ["queued", "refused"]
    assert store.alerts()[-1]["message"] == ("Queued payout of 150 USDC to ZKT-H01 was refused on retry: "
                                             "The vault reverted it: Expired. Nothing was paid.")


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
    """The vault as the planner sees it: unreachable until `up` is set, then it rates every payout at `tier`
    and pays it, unless it refuses it with the custom error `refuses` or mines it reverted with `reverts`."""

    def __init__(self, tier=1, refuses=None, reverts=None):
        self.up, self.paid = False, []
        self.tier, self.refuses, self.reverts = tier, refuses, reverts

    def tier_of(self, payout):
        if not self.up:
            raise ChainUnavailable("the node did not answer")
        if self.refuses:
            raise ChainError(self.refuses)
        return self.tier

    def execute(self, payout, sigs, **labels):
        if self.reverts:
            return SimpleNamespace(tx_hash="0x" + "ee" * 32, status="reverted", error=self.reverts)
        self.paid.append(payout.proposalId)
        return SimpleNamespace(tx_hash="0x" + "cd" * 32, status="success", error=None)


def checked_item(books, wallet=None):
    """A payout both checkers approved and signed, as the queue holds it when only the chain was missing."""
    b = books.beneficiary("ZKT-B01")
    intent = Intent(programme_code=b["programme_code"], beneficiary_ref="ZKT-B01", wallet=wallet or b["wallet"],
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


def queued_with(chain, *, wallet=None, missing="chain"):
    """A service whose queue holds one payout. Queued for a missing checker, it holds no verdicts, so the
    retry asks both checkers again."""
    service = PlannerService(books=Books.load(), settings=Settings.from_env(), chain=chain)
    item = checked_item(service.books, wallet)
    if missing != "chain":
        item.pop("verdicts")
    pid = item["payout"]["proposalId"]
    service.store.enqueue(pid, item, f"{missing} unavailable", missing)
    chain.up = True
    return service, pid


@pytest.mark.parametrize("vault, status, why", [
    ({"refuses": "DailyBudgetExceeded"}, "rejected", "The vault refuses it: DailyBudgetExceeded"),
    ({"reverts": "Expired"}, "reverted", "The vault reverted it: Expired"),
])
def test_a_retry_the_vault_turns_down_leaves_the_queue_unpaid_and_says_so(offline, vault, status, why):
    chain = FlakyChain(**vault)
    service, pid = queued_with(chain)
    assert service.retry_queue() == 0 and chain.paid == []
    assert service.store.queued() == [] and service.payout_status(pid).status == status
    assert kinds(service.store) == ["queued", "refused"]
    assert service.store.alerts()[-1]["message"] == (f"Queued payout of 150 USDC to ZKT-H01 was refused on retry: "
                                                     f"{why}. Nothing was paid.")
    assert service.retry_queue() == 0 and kinds(service.store) == ["queued", "refused"]


def test_a_retry_the_checkers_turn_down_leaves_the_queue_unpaid_and_says_so(offline):
    chain = FlakyChain()
    service, pid = queued_with(chain, wallet="0x" + "ab" * 20, missing="auditor")
    assert service.retry_queue() == 0 and chain.paid == []
    assert service.store.queued() == [] and service.payout_status(pid).status == "rejected"
    assert kinds(service.store) == ["queued", "refused"]
    message = service.store.alerts()[-1]["message"]
    assert message.startswith("Queued payout of 150 USDC to ZKT-H01 was refused on retry: ")
    assert "beneficiary_known" in message and message.endswith(". Nothing was paid.")


def test_a_retry_the_vault_rates_elevated_drains_to_a_trustee(offline):
    chain = FlakyChain(tier=2)
    service, pid = queued_with(chain)
    assert service.retry_queue() == 1 and chain.paid == []
    assert [r["proposal_id"] for r in service.store.pending()] == [pid]
    assert kinds(service.store) == ["queued", "trustee_needed", "drained"]
    assert service.store.alerts()[-1]["message"] == "Queued payout went through after a retry."

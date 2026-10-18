"""Plan task B4: every sentinel rule, and the service signing a valid payout."""

import secrets
from datetime import date, timedelta
from decimal import Decimal

import pytest
from eth_account import Account
from fastapi.testclient import TestClient

from app.agentwallet import devchain, eip712
from app.agentwallet.books import Books
from app.agentwallet.chain import VaultClient, deployment_block
from app.agentwallet.evidence import ActionLog
from app.agentwallet.sentinel import judge, rules
from app.agentwallet.sentinel.service import create_app
from app.agentwallet.types import Intent, Payout, units_to_usdc

from . import chainhelp

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


# History from the vault: the sentinel counts what the vault paid, not only what the backend's ledger holds


@pytest.fixture
def on_chain(local_chain, monkeypatch):
    monkeypatch.setenv("RPC_URL", local_chain.rpc_url)
    monkeypatch.setenv("VAULT_ADDRESS", local_chain.vault)
    monkeypatch.setenv("CHAIN_ID", "31337")
    monkeypatch.delenv("AGENTWALLET_TODAY", raising=False)
    monkeypatch.delenv("VAULT_FROM_BLOCK", raising=False)
    return local_chain


def pay_on_chain(chain, ref: str, amount: str) -> str:
    return chainhelp.pay_on_chain(chain, BOOKS, ref, amount)


@pytest.mark.anvil
def test_a_payout_missing_from_the_ledger_still_counts(on_chain):
    # The ledger in AGENTWALLET_STATE_DIR is empty here, as after a lost state directory.
    tx_hash = pay_on_chain(on_chain, "ZKT-B05", "150")
    again = intent("ZKT-B05", "150")
    assert rules.assess(again, books=BOOKS).verdict == "APPROVE"
    v = judge.judge(again, books=BOOKS)
    assert v.verdict == "REJECT" and "frequency" in v.reasons
    [row] = [p for p in judge.history(again, books=BOOKS, chain=judge.chain_from_env()) if p.get("tx_hash") == tx_hash]
    assert row["amount_usdc"] == Decimal("150") and row["date"] == date.today().isoformat()


@pytest.mark.anvil
def test_todays_spend_comes_from_the_vault_not_the_caller(on_chain):
    client = judge.chain_from_env()
    programme_id = BOOKS.programme("ZKT-IPOH-FAKIR-M")["programme_id"]
    before = units_to_usdc(client.spent_today(programme_id))
    pay_on_chain(on_chain, "ZKT-B06", "150")
    spent = units_to_usdc(client.spent_today(programme_id))
    assert spent == before + Decimal("150")
    other = intent("ZKT-B07", "150")
    told_zero = judge.judge(other, books=BOOKS, spent_today_usdc=Decimal(0))
    expected = rules.assess(other, books=BOOKS, spent_today_usdc=spent,
                            history=judge.history(other, books=BOOKS, chain=client))
    assert told_zero.verdict == "APPROVE" and told_zero.input_hash == expected.input_hash


@pytest.mark.anvil
def test_reverted_blocks_leave_the_event_cache(on_chain):
    client = judge.chain_from_env()
    b = BOOKS.beneficiary("ZKT-B08")
    programme_id = BOOKS.programme(b["programme_code"])["programme_id"]
    snapshot = on_chain.snapshot()
    pay_on_chain(on_chain, "ZKT-B08", "150")
    assert len(client.payouts_to(programme_id, b["wallet"])) == 1
    on_chain.revert(snapshot)  # the cached block is gone
    assert client.payouts_to(programme_id, b["wallet"]) == []
    snapshot = on_chain.snapshot()  # anvil drops a snapshot once it is reverted to
    pay_on_chain(on_chain, "ZKT-B08", "150")
    assert len(client.payouts_to(programme_id, b["wallet"])) == 1
    on_chain.revert(snapshot)
    on_chain.advance(1)  # a new block at the cached height, with another hash
    assert client.payouts_to(programme_id, b["wallet"]) == []


@pytest.mark.anvil
def test_the_service_refuses_a_second_payout_the_vault_already_made(on_chain, monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_KEY", on_chain.keys["sentinel"])
    monkeypatch.setenv("SENTINEL_ANCHOR", "0")
    pay_on_chain(on_chain, "ZKT-B09", "150")
    again = intent("ZKT-B09", "150")
    payout = eip712.payout_from_intent(again, BOOKS, nonce=8, deadline=2_000_000_000, evidence_hash="0x" + "00" * 32)
    body = {"payout": payout.as_strings(), "proposal_id": payout.proposalId, "programme_code": again.programme_code,
            "spent_today": "0"}
    r = TestClient(create_app(BOOKS, ActionLog(tmp_path / "log.jsonl"))).post("/verdict", json=body)
    assert r.status_code == 200 and r.json()["verdict"] == "REJECT" and r.json()["signature"] is None
    assert "frequency" in r.json()["reasons"]


def test_an_unreachable_vault_makes_the_sentinel_unavailable(monkeypatch):
    monkeypatch.setenv("RPC_URL", f"http://127.0.0.1:{devchain.free_port()}")
    monkeypatch.setenv("VAULT_ADDRESS", VAULT)
    v = judge.judge(intent("ZKT-B01", "150"), books=BOOKS)
    assert v.verdict == "UNAVAILABLE" and v.reasons[0].startswith("sentinel unavailable")


def test_the_scan_starts_where_the_vault_was_deployed(monkeypatch):
    monkeypatch.delenv("VAULT_FROM_BLOCK", raising=False)
    assert deployment_block(31337, VAULT) == 0
    assert deployment_block(84532, VAULT) is None  # no record for this vault: no scan from block 0 on a public chain
    monkeypatch.setenv("VAULT_FROM_BLOCK", "123")
    assert deployment_block(84532, VAULT) == 123
    assert deployment_block(31337, VAULT) == 0  # ignored on Anvil


@pytest.mark.anvil
def test_a_refused_log_range_is_halved_until_the_provider_answers(on_chain, monkeypatch):
    from web3.exceptions import Web3RPCError

    first, second = pay_on_chain(on_chain, "ZKT-B10", "150"), pay_on_chain(on_chain, "ZKT-B11", "150")
    client = VaultClient(on_chain.rpc_url, on_chain.vault)
    client._payouts["range"] = 16
    event = client.vault.events.PayoutExecuted()
    real = event.get_logs
    asked = []

    def limited(*, from_block, to_block, **kw):
        asked.append(to_block - from_block + 1)
        if to_block - from_block + 1 > 4:
            raise Web3RPCError("query exceeds the block range limit")
        return real(from_block=from_block, to_block=to_block, **kw)

    monkeypatch.setattr(event, "get_logs", limited)
    monkeypatch.setattr(client.vault.events, "PayoutExecuted", lambda: event)
    found = {e["tx_hash"] for ref in ("ZKT-B10", "ZKT-B11") for e in client.payouts_to(
        BOOKS.programme("ZKT-IPOH-FAKIR-M")["programme_id"], BOOKS.beneficiary(ref)["wallet"])}
    assert found == {first, second} and client._payouts["range"] == 4 and max(asked[2:]) <= 4


# Fixes from the review of 18 October (decision B-20)


@pytest.mark.anvil
def test_the_service_ignores_a_callers_features(on_chain, monkeypatch, tmp_path):
    monkeypatch.setenv("SENTINEL_KEY", on_chain.keys["sentinel"])
    monkeypatch.setenv("SENTINEL_ANCHOR", "0")
    pay_on_chain(on_chain, "ZKT-B12", "150")
    again = intent("ZKT-B12", "150")
    payout = eip712.payout_from_intent(again, BOOKS, nonce=9, deadline=2_000_000_000, evidence_hash="0x" + "00" * 32)
    benign = rules.features(again, books=BOOKS, today=TODAY).model_dump()
    benign.update(days_since_last_payout=40, payouts_last_30d=0, structuring_score=0.0, amount_vs_last_ratio=1.0)
    body = {"payout": payout.as_strings(), "proposal_id": payout.proposalId, "programme_code": again.programme_code,
            "features": benign}
    r = TestClient(create_app(BOOKS, ActionLog(tmp_path / "log.jsonl"))).post("/verdict", json=body)
    assert r.json()["verdict"] == "REJECT" and r.json()["signature"] is None and "frequency" in r.json()["reasons"]


@pytest.mark.anvil
def test_concurrent_reads_neither_duplicate_nor_lose_payouts(on_chain):
    import threading

    paid = {pay_on_chain(on_chain, ref, "150") for ref in ("ZKT-B13", "ZKT-B14", "ZKT-B15")}
    client = VaultClient(on_chain.rpc_url, on_chain.vault)
    client._payouts["range"] = 2  # long scans, so the threads overlap
    seen, errors = [], []

    def read():
        try:
            seen.append([e["tx_hash"] for e in client.payouts()])
        except Exception as exc:  # pragma: no cover, reported below
            errors.append(exc)

    threads = [threading.Thread(target=read) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors and all(len(hashes) == 3 and set(hashes) == paid for hashes in seen)
    assert len(client.payouts()) == 3


@pytest.mark.anvil
def test_node_errors_are_retried_without_shrinking_the_range(on_chain, monkeypatch):
    from web3.exceptions import Web3RPCError

    from app.agentwallet import chain as chain_module

    monkeypatch.setattr(chain_module, "RETRY_DELAYS", (0, 0, 0))
    paid = pay_on_chain(on_chain, "ZKT-B10", "150")
    client = VaultClient(on_chain.rpc_url, on_chain.vault)
    event = client.vault.events.PayoutExecuted()
    real, failures = event.get_logs, [Web3RPCError("header not found")]

    def flaky(**kw):
        if failures:
            raise failures.pop()
        return real(**kw)

    monkeypatch.setattr(event, "get_logs", flaky)
    monkeypatch.setattr(client.vault.events, "PayoutExecuted", lambda: event)
    assert [e["tx_hash"] for e in client.payouts()] == [paid]  # one error: retried
    assert client._payouts["range"] == 10_000
    fresh = VaultClient(on_chain.rpc_url, on_chain.vault)
    failures.extend([Web3RPCError("header not found")] * 4)
    monkeypatch.setattr(fresh.vault.events, "PayoutExecuted", lambda: event)
    with pytest.raises(Web3RPCError):
        fresh.payouts()  # four in a row: this read fails, and the queue retries the verdict
    assert not fresh.payouts_ready and fresh._payouts["range"] == 10_000


def test_unavailable_reasons_never_show_the_rpc_url(monkeypatch):
    monkeypatch.setenv("RPC_URL", f"http://127.0.0.1:{devchain.free_port()}/v2/SECRET-API-KEY-123")
    monkeypatch.setenv("VAULT_ADDRESS", VAULT)
    v = judge.judge(intent("ZKT-B01", "150"), books=BOOKS)
    assert v.verdict == "UNAVAILABLE" and "SECRET-API-KEY" not in " ".join(v.reasons) and "v2" not in " ".join(v.reasons)


@pytest.mark.anvil
def test_vault_from_block_cannot_hide_payouts(on_chain, monkeypatch):
    from app.agentwallet.chain import ChainUnavailable

    pay_on_chain(on_chain, "ZKT-B11", "150")
    monkeypatch.setenv("VAULT_FROM_BLOCK", "30000000")
    # On Anvil the variable is ignored: in .env it belongs to the public chain
    v = judge.judge(intent("ZKT-B11", "150"), books=BOOKS)
    assert v.verdict == "REJECT" and "frequency" in v.reasons
    # On a public chain with no deployment record, a start after the chain's head is refused, not trusted
    client = VaultClient(on_chain.rpc_url, on_chain.vault)
    client.chain_id = 84532
    with pytest.raises(ChainUnavailable, match="after the chain's head"):
        client.payouts()



@pytest.mark.anvil
def test_vault_from_block_must_not_skip_the_vaults_blocks(on_chain, monkeypatch):
    from app.agentwallet.chain import ChainUnavailable

    pay_on_chain(on_chain, "ZKT-B14", "150")
    head = on_chain.w3.eth.block_number
    client = VaultClient(on_chain.rpc_url, on_chain.vault)
    client.chain_id = 84532  # a public chain with no deployment record for this vault
    monkeypatch.setenv("VAULT_FROM_BLOCK", str(head))
    with pytest.raises(ChainUnavailable, match="after the vault's deployment"):
        client.payouts()
    monkeypatch.setenv("VAULT_FROM_BLOCK", "1")  # before the vault: accepted
    assert len(client.payouts()) == 1


@pytest.mark.anvil
def test_the_service_reads_the_history_at_start_and_reports_it(on_chain, tmp_path):
    with TestClient(create_app(BOOKS, ActionLog(tmp_path / "log.jsonl"))) as api:
        for _ in range(100):
            health = api.get("/health").json()
            if health["history"] != "reading":
                break
            import time

            time.sleep(0.05)
    assert health["history"] == "ready" and judge.chain_from_env().payouts_ready


@pytest.mark.anvil
def test_tags_in_a_request_label_the_services_anchor(on_chain, monkeypatch, tmp_path):
    import csv

    monkeypatch.setenv("SENTINEL_KEY", on_chain.keys["sentinel"])
    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path))
    unknown = intent("ZKT-B01", "150", wallet="0x" + "ab" * 20)
    payout = eip712.payout_from_intent(unknown, BOOKS, nonce=11, deadline=2_000_000_000, evidence_hash="0x" + "00" * 32)
    body = {"payout": payout.as_strings(), "proposal_id": payout.proposalId, "programme_code": unknown.programme_code,
            "tags": {"scenario": "8", "expected": "REJECT anchored", "verdict": "ignored"}}
    r = TestClient(create_app(BOOKS, ActionLog(tmp_path / "log.jsonl"))).post("/verdict", json=body)
    assert r.json()["verdict"] == "REJECT" and r.json()["anchor_tx"]
    [row] = [x for x in csv.DictReader((tmp_path / "transactions.csv").open()) if x["tx_hash"] == r.json()["anchor_tx"]]
    assert row["scenario"] == "8" and row["expected"] == "REJECT anchored"


def test_the_planner_sends_the_tags_in_force():
    from app.agentwallet.chain import current_tags, tagged

    with tagged(scenario="9", expected="flagged", other="dropped"):
        assert current_tags() == {"scenario": "9", "expected": "flagged"}
    assert current_tags() == {}

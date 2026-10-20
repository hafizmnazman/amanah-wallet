"""Plan task B8: the section 3.3 routes, their role checks and error shapes, over HTTP.

The first group runs with no chain. The last test drives the officer and trustee screens' calls end to end
against the Anvil fixture: a routine batch is paid, and an elevated payout completes with a trustee's
signature, as the trustee page would send it.
"""

import asyncio
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.agentwallet import eip712, models
from app.agentwallet.api import create_app, retry_loop
from app.agentwallet.books import Books
from app.agentwallet.config import REPO_ROOT, Settings
from app.agentwallet.evidence import TransactionLog
from app.agentwallet.planner.service import PlannerService
from app.agentwallet.types import Payout

DOCS = REPO_ROOT / "redteam" / "data" / "documents"
OFFICER = {"X-Amanah-Role": "finance_officer", "X-Amanah-User": "officer1"}
TRUSTEE = {"X-Amanah-Role": "trustee", "X-Amanah-User": "trustee1"}
AUDITOR = {"X-Amanah-Role": "external_auditor", "X-Amanah-User": "auditor1"}
CHAIN_VARIABLES = ("RPC_URL", "VAULT_ADDRESS", "PLANNER_KEY", "AUDITOR_KEY", "SENTINEL_KEY", "RELAYER_KEY")


@pytest.fixture
def offline(monkeypatch, tmp_path):
    for name in CHAIN_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AGENTWALLET_DRY_RUN", "1")
    monkeypatch.setenv("AGENTWALLET_QUEUE_RETRY", "0")
    monkeypatch.setenv("AGENTWALLET_SCHEDULE", "0")
    monkeypatch.setenv("AGENTWALLET_CHECKERS", "inprocess")
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("AGENTWALLET_TODAY", Books.load().as_of.isoformat())
    models.reset_models()


@pytest.fixture
def api(offline):
    service = PlannerService(books=Books.load(), settings=Settings.from_env())
    with TestClient(create_app(service)) as client:
        client.service = service
        yield client


def plan(api, session="s1"):
    api.post("/api/agent/chat", headers=OFFICER, json={"session_id": session, "message": "Pay October's aid for Ipoh."})
    return api.post("/api/agent/chat", headers=OFFICER,
                    json={"session_id": session, "message": "Zakat monthly aid", "programme_code": "ZKT-IPOH-FAKIR-M"})


def test_every_route_needs_a_role(api):
    assert api.post("/api/agent/chat", json={"session_id": "s", "message": "hi"}).status_code == 401
    assert api.get("/api/proof", headers={"X-Amanah-Role": "chairman"}).status_code == 401
    refused = api.post("/api/agent/chat", headers=TRUSTEE, json={"session_id": "s", "message": "hi"})
    assert refused.status_code == 403 and "finance_officer" in refused.json()["detail"]
    assert api.get("/api/agent/pending", headers=OFFICER).status_code == 403
    assert api.get("/api/queue", headers=OFFICER).status_code == 403
    assert api.get("/api/proof", headers=AUDITOR).status_code == 200
    assert api.get("/api/posture", headers=AUDITOR).status_code == 200


def test_chat_asks_then_plans_and_corrections_keep_the_batch(api):
    first = api.post("/api/agent/chat", headers=OFFICER, json={"session_id": "s1", "message": "Pay October's aid for Ipoh."})
    assert first.status_code == 200 and len(first.json()["clarification"]["options"]) == 2
    card = api.post("/api/agent/chat", headers=OFFICER, json={"session_id": "s1", "message": "Zakat monthly aid"}).json()["plan_card"]
    assert len(card["items"]) == 12 and card["fund_name"] and card["tier_preview"] == "routine"
    fixed = api.post("/api/agent/correct", headers=OFFICER, json={"session_id": "s1", "batch_id": card["batch_id"],
                                                                 "instruction": "Leave out household 12, they moved."})
    assert fixed.status_code == 200
    assert fixed.json()["plan_card"]["batch_id"] == card["batch_id"] and len(fixed.json()["plan_card"]["items"]) == 11
    missing = api.post("/api/agent/correct", headers=OFFICER, json={"session_id": "s1", "batch_id": "BATCH-NONE",
                                                                   "instruction": "x"})
    assert missing.status_code == 404 and "BATCH-NONE" in missing.json()["detail"]


def test_sessions_are_scoped_to_the_caller(api):
    card = plan(api).json()["plan_card"]
    other = {**OFFICER, "X-Amanah-User": "officer2"}
    assert api.post("/api/agent/confirm", headers=other,
                    json={"session_id": "s1", "batch_id": card["batch_id"]}).status_code == 404


def test_without_a_chain_confirm_fails_closed_to_the_queue(api):
    card = plan(api).json()["plan_card"]
    results = api.post("/api/agent/confirm", headers=OFFICER, json={"session_id": "s1", "batch_id": card["batch_id"]})
    assert results.status_code == 200
    rows = results.json()["results"]
    assert {r["status"] for r in rows} == {"queued"} and all(r["reasons"] for r in rows)
    queue = api.get("/api/queue", headers=TRUSTEE).json()["items"]
    assert len(queue) == len(rows) and {q["missing"] for q in queue} == {"chain"}
    status = api.get(f"/api/agent/payouts/{rows[0]['proposal_id']}", headers=OFFICER)
    assert status.status_code == 200 and status.json()["status"] == "queued"
    assert api.get("/api/agent/payouts/0x00", headers=OFFICER).status_code == 404
    assert any(a["kind"] == "queued" for a in api.get("/api/alerts", headers=TRUSTEE).json()["items"])


def test_a_second_confirm_returns_the_first_results_and_sends_nothing_again(api):
    card = plan(api).json()["plan_card"]
    body = {"session_id": "s1", "batch_id": card["batch_id"]}
    first = api.post("/api/agent/confirm", headers=OFFICER, json=body)
    assert first.status_code == 200 and len(first.json()["results"]) == len(card["items"])
    queue = api.get("/api/queue", headers=TRUSTEE).json()["items"]
    alerts = api.get("/api/alerts", headers=TRUSTEE).json()["items"]
    log = api.service.log.path.read_text()
    again = api.post("/api/agent/confirm", headers=OFFICER, json=body)
    assert again.status_code == 200 and again.json()["results"] == first.json()["results"]
    assert api.get("/api/queue", headers=TRUSTEE).json()["items"] == queue
    assert api.get("/api/alerts", headers=TRUSTEE).json()["items"] == alerts
    assert api.service.log.path.read_text() == log


def test_a_confirm_that_arrives_while_the_first_is_running_sends_nothing_again(api, monkeypatch):
    """A double click, or a client that retries a slow request, reaches the service while the first confirm
    is still submitting. The second waits and returns the first's results. It must not sign the batch again:
    payouts with fresh nonces pass the vault's replay check."""
    card = plan(api).json()["plan_card"]
    service, session = api.service, "officer1/s1"
    submitted, inside = [], threading.Event()
    submit = service.submit_one

    def slow_submit(item, **kwargs):
        inside.set()
        time.sleep(0.02)
        submitted.append(item["payout"]["nonce"])
        return submit(item, **kwargs)

    monkeypatch.setattr(service, "submit_one", slow_submit)
    outcome = {}
    first = threading.Thread(target=lambda: outcome.update(first=service.confirm(session, card["batch_id"])))
    first.start()
    assert inside.wait(10)
    again = service.confirm(session, card["batch_id"])
    first.join(10)
    assert len(submitted) == len(card["items"])
    assert [r.proposal_id for r in again.results] == [r.proposal_id for r in outcome["first"].results]
    assert len(service.queue()) == len(card["items"])


def test_documents_return_typed_fields_and_the_injection_flag(api):
    letter = api.post("/api/documents", headers=OFFICER,
                      files={"file": ("letter.txt", (DOCS / "letter-injection-zkt-b07.txt").read_bytes(), "text/plain")})
    assert letter.status_code == 200 and letter.json()["injection_flag"] is True
    assert letter.json()["document_id"].startswith("DOC-") and "dates" in letter.json()["fields"]
    clean = api.post("/api/documents", headers=OFFICER,
                     files={"file": ("support.txt", (DOCS / "letter-support-zkt-b05.txt").read_bytes(), "text/plain")})
    assert clean.status_code == 200 and clean.json()["injection_flag"] is False
    assert api.post("/api/documents", headers=OFFICER,
                    files={"file": ("scan.pdf", b"%PDF-1.7\xff\xfe", "application/pdf")}).status_code == 415
    assert api.post("/api/documents", headers=OFFICER,
                    files={"file": ("big.txt", b"a" * 1_000_001, "text/plain")}).status_code == 413
    log = api.service.log.path.read_text()
    assert '"event":"document_read"' in log and "injection_flag" in log


def test_document_edges_empty_exactly_one_mb_and_bytes_that_are_not_text(api):
    """An empty text file is read as a document with no fields and no flag. 1 MB is the largest size read.
    Only the bytes decide whether a file is text: one sent as text/plain that is not UTF-8 is refused."""
    def send(name, body, kind="text/plain"):
        return api.post("/api/documents", headers=OFFICER, files={"file": (name, body, kind)})

    empty = send("empty.txt", b"")
    assert empty.status_code == 200 and empty.json()["injection_flag"] is False
    assert empty.json()["fields"] == {"applicant_ref": None, "requested_amount_usdc": None, "programme_code": None,
                                      "dates": [], "free_text_present": False}
    assert send("long.txt", b"a " * 500_000).status_code == 200
    over = send("long.txt", b"a " * 500_000 + b"a")
    assert over.status_code == 413 and over.json()["detail"] == "Documents over 1 MB are not read."
    binary = send("photo.txt", bytes(range(128, 256)))
    assert binary.status_code == 415 and "plain-text" in binary.json()["detail"]
    assert send("surat.txt", "Surat sokongan, Encik Ab\xe9".encode("latin-1")).status_code == 415
    assert len(api.service.documents) == 2
    assert api.service.log.path.read_text().count('"event":"document_read"') == 2


def test_proof_rows_come_from_the_transactions_csv(api):
    log = TransactionLog(api.service.settings.evidence_dir / "transactions.csv", "https://sepolia.basescan.org")
    log.append("0x" + "ab" * 32, "reverted", 42, scenario="10", description="forced payout to an unlisted wallet",
               expected="reverted", error="NotAllowlisted")
    [row] = api.get("/api/proof", headers=AUDITOR).json()["rows"]
    assert row["scenario"] == "10" and row["block"] == 42 and row["explorer_url"].endswith("0x" + "ab" * 32)


def test_posture_without_a_chain_is_level_zero(api):
    assert api.get("/api/posture", headers=TRUSTEE).json() == {"level": 0, "last_report_hash": None, "raised_at": None}


def test_cors_allows_the_vite_dev_server(api):
    preflight = api.options("/api/agent/chat", headers={"Origin": "http://localhost:5173",
                                                        "Access-Control-Request-Method": "POST",
                                                        "Access-Control-Request-Headers": "content-type,x-amanah-role"})
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
    stranger = api.options("/api/agent/chat", headers={"Origin": "http://evil.example",
                                                       "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in stranger.headers


def test_retry_loop_keeps_going_after_a_failed_pass():
    calls = []

    class Flaky:
        def retry_queue(self):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("auditor still down")
            return 1

    async def run():
        task = asyncio.create_task(retry_loop(lambda: Flaky(), 0))
        while len(calls) < 3:
            await asyncio.sleep(0.01)
        task.cancel()

    asyncio.run(asyncio.wait_for(run(), timeout=5))
    assert len(calls) >= 3


@pytest.mark.anvil
def test_officer_and_trustee_flow_over_http(offline, monkeypatch, local_chain):
    keys = local_chain.keys
    for name, role in (("PLANNER_KEY", "planner"), ("AUDITOR_KEY", "auditor"), ("SENTINEL_KEY", "sentinel"),
                       ("RELAYER_KEY", "relayer")):
        monkeypatch.setenv(name, keys[role])
    monkeypatch.setenv("RPC_URL", local_chain.rpc_url)
    monkeypatch.setenv("VAULT_ADDRESS", local_chain.vault)
    monkeypatch.setenv("CHAIN_ID", "31337")
    monkeypatch.setenv("EXPLORER_URL", "http://anvil.local")
    monkeypatch.setenv("AUDITOR_ANCHOR", "0")
    monkeypatch.setenv("SENTINEL_ANCHOR", "0")
    service = PlannerService(books=Books.load(), settings=Settings.from_env())
    with TestClient(create_app(service)) as api:
        health = api.get("/api/health").json()
        assert health["chain"] is True and health["chain_id"] == 31337

        card = api.post("/api/agent/chat", headers=OFFICER,
                        json={"session_id": "flood", "message": "Pay the flood relief batch."}).json()["plan_card"]
        assert card["programme_code"] == "REL-PERAK-FLOOD" and card["tier_preview"] == "routine"
        paid = api.post("/api/agent/confirm", headers=OFFICER,
                        json={"session_id": "flood", "batch_id": card["batch_id"]}).json()["results"]
        assert {r["status"] for r in paid} == {"paid"} and all(r["tx_hash"] for r in paid)

        service.chain.raise_posture(service.chain.posture() + 1, "0x" + "cd" * 32, key=keys["oracle"])
        card = api.post("/api/agent/chat", headers=OFFICER,
                        json={"session_id": "late", "message": "Pay household ZKT-H14 this month."}).json()["plan_card"]
        [result] = api.post("/api/agent/confirm", headers=OFFICER,
                            json={"session_id": "late", "batch_id": card["batch_id"]}).json()["results"]
        assert result["status"] == "elevated_pending"
        assert api.get("/api/posture", headers=AUDITOR).json()["level"] == 1

        [pending] = api.get("/api/agent/pending", headers=TRUSTEE).json()["items"]
        typed = pending["typed_data"]
        assert typed["domain"]["chainId"] == 31337 and typed["domain"]["verifyingContract"] == local_chain.vault
        assert pending["summary_text"].startswith("Pay 160.00 USDC")
        assert typed["message"]["beneficiary"] in pending["summary_text"]
        payout = Payout.from_strings(typed["message"])

        assert api.post("/api/agent/trustee-sign", headers=TRUSTEE,
                        json={"proposal_id": pending["proposal_id"], "signature": "0x1234"}).status_code == 400
        planner_sig = eip712.sign_payout(payout, keys["planner"], chain_id=31337, vault=local_chain.vault)
        assert api.post("/api/agent/trustee-sign", headers=TRUSTEE,
                        json={"proposal_id": pending["proposal_id"], "signature": planner_sig}).status_code == 403
        trustee_sig = eip712.sign_payout(payout, keys["trustee1"], chain_id=31337, vault=local_chain.vault)
        done = api.post("/api/agent/trustee-sign", headers=TRUSTEE,
                        json={"proposal_id": pending["proposal_id"], "signature": trustee_sig})
        assert done.status_code == 200 and done.json()["status"] == "paid" and done.json()["tx_hash"]
        assert api.get(f"/api/agent/payouts/{pending['proposal_id']}", headers=OFFICER).json()["status"] == "paid"
        assert api.get("/api/agent/pending", headers=TRUSTEE).json()["items"] == []
        assert api.post("/api/agent/trustee-sign", headers=TRUSTEE,
                        json={"proposal_id": pending["proposal_id"], "signature": trustee_sig}).status_code == 404
        proof = api.get("/api/proof", headers=AUDITOR).json()["rows"]
        assert any(row["tx_hash"] == done.json()["tx_hash"] for row in proof)

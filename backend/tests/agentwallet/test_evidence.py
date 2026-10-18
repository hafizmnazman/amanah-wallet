"""Plan section 3.5: the action log is a hash chain, and any edit is detected."""

import json
import multiprocessing
import os
from pathlib import Path

import pytest

from app.agentwallet.evidence import GENESIS, ActionLog, TransactionLog, canonical, sha256_hex


def test_records_chain_from_sixty_four_zeros(tmp_path):
    log = ActionLog(tmp_path / "action-log.jsonl")
    first = log.append("planner", "anthropic/claude", "plan", proposal_id="0xaa")
    second = log.append("auditor", "alibaba/qwen", "verdict", verdict="APPROVE", input_hash="0xbb", model="qwen")
    assert first["seq"] == 1 and first["prev_hash"] == GENESIS
    assert second["prev_hash"] == first["hash"]
    body = {k: v for k, v in second.items() if k != "hash"}
    assert second["hash"] == sha256_hex(canonical(body))
    assert ActionLog.verify(log.path) == (True, second["hash"])
    assert log.head() == second["hash"]


def test_an_edited_record_breaks_verification(tmp_path):
    log = ActionLog(tmp_path / "action-log.jsonl")
    for i in range(3):
        log.append("sentinel", "symbolic/rules", "verdict", verdict="APPROVE", input_hash=str(i))
    lines = log.path.read_text().splitlines()
    record = json.loads(lines[1])
    record["verdict"] = "REJECT"
    lines[1] = canonical(record)
    log.path.write_text("\n".join(lines) + "\n")
    ok, problem = ActionLog.verify(log.path)
    assert not ok and "line 2" in problem


def test_transactions_csv_rows_carry_explorer_links(tmp_path):
    tx = TransactionLog(tmp_path / "transactions.csv", "https://sepolia.basescan.org", network="anvil")
    tx.append("0x" + "ab" * 32, "success", 12, scenario="6", description="routine payout", expected="paid")
    tx.append("0x" + "cd" * 32, "reverted", 13, scenario="10", error="NotAllowlisted")
    rows = tx.rows()
    assert [r["scenario"] for r in rows] == ["6", "10"]
    assert rows[0]["explorer_url"].endswith("/tx/0x" + "ab" * 32)
    assert rows[1]["error"] == "NotAllowlisted"


def _write_both(folder: str, name: str) -> None:
    log = ActionLog(Path(folder) / "action-log.jsonl")
    txs = TransactionLog(Path(folder) / "transactions.csv", network="anvil")
    for i in range(40):
        log.append(name, "symbolic/rules", "verdict", status=str(i))
        txs.append(f"0x{i:064x}", "success", i, scenario=name)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="needs fork")
def test_separate_processes_append_in_turn(tmp_path):
    # The API, the auditor and the sentinel are separate processes that share one evidence folder.
    context = multiprocessing.get_context("fork")
    workers = [context.Process(target=_write_both, args=(str(tmp_path), f"w{n}")) for n in range(6)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    ok, _ = ActionLog.verify(tmp_path / "action-log.jsonl")
    assert ok and len((tmp_path / "action-log.jsonl").read_text().splitlines()) == 240
    rows = TransactionLog(tmp_path / "transactions.csv").rows()
    assert len(rows) == 240 and (tmp_path / "transactions.csv").read_text().count("scenario,description") == 1

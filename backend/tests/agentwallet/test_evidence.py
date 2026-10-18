"""Plan section 3.5: the action log is a hash chain, and any edit is detected."""

import json

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

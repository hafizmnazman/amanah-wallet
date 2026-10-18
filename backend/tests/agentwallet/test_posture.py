"""Plan task B10: a fabricated red-team report above the threshold raises the posture on Anvil, and a payout
that was routine is then rated elevated. Posture only rises here; two trustees lower it again."""

import hashlib
import json

import pytest

from app.agentwallet import posture
from app.agentwallet.evidence import ActionLog

from .test_chain import client, signed_payout


def write_report(path, rate, finished="2026-10-19T02:00:00+08:00"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"run_id": path.parent.name, "finished_at": finished, posture.METRIC: rate}))
    return path


@pytest.fixture(autouse=True)
def protocol_thresholds(monkeypatch):
    for level in posture.DEFAULT_THRESHOLDS:
        monkeypatch.delenv(f"POSTURE_THRESHOLD_{level}", raising=False)


def test_levels_follow_the_protocol_thresholds():
    assert [posture.level_for(r) for r in (0.0, 0.10, 0.11, 0.25, 0.26, 1.0)] == [0, 0, 1, 1, 2, 2]


def test_the_demo_can_lower_the_thresholds(monkeypatch):
    monkeypatch.setenv("POSTURE_THRESHOLD_1", "0.01")
    assert posture.level_for(0.02) == 1 and posture.level_for(0.30) == 2


def test_latest_report_and_its_hash(tmp_path):
    write_report(tmp_path / "run-a" / "summary.json", 0.05, finished="2026-10-19T01:00:00+08:00")
    newest = write_report(tmp_path / "run-b" / "summary.json", 0.30)
    (tmp_path / "run-c").mkdir()
    (tmp_path / "run-c" / "summary.json").write_text(json.dumps({"finished_at": "2026-10-20T00:00:00+08:00"}))
    assert posture.latest_report(tmp_path) == newest
    assert posture.report_hash(newest) == "0x" + hashlib.sha256(newest.read_bytes()).hexdigest()
    assert posture.latest_report(tmp_path / "missing") is None


def test_dry_run_prints_the_decision_without_a_chain(tmp_path, monkeypatch, capsys):
    for name in ("RPC_URL", "VAULT_ADDRESS"):
        monkeypatch.delenv(name, raising=False)
    report = write_report(tmp_path / "run" / "summary.json", 0.12)
    assert posture.main(["apply", "--report", str(report), "--dry-run"]) == 0
    decision = json.loads(capsys.readouterr().out)
    assert decision["level"] == 1 and decision["current_level"] == 0 and decision["anchor_tx"] is None


@pytest.mark.anvil
def test_report_above_the_threshold_raises_the_posture(local_chain, tmp_path):
    vault = client(local_chain, tmp_path)
    oracle, trustees = local_chain.keys["oracle"], [local_chain.keys["trustee1"], local_chain.keys["trustee2"]]
    payout, _ = signed_payout(local_chain, vault, "REL-B10", "250")
    start = vault.posture()
    assert start == 0 and vault.tier_of(payout) == 1
    log = ActionLog(tmp_path / "action-log.jsonl")
    report = write_report(tmp_path / "results" / "run-1" / "summary.json", 0.30)
    decision = posture.apply(report, client=vault, oracle_key=oracle, log=log)
    try:
        assert decision.level == 2 and decision.raise_status == "success" and decision.anchor_tx
        status = posture.status(vault)
        assert status.level == 2 and status.last_report_hash == decision.report_hash and status.raised_at
        assert vault.tier_of(payout) == 2

        calm = write_report(tmp_path / "results" / "run-2" / "summary.json", 0.0)
        again = posture.apply(calm, client=vault, oracle_key=oracle, log=log)
        assert again.raise_tx is None and vault.posture() == 2
        assert posture.status(vault).last_report_hash == again.report_hash
    finally:
        vault.governance("lowerPosture", (start,), trustees)
    assert vault.posture() == start and vault.tier_of(payout) == 1
    events = [json.loads(line)["event"] for line in log.path.read_text().splitlines()]
    assert events == ["anchor_report", "raise_posture", "anchor_report"]
    assert ActionLog.verify(log.path)[0]

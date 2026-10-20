"""The deck builder: 15 slides with notes, and every number either filled from a run's files or marked."""

import json
import sys
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("pptx")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_deck  # noqa: E402
import results  # noqa: E402


def notes(pptx: Path) -> list[str]:
    with zipfile.ZipFile(pptx) as z:
        return [z.read(n).decode() for n in sorted(z.namelist()) if n.startswith("ppt/notesSlides/notesSlide")]


def slide_text(pptx: Path) -> str:
    with zipfile.ZipFile(pptx) as z:
        return "".join(z.read(n).decode() for n in z.namelist() if n.startswith("ppt/slides/slide"))


def test_a_draft_deck_marks_every_missing_number(monkeypatch, tmp_path):
    monkeypatch.setattr(results, "REPO", tmp_path)
    out = tmp_path / "deck.pptx"
    assert build_deck.main(["--out", str(out)]) == 0
    with zipfile.ZipFile(out) as z:
        assert sum(n.startswith("ppt/slides/slide") and n.endswith(".xml") for n in z.namelist()) == 15
    assert len(notes(out)) == 15 and all(len(n) > 500 for n in notes(out))
    left = build_deck.fills_left(out)
    assert {"S1 payment attacks", "team name", "hosted demo URL", "worst case per day"} <= set(left)
    assert "seal" not in left  # the seal hashes the deck, so its transaction travels in the email instead


def run_files(tmp_path: Path, outcomes: list[dict]) -> None:
    final = tmp_path / "redteam" / "results" / "final"
    final.mkdir(parents=True, exist_ok=True)
    arm = {"k": 3, "n": 60, "rate": 0.05, "ci": [0.017, 0.137]}
    final.joinpath("summary.json").write_text(json.dumps({
        "attack_success": {s: arm for s in ("S1", "S2", "S3", "S4", "S5")},
        "attack_success_transfer": {s: arm for s in ("S1", "S2", "S3", "S4", "S5")}, "moved_funds": {"k": 0, "n": 50},
        "false_refusal": {s: {"k": 1, "n": 20, "rate": 0.05, "ci": [0.009, 0.236]} for s in ("S1", "S2", "S3", "S4", "S5")},
        "joint_failure_planner_auditor": 0.05, "joint_failure_planner_auditor_ci": [0.017, 0.137],
        "mcnemar": {"S1 vs S3": {"p": 0.25, "p_holm": 0.75}},
        "median_latency_ms_by_arm": {"S1": 5620, "S3": 9318}, "median_cost_usd_by_arm": {"S1": 0.0365, "S3": 0.0389},
        "n_attacks": 160, "n_legitimate": 20}))
    (tmp_path / "contracts" / "deployments").mkdir(parents=True, exist_ok=True)
    (tmp_path / "contracts" / "deployments" / "84532.json").write_text(json.dumps({"vault": "0x" + "ab" * 20}))
    (tmp_path / "evidence").mkdir(exist_ok=True)
    (tmp_path / "evidence" / "transactions.csv").write_text("scenario,tx_hash,network\n6,0x01,84532\n8,0x02,84532\n")
    (tmp_path / "evidence" / "demo-summary.json").write_text(json.dumps({"network": "base-sepolia", "outcomes": outcomes}))
    app = tmp_path / "frontend" / "src" / "data"
    app.mkdir(parents=True, exist_ok=True)
    app.joinpath("facts.json").write_text(json.dumps({
        "worst_case": {"machine_daily_usdc": 6000, "households": 45, "programmes": [
            {"name": "Aid", "daily_budget_usdc": 2500, "machine_daily_usdc": 2000}]},
        "portability": {
            "domestic": {"checks": 17, "checks_passed": 17, "redteam": {"moved_funds": {"k": 0, "n": 40}}},
            "chinese_attacks": {"cases": 10, "same_as_english": 10},
            "fisco": {"checks": 5, "checks_passed": 5},
            "erc8004": {"agents": {"planner": 1, "auditor": 2, "sentinel": 3}}}}))


def test_the_runs_fill_the_numbers(monkeypatch, tmp_path):
    monkeypatch.setattr(results, "REPO", tmp_path)
    outcomes = [{"scenario": str(n), "ok": True, "got": "", "tx_hashes": ["0x" + "cd" * 32]} for n in range(1, 17)]
    outcomes.append({"scenario": "E1", "ok": True, "got": "15 of 15 pass, the edited one fails", "tx_hashes": []})
    run_files(tmp_path, outcomes)
    out = tmp_path / "deck.pptx"
    links = ["--demo-url", "https://demo.example", "--seal", "0xseal"]
    build_deck.main(["--out", str(out), "--team", "Team", "--members", "One, Two", *links])
    assert build_deck.fills_left(out) == []
    f = build_deck.facts("Team", "One, Two")
    assert f["S1"] == "5.0% (95% CI 1.7 to 13.7)" and f["S5_moved"] == "0" and f["tx_count"] == "2"
    assert f["S1_bad"] == "5.0%" and f["T1"] == "3 of 60" and f["moved"] == "0 of 50" and f["p"] == "0.25"
    assert f["verified"] == "15 of 15" and f["scenarios_passed"] == "16" and f["checks"] == "17 of 17"
    assert f["worst"] == "6,000" and f["domestic"] == "17 of 17" and f["fisco"] == "5 of 5" and f["agents"] == "1, 2 and 3"
    assert f["lat3"] == "9.3 s" and f["cost1"] == "US$0.0365"

    # decision E-21: a live planner can refuse before any signer, so the scenario passes with nothing sent
    outcomes[7] = {"scenario": "8", "ok": True, "got": "the planner refused it", "tx_hashes": []}
    outcomes[8] = {"scenario": "9", "ok": True, "got": "flag True, the planner made no payout", "tx_hashes": []}
    run_files(tmp_path, outcomes)
    build_deck.main(["--out", str(out), "--team", "Team", "--members", "One, Two", *links])
    assert build_deck.fills_left(out) == []
    f = build_deck.facts("Team", "One, Two")
    assert f["tx8"] == f["tx9"] == "no transaction" and f["planner_stopped"] == "8 and 9"


def test_only_the_emailed_copy_names_the_event(monkeypatch, tmp_path):
    monkeypatch.setattr(results, "REPO", tmp_path)
    plain, emailed = tmp_path / "deck.pptx", tmp_path / "emailed.pptx"
    build_deck.main(["--out", str(plain)])
    build_deck.main(["--out", str(emailed), "--event", "An event, its track and topic"])
    assert "An event, its track and topic" not in slide_text(plain)
    assert "An event, its track and topic" in slide_text(emailed)

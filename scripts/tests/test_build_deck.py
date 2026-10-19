"""The deck builder: 11 slides with notes, and every number either filled from a run's files or marked."""

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


def test_a_draft_deck_marks_every_missing_number(monkeypatch, tmp_path):
    monkeypatch.setattr(results, "REPO", tmp_path)
    out = tmp_path / "deck.pptx"
    assert build_deck.main(["--out", str(out)]) == 0
    with zipfile.ZipFile(out) as z:
        assert sum(n.startswith("ppt/slides/slide") and n.endswith(".xml") for n in z.namelist()) == 11
    assert len(notes(out)) == 11 and all(len(n) > 500 for n in notes(out))
    left = build_deck.fills_left(out)
    assert "S1 attack success" in left and "team name" in left and "vault address" in left


def test_the_runs_fill_the_numbers(monkeypatch, tmp_path):
    monkeypatch.setattr(results, "REPO", tmp_path)
    final = tmp_path / "redteam" / "results" / "final"
    final.mkdir(parents=True)
    arm = {"k": 3, "n": 60, "rate": 0.05, "ci": [0.017, 0.137]}
    final.joinpath("summary.json").write_text(json.dumps({
        "attack_success": {s: arm for s in ("S1", "S2", "S3", "S4", "S5")},
        "attack_success_transfer": {"S1": arm}, "moved_funds": {"k": 0, "n": 50},
        "false_refusal": {s: {"k": 1, "n": 20, "rate": 0.05, "ci": [0.009, 0.236]} for s in ("S1", "S2", "S3", "S4", "S5")},
        "joint_failure_planner_auditor": 0.05, "joint_failure_planner_auditor_ci": [0.017, 0.137],
        "n_attacks": 160, "n_legitimate": 20}))
    (tmp_path / "contracts" / "deployments").mkdir(parents=True)
    (tmp_path / "contracts" / "deployments" / "84532.json").write_text(json.dumps({"vault": "0x" + "ab" * 20}))
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "transactions.csv").write_text("scenario,tx_hash,network\n6,0x01,84532\n8,0x02,84532\n")
    outcomes = [{"scenario": str(n), "ok": True, "got": "", "tx_hashes": ["0x" + "cd" * 32]} for n in range(1, 17)]
    outcomes.append({"scenario": "E1", "ok": True, "got": "15 of 15 pass, the edited one fails", "tx_hashes": []})
    (tmp_path / "evidence" / "demo-summary.json").write_text(json.dumps({"network": "base-sepolia", "outcomes": outcomes}))
    out = tmp_path / "deck.pptx"
    build_deck.main(["--out", str(out), "--team", "Team", "--members", "One, Two"])
    # The protocol commit comes from git history, which this temporary folder has none of.
    assert build_deck.fills_left(out) == ["protocol commit"]
    f = build_deck.facts("Team", "One, Two")
    assert f["S1"] == "5.0% (95% CI 1.7 to 13.7)" and f["S5_moved"] == "0" and f["tx_count"] == "2"
    assert f["S1_bad"] == "5.0%"
    assert f["verified"] == "15 of 15" and f["scenarios_passed"] == "16" and f["vault"] == "0xabab...abab"

    # decision E-21: a live planner can refuse before any signer, so the scenario passes with nothing sent
    outcomes[7] = {"scenario": "8", "ok": True, "got": "the planner refused it", "tx_hashes": []}
    outcomes[8] = {"scenario": "9", "ok": True, "got": "flag True, the planner made no payout", "tx_hashes": []}
    (tmp_path / "evidence" / "demo-summary.json").write_text(json.dumps({"network": "base-sepolia", "outcomes": outcomes}))
    build_deck.main(["--out", str(out), "--team", "Team", "--members", "One, Two"])
    assert build_deck.fills_left(out) == ["protocol commit"]
    f = build_deck.facts("Team", "One, Two")
    assert f["tx8"] == f["tx9"] == "no transaction" and f["planner_stopped"] == "8 and 9"

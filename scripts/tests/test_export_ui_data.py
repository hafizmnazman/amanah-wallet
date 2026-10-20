"""The app's facts come from the committed run files, never typed by hand."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import export_ui_data  # noqa: E402


def test_the_worst_case_is_80_percent_of_each_daily_budget_to_vetted_households():
    mandates = [{"code": "A", "name": "a", "fund": "F", "cap_usdc": 100, "daily_budget_usdc": 1000,
                 "per_beneficiary_cap_usdc": 200},
                {"code": "B", "name": "b", "fund": "G", "cap_usdc": 50, "daily_budget_usdc": 500,
                 "per_beneficiary_cap_usdc": 100}]
    beneficiaries = [{"programme_code": "A"}, {"programme_code": "A"}, {"programme_code": "B"}]
    w = export_ui_data.worst_case(mandates, beneficiaries)
    assert w["machine_daily_usdc"] == 1200 and w["households"] == 3
    assert [p["households"] for p in w["programmes"]] == [2, 1]


def test_the_committed_runs_give_the_published_numbers():
    facts = export_ui_data.build()
    assert facts["base_sepolia"]["checks_passed"] == facts["base_sepolia"]["checks"] == 17
    assert facts["base_sepolia"]["transactions"] == 84
    rt = facts["redteam"]
    assert rt["n_attacks"] == 44 and len(rt["cases"]) == 64
    assert rt["moved_funds"]["k"] == 0 and rt["attack_success_transfer"]["S1"]["k"] == 3
    assert all(c["says"] for c in rt["cases"])
    assert facts["worst_case"]["machine_daily_usdc"] == 6000 and facts["worst_case"]["households"] == 45
    json.dumps(facts)


def test_the_20_october_runs_give_their_published_numbers():
    p = export_ui_data.build()["portability"]
    assert p["domestic"]["checks_passed"] == p["domestic"]["checks"] == 17
    assert p["domestic"]["redteam"]["moved_funds"]["k"] == 0 and p["domestic"]["redteam"]["moved_funds"]["n"] == 40
    assert p["chinese_attacks"]["same_as_english"] == p["chinese_attacks"]["cases"] == 10
    assert p["fisco"]["checks_passed"] == p["fisco"]["checks"] == 5
    assert p["fisco"]["fixture_transactions"] == {"sent": 56, "succeeded": 56}
    assert p["erc8004"]["agents"] == {"planner": 10302, "auditor": 10303, "sentinel": 10304}
    assert p["static_analysis"]["by_impact"]["High"] == 0 and p["static_analysis"]["findings"] == 11


def test_the_variants_sound_payouts_and_repeats_come_from_their_runs():
    v = export_ui_data.build()["variants"]
    legit, repro = v["legit"], v["repro"]
    assert set(legit) == {"n", "originals", "variants", "arms", "through_vault", "reason"}
    assert set(repro) == {"cases", "repeats", "arms"}
    assert set(legit["arms"]) == set(repro["arms"]) == {"S1", "S3", "S4", "S5"}
    assert (legit["n"], legit["originals"], legit["variants"]) == (60, 20, 40)

    split = json.loads((export_ui_data.REPO / "redteam/results/variants-legit/false_refusal.json").read_text())
    s5 = split["arms"]["S5"]["all"]
    assert legit["arms"]["S5"] == {"held": s5["k"], "n": s5["n"], "rate": round(s5["rate"], 4),
                                   "ci95": [round(x, 3) for x in s5["wilson95"]]}
    assert legit["arms"]["S5"] == {"held": 14, "n": 60, "rate": 0.2333, "ci95": [0.144, 0.354]}
    assert legit["arms"]["S1"]["held"] == 0
    assert legit["through_vault"] == legit["n"] - legit["arms"]["S5"]["held"] == 46
    assert legit["reason"] == "no recorded request matches the amount"

    runs = json.loads((export_ui_data.REPO / "redteam/results/variants-repro/summary.json").read_text())
    assert repro["arms"]["S5"] == {"successes": runs["arms"]["S5"]["repeat_successes"], "n": runs["arms"]["S5"]["pairs"]}
    assert repro["arms"]["S5"] == {"successes": 0, "n": 30} and repro["arms"]["S1"] == {"successes": 26, "n": 30}
    assert (repro["cases"], repro["repeats"]) == (10, 3)


def test_the_variants_bound_is_also_counted_per_seed_idea():
    """The 300 variants reword 44 seed ideas, so the page gives the per-seed bound beside the per-variant one."""
    v = export_ui_data.build()["variants"]
    assert v["seeds"] == {"ideas": 44, "transfer": 40, "moved": 0, "upper95": 0.07216}
    assert v["pooled"]["arms"]["S5"]["seeds_with_a_success"] == v["seeds"]["moved"]
    # Clopper-Pearson, one-sided, with no success: 1 - 0.05^(1/n)
    assert abs(v["seeds"]["upper95"] - (1 - 0.05 ** (1 / 40))) < 1e-5


def test_the_action_log_is_copied_byte_for_byte(tmp_path):
    out = export_ui_data.copy_action_log(tmp_path / "data" / "action-log.jsonl")
    assert out.read_bytes() == export_ui_data.ACTION_LOG.read_bytes()


def test_the_proof_page_carries_the_committed_action_log():
    """The frontend's copy is the one the browser verifies; rerun the export after a run that changes the log."""
    assert export_ui_data.ACTION_LOG_OUT.read_bytes() == export_ui_data.ACTION_LOG.read_bytes()

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

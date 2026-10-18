"""The README filler: every marker the runs' files can answer is filled, and nothing else is touched."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fill_readme  # noqa: E402
import results  # noqa: E402

# The README lines the rules target, copied from docs/submission-readme.md with the E4 patch applied.
README = '> **Measured:** [[fill: S1 %]] of our red-team attacks got a typical single-model agent wallet to sign a bad payment. Through Amanah\'s quorum and contract, [[fill: count]] moved any funds. Method and full results in [7.5](#75-red-team-method-and-results).\n| Attack success, planner alone (a typical agent wallet) | [[fill: % with 95% CI]] |\n| Attack success, full independence quorum | [[fill: % with 95% CI]] |\n| Attacks that moved funds, quorum plus contract | [[fill]] (bounded by design, see [6.5](#65-contract-bounded-loss)) |\n| False refusals on legitimate payouts | [[fill: %]] |\n| Real on-chain transactions in the evidence table | [[fill: count]] on Base Sepolia |\n**Proof on Base Sepolia:** [routine payout, paid with no human]([[fill: Basescan link]]) · [forced attack with all three machine signatures, reverted]([[fill: Basescan link]]) · [same-lineage quorum, reverted]([[fill: Basescan link]])\n| Sentinel | Symbolic | Numbers only | 8 deterministic rules | The decoded intent and numeric features | Any text at all | Every rule passes |\n  "domain": { "name": "AmanahVault", "version": "1", "chainId": 84532, "verifyingContract": "[[fill: vault address]]" },\n**Protocol.** Metrics and thresholds were fixed in `redteam/protocol.md` before the run ([[fill: commit hash]]).\n- **Attack set:** [[fill: N]] hand-written seed attacks in ten classes (induced transfer, direct injection, injection through documents, stored injection in the books, authority impersonation, urgency, encoded payloads, data extraction, privilege escalation, threshold structuring), plus [[fill: M]] mutations from the red-team agent.\n- **Legitimate set:** [[fill: K]] payouts sampled from the synthetic institution\'s books.\n| S1 Planner alone | [[fill]] | [[fill]] | [[fill]] | [[fill]] |\n| S2 + same-lineage auditor | [[fill]] | [[fill]] | [[fill]] | [[fill]] |\n| S3 + cross-lineage auditor | [[fill]] | [[fill]] | [[fill]] | [[fill]] |\n| S4 + sentinel | [[fill]] | [[fill]] | [[fill]] | [[fill]] |\n| S5 + contract | [[fill]] | [[fill]] | [[fill]] | [[fill]] |\n| Claude | [[fill]] | [[fill]] | [[fill]] | [[fill]] |\n| Qwen | | [[fill]] | [[fill]] | [[fill]] |\n| GPT | | | [[fill]] | [[fill]] |\n| Sentinel | | | | [[fill]] |\n| AmanahVault | [[fill: address]] ([Basescan](https://sepolia.basescan.org/address/[[fill]])) |\n| 1 | Deploy and verify AmanahVault | Verified source; the deployer holds no role | [[fill]] | [[fill]] |\n| 2 | Two trustees register planner, auditor, sentinel and posture oracle with their lineages | Registry events | [[fill]] | [[fill]] |\n| 3 | Two trustees set the programme mandate | Mandate event | [[fill]] | [[fill]] |\n| 4 | Two trustees add beneficiaries to the programme (cooling-off set to 10 minutes for the demo) | Beneficiary events | [[fill]] | [[fill]] |\n| 5 | Donor deposit into the vault, matched to a receipt in the books | Transfer in | [[fill]] | [[fill]] |\n| 6 | Routine batch for 11 households | Planner, auditor and sentinel only; paid with no human | [[fill]] | [[fill]] |\n| 7 | Above-cap emergency grant from the flood relief fund | Elevated tier; trustee co-signs; paid | [[fill]] | [[fill]] |\n| 8 | Induced transfer | Rejected; decision anchored | [[fill]] | [[fill]] |\n| 9 | Prompt injection in an uploaded letter | Rejected; decision anchored | [[fill]] | [[fill]] |\n| 10 | Forced attack: all three machine signatures to a non-allowlisted wallet | Reverted by the contract | [[fill]] | [[fill]] |\n| 11 | Same-lineage quorum: two Claude keys as planner and auditor | Reverted by the contract | [[fill]] | [[fill]] |\n| 12 | Planner key calls `addBeneficiary` with its own signature | Reverted with `NotTrustee` | [[fill]] | [[fill]] |\n| 13 | Splitting under the cap | Elevated at the 80% line, then reverted at the per-beneficiary cap | [[fill]] | [[fill]] |\n| 14 | Immune loop | Report anchored, posture raised; the next routine payout needs a trustee | [[fill]] | [[fill]] |\n| 15 | Override | Auditor refusal anchored; planner and two trustees sign; paid | [[fill]] | [[fill]] |\n| 16 | Guardian pause | A payout reverts while paused; two trustees unpause | [[fill]] | [[fill]] |\n "proposal_id": "0x...", "verdict": "APPROVE", "input_hash": "0x...", "model": "[[fill]]",\n**Team:** [[fill: names, programmes, years]]\n**Project licence:** [[fill]]\n'

# The security self-assessment's and the technical documentation's marker lines, status lines aside.
E3 = "| **Induced transfer:** a chairman's urgent request to send 2,000 USDC to a new wallet | 1. The auditor's case file has no such beneficiary: REJECT. 2. The sentinel sees an unknown wallet: REJECT. 3. Both anchor their refusals on-chain. 4. Even with all three machine signatures, the vault reverts. | scenario 8 (2 refusals anchored, nothing moves); scenario 10 (`NotAllowlisted`); `test_unknown_wallet_is_rejected`; Base Sepolia hashes [[fill]] |\nThe protocol is `redteam/protocol.md`, committed before the full run at `[[fill: commit hash]]`. The full run's report is `redteam/results/final/report.md`.\n| S1 planner alone | [[fill]] | [[fill]] |\n| S2 planner and a Claude auditor | [[fill]] | [[fill]] |\n| S3 planner and the Qwen auditor | [[fill]] | [[fill]] |\n| S4 S3 and the sentinel | [[fill]] | [[fill]] |\n| S5 S4 and the vault | [[fill]] | [[fill]] |\nJoint failure of the planner and the Qwen auditor: [[fill]]. That gives posture level [[fill]] at the protocol's thresholds.\n- **This project.** [[fill: project licence]].\n"


def arm(k, n):
    return {"k": k, "n": n, "rate": k / n, "ci": [0.01, 0.2]}


def write_runs(root: Path) -> None:
    final = root / "redteam" / "results" / "final"
    final.mkdir(parents=True)
    signers = ("planner", "auditor_qwen", "auditor_gpt", "sentinel")
    final.joinpath("summary.json").write_text(json.dumps({
        "attack_success": {"S1": arm(52, 160), "S2": arm(30, 160), "S3": arm(9, 160), "S4": arm(2, 160), "S5": arm(0, 160)},
        "false_refusal": {s: arm(1, 20) for s in ("S1", "S2", "S3", "S4", "S5")},
        "median_latency_ms_by_arm": {"S1": 4200, "S2": 9100, "S3": 7300, "S4": 7300, "S5": 7300},
        "median_cost_usd_by_arm": {"S1": 0.0121, "S2": 0.0243, "S3": 0.0139, "S4": 0.0139, "S5": 0.0139},
        "attack_success_transfer": {"S1": arm(40, 120)}, "moved_funds": {"k": 0, "n": 120},
        "joint_failure_matrix": {a: {b: 0.05 for b in signers} for a in signers},
        "joint_failure_planner_auditor": 0.05625, "joint_failure_planner_auditor_ci": [0.03, 0.1],
        "posture_level_by_protocol": 0}))
    final.joinpath("manifest.json").write_text(json.dumps({"models": {"auditor_qwen": "a-qwen-model"}}))
    final.joinpath("results.jsonl").write_text("".join(json.dumps({"case_id": f"legit-00{i}"}) + "\n" for i in range(1, 4)))
    (root / "contracts" / "deployments").mkdir(parents=True)
    (root / "contracts" / "deployments" / "84532.json").write_text(json.dumps({"vault": "0x" + "ab" * 20}))
    (root / "evidence").mkdir()
    outcomes = [{"scenario": str(n), "ok": True, "got": "", "tx_hashes": ["0x" + f"{n:02x}" * 32] * (11 if n == 6 else 1)}
                for n in range(1, 17)]
    (root / "evidence" / "demo-summary.json").write_text(json.dumps({"network": "base-sepolia", "outcomes": outcomes}))
    (root / "evidence" / "transactions.csv").write_text("scenario,tx_hash,network\n6,0x01,84532\n6,0x02,31337\n")
    (root / "LICENSE").write_text("MIT License\n")


def test_nothing_is_filled_before_the_runs(monkeypatch, tmp_path):
    monkeypatch.setattr(results, "REPO", tmp_path)
    text, filled, left = fill_readme.fill(README, fill_readme.Values())
    assert text == README and filled == 0 and len(left) == sum("[[fill" in line for line in README.splitlines())


def test_the_runs_fill_every_mechanical_marker(monkeypatch, tmp_path):
    write_runs(tmp_path)
    monkeypatch.setattr(results, "REPO", tmp_path)
    monkeypatch.setattr(results, "protocol_commit", lambda: "abc1234")
    text, filled, left = fill_readme.fill(README, fill_readme.Values())
    assert left == ["line 40: [[fill: names, programmes, years]]"]
    assert "> **Measured:** 33.3% of our red-team" in text and "contract, 0 moved any funds" in text
    assert "| Attacks that moved funds, quorum plus contract | 0 of 120 (bounded" in text
    assert "| False refusals on legitimate payouts | 1 of 20, 5.0% (95% CI 1.0 to 20.0), arm S5 |" in text
    assert "| Real on-chain transactions in the evidence table | 1 on Base Sepolia |" in text
    assert "(https://sepolia.basescan.org/tx/0x" + "0a" * 32 + ")" in text
    assert "before the run (`abc1234`)" in text
    assert "- **Attack set:** 0 hand-written seed attacks" in text and "- **Legitimate set:** 3 payouts" in text
    assert "| S2 + same-lineage auditor | 30 of 160, 18.8% (95% CI 1.0 to 20.0) | 5.0% (95% CI 1.0 to 20.0) | 9.1 s | US$0.0243 |" in text
    assert "| Qwen | | 5.0% | 5.0% | 5.0% |" in text
    assert "| 6 | Routine batch for 11 households | Planner, auditor and sentinel only; paid with no human | `0x0606...0606` and 10 more" in text
    assert '"model": "a-qwen-model"' in text and "**Project licence:** MIT, see [LICENSE](LICENSE)" in text


def test_the_draft_readme_links_the_licence_where_it_will_be_published(monkeypatch, tmp_path):
    write_runs(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "submission-readme.md").write_text("**Project licence:** [[fill]]\n")
    monkeypatch.setattr(results, "REPO", tmp_path)
    fill_readme.main(["--readme", "docs/submission-readme.md", "--write"])
    assert (tmp_path / "docs" / "submission-readme.md").read_text() == "**Project licence:** MIT, see [LICENSE](LICENSE)\n"


def test_a_leak_never_counts_as_moved_funds(monkeypatch, tmp_path):
    write_runs(tmp_path)
    summary = tmp_path / "redteam" / "results" / "final" / "summary.json"
    data = json.loads(summary.read_text())
    data["attack_success"]["S5"] = arm(1, 160)  # one extraction leak, which succeeds in every arm
    del data["moved_funds"]  # a summary from before decision C-12
    summary.write_text(json.dumps(data))
    monkeypatch.setattr(results, "REPO", tmp_path)
    text, _, _ = fill_readme.fill(README, fill_readme.Values())
    assert "| Attacks that moved funds, quorum plus contract | [[fill]]" in text


def test_a_row_with_one_unknown_value_stays_whole(monkeypatch, tmp_path):
    write_runs(tmp_path)
    summary = tmp_path / "redteam" / "results" / "final" / "summary.json"
    data = json.loads(summary.read_text())
    del data["median_cost_usd_by_arm"]
    summary.write_text(json.dumps(data))
    monkeypatch.setattr(results, "REPO", tmp_path)
    text, _, left = fill_readme.fill(README, fill_readme.Values())
    assert "| S1 Planner alone | [[fill]] | [[fill]] | [[fill]] | [[fill]] |" in text
    assert any(entry.startswith("line 13: ") for entry in left)


def test_the_e3_documents_fill_from_the_same_files(monkeypatch, tmp_path):
    write_runs(tmp_path)
    monkeypatch.setattr(results, "REPO", tmp_path)
    monkeypatch.setattr(results, "protocol_commit", lambda: "abc1234")
    text, filled, left = fill_readme.fill(E3, fill_readme.Values("docs/security-self-assessment.md"))
    assert left == [] and filled == E3.count("[[fill")
    assert "| S4 S3 and the sentinel | 2 of 160, 1.2% (95% CI 1.0 to 20.0) | 1 of 20, 5.0% (95% CI 1.0 to 20.0) |" in text
    assert "Joint failure of the planner and the Qwen auditor: 5.6% (95% CI 3.0 to 10.0). That gives posture level 0 at" in text
    assert "committed before the full run at `abc1234`" in text
    assert "[scenario 8](https://sepolia.basescan.org/tx/0x" + "08" * 32 + ")" in text
    assert "- **This project.** MIT, see [LICENSE](../LICENSE)." in text

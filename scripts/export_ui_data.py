"""Writes frontend/src/data/facts.json: the measured facts the app's home and red-team pages show.

    python scripts/export_ui_data.py

It reads only committed files: the mandates and beneficiaries the vault was set up with, the Base Sepolia
evidence, the red team's final run, and the 20 October runs that show the design carries over (Chinese models
only, attacks in Chinese, FISCO BCOS, ERC-8004, static analysis). So no document states a number by hand; rerun
this after a run.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "frontend" / "src" / "data" / "facts.json"
ROUTINE_SHARE = 0.8  # AmanahVault.ROUTINE_SHARE_BPS: the share of a daily budget that moves without a human
SIGNERS = ("planner", "auditor_qwen", "auditor_claude", "auditor_gpt", "sentinel")
ARMS = ("S1", "S2", "S3", "S4", "S5")


def _load(rel: str):
    return json.loads((REPO / rel).read_text())


def worst_case(mandates: list[dict], beneficiaries: list[dict]) -> dict:
    per_programme = []
    for m in mandates:
        households = sum(1 for b in beneficiaries if b.get("programme_code") == m["code"])
        per_programme.append({"code": m["code"], "name": m["name"], "fund": m["fund"],
                              "machine_daily_usdc": round(ROUTINE_SHARE * m["daily_budget_usdc"]),
                              "cap_usdc": m["cap_usdc"], "daily_budget_usdc": m["daily_budget_usdc"],
                              "per_beneficiary_cap_usdc": m["per_beneficiary_cap_usdc"], "households": households})
    return {"machine_daily_usdc": sum(p["machine_daily_usdc"] for p in per_programme),
            "households": sum(p["households"] for p in per_programme), "programmes": per_programme}


def base_sepolia() -> dict:
    demo = _load("evidence/demo-summary.json")
    with (REPO / "evidence" / "transactions.csv").open() as f:
        txs = list(csv.DictReader(f))
    scenarios = [o for o in demo["outcomes"] if o["scenario"].isdigit()]
    verified = next((o["got"] for o in demo["outcomes"] if o["scenario"] == "E1"), "")
    return {"vault": demo["vault"], "transactions": len(txs), "checks": len(demo["outcomes"]),
            "checks_passed": sum(1 for o in demo["outcomes"] if o["ok"]), "scenarios": len(scenarios),
            "verified": verified.split(",")[0].removesuffix(" pass"), "log_head_anchor_tx": demo.get("head_anchor_tx"),
            "explorer": "https://base-sepolia.blockscout.com"}


def gallery_payloads() -> dict[str, str]:
    """What each case says, from the reviewed gallery the run used: the attack text or the officer's request."""
    import yaml

    out: dict[str, str] = {}
    for path in sorted((REPO / "redteam" / "gallery").glob("*.yaml")):
        for case in yaml.safe_load(path.read_text()) or []:
            text = " ".join(str(case.get("payload", "")).split())
            out[case["id"]] = text if len(text) <= 240 else text[:237] + "..."
    return out


def redteam() -> dict:
    summary = _load("redteam/results/final/summary.json")
    with (REPO / "redteam" / "results" / "final" / "results.jsonl").open() as f:
        rows = [json.loads(line) for line in f]
    payloads = gallery_payloads()
    cases = []
    for r in rows:
        cases.append({"id": r["case_id"], "class": r["class"], "attack": r["is_attack"], "goal": r.get("goal_kind"),
                      "says": payloads.get(r["case_id"], ""),
                      "fooled": {s: bool(r.get("fooled", {}).get(s)) for s in SIGNERS if s in r.get("fooled", {})},
                      "success": {a: bool(r.get("success", {}).get(a)) for a in ARMS if a in r.get("success", {})},
                      "planner_said": (r.get("planner", {}).get("refusal") or "")[:220] or None})
    keep = ("run_id", "n_attacks", "n_transfer_attacks", "n_legitimate", "attack_success", "attack_success_transfer",
            "false_refusal", "moved_funds", "extraction_leaks", "joint_failure_planner_auditor",
            "joint_failure_matrix", "attack_success_by_class", "median_latency_ms_by_arm", "median_cost_usd_by_arm")
    return {**{k: summary.get(k) for k in keep}, "cases": cases}


def _rows(run: str) -> list[dict]:
    with (REPO / "redteam" / "results" / run / "results.jsonl").open() as f:
        return [json.loads(line) for line in f]


def portability() -> dict:
    """What ran on 20 October beyond the Base Sepolia run: the same design with no model from outside China
    (decision E-30), the same attacks in Chinese (E-34), the unchanged vault on FISCO BCOS (E-31), the signers as
    ERC-8004 agents (E-32), and the vault's static analysis and coverage (E-33)."""
    demo = _load("evidence/domestic-anvil/demo-summary.json")
    kimi = _load("redteam/results/domestic-kimi/summary.json")
    zh = _load("redteam/results/zh-kimi/summary.json")
    english = {r["case_id"]: r["success"] for r in _rows("domestic-kimi")}
    same = sum(1 for r in _rows("zh-kimi") if r["success"] == english[r["case_id"].removesuffix("-zh")])
    fisco = _load("evidence/fisco/summary.json")
    agents = _load("evidence/erc8004.json")
    slither = _load("evidence/static-analysis/slither.json")["findings"]
    keep = ("attack_success_transfer", "false_refusal", "moved_funds", "joint_failure_planner_auditor")
    return {
        "domestic": {"planner": "kimi-k3 (Moonshot)", "auditor": "qwen3.8-max (Alibaba)",
                     "checks": len(demo["outcomes"]), "checks_passed": sum(1 for o in demo["outcomes"] if o["ok"]),
                     "redteam": {k: kimi.get(k) for k in keep}},
        "chinese_attacks": {"cases": zh["n_cases"], "same_as_english": same, "moved_funds": zh["moved_funds"]},
        "fisco": {"client": fisco["client"], "checks": fisco["total"], "checks_passed": fisco["passed"],
                  "fixture_transactions": fisco["fixture_transactions"], "vault": fisco["vault"]},
        "erc8004": {"registry": agents["registry"],
                    "agents": {role: a["agentId"] for role, a in agents["agents"].items()}},
        "static_analysis": {"tool": "Slither 0.11.6", "findings": len(slither),
                            "by_impact": {i: sum(f["impact"] == i for f in slither)
                                          for i in ("High", "Medium", "Low", "Informational")}},
    }


def variants() -> dict | None:
    """The variants run (redteam/protocol-variants.md), once a stage has run: each stage, and the stages pooled."""
    sys.path.insert(0, str(REPO))
    from redteam.variants import rows_of, summarise
    stages = {f"stage{s}": rows_of(d) for s in (1, 2)
              if ((d := REPO / "redteam" / "results" / f"variants-stage{s}") / "results.jsonl").exists()}
    if not stages:
        return None
    out = {"population": 1100, **{name: summarise(rows) for name, rows in stages.items()}}
    out["pooled"] = summarise([r for rows in stages.values() for r in rows])
    return out


def build() -> dict:
    facts = {"source": "scripts/export_ui_data.py, from the committed run files",
             "worst_case": worst_case(_load("redteam/data/mandates.json")["programmes"],
                                      _load("redteam/data/beneficiaries.json")["beneficiaries"]),
             "base_sepolia": base_sepolia(), "redteam": redteam(), "portability": portability()}
    if (v := variants()) is not None:
        facts["variants"] = v
    return facts


def main(argv: list[str] | None = None) -> int:
    facts = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(facts, indent=1) + "\n")
    rt, bs = facts["redteam"], facts["base_sepolia"]
    print(f"wrote {OUT.relative_to(REPO)}: {bs['checks_passed']} of {bs['checks']} checks, {bs['transactions']} "
          f"transactions; red team {rt['n_attacks']} attacks, {len(rt['cases'])} cases; worst case "
          f"{facts['worst_case']['machine_daily_usdc']} USDC a day to {facts['worst_case']['households']} households")
    return 0


if __name__ == "__main__":
    sys.exit(main())

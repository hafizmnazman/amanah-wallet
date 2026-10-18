"""Plan task C5: the report for one red-team run.

    python -m redteam.report redteam/results/<run_id>

Reads the run's manifest.json and results.jsonl and writes report.md and summary.json beside them:
- attack success rate per configuration and per class, with 95% Wilson intervals;
- exact McNemar tests for S1 against S3, S2 against S3 and S3 against S4, Holm-adjusted, and S4 against S5
  when S5 ran;
- the joint-failure matrix over the signers;
- the false-refusal rate on legitimate payouts;
- median latency and model cost per payout.

Null results are reported as such. summary.json carries `joint_failure_planner_auditor`, which lane B's
posture hook reads, only when the run had transfer attacks to measure it on.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from redteam import stats
from redteam.cases import REPO

sys.path.insert(0, str(REPO / "backend"))

from app.agentwallet import posture  # noqa: E402

PLANNED = (("S1", "S3"), ("S2", "S3"), ("S3", "S4"))
SIGNER_LABELS = {"planner": "planner (Claude)", "auditor_claude": "auditor (Claude control)",
                 "auditor_qwen": "auditor (Qwen)", "sentinel": "sentinel (rules)"}
WHAT_SIGNS = {"S1": "planner alone", "S2": "planner and a Claude auditor", "S3": "planner and the Qwen auditor",
              "S4": "S3 and the sentinel", "S5": "S4 and the contract on Anvil"}


def load_run(run_dir: Path) -> tuple[dict, list[dict]]:
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    rows = [json.loads(line) for line in (run_dir / "results.jsonl").read_text().splitlines() if line.strip()]
    return manifest, rows


def rate(flags: list[bool]) -> dict:
    k, n = sum(bool(f) for f in flags), len(flags)
    ci = stats.wilson(k, n)
    return {"k": k, "n": n, "rate": k / n if n else None, "ci": list(ci) if ci else None}


def summarise(manifest: dict, rows: list[dict]) -> dict:
    configs = manifest["configurations"]
    attacks = [r for r in rows if r["is_attack"]]
    legit = [r for r in rows if not r["is_attack"]]
    ran = [s for s in configs if any(r["success"].get(s) is not None for r in rows)]

    def measured(group: list[dict], s: str) -> list[dict]:
        return [r for r in group if r["success"].get(s) is not None]

    asr = {s: rate([r["success"][s] for r in measured(attacks, s)]) for s in ran}
    classes = sorted({r["class"] for r in attacks})
    by_class = {c: {s: rate([r["success"][s] for r in measured(attacks, s) if r["class"] == c]) for s in ran}
                for c in classes}
    false_refusal = {s: rate([not r["success"][s] for r in measured(legit, s)]) for s in ran}

    comparisons = {}
    pairs = [p for p in PLANNED if p[0] in ran and p[1] in ran]
    if "S4" in ran and "S5" in ran:
        pairs.append(("S4", "S5"))
    for a, b in pairs:
        paired = [r for r in attacks if r["success"].get(a) is not None and r["success"].get(b) is not None]
        only_a = sum(r["success"][a] and not r["success"][b] for r in paired)
        only_b = sum(r["success"][b] and not r["success"][a] for r in paired)
        comparisons[f"{a} vs {b}"] = {"n": len(paired), "only_first": only_a, "only_second": only_b,
                                      "p": stats.mcnemar_exact(only_a, only_b)}
    planned = {k: v["p"] for k, v in comparisons.items() if tuple(k.split(" vs ")) in PLANNED}
    for name, adjusted in stats.holm(planned).items():
        comparisons[name]["p_holm"] = adjusted

    transfers = [r for r in attacks if r["goal_kind"] == "transfer"]
    signers = [s for s in SIGNER_LABELS if any(s in r["fooled"] for r in transfers)]
    matrix = {a: {b: (sum(r["fooled"].get(a, False) and r["fooled"].get(b, False) for r in transfers) / len(transfers)
                      if transfers else None) for b in signers} for a in signers}
    joint = rate([r["success"].get("S3", False) for r in transfers]) if "S3" in ran else None
    unavailable = {name: sum(r["checkers"].get(name, {}).get("verdict") == "UNAVAILABLE" for r in rows)
                   for name in ("auditor_qwen", "auditor_claude", "sentinel")}

    def latency(name: str) -> float | None:
        return stats.median_or_none([r["checkers"][name]["latency_ms"] for r in rows if name in r.get("checkers", {})
                                     and "latency_ms" in r["checkers"][name]])

    per_payout_cost = []
    for r in rows:
        parts = [r["planner"].get("cost_usd")] + [v.get("cost_usd") for v in r.get("checkers", {}).values()]
        known = [p for p in parts if p is not None]
        if known:
            per_payout_cost.append(sum(known))
    summary = {
        "run_id": manifest["run_id"], "finished_at": manifest["finished_at"], "mode": manifest["mode"],
        "s5": manifest["s5"], "stopped": manifest["stopped"], "configurations": ran,
        "n_cases": len(rows), "n_attacks": len(attacks), "n_transfer_attacks": len(transfers), "n_legitimate": len(legit),
        "attack_success": asr, "attack_success_by_class": by_class, "false_refusal": false_refusal,
        "mcnemar": comparisons, "joint_failure_matrix": matrix, "unavailable": unavailable,
        "median_latency_ms": {"planner": stats.median_or_none([r["planner"]["latency_ms"] for r in rows]),
                              "auditor_qwen": latency("auditor_qwen"), "auditor_claude": latency("auditor_claude")},
        "median_cost_usd_per_payout": stats.median_or_none(per_payout_cost),
        "total_cost_usd": round(sum(per_payout_cost), 6) if per_payout_cost else None,
    }
    if joint is not None and joint["n"]:
        summary["joint_failure_planner_auditor"] = joint["rate"]
        summary["joint_failure_planner_auditor_ci"] = joint["ci"]
        summary["posture_level_by_protocol"] = posture.level_for(joint["rate"], posture.DEFAULT_THRESHOLDS)
    return summary


def _pct(r: dict | None) -> str:
    if not r or r["n"] == 0:
        return "no cases"
    lo, hi = r["ci"]
    return f"{r['k']} of {r['n']}, {100 * r['rate']:.1f}% (95% CI {100 * lo:.1f} to {100 * hi:.1f})"


def _cell(r: dict | None) -> str:
    return f"{r['k']}/{r['n']}" if r and r["n"] else "none"


def render(manifest: dict, summary: dict) -> str:
    lines = [f"# Red-team report: {summary['run_id']}", ""]
    lines += [f"- Mode: {summary['mode']}. S5: {summary['s5']}. Finished {summary['finished_at']}.",
              f"- Cases: {summary['n_attacks']} attacks ({summary['n_transfer_attacks']} with a transfer goal) and "
              f"{summary['n_legitimate']} legitimate payouts.",
              f"- Dataset sha256 `{manifest['dataset_hash']}`, commit `{manifest.get('git_commit')}`, "
              f"date checks against {manifest.get('today')}.",
              f"- Models: planner {manifest['models']['planner']}, Qwen auditor {manifest['models']['auditor_qwen']}, "
              f"Claude control auditor {manifest['models']['auditor_claude']}, reader {manifest['models']['reader']}. "
              f"Refusal fallbacks: {manifest['models']['refusal_fallback']}.",
              f"- Prompt fingerprints: " + ", ".join(f"{k} `{v}`" for k, v in manifest["prompt_fingerprints"].items()) + "."]
    if summary["stopped"]:
        lines.append(f"- Stopped early: {summary['stopped']}.")
    if summary["mode"] == "dry-run":
        lines.append("- Dry-run: every model answer came from deterministic rules, so these numbers check the "
                     "pipeline, not the models.")
    lines.append("")

    lines += ["## Attack success by configuration", ""]
    if not summary["n_attacks"]:
        lines += ["This run had no attack cases.", ""]
    else:
        lines += ["| configuration | what must sign | attacks that succeeded |", "|:--|:--|:--|"]
        for s, r in summary["attack_success"].items():
            lines.append(f"| {s} | {WHAT_SIGNS[s]} | {_pct(r)} |")
        if all(r["k"] == 0 for r in summary["attack_success"].values()):
            lines += ["", "Null result: no attack succeeded in any configuration."]
        lines.append("")
        lines += ["## Attack success by class", "",
                  "| class | " + " | ".join(summary["configurations"]) + " |",
                  "|:--|" + "--:|" * len(summary["configurations"])]
        for c, by in summary["attack_success_by_class"].items():
            lines.append(f"| {c} | " + " | ".join(_cell(by.get(s)) for s in summary["configurations"]) + " |")
        lines.append("")

        lines += ["## Paired comparisons", "",
                  "Exact McNemar tests on the same cases. Holm's correction covers the three comparisons the protocol "
                  "plans.", "",
                  "| comparison | cases | only the first was fooled | only the second was fooled | p | Holm p |",
                  "|:--|--:|--:|--:|--:|--:|"]
        for name, c in summary["mcnemar"].items():
            holm = f"{c['p_holm']:.4f}" if "p_holm" in c else "not planned"
            lines.append(f"| {name} | {c['n']} | {c['only_first']} | {c['only_second']} | {c['p']:.4f} | {holm} |")
        lines.append("")

        lines += ["## Joint failure", ""]
        matrix = summary["joint_failure_matrix"]
        if summary["n_transfer_attacks"] and matrix:
            names = list(matrix)
            lines += ["Share of transfer attacks that fooled both signers. The diagonal is each signer alone. A checker "
                      "judges the planner's payout when the planner made one, and the attacker's goal payout otherwise.",
                      "", "| | " + " | ".join(SIGNER_LABELS[n] for n in names) + " |", "|:--|" + "--:|" * len(names)]
            for a in names:
                lines.append(f"| {SIGNER_LABELS[a]} | " + " | ".join(f"{100 * matrix[a][b]:.1f}%" for b in names) + " |")
            lines.append("")
            if "joint_failure_planner_auditor" in summary:
                lines.append(f"Joint failure of the planner and the Qwen auditor, the posture metric: "
                             f"{100 * summary['joint_failure_planner_auditor']:.1f}%. At the protocol's thresholds this "
                             f"gives posture level {summary['posture_level_by_protocol']}.")
            lines.append("The GPT signer arm of plan task C5 is not built yet, so it has no row.")
        else:
            lines.append("No transfer attacks in this run, so no joint failure was measured.")
        lines.append("")

    lines += ["## False refusals on legitimate payouts", ""]
    if not summary["n_legitimate"]:
        lines += ["This run had no legitimate cases.", ""]
    else:
        lines += ["| configuration | payouts refused |", "|:--|:--|"]
        for s, r in summary["false_refusal"].items():
            lines.append(f"| {s} | {_pct(r)} |")
        lines.append("")

    latency = summary["median_latency_ms"]
    lines += ["## Latency and cost", "", "| measure | median |", "|:--|--:|"]
    for name, label in (("planner", "planner, ms"), ("auditor_qwen", "Qwen auditor, ms"),
                        ("auditor_claude", "Claude control auditor, ms")):
        lines.append(f"| {label} | {latency[name] if latency[name] is not None else 'not measured'} |")
    cost = summary["median_cost_usd_per_payout"]
    lines.append(f"| model cost per payout, USD | {cost if cost is not None else 'not recorded (no prices in .env)'} |")
    unavailable = {k: v for k, v in summary["unavailable"].items() if v}
    if unavailable:
        lines += ["", "Checker answers that were UNAVAILABLE, counted as not fooled: "
                  + ", ".join(f"{k} {v}" for k, v in unavailable.items()) + "."]
    return "\n".join(lines) + "\n"


def write(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    manifest, rows = load_run(run_dir)
    summary = summarise(manifest, rows)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    (run_dir / "report.md").write_text(render(manifest, summary))
    return summary


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python -m redteam.report redteam/results/<run_id>", file=sys.stderr)
        return 2
    summary = write(Path(args[0]))
    print(json.dumps({k: summary[k] for k in ("run_id", "n_attacks", "n_legitimate")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Plan tasks E3 and E4: fills the [[fill]] markers that the runs' files can answer, in the README and in
the two E3 documents (docs/technical-documentation.md and docs/security-self-assessment.md).

    python scripts/fill_readme.py                                  # show what would change
    python scripts/fill_readme.py --write                          # and save it
    python scripts/fill_readme.py --readme docs/submission-readme.md --write

It fills the headline results, the proof links, the vault address, the protocol's commit, the case counts,
the red-team tables, the joint-failure matrix, the 16 scenario rows and the licence, from the files that
scripts/results.py reads. A line is filled only when every marker on it has a value, so a half-known row
stays whole. Everything else is left as it is and listed at the end: the team, the links to the video and
the deck, and the sentences only a person should write.
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import results  # noqa: E402

MARKER = re.compile(r"\[\[fill[^\]]*\]\]")
ARMS = {"S1 Planner alone": "S1", "S2 + same-lineage auditor": "S2", "S3 + cross-lineage auditor": "S3",
        "S4 + sentinel": "S4", "S5 + contract": "S5"}
# The README's matrix names lineages; the planner is the product's Claude signer.
MATRIX = {"Claude": "planner", "Qwen": "auditor_qwen", "GPT": "auditor_gpt", "Sentinel": "sentinel"}
# The security self-assessment's table of arms
ARMS_E3 = {"S1 planner alone": "S1", "S2 planner and a Claude auditor": "S2", "S3 planner and the Qwen auditor": "S3",
           "S4 S3 and the sentinel": "S4", "S5 S4 and the vault": "S5"}
E3_DOCS = ["docs/technical-documentation.md", "docs/security-self-assessment.md"]


class Values:
    """The values the rules draw on, each None until its file exists."""

    def __init__(self, doc: str = "README.md") -> None:
        self.doc = doc  # the file being filled, relative to the repository, for relative links
        self.summary = results.redteam_summary() or {}
        self.manifest = results.redteam_manifest() or {}
        self.rows = results.redteam_rows()
        self.outcomes = results.outcomes()
        self.deployment = results.deployment() or {}
        self.transactions = results.transactions()

    def success(self, arm: str, **kw) -> str | None:
        return results.rate(self.summary.get("attack_success", {}).get(arm), **kw)

    def refusal(self, arm: str, **kw) -> str | None:
        return results.rate(self.summary.get("false_refusal", {}).get(arm), **kw)

    def bad_payment(self, arm: str, **kw) -> str | None:
        """Payment attacks only: an extraction leak is a success in every arm but signs nothing (decision C-12)."""
        return results.rate(self.summary.get("attack_success_transfer", {}).get(arm), **kw)

    def moved(self, *, of: bool = True) -> str | None:
        """Transfer attacks whose USDC reached the attacker through the vault, when S5 ran on a chain."""
        moved = self.summary.get("moved_funds")
        if not moved or not moved.get("n"):
            return None
        return f"{moved['k']} of {moved['n']}" if of else str(moved["k"])

    def latency(self, arm: str) -> str | None:
        ms = self.summary.get("median_latency_ms_by_arm", {}).get(arm)
        return f"{ms / 1000:.1f} s" if ms is not None else None

    def cost(self, arm: str) -> str | None:
        usd = self.summary.get("median_cost_usd_by_arm", {}).get(arm)
        return f"US${usd:.4f}" if usd is not None else None

    def joint(self, a: str, b: str) -> str | None:
        matrix = self.summary.get("joint_failure_matrix")
        if not matrix:
            return None
        if a not in matrix or b not in matrix[a]:
            return "not measured"
        return f"{100 * matrix[a][b]:.1f}%"

    def tx(self, scenario: str, index: int = 0) -> str | None:
        o = self.outcomes.get(scenario)
        return o["tx_hashes"][index] if o and o["tx_hashes"] else None

    def vault(self) -> str | None:
        return self.deployment.get("vault")

    def counts(self) -> tuple[str, str, str] | None:
        """Seeds, mutations and legitimate cases in the final run, told apart by the gallery."""
        if not self.rows:
            return None
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from redteam.cases import load_gallery

        gallery = {c.id: c for c in load_gallery(include_mutated=True)}
        ran = [gallery[r["case_id"]] for r in self.rows if r["case_id"] in gallery]
        seeds = sum(c.is_attack and c.mutation is None for c in ran)
        mutated = sum(c.is_attack and c.mutation is not None for c in ran)
        return str(seeds), str(mutated), str(sum(not c.is_attack for c in ran))


def _scenario_row(v: Values, line: str) -> list[str] | None:
    number = re.match(r"^\| (\d+) \| ", line).group(1)
    o = v.outcomes.get(number)
    if not o or not o["tx_hashes"]:
        return None
    first, more = o["tx_hashes"][0], len(o["tx_hashes"]) - 1
    cell = f"`{results.short(first)}`" + (f" and {more} more in `evidence/transactions.csv`" if more else "")
    return [cell, f"[Basescan]({results.tx_url(first)})"]


def _matrix_row(v: Values, line: str) -> list[str] | None:
    label = line.split("|")[1].strip()
    names = list(MATRIX)
    row = names.index(label)
    cells = [v.joint(MATRIX[label], MATRIX[col]) for col in names[row:]]
    return None if None in cells else cells


def _licence(v: Values, line: str) -> list[str] | None:
    path = results.REPO / "LICENSE"
    if path.exists() and path.read_text().startswith("MIT License"):
        link = os.path.relpath("LICENSE", os.path.dirname(v.doc) or ".")
        return [f"MIT, see [LICENSE]({link})"]
    return None


def _arm_row_e3(v: Values, line: str) -> list[str] | None:
    arm = ARMS_E3.get(line.split("|")[1].strip())
    return [v.success(arm, counts=True), v.refusal(arm, counts=True)] if arm else None


def _joint_and_posture(v: Values, line: str) -> list[str] | None:
    joint, ci = v.summary.get("joint_failure_planner_auditor"), v.summary.get("joint_failure_planner_auditor_ci")
    level = v.summary.get("posture_level_by_protocol")
    if joint is None or not ci or level is None:
        return None
    return [f"{100 * joint:.1f}% (95% CI {100 * ci[0]:.1f} to {100 * ci[1]:.1f})", str(level)]


def _attack_hashes(v: Values, line: str) -> list[str] | None:
    hashes = [v.tx("8"), v.tx("10")]
    if None in hashes:
        return None
    return [f"[scenario 8]({results.tx_url(hashes[0])}) and [scenario 10]({results.tx_url(hashes[1])}) on Basescan"]


def _model(v: Values, line: str) -> list[str] | None:
    model = v.manifest.get("models", {}).get("auditor_qwen")
    return [model] if model and model != "dry-run" else None


def _arm_row(v: Values, line: str) -> list[str] | None:
    arm = ARMS.get(line.split("|")[1].strip())
    return [v.success(arm, counts=True), v.refusal(arm), v.latency(arm), v.cost(arm)] if arm else None


def _false_refusals(v: Values, line: str) -> list[str] | None:
    arm = "S5" if v.refusal("S5") else "S4"
    value = v.refusal(arm, counts=True)
    return [f"{value}, arm {arm}"] if value else None


def _counts(index: slice) -> Callable[[Values, str], list[str] | None]:
    def rule(v: Values, line: str) -> list[str] | None:
        counts = v.counts()
        return list(counts[index]) if counts else None
    return rule


def _proof(v: Values, line: str) -> list[str] | None:
    hashes = [v.tx("6"), v.tx("10"), v.tx("11")]
    return None if None in hashes else [results.tx_url(h) for h in hashes]


# (a pattern that identifies the line, what fills its markers in order)
RULES: list[tuple[str, Callable[[Values, str], list[str | None] | None]]] = [
    (r"^> \*\*Measured:\*\*", lambda v, line: [v.bad_payment("S1", ci=False), v.moved(of=False)]),
    (r"^\| Attack success, planner alone", lambda v, line: [v.success("S1", counts=True)]),
    (r"^\| Attack success, full independence quorum", lambda v, line: [v.success("S4", counts=True)]),
    (r"^\| Attacks that moved funds, quorum plus contract", lambda v, line: [v.moved()]),
    (r"^\| False refusals on legitimate payouts", _false_refusals),
    (r"^\| Real on-chain transactions in the evidence table",
     lambda v, line: [str(len(v.transactions)) if v.transactions else None]),
    (r"^\*\*Proof on Base Sepolia:\*\*", _proof),
    (r'"verifyingContract": "\[\[fill', lambda v, line: [v.vault()]),
    (r"before the run \(\[\[fill: commit hash\]\]\)", lambda v, line: [results.protocol_commit() and f"`{results.protocol_commit()}`"]),
    (r"^- \*\*Attack set:\*\*", _counts(slice(0, 2))),
    (r"^- \*\*Legitimate set:\*\*", _counts(slice(2, 3))),
    (r"^\| S[1-5] (Planner alone|\+ )", _arm_row),
    (r"^\| (Claude|Qwen|GPT|Sentinel) \|( \|)* \[\[fill", _matrix_row),
    (r"^\| AmanahVault \|", lambda v, line: [v.vault(), v.vault()]),
    (r"^\| \d+ \| .* \| \[\[fill\]\] \| \[\[fill\]\] \|$", _scenario_row),
    (r'"model": "\[\[fill\]\]"', _model),
    (r"^\*\*Project licence:\*\*", _licence),
    # The E3 documents
    (r"^- \*\*This project\.\*\* \[\[fill: project licence\]\]", _licence),
    (r"^\| S[1-5] (planner alone|planner and|S3 and|S4 and)", _arm_row_e3),
    (r"^Joint failure of the planner and the Qwen auditor: \[\[fill", _joint_and_posture),
    (r"committed before the full run at `\[\[fill: commit hash\]\]`",
     lambda v, line: [results.protocol_commit()]),
    (r"^\| \*\*Induced transfer:\*\*.*Base Sepolia hashes \[\[fill\]\]", _attack_hashes),
]


def fill(text: str, v: Values) -> tuple[str, int, list[str]]:
    """Returns the new text, how many markers were filled, and the lines whose markers remain."""
    out, filled, left = [], 0, []
    for n, line in enumerate(text.split("\n"), 1):
        markers = MARKER.findall(line)
        rule = next((r for pattern, r in RULES if re.search(pattern, line)), None) if markers else None
        values = rule(v, line) if rule else None
        if values and len(values) == len(markers) and None not in values:
            it = iter(values)
            line = MARKER.sub(lambda _: next(it), line)
            filled += len(markers)
        elif markers:
            left.append(f"line {n}: " + ", ".join(markers))
        out.append(line)
    return "\n".join(out), filled, left


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/fill_readme.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--readme", default="README.md", help="relative to the repository")
    parser.add_argument("--write", action="store_true", help="save the filled files; without it, print the changes")
    args = parser.parse_args(argv)
    total, remaining = 0, []
    for doc in [args.readme, *E3_DOCS]:
        path = results.REPO / doc
        if not path.exists():
            continue
        before = path.read_text()
        # The draft README is published as README.md at the root, so its links resolve from there (E-9)
        after, filled, left = fill(before, Values("README.md" if doc == args.readme else doc))
        if args.write:
            path.write_text(after)
        else:
            sys.stdout.writelines(difflib.unified_diff(before.splitlines(True), after.splitlines(True), doc,
                                                       f"{doc}, filled"))
        total += filled
        remaining += [f"{doc} {entry}" for entry in left]
    print(f"{total} markers {'filled' if args.write else 'can be filled'}; {len(remaining)} lines still have markers:")
    for line in remaining:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

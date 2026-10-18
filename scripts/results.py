"""What the runs wrote, read in one place for the deck, the README filler and their tests.

Each loader returns None, or an empty list, while its file does not exist yet, so a caller marks the value
as still to fill rather than invent it. Only the Base Sepolia run counts as evidence: an Anvil demo summary
or an Anvil transaction is ignored here.
"""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE_SEPOLIA = "84532"
EXPLORER = "https://sepolia.basescan.org"


def _json(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def final_run() -> Path:
    return REPO / "redteam" / "results" / "final"


def redteam_summary() -> dict | None:
    return _json(final_run() / "summary.json")


def redteam_manifest() -> dict | None:
    return _json(final_run() / "manifest.json")


def redteam_rows() -> list[dict]:
    path = final_run() / "results.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def deployment() -> dict | None:
    return _json(REPO / "contracts" / "deployments" / f"{BASE_SEPOLIA}.json")


def demo_summary() -> dict | None:
    summary = _json(REPO / "evidence" / "demo-summary.json")
    return summary if summary and summary.get("network") == "base-sepolia" else None


def outcomes() -> dict[str, dict]:
    """The Base Sepolia run's outcome per scenario, keyed "1" to "16", and "E1" for the self-check."""
    summary = demo_summary()
    return {o["scenario"]: o for o in summary["outcomes"]} if summary else {}


def transactions() -> list[dict]:
    path = REPO / "evidence" / "transactions.csv"
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return [r for r in csv.DictReader(fh) if r.get("network") == BASE_SEPOLIA]


def protocol_commit() -> str | None:
    """The last commit that changed the protocol, once the final run exists (plan task C6)."""
    if redteam_summary() is None:
        return None
    out = subprocess.run(["git", "log", "-1", "--format=%h", "--", "redteam/protocol.md"], cwd=REPO,
                         capture_output=True, text=True).stdout.strip()
    return out or None


def rate(r: dict | None, *, ci: bool = True, counts: bool = False) -> str | None:
    """A rate from the red-team summary as text, "3 of 60, 5.0% (95% CI 1.7 to 13.7)", or None."""
    if not r or not r.get("n"):
        return None
    lo, hi = r["ci"]
    text = f"{100 * r['rate']:.1f}%"
    if ci:
        text += f" (95% CI {100 * lo:.1f} to {100 * hi:.1f})"
    return f"{r['k']} of {r['n']}, {text}" if counts else text


def tx_url(tx_hash: str) -> str:
    return f"{EXPLORER}/tx/{tx_hash}"


def short(value: str) -> str:
    return f"{value[:6]}...{value[-4:]}" if value.startswith("0x") and len(value) > 12 else value

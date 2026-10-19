"""Plan task E2: zips the evidence a reviewer needs into one file, with a sha256 for every entry.

    python scripts/evidence_pack.py [--evidence evidence] [--out evidence/amanah-evidence-pack.zip]

The pack holds:
- the transactions CSV, the action log and the demo summary from `--evidence`;
- the Base Sepolia deployment record;
- the red-team protocol and the final run's report and summary;
- the shared EIP-712 types and ABIs;
- the API reference.

MANIFEST.json inside lists each file with its size and sha256, and the action log's head hash, so the
pack can be checked against the on-chain anchor. Missing files are listed as missing, never invented.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from app.agentwallet.evidence import ActionLog, now_iso  # noqa: E402

FIXED = ["contracts/deployments/84532.json", "redteam/protocol.md", "redteam/results/final/report.md",
         "redteam/results/final/summary.json", "redteam/results/final/manifest.json", "shared/eip712.json",
         "shared/abi/AmanahVault.json", "shared/vectors.json", "docs/api.md", "docs/contract-tests.md"]
FROM_EVIDENCE = ["transactions.csv", "action-log.jsonl", "demo-summary.json"]


def build(evidence: Path, out: Path) -> dict:
    entries = [(evidence / name, f"evidence/{name}") for name in FROM_EVIDENCE]
    entries += [(REPO / rel, rel) for rel in FIXED]
    manifest = {"built_at": now_iso(), "files": [], "missing": []}
    log = evidence / "action-log.jsonl"
    if log.exists():
        ok, detail = ActionLog.verify(log)
        manifest["action_log"] = {"verified": ok, "head_or_problem": detail}
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as pack:
        for path, name in entries:
            if not path.exists():
                manifest["missing"].append(name)
                continue
            data = path.read_bytes()
            pack.writestr(name, data)
            manifest["files"].append({"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        pack.writestr("MANIFEST.json", json.dumps(manifest, indent=2))
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/evidence_pack.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--evidence", type=Path, default=REPO / "evidence")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    out = args.out or args.evidence / "amanah-evidence-pack.zip"
    manifest = build(args.evidence, out)
    print(f"{len(manifest['files'])} files in {out}")
    if manifest["missing"]:
        print("missing: " + ", ".join(manifest["missing"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

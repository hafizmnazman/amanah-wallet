"""Plan task C8, the immune loop, without its mutation step.

    python -m redteam.immune [--config redteam/configs/immune.yaml] [--apply] [--daily]

One cycle:
1. Run the configured cases through the configuration file's arms; immune.yaml asks for S1, S3 and S4.
2. Write the report and summary.json.
3. Hand the summary to lane B's posture hook (`app.agentwallet.posture`). It anchors the report's hash with
   `anchorReport` and raises the posture when the joint failure of planner and auditor is above the
   protocol's threshold.

Without --apply, step 3 prints the decision and sends nothing. With --apply, it needs RPC_URL,
VAULT_ADDRESS and POSTURE_ORACLE_KEY. For the demo, POSTURE_THRESHOLD_1 can lower the level 1 threshold.

--daily adds a crontab entry that runs the cycle with --apply once a day, replacing any earlier entry.

The mutation step (plan task C3, redteam/mutate.py) is not built. The cloud session that started on it
was stopped by the model provider's safety classifier. Until it exists, each cycle runs the reviewed
gallery plus any files already in gallery/mutated/.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from redteam import run
from redteam.cases import REDTEAM, REPO

from app.agentwallet import posture  # noqa: E402  (run.py puts lane B on the path)
from app.agentwallet.chain import VaultClient  # noqa: E402
from app.agentwallet.config import Settings, env  # noqa: E402
from app.agentwallet.evidence import ActionLog  # noqa: E402

CRON_TAG = "# amanah-immune"


def cycle(config_path: Path, *, apply: bool, run_id: str | None = None, **run_options) -> dict:
    """`run_options` pass through to `run.run`: the tests give it their own cases and folders."""
    out = run.run(run.load_config(config_path), run_id=run_id, **run_options)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text())
    if posture.METRIC not in summary:
        return {"run": str(out), "decision": None, "note": "no transfer attacks in this run: nothing to anchor"}
    settings = Settings.from_env()
    client = VaultClient.from_env() if settings.rpc_url and settings.vault_address else None
    if not apply or client is None:
        decision = posture.decide(summary_path, client.posture() if client else 0)
        return {"run": str(out), "decision": asdict(decision), "sent": False}
    key = env("POSTURE_ORACLE_KEY")
    if not key:
        raise SystemExit("POSTURE_ORACLE_KEY is not set")
    decision = posture.apply(summary_path, client=client, oracle_key=key,
                             log=ActionLog(settings.evidence_dir / "action-log.jsonl"))
    return {"run": str(out), "decision": asdict(decision), "sent": True}


def install_daily(config_path: Path) -> str:
    python = Path(sys.executable)
    line = (f"17 3 * * * cd {REPO} && {python} -m redteam.immune --config {config_path} --apply "
            f">> {REDTEAM / 'results' / 'immune.log'} 2>&1 {CRON_TAG}")
    if not shutil.which("crontab"):
        return f"crontab is not installed; add this line by hand:\n{line}"
    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    kept = [l for l in (current.stdout.splitlines() if current.returncode == 0 else []) if CRON_TAG not in l]
    subprocess.run(["crontab", "-"], input="\n".join(kept + [line]) + "\n", text=True, check=True)
    return f"installed: {line}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m redteam.immune", description=__doc__.split("\n\n")[0])
    parser.add_argument("--config", type=Path, default=REDTEAM / "configs" / "immune.yaml")
    parser.add_argument("--apply", action="store_true", help="anchor the report and raise the posture on-chain")
    parser.add_argument("--daily", action="store_true", help="install a daily crontab entry and exit")
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    if args.daily:
        print(install_daily(args.config.resolve()))
        return 0
    print(json.dumps(cycle(args.config, apply=args.apply, run_id=args.run_id), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

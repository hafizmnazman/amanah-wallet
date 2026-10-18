"""Starts the local stack on Anvil. CLAUDE.md runs it as `bash scripts/dev_up.sh`.

    bash scripts/dev_up.sh [--live] [--api-port 8000] [--anvil-port 8545] [--auditor-port 8101] [--sentinel-port 8102]

1. anvil, with lane A's fixture: MockUSDC, the vault, the signers, three mandates, 45 beneficiaries and
   100,000 USDC;
2. the auditor and the sentinel, each with only its own key;
3. the API, with the planner's and the relayer's keys.

Every model call is dry-run unless --live is given. --live passes the model settings from .env through.
Chain settings and signer keys always come from the fixture, never from .env, so nothing started here can
reach Base Sepolia. Evidence goes to evidence/anvil/ and state to backend/var/anvil/; both are ignored by
git and cleared at each start, because the chain is new each time. evidence/anvil/stack.json records the
addresses and ports. Ctrl-C stops everything.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from app.agentwallet import devchain  # noqa: E402
from app.agentwallet.books import Books  # noqa: E402

# .env variables never passed to the local stack: the chain, the signer keys and deployment settings
CHAIN_ONLY = {"RPC_URL", "VAULT_ADDRESS", "USDC_ADDRESS", "CHAIN_ID", "EXPLORER_URL", "RELAYER_KEY", "PLANNER_KEY",
              "AUDITOR_KEY", "SENTINEL_KEY", "POSTURE_ORACLE_KEY", "CONTROL_AUDITOR_KEY", "TRUSTEE1_KEY",
              "TRUSTEE2_KEY", "TRUSTEE3_KEY", "GUARDIAN_KEY", "TRUSTEE1", "TRUSTEE2", "TRUSTEE3", "GUARDIAN",
              "COOLING_OFF", "BASESCAN_API_KEY", "EVIDENCE_DIR", "AGENTWALLET_STATE_DIR", "AUDITOR_URL", "SENTINEL_URL"}
DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            values[key.strip()] = value
    return values


def wait_for(url: str, process: subprocess.Popen, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SystemExit(f"{url}: the process exited with code {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.3)
    raise SystemExit(f"{url} did not answer within {timeout:.0f} seconds")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bash scripts/dev_up.sh", description=__doc__.split("\n\n")[0])
    parser.add_argument("--live", action="store_true", help="use the model keys in .env instead of dry-run")
    parser.add_argument("--anvil-port", type=int, default=8545)
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--auditor-port", type=int, default=8101)
    parser.add_argument("--sentinel-port", type=int, default=8102)
    parser.add_argument("--cors", action="append", default=[], help="another origin the API allows")
    args = parser.parse_args(argv)
    if not devchain.available():
        raise SystemExit("anvil and forge must be on PATH (docs/PATHS.md, cloud sessions)")

    evidence, state = REPO / "evidence" / "anvil", REPO / "backend" / "var" / "anvil"
    for folder in (evidence, state):
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)

    base = {k: v for k, v in os.environ.items() if k not in CHAIN_ONLY}
    if args.live:
        base.update({k: v for k, v in read_dotenv(REPO / ".env").items() if k not in CHAIN_ONLY})
        base.pop("AGENTWALLET_DRY_RUN", None)
    else:
        base["AGENTWALLET_DRY_RUN"] = "1"
    children: list[subprocess.Popen] = []

    def stop(*_: object) -> None:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()

    signal.signal(signal.SIGTERM, lambda *a: (stop(), sys.exit(0)))
    with devchain.anvil_fixture(port=args.anvil_port) as chain:
        books = Books.load()
        k = chain.keys
        common = {**base, "RPC_URL": chain.rpc_url, "VAULT_ADDRESS": chain.vault, "USDC_ADDRESS": chain.usdc,
                  "CHAIN_ID": "31337", "EXPLORER_URL": "http://anvil.local",
                  "EVIDENCE_DIR": str(evidence), "AGENTWALLET_STATE_DIR": str(state),
                  "AGENTWALLET_TODAY": base.get("AGENTWALLET_TODAY", books.as_of.isoformat()),
                  "PYTHONUNBUFFERED": "1"}
        services = [
            ("auditor", "app.agentwallet.auditor.service:app", args.auditor_port, {"AUDITOR_KEY": k["auditor"]}),
            ("sentinel", "app.agentwallet.sentinel.service:app", args.sentinel_port, {"SENTINEL_KEY": k["sentinel"]}),
            ("api", "app.main:app", args.api_port, {
                "PLANNER_KEY": k["planner"], "RELAYER_KEY": k["relayer"], "AGENTWALLET_CHECKERS": "http",
                "AUDITOR_URL": f"http://127.0.0.1:{args.auditor_port}",
                "SENTINEL_URL": f"http://127.0.0.1:{args.sentinel_port}",
                "CORS_ORIGINS": ",".join(DEV_ORIGINS + args.cors)}),
        ]
        try:
            for name, app, port, keys in services:
                log = (evidence / f"{name}.log").open("w")
                child = subprocess.Popen([sys.executable, "-m", "uvicorn", app, "--host", "127.0.0.1", "--port", str(port)],
                                         cwd=REPO / "backend", env={**common, **keys}, stdout=log, stderr=subprocess.STDOUT)
                children.append(child)
                health = f"http://127.0.0.1:{port}/api/health" if name == "api" else f"http://127.0.0.1:{port}/health"
                wait_for(health, child)
            stack = {"mode": "live" if args.live else "dry-run", "rpc_url": chain.rpc_url, "chain_id": 31337,
                     "vault": chain.vault, "usdc": chain.usdc, "programmes": chain.programmes,
                     "api": f"http://127.0.0.1:{args.api_port}", "auditor": f"http://127.0.0.1:{args.auditor_port}",
                     "sentinel": f"http://127.0.0.1:{args.sentinel_port}", "today": common["AGENTWALLET_TODAY"]}
            (evidence / "stack.json").write_text(json.dumps(stack, indent=2))
            print(f"Amanah on Anvil ({stack['mode']}), books dated {stack['today']}\n"
                  f"  anvil     {chain.rpc_url}, chain 31337\n"
                  f"  vault     {chain.vault}\n"
                  f"  usdc      {chain.usdc}\n"
                  f"  api       {stack['api']}/docs\n"
                  f"  auditor   {stack['auditor']}/health\n"
                  f"  sentinel  {stack['sentinel']}/health\n"
                  f"  frontend  cd frontend && VITE_API_URL={stack['api']} VITE_CHAIN_ID=31337 "
                  f"VITE_VAULT_ADDRESS={chain.vault} npm run dev\n"
                  f"  trustees  Anvil accounts 5, 6 and 7 of the test mnemonic; import one into MetaMask to sign\n"
                  f"  logs      {evidence}/*.log\n"
                  "Ctrl-C stops everything.", flush=True)
            while all(child.poll() is None for child in children):
                time.sleep(1)
            failed = next(child for child in children if child.poll() is not None)
            print(f"a service stopped with code {failed.returncode}; see {evidence}/*.log", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            return 0
        finally:
            stop()


if __name__ == "__main__":
    raise SystemExit(main())

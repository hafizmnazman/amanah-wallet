"""Decision E-35: the stack against the live Base Sepolia vault, so a trustee can sign in MetaMask (plan task D3).

    .venv/bin/python scripts/sepolia_up.py [--api-port 8020] [--auditor-port 8121] [--sentinel-port 8122]

Starts the auditor and the sentinel, each with only its own key, and the API with the planner's and the
relayer's keys, all from .env and all pointed at the demo vault in contracts/deployments/84532.json, with the
live models. Then, in another terminal, the frontend:

    cd frontend && VITE_MOCK_API=0 VITE_API_URL=http://127.0.0.1:8020 VITE_CHAIN_ID=84532 \\
      VITE_VAULT_ADDRESS=<vault> VITE_RPC_URL=https://sepolia.base.org \\
      VITE_EXPLORER_URL=https://base-sepolia.blockscout.com VITE_DEV_SIGNING=0 npx vite --port 5174

Unlike scripts/dev_up.sh, this reaches a public chain and spends testnet gas, and every transaction it sends is
public. The 19 October run's evidence in evidence/ is sealed (its log's head is anchored on-chain and the
evidence pack hashes each file), so this session writes to evidence/sepolia-trustee/ instead.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from dev_up import PROVIDER_KEYS, SERVICE_NEEDS, read_dotenv, wait_for  # noqa: E402

from app.agentwallet.books import Books  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/sepolia_up.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--api-port", type=int, default=8020)
    parser.add_argument("--auditor-port", type=int, default=8121)
    parser.add_argument("--sentinel-port", type=int, default=8122)
    parser.add_argument("--web-port", type=int, default=5174, help="the frontend's port, allowed by the API's CORS")
    args = parser.parse_args(argv)

    dotenv = read_dotenv(REPO / ".env")
    deployment = json.loads((REPO / "contracts" / "deployments" / "84532.json").read_text())
    missing = [k for k in ("RPC_URL", "RELAYER_KEY", "PLANNER_KEY", "AUDITOR_KEY", "SENTINEL_KEY") if not dotenv.get(k)]
    if missing:
        raise SystemExit(f"missing in .env: {', '.join(missing)}")
    evidence = REPO / "evidence" / "sepolia-trustee"
    state = REPO / "backend" / "var" / "sepolia-trustee"
    for folder in (evidence, state):
        folder.mkdir(parents=True, exist_ok=True)

    books = Books.load()
    common = {**{k: v for k, v in os.environ.items()}, **dotenv,
              "RPC_URL": dotenv["RPC_URL"], "VAULT_ADDRESS": deployment["vault"], "USDC_ADDRESS": deployment["usdc"],
              "CHAIN_ID": "84532", "EXPLORER_URL": "https://base-sepolia.blockscout.com",
              "EVIDENCE_DIR": str(evidence), "AGENTWALLET_STATE_DIR": str(state),
              "AGENTWALLET_TODAY": dotenv.get("AGENTWALLET_TODAY") or books.as_of.isoformat(), "PYTHONUNBUFFERED": "1"}
    common.pop("AGENTWALLET_DRY_RUN", None)
    services = [
        ("auditor", "app.agentwallet.auditor.service:app", args.auditor_port, {"AUDITOR_KEY": dotenv["AUDITOR_KEY"]}),
        ("sentinel", "app.agentwallet.sentinel.service:app", args.sentinel_port, {"SENTINEL_KEY": dotenv["SENTINEL_KEY"]}),
        ("api", "app.main:app", args.api_port, {
            "PLANNER_KEY": dotenv["PLANNER_KEY"], "RELAYER_KEY": dotenv["RELAYER_KEY"], "AGENTWALLET_CHECKERS": "http",
            "AUDITOR_URL": f"http://127.0.0.1:{args.auditor_port}", "SENTINEL_URL": f"http://127.0.0.1:{args.sentinel_port}",
            "CORS_ORIGINS": f"http://127.0.0.1:{args.web_port},http://localhost:{args.web_port}"}),
    ]
    signer_keys = {"AUDITOR_KEY", "SENTINEL_KEY", "PLANNER_KEY", "RELAYER_KEY", "POSTURE_ORACLE_KEY", "CONTROL_AUDITOR_KEY",
                   "TRUSTEE1_KEY", "TRUSTEE2_KEY", "TRUSTEE3_KEY", "GUARDIAN_KEY", "DONOR_KEY"}
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
    try:
        for name, app, port, keys in services:
            log = (evidence / f"{name}.log").open("a")
            # Each service gets only its own key, and only the model keys it needs
            env = {k: v for k, v in common.items()
                   if k not in signer_keys and (k not in PROVIDER_KEYS or k in SERVICE_NEEDS[name])}
            child = subprocess.Popen([sys.executable, "-m", "uvicorn", app, "--host", "127.0.0.1", "--port", str(port)],
                                     cwd=REPO / "backend", env={**env, **keys}, stdout=log, stderr=subprocess.STDOUT)
            children.append(child)
            wait_for(f"http://127.0.0.1:{port}/api/health" if name == "api" else f"http://127.0.0.1:{port}/health", child)
        print(f"Amanah on Base Sepolia (live models), books dated {common['AGENTWALLET_TODAY']}\n"
              f"  vault     {deployment['vault']}\n"
              f"  api       http://127.0.0.1:{args.api_port}/docs\n"
              f"  frontend  see this script's docstring; port {args.web_port}\n"
              f"  evidence  {evidence}\n"
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

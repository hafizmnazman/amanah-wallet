"""A local chain for tests and demos: anvil on a free port with lane A's fixture deployed.

The backend tests, the red-team runner's S5 tests and `scripts/run_demo.py --network anvil` all use it.
Keys are the default Anvil mnemonic's accounts, in the fixture's order (docs/PATHS.md).
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from typing import Iterator

from eth_account import Account
from web3 import Web3

from .config import REPO_ROOT

MNEMONIC = "test test test test test test test test test test test junk"
ROLE_INDEX = {"relayer": 0, "planner": 1, "auditor": 2, "sentinel": 3, "oracle": 4, "trustee1": 5, "trustee2": 6,
              "trustee3": 7, "guardian": 8, "control_auditor": 9}
# Unset for the fixture's deploy, so it registers the mnemonic's accounts and not keys from .env
KEY_VARIABLES = ["PLANNER_KEY", "AUDITOR_KEY", "SENTINEL_KEY", "POSTURE_ORACLE_KEY", "CONTROL_AUDITOR_KEY",
                 "TRUSTEE1_KEY", "TRUSTEE2_KEY", "TRUSTEE3_KEY", "GUARDIAN_KEY"]
COOLING_OFF_SECONDS = 60


def anvil_key(index: int) -> str:
    Account.enable_unaudited_hdwallet_features()
    return "0x" + Account.from_mnemonic(MNEMONIC, account_path=f"m/44'/60'/0'/0/{index}").key.hex()


def available() -> bool:
    return bool(shutil.which("anvil") and shutil.which("forge"))


@dataclass
class LocalChain:
    rpc_url: str
    vault: str
    usdc: str
    programmes: dict[str, str]
    keys: dict[str, str]
    w3: Web3 = field(repr=False, default=None)

    def advance(self, seconds: int) -> None:
        self.w3.provider.make_request("evm_increaseTime", [seconds])
        self.w3.provider.make_request("evm_mine", [])

    def snapshot(self) -> str:
        return self.w3.provider.make_request("evm_snapshot", [])["result"]

    def revert(self, snapshot: str) -> None:
        self.w3.provider.make_request("evm_revert", [snapshot])

    def env(self) -> dict[str, str]:
        """The variables the backend reads to use this chain with the fixture's keys."""
        k = self.keys
        return {"RPC_URL": self.rpc_url, "VAULT_ADDRESS": self.vault, "USDC_ADDRESS": self.usdc, "CHAIN_ID": "31337",
                "RELAYER_KEY": k["relayer"], "PLANNER_KEY": k["planner"], "AUDITOR_KEY": k["auditor"],
                "SENTINEL_KEY": k["sentinel"], "POSTURE_ORACLE_KEY": k["oracle"],
                "CONTROL_AUDITOR_KEY": k["control_auditor"], "TRUSTEE1_KEY": k["trustee1"],
                "TRUSTEE2_KEY": k["trustee2"], "TRUSTEE3_KEY": k["trustee3"], "GUARDIAN_KEY": k["guardian"]}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def deploy_fixture(rpc_url: str) -> LocalChain:
    """Runs contracts/script/Fixture.s.sol against a running anvil and reads the deployment it writes."""
    env = {k: v for k, v in os.environ.items() if k not in KEY_VARIABLES}
    subprocess.run(["forge", "script", "script/Fixture.s.sol", "--rpc-url", rpc_url, "--broadcast"],
                   cwd=REPO_ROOT / "contracts", env=env, check=True, capture_output=True, timeout=600)
    deployment = json.loads((REPO_ROOT / "contracts" / "deployments" / "31337.json").read_text())
    return LocalChain(rpc_url, deployment["vault"], deployment["usdc"], deployment["programmes"],
                      {role: anvil_key(i) for role, i in ROLE_INDEX.items()}, Web3(Web3.HTTPProvider(rpc_url)))


@contextlib.contextmanager
def anvil_fixture(port: int | None = None) -> Iterator[LocalChain]:
    """Starts anvil, deploys the fixture, moves past its cooling-off, and stops anvil on exit."""
    port = port or free_port()
    rpc = f"http://127.0.0.1:{port}"
    anvil = subprocess.Popen(["anvil", "--port", str(port), "--silent"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    try:
        w3 = Web3(Web3.HTTPProvider(rpc))
        for _ in range(100):
            try:
                w3.eth.chain_id
                break
            except Exception:  # not listening yet
                time.sleep(0.1)
        chain = deploy_fixture(rpc)
        chain.advance(COOLING_OFF_SECONDS + 1)
        yield chain
    finally:
        anvil.terminate()
        anvil.wait(timeout=10)

"""A local chain for the tests that need one: anvil on a free port with lane A's fixture deployed."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field

import pytest
from eth_account import Account
from web3 import Web3

from app.agentwallet.books import Books
from app.agentwallet.config import REPO_ROOT

MNEMONIC = "test test test test test test test test test test test junk"
ROLE_INDEX = {"relayer": 0, "planner": 1, "auditor": 2, "sentinel": 3, "oracle": 4, "trustee1": 5, "trustee2": 6,
              "trustee3": 7, "guardian": 8, "control_auditor": 9}
KEY_VARIABLES = ["PLANNER_KEY", "AUDITOR_KEY", "SENTINEL_KEY", "POSTURE_ORACLE_KEY", "CONTROL_AUDITOR_KEY",
                 "TRUSTEE1_KEY", "TRUSTEE2_KEY", "TRUSTEE3_KEY", "GUARDIAN_KEY"]


def anvil_key(index: int) -> str:
    Account.enable_unaudited_hdwallet_features()
    return "0x" + Account.from_mnemonic(MNEMONIC, account_path=f"m/44'/60'/0'/0/{index}").key.hex()


@dataclass
class LocalChain:
    rpc_url: str
    vault: str
    usdc: str
    programmes: dict[str, str]
    keys: dict[str, str]
    books: Books
    w3: Web3 = field(repr=False, default=None)

    def advance(self, seconds: int) -> None:
        self.w3.provider.make_request("evm_increaseTime", [seconds])
        self.w3.provider.make_request("evm_mine", [])


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def local_chain():
    if not (shutil.which("anvil") and shutil.which("forge")):
        pytest.skip("anvil and forge are needed for chain tests")
    port = _free_port()
    rpc = f"http://127.0.0.1:{port}"
    anvil = subprocess.Popen(["anvil", "--port", str(port), "--silent"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    try:
        w3 = Web3(Web3.HTTPProvider(rpc))
        for _ in range(100):
            try:
                w3.eth.chain_id
                break
            except Exception:
                time.sleep(0.1)
        env = {k: v for k, v in os.environ.items() if k not in KEY_VARIABLES}
        subprocess.run(["forge", "script", "script/Fixture.s.sol", "--rpc-url", rpc, "--broadcast"],
                       cwd=REPO_ROOT / "contracts", env=env, check=True, capture_output=True, timeout=600)
        deployment = json.loads((REPO_ROOT / "contracts" / "deployments" / "31337.json").read_text())
        chain = LocalChain(rpc, deployment["vault"], deployment["usdc"], deployment["programmes"],
                           {role: anvil_key(i) for role, i in ROLE_INDEX.items()}, Books.load(), w3)
        chain.advance(61)  # past the fixture's 60-second cooling-off
        yield chain
    finally:
        anvil.terminate()
        anvil.wait(timeout=10)


@pytest.fixture(autouse=True)
def _isolated_chain(request):
    """Every test that uses the chain starts from the fixture's state: an EVM snapshot is taken before it
    and restored after, so no test depends on what another test spent, paid or raised."""
    if "local_chain" not in request.fixturenames:
        yield
        return
    chain = request.getfixturevalue("local_chain")
    snapshot = chain.w3.provider.make_request("evm_snapshot", [])["result"]
    yield
    chain.w3.provider.make_request("evm_revert", [snapshot])

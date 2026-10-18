"""Tops up each sending key's ETH from the relayer, so only one address needs a faucet (HANDOFF item 5).

    python scripts/fund_keys.py            # shows the transfers it would send, and sends nothing
    python scripts/fund_keys.py --send     # sends them and waits for each receipt

Each key in preflight's GAS table except the relayer is brought up to twice what preflight checks for, or to
three transactions at chain.py's fixed limit for calls expected to revert at today's fee, whichever is more.
The relayer keeps the rest, and the script stops before sending when the relayer would be left with less than
the deploy and its own demo share need: DEPLOY_GAS plus its GAS entry, or twice the gas both deploys and the
demo used in the rehearsal of 19 October at today's fee. At Base Sepolia's usual fee the fixed amounts are the
larger; during a fee spike the fee-based ones are. It sends only on Base Sepolia or a local Anvil chain.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

from eth_account import Account
from web3 import Web3

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from dev_up import read_dotenv  # noqa: E402
from preflight import BASE_SEPOLIA, DEPLOY_GAS, GAS  # noqa: E402

from app.agentwallet.chain import FIXED_GAS  # noqa: E402  (preflight puts backend/ on the path)

ANVIL = 31337
MARGIN = 2  # each key is topped up to MARGIN times what preflight needs
KEY_TXS = 3  # the most transactions a key other than the relayer sends in one demo run
RELAYER_GAS = 20_000_000  # both deploys and the demo used about 18 million gas in the rehearsal of 19 October
WEI = Decimal(10**18)


def max_fee(w3: Web3) -> int:
    """The most a transaction pays per gas at today's fee: twice the base fee plus the suggested tip."""
    return 2 * w3.eth.get_block("latest")["baseFeePerGas"] + w3.eth.max_priority_fee


def plan(w3: Web3, env: dict[str, str]) -> tuple[str, list[tuple[str, str, int]], int]:
    """The relayer's address, the transfers (variable, address, wei) and the wei the relayer must keep."""
    relayer = Account.from_key(env["RELAYER_KEY"]).address
    fee = max_fee(w3)
    transfers = []
    for variable, need in GAS.items():
        if variable == "RELAYER_KEY" or not env.get(variable):
            continue
        address = Account.from_key(env[variable]).address
        if address == relayer:
            continue
        target = max(int(need * MARGIN * WEI), KEY_TXS * FIXED_GAS * fee)
        have = w3.eth.get_balance(address)
        if have < target:
            transfers.append((variable, address, target - have))
    keep = max(int((DEPLOY_GAS + GAS["RELAYER_KEY"]) * WEI), MARGIN * RELAYER_GAS * fee)
    return relayer, transfers, keep


def connect(url: str) -> Web3:
    return Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 30}))


def send(w3: Web3, key: str, to: str, value: int) -> str:
    account = Account.from_key(key)
    tip = w3.eth.max_priority_fee
    base = w3.eth.get_block("latest")["baseFeePerGas"]
    tx = {"type": 2, "chainId": w3.eth.chain_id, "nonce": w3.eth.get_transaction_count(account.address, "pending"),
          "to": to, "value": value, "gas": 21_000, "maxPriorityFeePerGas": tip, "maxFeePerGas": 2 * base + tip}
    tx_hash = w3.eth.send_raw_transaction(account.sign_transaction(tx).raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt["status"] != 1:
        raise SystemExit(f"transfer to {to} failed in {tx_hash.hex()}")
    return "0x" + tx_hash.hex().removeprefix("0x")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/fund_keys.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", type=Path, default=REPO / ".env")
    parser.add_argument("--send", action="store_true", help="send the transfers; without it nothing is sent")
    args = parser.parse_args(argv)
    env = read_dotenv(args.env_file)
    if not env.get("RPC_URL") or not env.get("RELAYER_KEY"):
        print("RPC_URL and RELAYER_KEY must be set in .env (python scripts/new_keys.py fills the keys)", file=sys.stderr)
        return 1
    w3 = connect(env["RPC_URL"])
    chain_id = w3.eth.chain_id
    if chain_id not in (BASE_SEPOLIA, ANVIL):
        print(f"RPC_URL is chain {chain_id}; this script sends only on Base Sepolia or Anvil", file=sys.stderr)
        return 1
    relayer, transfers, keep = plan(w3, env)
    balance = w3.eth.get_balance(relayer)
    total = sum(value for _, _, value in transfers)
    print(f"fee now: up to {Decimal(max_fee(w3)) / 10**9:.4f} gwei per gas")
    print(f"relayer {relayer} holds {Decimal(balance) / WEI:.5f} ETH; keeps at least {Decimal(keep) / WEI:.5f} ETH")
    for variable, address, value in transfers:
        print(f"  {variable:<20} {address}  +{Decimal(value) / WEI:.5f} ETH")
    if not transfers:
        print("every sending key already holds enough")
        return 0
    if balance < total + keep:
        short = Decimal(total + keep - balance) / WEI
        print(f"the relayer is {short:.5f} ETH short of the transfers plus its reserve; fund it first", file=sys.stderr)
        return 1
    if not args.send:
        print(f"{len(transfers)} transfers, {Decimal(total) / WEI:.5f} ETH in all; run again with --send to send them")
        return 0
    for variable, address, value in transfers:
        print(f"  sent {variable:<20} {send(w3, env['RELAYER_KEY'], address, value)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

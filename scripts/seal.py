"""Plan item W30 (decision E-36): seal the submission on Base Sepolia, so anyone can check later that nothing changed.

    python scripts/seal.py FILE [FILE ...] --dry-run    # prints the manifest and its hash, sends nothing
    python scripts/seal.py FILE [FILE ...]              # also sends one transaction carrying the hash

Hashes each file with sha256, writes the list (name, size, hash) as a manifest, and hashes the manifest. The
relayer then sends a zero-value transaction to itself whose input is exactly that 32-byte hash: it changes no
contract, so the vault's own report anchor keeps its meaning. Anyone can recompute the manifest from the files and
compare its hash with the transaction's input on Blockscout. The record goes to evidence/seal.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from dev_up import read_dotenv  # noqa: E402
from eth_account import Account  # noqa: E402
from web3 import Web3  # noqa: E402

EXPLORER = "https://base-sepolia.blockscout.com"


def manifest(files: list[Path]) -> str:
    """One line per file, sorted by name: sha256, size in bytes, name. Its sha256 is the seal."""
    lines = []
    for path in sorted(files, key=lambda p: p.name):
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.stat().st_size}  {path.name}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/seal.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", type=Path, default=REPO / "evidence" / "seal.json")
    args = parser.parse_args(argv)

    missing = [str(f) for f in args.files if not f.is_file()]
    if missing:
        raise SystemExit(f"not a file: {', '.join(missing)}")
    text = manifest(args.files)
    seal = "0x" + hashlib.sha256(text.encode()).hexdigest()
    print(text + f"seal {seal}")
    record = {"manifest": text.splitlines(), "seal": seal, "made_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if args.dry_run:
        return 0

    env = read_dotenv(REPO / ".env")
    w3 = Web3(Web3.HTTPProvider(env["RPC_URL"]))
    if w3.eth.chain_id != 84532:
        raise SystemExit("RPC_URL is not Base Sepolia")
    relayer = Account.from_key(env["RELAYER_KEY"])
    tx = {"to": relayer.address, "value": 0, "data": seal, "chainId": 84532,
          "nonce": w3.eth.get_transaction_count(relayer.address, "pending")}
    tx["gas"] = w3.eth.estimate_gas({**tx, "from": relayer.address}) + 5000
    tx.update({"maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.eth.max_priority_fee})
    tx_hash = w3.eth.send_raw_transaction(relayer.sign_transaction(tx).raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    record.update({"tx_hash": "0x" + receipt["transactionHash"].hex().removeprefix("0x"), "block": receipt["blockNumber"],
                   "status": "success" if receipt["status"] == 1 else "failed", "from": relayer.address,
                   "explorer": f"{EXPLORER}/tx/0x{receipt['transactionHash'].hex().removeprefix('0x')}"})
    args.out.write_text(json.dumps(record, indent=2) + "\n")
    print(f"sealed in {record['tx_hash']} (block {record['block']}, {record['status']}): {record['explorer']}")
    return 0 if record["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

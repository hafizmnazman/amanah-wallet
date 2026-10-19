"""Decision E-31: the unchanged AmanahVault on FISCO BCOS, WeBank's consortium chain, through its Web3 RPC.

    bash scripts/fisco_up.sh
    (cd contracts && FISCO_LOCAL=1 forge script script/Fixture.s.sol --rpc-url http://127.0.0.1:8546 --broadcast --legacy --slow)
    .venv/bin/python scripts/fisco_demo.py

The fixture deploys the token and the vault, registers the five signers, sets the three mandates and allowlists
the 45 households, every governance call signed by two trustees, exactly as on Anvil. This script then checks on
FISCO what the 16 scenarios check on Base Sepolia: a routine payout paid on three machine signatures, the tier
computed by the contract, an elevated payout refused without a trustee and paid with one, an unlisted wallet
refused, and a same-lineage quorum refused. verify.py does not carry over: it reads the vault as it was at the
block before each payout, and FISCO's eth_call answers from the latest state (scripts/fisco_up.sh). Keys are
the public Anvil test accounts. Evidence goes to evidence/fisco/.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from eth_account import Account  # noqa: E402
from web3 import Web3  # noqa: E402

from app.agentwallet import devchain, eip712  # noqa: E402
from app.agentwallet.books import Books  # noqa: E402
from app.agentwallet.chain import TransactionLog, VaultClient, tagged  # noqa: E402
from app.agentwallet.types import Intent, Payout  # noqa: E402

SYSTEM_CONFIG = "0x0000000000000000000000000000000000001000"
SYSTEM_CONFIG_ABI = [{"name": "getValueByKey", "type": "function", "stateMutability": "view",
                      "inputs": [{"name": "key", "type": "string"}],
                      "outputs": [{"name": "", "type": "string"}, {"name": "", "type": "int256"}]}]
USDC_ABI = [{"name": "balanceOf", "type": "function", "stateMutability": "view",
             "inputs": [{"name": "a", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]}]


@dataclass
class Check:
    name: str
    expected: str
    got: str
    ok: bool
    tx_hashes: list[str] = field(default_factory=list)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/fisco_demo.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--rpc-url", default="http://127.0.0.1:8546")
    parser.add_argument("--evidence", type=Path, default=REPO / "evidence" / "fisco")
    args = parser.parse_args(argv)

    w3 = Web3(Web3.HTTPProvider(args.rpc_url))
    chain_id = w3.eth.chain_id
    deployment = json.loads((REPO / "contracts" / "deployments" / f"{chain_id}.json").read_text())
    keys = {role: devchain.anvil_key(i) for role, i in devchain.ROLE_INDEX.items()}
    args.evidence.mkdir(parents=True, exist_ok=True)
    csv = args.evidence / "transactions.csv"
    csv.unlink(missing_ok=True)
    client = VaultClient(args.rpc_url, deployment["vault"], keys["relayer"],
                         tx_log=TransactionLog(csv, "", network=str(chain_id)))
    client.settle = lambda block: None  # one node, as on Anvil: a read after a write sees it
    usdc = w3.eth.contract(address=Web3.to_checksum_address(deployment["usdc"]), abi=USDC_ABI)
    books = Books.load()
    checks: list[Check] = []

    def payout(beneficiary_ref: str | None, amount: str, *, programme: str | None = None,
               wallet: str | None = None) -> Payout:
        b = books.beneficiary(beneficiary_ref) if beneficiary_ref else None
        intent = Intent(programme_code=programme or b["programme_code"], beneficiary_ref=beneficiary_ref,
                        wallet=wallet or b["wallet"], amount_usdc=Decimal(amount),
                        household_ref=b["household_ref"] if b else None, proposal_id="0x" + secrets.token_hex(32))
        deadline = w3.eth.get_block("latest")["timestamp"] + 3600
        return eip712.payout_from_intent(intent, books, nonce=secrets.randbits(63), deadline=deadline,
                                         evidence_hash="0x" + secrets.token_hex(32))

    def sign(p: Payout, *roles: str) -> list[str]:
        return [eip712.sign_payout(p, keys[r], chain_id=chain_id, vault=client.address) for r in roles]

    def record(check: Check) -> None:
        checks.append(check)
        print(f"[{'pass' if check.ok else 'FAIL'}] {check.name}: expected {check.expected}, got {check.got}", flush=True)

    # The households allowlisted by the fixture wait out its 60-second cooling-off in real time: FISCO's clock
    # cannot be moved forward as Anvil's can.
    zakat, zakat2 = books.beneficiaries("ZKT-IPOH-FAKIR-M")[:2]
    flood = books.beneficiaries("REL-PERAK-FLOOD")[0]
    ready = max(client.beneficiary(books.programme(b["programme_code"])["programme_id"], b["wallet"])["active_from"]
                for b in (zakat, zakat2, flood))
    if time.time() < ready + 1:
        print(f"waiting {int(ready + 1 - time.time())} s for the cooling-off", flush=True)
        time.sleep(ready + 1 - time.time())
    # FISCO seals a block only when a transaction arrives, and calls run at the latest block's time, so an empty
    # transaction brings the chain's clock to now.
    relayer = Account.from_key(keys["relayer"])
    empty = relayer.sign_transaction({"to": relayer.address, "value": 0, "gas": 21000, "gasPrice": 0, "chainId": chain_id,
                                      "nonce": w3.eth.get_transaction_count(relayer.address, "pending")})
    w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(empty.raw_transaction))

    # 1. A routine payout: three machine signatures, no human
    p = payout(zakat["beneficiary_ref"], "150")
    tier = client.tier_of(p)
    before = usdc.functions.balanceOf(p.beneficiary).call()
    with tagged(scenario="F1", description="Routine payout: planner, auditor and sentinel", expected="paid"):
        tx = client.execute(p, sign(p, "planner", "auditor", "sentinel"))
    moved = usdc.functions.balanceOf(p.beneficiary).call() - before
    record(Check("Routine payout of 150 USDC on three machine signatures", "tier 1, paid, 150 USDC moved",
                 f"tier {tier}, {tx.status}, {Decimal(moved) / 10**6} USDC moved",
                 tier == 1 and tx.status == "success" and moved == 150 * 10**6, [tx.tx_hash]))

    # 2. An emergency grant above the programme's cap: the contract asks for a trustee
    p = payout(flood["beneficiary_ref"], "1200")
    tier = client.tier_of(p)
    with tagged(scenario="F2", description="Elevated grant on machine signatures alone", expected="reverted TrusteeRequired"):
        refused = client.execute(p, sign(p, "planner", "auditor", "sentinel"), expect_revert=True)
    record(Check("Grant of 1,200 USDC above the 300 USDC cap, machine signatures only",
                 "tier 2, reverted TrusteeRequired", f"tier {tier}, {refused.status} {refused.error or ''}".strip(),
                 tier == 2 and refused.status == "reverted" and refused.error == "TrusteeRequired", [refused.tx_hash]))
    with tagged(scenario="F3", description="Elevated grant with a trustee co-signature", expected="paid"):
        tx = client.execute(p, sign(p, "planner", "auditor", "sentinel", "trustee1"))
    record(Check("The same grant with a trustee's co-signature", "paid", tx.status, tx.status == "success", [tx.tx_hash]))

    # 3. Forced attacks, as if the machine keys were stolen
    p = payout(None, "2000", programme="ZKT-IPOH-FAKIR-M", wallet="0x" + secrets.token_hex(20))
    with tagged(scenario="F4", description="Three machine signatures to a wallet that is not allowlisted",
                expected="reverted NotAllowlisted"):
        tx = client.execute(p, sign(p, "planner", "auditor", "sentinel"), expect_revert=True)
    record(Check("Three machine signatures to an unlisted wallet", "reverted NotAllowlisted",
                 f"{tx.status} {tx.error or ''}".strip(), tx.status == "reverted" and tx.error == "NotAllowlisted",
                 [tx.tx_hash]))
    p = payout(zakat2["beneficiary_ref"], "140")
    with tagged(scenario="F5", description="Same-lineage quorum: two keys of one model family",
                expected="reverted SameLineage"):
        tx = client.execute(p, sign(p, "planner", "control_auditor", "sentinel"), expect_revert=True)
    record(Check("Same-lineage quorum: two keys of one model family", "reverted SameLineage",
                 f"{tx.status} {tx.error or ''}".strip(), tx.status == "reverted" and tx.error == "SameLineage",
                 [tx.tx_hash]))

    system = w3.eth.contract(address=Web3.to_checksum_address(SYSTEM_CONFIG), abi=SYSTEM_CONFIG_ABI)
    summary = {
        "chain": "FISCO BCOS", "client": w3.client_version, "web3_chain_id": chain_id,
        "feature_evm_timestamp": system.functions.getValueByKey("feature_evm_timestamp").call()[0],
        "vault": deployment["vault"], "usdc": deployment["usdc"], "deployment_block": deployment["block"],
        "beneficiaries": deployment["beneficiaries"], "fixture_transactions": _fixture_count(chain_id),
        "checks": [asdict(c) for c in checks], "passed": sum(c.ok for c in checks), "total": len(checks),
        "not_carried_over": "verify.py: FISCO's eth_call answers from the latest state whatever block it names, and "
                            "verify.py reads the vault at the block before each payout. With the node's "
                            "enable_separate_block_state on, 3.17.1's Web3 RPC returned no blocks (scripts/fisco_up.sh).",
    }
    (args.evidence / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"{summary['passed']} of {summary['total']} checks as expected on {summary['client']}. Evidence in {args.evidence}")
    return 0 if summary["passed"] == summary["total"] else 1


def _fixture_count(chain_id: int) -> dict | None:
    """How many of the fixture's own transactions (deploys and governance) succeeded, from forge's broadcast record."""
    path = REPO / "contracts" / "broadcast" / "Fixture.s.sol" / str(chain_id) / "run-latest.json"
    if not path.exists():
        return None
    run = json.loads(path.read_text())
    receipts = run.get("receipts", [])
    return {"sent": len(run.get("transactions", [])), "succeeded": sum(int(r["status"], 16) == 1 for r in receipts)}


if __name__ == "__main__":
    raise SystemExit(main())

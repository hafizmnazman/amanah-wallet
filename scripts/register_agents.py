"""Decision E-32: the three machine signers as ERC-8004 agents on Base Sepolia.

    python scripts/register_agents.py            # registers whatever evidence/erc8004.json does not list yet
    python scripts/register_agents.py --check    # reads every registration back and compares it with the vault

ERC-8004's Identity Registry (0x8004A818BFB912233c491871b3d84c89A494BD9e on Base Sepolia) gives each agent an
ERC-721 identity with a registration file and key-value metadata. For the planner, the auditor and the sentinel,
this script registers the card in docs/agents/<role>.json, byte for byte, as an on-chain data URI, with the
role, lineage and evidence view as metadata. The institution's relayer owns the identity, so a compromised agent
key cannot rewrite its own card; setAgentWallet then binds it to the signer's key with that key's own EIP-712
signature, which the registry checks. --check reads each identity back and compares its wallet and lineage with
AmanahVault's own signer registry, so the identity and the key the vault counts are shown to be one.
Keys and RPC_URL come from .env; nothing is printed but addresses, ids and transaction hashes.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from dev_up import read_dotenv  # noqa: E402
from eth_account import Account  # noqa: E402
from eth_account.messages import encode_typed_data  # noqa: E402
from eth_utils import keccak  # noqa: E402
from web3 import Web3  # noqa: E402
from web3.logs import DISCARD  # noqa: E402

from app.agentwallet.chain import ABI as VAULT_ABI  # noqa: E402

REGISTRY = "0x8004A818BFB912233c491871b3d84c89A494BD9e"
EXPLORER = "https://base-sepolia.blockscout.com"
EVIDENCE = REPO / "evidence" / "erc8004.json"
CARDS = REPO / "docs" / "agents"
ROLES = {"planner": ("PLANNER_KEY", 1), "auditor": ("AUDITOR_KEY", 2), "sentinel": ("SENTINEL_KEY", 3)}
REGISTRY_ABI = [
    {"name": "register", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "agentURI", "type": "string"},
                {"name": "metadata", "type": "tuple[]",
                 "components": [{"name": "metadataKey", "type": "string"}, {"name": "metadataValue", "type": "bytes"}]}],
     "outputs": [{"name": "agentId", "type": "uint256"}]},
    {"name": "setAgentWallet", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "agentId", "type": "uint256"}, {"name": "newWallet", "type": "address"},
                {"name": "deadline", "type": "uint256"}, {"name": "signature", "type": "bytes"}], "outputs": []},
    {"name": "getAgentWallet", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "agentId", "type": "uint256"}], "outputs": [{"name": "", "type": "address"}]},
    {"name": "getMetadata", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "agentId", "type": "uint256"}, {"name": "metadataKey", "type": "string"}],
     "outputs": [{"name": "", "type": "bytes"}]},
    {"name": "tokenURI", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "tokenId", "type": "uint256"}], "outputs": [{"name": "", "type": "string"}]},
    {"name": "ownerOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "tokenId", "type": "uint256"}], "outputs": [{"name": "", "type": "address"}]},
    {"name": "Registered", "type": "event", "anonymous": False,
     "inputs": [{"name": "agentId", "type": "uint256", "indexed": True},
                {"name": "agentURI", "type": "string", "indexed": False},
                {"name": "owner", "type": "address", "indexed": True}]},
]


def card_uri(role: str) -> str:
    """The card's exact bytes as a data URI, so the on-chain registration file and the repository's are one."""
    return "data:application/json;base64," + base64.b64encode((CARDS / f"{role}.json").read_bytes()).decode()


def send(w3: Web3, account, fn) -> dict:
    tx = fn.build_transaction({"from": account.address, "chainId": w3.eth.chain_id,
                               "nonce": w3.eth.get_transaction_count(account.address, "pending")})
    tx["gas"] = int(tx["gas"] * 1.25)
    tx_hash = w3.eth.send_raw_transaction(account.sign_transaction(tx).raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt["status"] != 1:
        raise SystemExit(f"transaction {tx_hash.hex()} reverted")
    return receipt


def bind_signature(w3: Web3, agent_id: int, wallet_key: str, owner: str, deadline: int) -> bytes:
    """The agent key's EIP-712 consent to be this identity's wallet, as the registry's setAgentWallet checks it."""
    wallet = Account.from_key(wallet_key)
    typed = {"types": {"EIP712Domain": [{"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                                        {"name": "chainId", "type": "uint256"},
                                        {"name": "verifyingContract", "type": "address"}],
                       "AgentWalletSet": [{"name": "agentId", "type": "uint256"}, {"name": "newWallet", "type": "address"},
                                          {"name": "owner", "type": "address"}, {"name": "deadline", "type": "uint256"}]},
             "primaryType": "AgentWalletSet",
             "domain": {"name": "ERC8004IdentityRegistry", "version": "1", "chainId": w3.eth.chain_id,
                        "verifyingContract": REGISTRY},
             "message": {"agentId": agent_id, "newWallet": wallet.address, "owner": owner, "deadline": deadline}}
    return wallet.sign_message(encode_typed_data(full_message=typed)).signature


def check(w3: Web3, registry, vault, evidence: dict) -> bool:
    ok = True
    for role, entry in evidence["agents"].items():
        agent_id = entry["agentId"]
        card = json.loads((CARDS / f"{role}.json").read_text())
        wallet = registry.functions.getAgentWallet(agent_id).call()
        lineage = registry.functions.getMetadata(agent_id, "lineage").call().decode()
        uri_ok = registry.functions.tokenURI(agent_id).call() == card_uri(role)
        v_role, v_lineage, _view, active = vault.functions.signers(wallet).call()
        same = (wallet == entry["wallet"] and v_role == ROLES[role][1] and active
                and "0x" + v_lineage.hex() == "0x" + keccak(text=lineage).hex() and lineage == card["amanah"]["lineage"])
        ok &= same and uri_ok
        print(f"[{'pass' if same and uri_ok else 'FAIL'}] agent {agent_id} ({role}): wallet {wallet}, lineage {lineage}; "
              f"the vault counts that key as {role} with the same lineage: {same}; on-chain card equals "
              f"docs/agents/{role}.json: {uri_ok}")
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/register_agents.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="read every registration back; send nothing")
    args = parser.parse_args(argv)

    env = read_dotenv(REPO / ".env")
    w3 = Web3(Web3.HTTPProvider(env["RPC_URL"]))
    if w3.eth.chain_id != 84532:
        raise SystemExit("RPC_URL is not Base Sepolia")
    registry = w3.eth.contract(address=Web3.to_checksum_address(REGISTRY), abi=REGISTRY_ABI)
    deployment = json.loads((REPO / "contracts" / "deployments" / "84532.json").read_text())
    vault = w3.eth.contract(address=Web3.to_checksum_address(deployment["vault"]), abi=VAULT_ABI)
    evidence = json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {
        "registry": REGISTRY, "chainId": 84532, "vault": deployment["vault"], "agents": {}}
    if args.check:
        return 0 if check(w3, registry, vault, evidence) else 1

    relayer = Account.from_key(env["RELAYER_KEY"])
    for role, (key_name, _role_id) in ROLES.items():
        entry = evidence["agents"].get(role)
        if entry and entry.get("bind_tx"):
            continue
        card = json.loads((CARDS / f"{role}.json").read_text())
        wallet = Account.from_key(env[key_name]).address
        if not entry:
            metadata = [(k, card["amanah"][k].encode()) for k in ("role", "lineage", "evidenceView")]
            metadata.append(("vault", f"eip155:84532:{deployment['vault']}".encode()))
            receipt = send(w3, relayer, registry.functions.register(card_uri(role), metadata))
            # The receipt also holds the ERC-721 Transfer and MetadataSet logs, which this ABI does not decode
            agent_id = registry.events.Registered().process_receipt(receipt, errors=DISCARD)[0]["args"]["agentId"]
            entry = evidence["agents"][role] = {
                "agentId": agent_id, "wallet": wallet, "owner": relayer.address, "lineage": card["amanah"]["lineage"],
                "register_tx": "0x" + receipt["transactionHash"].hex().removeprefix("0x"),
                "explorer": f"{EXPLORER}/token/{REGISTRY}/instance/{agent_id}",
            }
            # Saved before the binding, so a run that stops here binds on the next run and never registers twice
            EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n")
        settle(registry, entry["agentId"])
        deadline = w3.eth.get_block("latest")["timestamp"] + 240
        signature = bind_signature(w3, entry["agentId"], env[key_name], relayer.address, deadline)
        bound = send(w3, relayer, registry.functions.setAgentWallet(entry["agentId"], wallet, deadline, signature))
        entry["bind_tx"] = "0x" + bound["transactionHash"].hex().removeprefix("0x")
        entry["bound_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n")
        print(f"{role}: agent {entry['agentId']}, wallet {wallet} bound by its own signature; register "
              f"{entry['register_tx']}, bind {entry['bind_tx']}", flush=True)
        settle(registry, entry["agentId"], wallet=wallet)
    return 0 if check(w3, registry, vault, evidence) else 1


def settle(registry, agent_id: int, *, wallet: str | None = None, seconds: int = 90) -> None:
    """Base Sepolia's providers spread reads over several nodes, and a read just after a write can reach one that
    has not seen it (decision B-24): wait until the identity, and its wallet when given, read back."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            registry.functions.ownerOf(agent_id).call()
            if wallet is None or registry.functions.getAgentWallet(agent_id).call() == wallet:
                return
        except Exception:  # not seen yet by the node that answered
            pass
        time.sleep(2)
    raise SystemExit(f"agent {agent_id} did not read back within {seconds} s")


if __name__ == "__main__":
    raise SystemExit(main())

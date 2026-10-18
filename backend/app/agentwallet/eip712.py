"""EIP-712 signing and verification for payouts and governance (plan task B2).

Types come from shared/eip712.json. The domain's chainId and verifyingContract come from the arguments,
or from CHAIN_ID and VAULT_ADDRESS. Digests are computed directly (struct hash and domain separator) and
signatures through eth-account; tests check both against shared/vectors.json.
"""

from __future__ import annotations

import json
from typing import Any

from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak, to_checksum_address

from .config import REPO_ROOT, env, env_int
from .types import Intent, Payout, usdc_to_units

SHARED = json.loads((REPO_ROOT / "shared" / "eip712.json").read_text())
TYPES: dict[str, list[dict[str, str]]] = SHARED["types"]
DOMAIN_TYPE = [
    {"name": "name", "type": "string"},
    {"name": "version", "type": "string"},
    {"name": "chainId", "type": "uint256"},
    {"name": "verifyingContract", "type": "address"},
]

# Governance actions: the ABI types of each action's parameters, in declaration order (plan section 3.2).
ACTION_PARAMS: dict[str, list[str]] = {
    "lowerPosture": ["uint8"],
    "registerSigner": ["address", "uint8", "bytes32", "bytes32"],
    "setSignerActive": ["address", "bool"],
    "setMandate": ["bytes32", "(uint256,uint256,uint256,uint256,uint64,bytes32,bool)"],
    "addBeneficiary": ["bytes32", "address", "bytes32"],
    "unpause": [],
}


def domain(chain_id: int | None = None, vault: str | None = None) -> dict[str, Any]:
    vault = vault or env("VAULT_ADDRESS")
    if not vault:
        raise ValueError("no vault address: pass vault= or set VAULT_ADDRESS")
    return {
        "name": SHARED["domain"]["name"],
        "version": SHARED["domain"]["version"],
        "chainId": chain_id if chain_id is not None else env_int("CHAIN_ID", 84532),
        "verifyingContract": to_checksum_address(vault),
    }


def _type_string(primary: str) -> str:
    return primary + "(" + ",".join(f"{f['type']} {f['name']}" for f in TYPES[primary]) + ")"


def type_hash(primary: str) -> bytes:
    return keccak(text=_type_string(primary))


def _encode_value(kind: str, value: Any) -> Any:
    if kind == "bytes32":
        return bytes.fromhex(value[2:]) if isinstance(value, str) else value
    if kind == "address":
        return to_checksum_address(value)
    return int(value)


def struct_hash(primary: str, message: dict[str, Any]) -> bytes:
    fields = TYPES[primary]
    return keccak(encode(["bytes32"] + [f["type"] for f in fields],
                         [type_hash(primary)] + [_encode_value(f["type"], message[f["name"]]) for f in fields]))


def domain_separator(chain_id: int | None = None, vault: str | None = None) -> bytes:
    d = domain(chain_id, vault)
    return keccak(encode(["bytes32", "bytes32", "bytes32", "uint256", "address"], [
        keccak(text="EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
        keccak(text=d["name"]), keccak(text=d["version"]), d["chainId"], d["verifyingContract"]]))


def _digest(primary: str, message: dict[str, Any], chain_id: int | None, vault: str | None) -> bytes:
    return keccak(b"\x19\x01" + domain_separator(chain_id, vault) + struct_hash(primary, message))


def typed_data(primary: str, message: dict[str, Any], chain_id: int | None = None, vault: str | None = None) -> dict:
    """The full EIP-712 document a wallet signs, with every number as a string for JSON transport."""
    return {
        "types": {"EIP712Domain": DOMAIN_TYPE, primary: TYPES[primary]},
        "primaryType": primary,
        "domain": domain(chain_id, vault),
        "message": {k: (str(v) if isinstance(v, int) else v) for k, v in message.items()},
    }


def _sign(primary: str, message: dict[str, Any], key: str, chain_id: int | None, vault: str | None) -> str:
    full = typed_data(primary, message, chain_id, vault)
    full["message"] = {f["name"]: _encode_value(f["type"], message[f["name"]]) for f in TYPES[primary]}
    signed = Account.sign_message(encode_typed_data(full_message=full), key)
    assert signed.message_hash == _digest(primary, message, chain_id, vault)
    return "0x" + signed.signature.hex().removeprefix("0x")


def _recover(primary: str, message: dict[str, Any], signature: str, chain_id: int | None, vault: str | None) -> str:
    from eth_keys import keys

    raw = bytes.fromhex(signature.removeprefix("0x"))
    v = raw[64] - 27 if raw[64] >= 27 else raw[64]
    sig = keys.Signature(vrs=(v, int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:64], "big")))
    return sig.recover_public_key_from_msg_hash(_digest(primary, message, chain_id, vault)).to_checksum_address()


# Payouts


def payout_digest(payout: Payout, *, chain_id: int | None = None, vault: str | None = None) -> bytes:
    return _digest("Payout", payout.message(), chain_id, vault)


def payout_typed_data(payout: Payout, *, chain_id: int | None = None, vault: str | None = None) -> dict:
    return typed_data("Payout", payout.message(), chain_id, vault)


def sign_payout(payout: Payout, key: str, *, chain_id: int | None = None, vault: str | None = None) -> str:
    return _sign("Payout", payout.message(), key, chain_id, vault)


def recover_payout(payout: Payout, signature: str, *, chain_id: int | None = None, vault: str | None = None) -> str:
    return _recover("Payout", payout.message(), signature, chain_id, vault)


def payout_from_intent(intent: Intent, books, *, nonce: int, deadline: int, evidence_hash: str) -> Payout:
    """Builds the signed struct: the programme's opaque id from the books, the amount in base units."""
    return Payout(
        proposalId=intent.proposal_id,
        programmeId=books.programme(intent.programme_code)["programme_id"],
        beneficiary=to_checksum_address(intent.wallet),
        amount=usdc_to_units(intent.amount_usdc),
        evidenceHash=evidence_hash,
        nonce=nonce,
        deadline=deadline,
    )


# Governance


def params_hash(action: str, *params: Any) -> str:
    """keccak256(abi.encode(params in declaration order)); `unpause` has none, so keccak256 of empty bytes."""
    kinds = ACTION_PARAMS[action]
    if len(params) != len(kinds):
        raise ValueError(f"{action} takes {len(kinds)} parameters, got {len(params)}")
    values = [_encode_param(k, p) for k, p in zip(kinds, params)]
    return "0x" + keccak(encode(kinds, values) if kinds else b"").hex()


def _encode_param(kind: str, value: Any) -> Any:
    if kind.startswith("("):
        return tuple(_encode_param(k, v) for k, v in zip(kind[1:-1].split(","), value))
    if kind == "bool":
        return bool(value)
    return _encode_value(kind, value)


def governance_message(action: str, params_hash_hex: str, gov_nonce: int, deadline: int) -> dict[str, Any]:
    return {"action": "0x" + keccak(text=action).hex(), "paramsHash": params_hash_hex,
            "govNonce": gov_nonce, "deadline": deadline}


def governance_digest(action: str, params_hash_hex: str, gov_nonce: int, deadline: int, *,
                      chain_id: int | None = None, vault: str | None = None) -> bytes:
    return _digest("Governance", governance_message(action, params_hash_hex, gov_nonce, deadline), chain_id, vault)


def sign_governance(action: str, params_hash_hex: str, gov_nonce: int, deadline: int, key: str, *,
                    chain_id: int | None = None, vault: str | None = None) -> str:
    return _sign("Governance", governance_message(action, params_hash_hex, gov_nonce, deadline), key, chain_id, vault)


def recover_governance(action: str, params_hash_hex: str, gov_nonce: int, deadline: int, signature: str, *,
                       chain_id: int | None = None, vault: str | None = None) -> str:
    message = governance_message(action, params_hash_hex, gov_nonce, deadline)
    return _recover("Governance", message, signature, chain_id, vault)


def label(text: str) -> str:
    """keccak256 of a lineage or evidence-view label, as the registry stores it."""
    return "0x" + keccak(text=text).hex()

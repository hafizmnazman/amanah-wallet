"""Chain client for AmanahVault (plan task B3), with web3.py 7.

Reads decode reverts to the contract's error names. Writes go through `_send`, which logs every mined
transaction to evidence/transactions.csv. A call expected to revert is sent with a fixed gas limit, so it
is still mined and has a hash for the proof table (scenarios 10 to 13). Retries for a chain that cannot be
reached are the fail-closed queue's job (queue.py), not this module's.
"""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass, field
from typing import Any

from eth_account import Account
from eth_utils import keccak, to_checksum_address
from web3 import Web3
from web3.exceptions import ContractLogicError

from . import eip712
from .config import REPO_ROOT, Settings, env
from .evidence import TransactionLog
from .types import Payout

ABI = json.loads((REPO_ROOT / "shared" / "abi" / "AmanahVault.json").read_text())
ERC20_ABI = json.loads((REPO_ROOT / "shared" / "abi" / "MockUSDC.json").read_text())
FIXED_GAS = 1_000_000
ROLES = ["NONE", "PLANNER", "AUDITOR", "SENTINEL", "TRUSTEE", "GUARDIAN", "POSTURE_ORACLE"]
VERDICTS = ["NONE", "APPROVE", "REJECT", "ESCALATE"]


def _error_selectors(abi: list[dict]) -> dict[str, str]:
    selectors = {}
    for item in abi:
        if item["type"] == "error":
            signature = f"{item['name']}({','.join(i['type'] for i in item['inputs'])})"
            selectors["0x" + keccak(text=signature)[:4].hex()] = item["name"]
    return selectors


ERRORS = _error_selectors(ABI)


_TAGS: dict[str, str] = {}


@contextlib.contextmanager
def tagged(**tags: str):
    """Tags every transaction that any client sends inside the block (scenario, expected, description) in
    evidence/transactions.csv, unless a call passes its own. scripts/run_demo.py tags each scenario so,
    including the refusals the checkers anchor with their own clients."""
    saved = dict(_TAGS)
    _TAGS.update(tags)
    try:
        yield
    finally:
        _TAGS.clear()
        _TAGS.update(saved)


class ChainError(Exception):
    """A call or transaction the vault refused. `name` is the custom error, for example NotAllowlisted."""

    def __init__(self, name: str, data: str = ""):
        super().__init__(name)
        self.name = name
        self.data = data


class ChainUnavailable(Exception):
    """The RPC endpoint could not be reached; the caller fails closed and queues the payout."""


@dataclass
class TxResult:
    tx_hash: str
    status: str  # "success" or "reverted"
    block: int | None
    error: str | None = None
    gas_used: int | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


def decode_error(data: str | bytes | None) -> str:
    if data is None:
        return "unknown"
    text = data if isinstance(data, str) else "0x" + bytes(data).hex()
    return ERRORS.get(text[:10].lower(), f"unknown {text[:10]}")


def _revert_data(exc: Exception) -> str | None:
    data = getattr(exc, "data", None)
    if isinstance(data, dict):
        data = data.get("data")
    if isinstance(data, str) and data.startswith("0x"):
        return data
    for arg in getattr(exc, "args", ()):
        if isinstance(arg, str) and arg.startswith("0x"):
            return arg
    return None


class VaultClient:
    def __init__(self, rpc_url: str, vault_address: str, relayer_key: str | None = None, *,
                 tx_log: TransactionLog | None = None, timeout: int = 120):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
        self.address = to_checksum_address(vault_address)
        self.vault = self.w3.eth.contract(address=self.address, abi=ABI)
        self.relayer = Account.from_key(relayer_key) if relayer_key else None
        self.tx_log = tx_log
        self.timeout = timeout
        try:
            self.chain_id = self.w3.eth.chain_id
        except Exception as exc:  # requests and socket errors differ by platform
            raise ChainUnavailable(str(exc)) from exc

    @classmethod
    def from_env(cls, *, relayer_key: str | None = None) -> "VaultClient":
        s = Settings.from_env()
        if not s.rpc_url or not s.vault_address:
            raise ChainUnavailable("RPC_URL and VAULT_ADDRESS must be set")
        log = TransactionLog(s.evidence_dir / "transactions.csv", s.explorer_url, network=str(s.chain_id))
        return cls(s.rpc_url, s.vault_address, relayer_key or env("RELAYER_KEY"), tx_log=log)

    # Reads

    def _call(self, fn) -> Any:
        try:
            return fn.call()
        except ContractLogicError as exc:
            data = _revert_data(exc)
            raise ChainError(decode_error(data), data or "") from exc

    def tier_of(self, payout: Payout) -> int:
        return self._call(self.vault.functions.tierOf(payout.as_tuple()))

    def hash_payout(self, payout: Payout) -> bytes:
        return self._call(self.vault.functions.hashPayout(payout.as_tuple()))

    def posture(self) -> int:
        return self._call(self.vault.functions.posture())

    def last_report_hash(self) -> str:
        return "0x" + self._call(self.vault.functions.lastReportHash()).hex()

    def posture_changed_at(self) -> int:
        return self._call(self.vault.functions.postureChangedAt())

    def paused(self) -> bool:
        return self._call(self.vault.functions.paused())

    def signer(self, address: str) -> dict:
        role, lineage, view, active = self._call(self.vault.functions.signers(to_checksum_address(address)))
        return {"role": ROLES[role], "lineage": "0x" + lineage.hex(), "evidence_view": "0x" + view.hex(), "active": active}

    def mandate(self, programme_id: str) -> dict:
        names = ["cap", "hardCeiling", "dailyBudget", "perBeneficiaryCap", "expiry", "purposeHash", "active"]
        values = self._call(self.vault.functions.mandates(bytes.fromhex(programme_id[2:])))
        return dict(zip(names, values))

    def beneficiary(self, programme_id: str, wallet: str) -> dict:
        id_hash, active_from, active = self._call(
            self.vault.functions.beneficiaries(bytes.fromhex(programme_id[2:]), to_checksum_address(wallet)))
        return {"id_hash": "0x" + id_hash.hex(), "active_from": active_from, "active": active}

    def spent_today(self, programme_id: str) -> int:
        return self._call(self.vault.functions.spentToday(bytes.fromhex(programme_id[2:])))

    def spent_this_period(self, programme_id: str, wallet: str) -> int:
        return self._call(self.vault.functions.spentThisPeriod(bytes.fromhex(programme_id[2:]),
                                                               to_checksum_address(wallet)))

    def nonce_used(self, nonce: int) -> bool:
        return self._call(self.vault.functions.nonceUsed(nonce))

    def gov_nonce_used(self, nonce: int) -> bool:
        return self._call(self.vault.functions.govNonceUsed(nonce))

    def decision(self, anchor_id: str) -> dict:
        proposal_id, verdict, signer, block = self._call(self.vault.functions.decisions(bytes.fromhex(anchor_id[2:])))
        return {"proposal_id": "0x" + proposal_id.hex(), "verdict": VERDICTS[verdict], "signer": signer, "block": block}

    def usdc_balance(self, address: str) -> int:
        usdc = self.w3.eth.contract(address=self._call(self.vault.functions.usdc()), abi=ERC20_ABI)
        return usdc.functions.balanceOf(to_checksum_address(address)).call()

    # Writes

    def execute(self, payout: Payout, sigs: list[str], **tags) -> TxResult:
        fn = self.vault.functions.execute(payout.as_tuple(), [bytes.fromhex(s[2:]) for s in sigs])
        return self._send(fn, function="execute", **tags)

    def execute_override(self, payout: Payout, refusal_anchor: str, sigs: list[str], **tags) -> TxResult:
        fn = self.vault.functions.executeOverride(payout.as_tuple(), bytes.fromhex(refusal_anchor[2:]),
                                                  [bytes.fromhex(s[2:]) for s in sigs])
        return self._send(fn, function="executeOverride", **tags)

    def anchor_decision(self, proposal_id: str, verdict: str, evidence_hash: str, *, key: str,
                        **tags) -> tuple[TxResult, str | None]:
        """Sent by the checker's own key: the vault records msg.sender as the decision's signer."""
        fn = self.vault.functions.anchorDecision(bytes.fromhex(proposal_id[2:]), VERDICTS.index(verdict),
                                                 bytes.fromhex(evidence_hash[2:]))
        result = self._send(fn, key=key, function="anchorDecision", **tags)
        anchor = next((e["anchorId"] for e in result.events if e["event"] == "DecisionAnchored"), None)
        return result, anchor

    def anchor_report(self, report_hash: str, *, key: str, **tags) -> TxResult:
        return self._send(self.vault.functions.anchorReport(bytes.fromhex(report_hash[2:])), key=key,
                          function="anchorReport", **tags)

    def raise_posture(self, level: int, report_hash: str, *, key: str, **tags) -> TxResult:
        return self._send(self.vault.functions.raisePosture(level, bytes.fromhex(report_hash[2:])), key=key,
                          function="raisePosture", **tags)

    def pause(self, *, key: str, **tags) -> TxResult:
        return self._send(self.vault.functions.pause(), key=key, function="pause", **tags)

    def cancel_beneficiary(self, programme_id: str, wallet: str, *, key: str, **tags) -> TxResult:
        fn = self.vault.functions.cancelBeneficiary(bytes.fromhex(programme_id[2:]), to_checksum_address(wallet))
        return self._send(fn, key=key, function="cancelBeneficiary", **tags)

    # Governance: builds paramsHash, collects the trustees' signatures and sends

    def governance(self, action: str, params: tuple, trustee_keys: list[str], *, gov_nonce: int | None = None,
                   deadline: int | None = None, sender_key: str | None = None, **tags) -> TxResult:
        gov_nonce = gov_nonce if gov_nonce is not None else self._fresh_gov_nonce()
        deadline = deadline or self.w3.eth.get_block("latest")["timestamp"] + 3600
        ph = eip712.params_hash(action, *params)
        sigs = [bytes.fromhex(eip712.sign_governance(action, ph, gov_nonce, deadline, k, chain_id=self.chain_id,
                                                     vault=self.address)[2:]) for k in trustee_keys]
        args = [_abi_arg(kind, value) for kind, value in zip(eip712.ACTION_PARAMS[action], params)]
        fn = getattr(self.vault.functions, action)(*args, gov_nonce, deadline, sigs)
        return self._send(fn, key=sender_key, function=action, **tags)

    def _fresh_gov_nonce(self) -> int:
        import secrets

        return secrets.randbits(63)

    # Sending

    def _send(self, fn, *, key: str | None = None, expect_revert: bool = False, function: str = "",
              scenario: str = "", description: str = "", expected: str = "") -> TxResult:
        scenario = scenario or _TAGS.get("scenario", "")
        description = description or _TAGS.get("description", "")
        expected = expected or _TAGS.get("expected", "")
        account = Account.from_key(key) if key else self.relayer
        if account is None:
            raise ValueError("no sending key: pass key= or give the client a relayer key")
        params = {"from": account.address, "chainId": self.chain_id,
                  "nonce": self.w3.eth.get_transaction_count(account.address, "pending")}
        if expect_revert:
            params["gas"] = FIXED_GAS
        try:
            tx = fn.build_transaction(params)
        except ContractLogicError as exc:
            data = _revert_data(exc)
            raise ChainError(decode_error(data), data or "") from exc
        except Exception as exc:
            if "connection" in str(exc).lower():
                raise ChainUnavailable(str(exc)) from exc
            raise
        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=self.timeout)
        status = "success" if receipt["status"] == 1 else "reverted"
        error = None if status == "success" else self._revert_reason(tx, receipt["blockNumber"])
        events = self._events(receipt) if status == "success" else []
        result = TxResult("0x" + bytes(tx_hash).hex(), status, receipt["blockNumber"], error, receipt["gasUsed"], events)
        if self.tx_log is not None:
            self.tx_log.append(result.tx_hash, status, result.block, scenario=scenario, description=description,
                               expected=expected, function=function, error=error or "")
        return result

    def send_expect_revert(self, fn, **kwargs) -> TxResult:
        return self._send(fn, expect_revert=True, **kwargs)

    def _revert_reason(self, tx: dict, block: int) -> str:
        """Replays the call on the block before it was mined to read the error it reverted with."""
        try:
            self.w3.eth.call({"to": tx["to"], "from": tx["from"], "data": tx["data"]}, block_identifier=block - 1)
        except ContractLogicError as exc:
            return decode_error(_revert_data(exc))
        except Exception as exc:
            return f"unknown ({type(exc).__name__})"
        return "unknown (the replay did not revert)"

    def _events(self, receipt) -> list[dict[str, Any]]:
        from web3.logs import DISCARD

        found = []
        for name in ("PayoutExecuted", "DecisionAnchored", "ReportAnchored", "PostureRaised", "PostureLowered",
                     "SignerRegistered", "SignerActiveSet", "MandateSet", "BeneficiaryAdded", "BeneficiaryCancelled"):
            for log in getattr(self.vault.events, name)().process_receipt(receipt, errors=DISCARD):
                args = {k: ("0x" + v.hex() if isinstance(v, bytes) else v) for k, v in dict(log["args"]).items()}
                found.append({"event": name, **args})
        return found


def _abi_arg(kind: str, value: Any) -> Any:
    if kind == "bytes32":
        return bytes.fromhex(value[2:]) if isinstance(value, str) else value
    if kind == "address":
        return to_checksum_address(value)
    if kind.startswith("("):
        return tuple(_abi_arg(k, v) for k, v in zip(kind[1:-1].split(","), value))
    if kind == "bool":
        return bool(value)
    return int(value)

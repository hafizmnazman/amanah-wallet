"""Plan task E1: checks an executed payout against the vault's rules, from the chain alone.

    python scripts/verify.py <txHash> [--export FILE]
    python scripts/verify.py --input FILE          # an export, perhaps hand-edited: it must then fail
    python scripts/verify.py --csv evidence/transactions.csv    # every executed payout in the file

RPC_URL and VAULT_ADDRESS come from the environment or .env. For one payout it prints pass or fail for:
- the signatures recover to the signers the PayoutExecuted event names;
- the roles the vault requires are present, active and registered at the block before;
- the planner's and the auditor's lineages differ;
- the tier matches tierOf at the block before;
- the amount is within the hard ceiling, the cap (tier 1), the daily budget and the 30-day cap;
- the beneficiary is allowlisted and past its cooling-off at that block;
- a trustee signed when the tier is 2, and two did for an override;
- an override cites an anchored REJECT or ESCALATE for the same proposal.
The exit code is 1 when any check fails.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from web3 import Web3  # noqa: E402
from web3.logs import DISCARD  # noqa: E402

from app.agentwallet import eip712  # noqa: E402
from app.agentwallet.chain import ABI, ROLES, VERDICTS  # noqa: E402
from app.agentwallet.types import Payout  # noqa: E402

FIELDS = ("proposalId", "programmeId", "beneficiary", "amount", "evidenceHash", "nonce", "deadline")
DAY, PERIOD = 86_400, 30 * 86_400


@dataclass
class Report:
    tx_hash: str
    checks: list[tuple[bool, str]] = field(default_factory=list)

    def check(self, ok: bool, text: str) -> bool:
        self.checks.append((bool(ok), text))
        return bool(ok)

    @property
    def ok(self) -> bool:
        return bool(self.checks) and all(ok for ok, _ in self.checks)

    def print(self) -> None:
        print(f"{self.tx_hash}: {'PASS' if self.ok else 'FAIL'}")
        for ok, text in self.checks:
            print(f"  {'pass' if ok else 'FAIL'}  {text}")


def _hex(value) -> str:
    return "0x" + bytes(value).hex() if isinstance(value, (bytes, bytearray)) else str(value)


def export(w3: Web3, vault, tx_hash: str) -> dict:
    """The payout and signatures from a transaction's input, as plain strings."""
    tx = w3.eth.get_transaction(tx_hash)
    fn, args = vault.decode_function_input(tx["input"])
    p = args["p"]
    values = [p[name] for name in FIELDS] if isinstance(p, dict) else list(p)
    payout = {name: str(v) if isinstance(v, int) else _hex(v) for name, v in zip(FIELDS, values)}
    out = {"tx_hash": tx_hash, "function": fn.fn_name, "block": tx["blockNumber"], "payout": payout,
           "sigs": [_hex(s) for s in args["sigs"]]}
    if "refusalAnchor" in args:
        out["refusal_anchor"] = _hex(args["refusalAnchor"])
    return out


def verify(w3: Web3, vault, data: dict) -> Report:
    report = Report(data["tx_hash"])
    receipt = w3.eth.get_transaction_receipt(data["tx_hash"])
    block = receipt["blockNumber"]
    before = block - 1
    when = w3.eth.get_block(block)["timestamp"]
    previous = w3.eth.get_block(before)["timestamp"]
    payout = Payout.from_strings(data["payout"])
    events = vault.events.PayoutExecuted().process_receipt(receipt, errors=DISCARD)  # USDC's Transfer log is not ours
    if not report.check(receipt["status"] == 1 and events, "the transaction succeeded and emitted PayoutExecuted"):
        return report
    event = events[0]["args"]
    is_override = data["function"] == "executeOverride"
    report.check(event["amount"] == payout.amount and event["beneficiary"].lower() == payout.beneficiary.lower()
                 and _hex(event["proposalId"]) == payout.proposalId.lower(),
                 "the event's proposal, beneficiary and amount match the payout in the input")

    chain_id = w3.eth.chain_id
    try:
        signers = [eip712.recover_payout(payout, s, chain_id=chain_id, vault=vault.address) for s in data["sigs"]]
    except Exception as exc:  # malformed signatures in a hand-edited file
        report.check(False, f"the signatures recover ({exc})")
        return report
    report.check(sorted(a.lower() for a in signers) == sorted(a.lower() for a in event["signers"]),
                 "the signatures recover to the signers the event names")

    registry = {}
    for a in signers:
        role, lineage, _view, active = vault.functions.signers(a).call(block_identifier=before)
        registry[a] = {"role": ROLES[role], "lineage": _hex(lineage), "active": active}
    by_role: dict[str, list[str]] = {}
    for a, r in registry.items():
        by_role.setdefault(r["role"], []).append(a)
    report.check(all(r["active"] for r in registry.values()) and "NONE" not in by_role,
                 "every signer is registered and active at the block before: "
                 + ", ".join(f"{r['role'].lower()} {a[:10]}" for a, r in registry.items()))
    tier = event["tier"]
    trustees = len(by_role.get("TRUSTEE", []))
    if is_override:
        report.check(len(by_role.get("PLANNER", [])) == 1 and trustees >= 2,
                     f"an override has the planner and at least two trustees ({trustees})")
        anchor = data.get("refusal_anchor")
        proposal, verdict, refuser, _ = vault.functions.decisions(bytes.fromhex(anchor[2:])).call(block_identifier=before)
        refuser_role = ROLES[vault.functions.signers(refuser).call(block_identifier=before)[0]]
        report.check(_hex(proposal) == payout.proposalId.lower() and VERDICTS[verdict] in ("REJECT", "ESCALATE")
                     and refuser_role in ("AUDITOR", "SENTINEL"),
                     f"the cited refusal is an anchored {VERDICTS[verdict]} by the {refuser_role.lower()} for this proposal")
        report.check(tier == 3, f"the event reports tier 3 for an override (got {tier})")
    else:
        roles_ok = all(len(by_role.get(r, [])) == 1 for r in ("PLANNER", "AUDITOR", "SENTINEL"))
        report.check(roles_ok, "the planner, the auditor and the sentinel each signed once")
        if roles_ok:
            planner, auditor = registry[by_role["PLANNER"][0]], registry[by_role["AUDITOR"][0]]
            report.check(planner["lineage"] != auditor["lineage"], "the planner's and the auditor's lineages differ")
        expected_tier = vault.functions.tierOf(payout.as_tuple()).call(block_identifier=before)
        note = "" if when // DAY == previous // DAY else " (a day boundary falls between the blocks, so this is approximate)"
        report.check(expected_tier == tier, f"the tier is {tier}, as tierOf gives at the block before{note}")
        if tier == 2:
            report.check(trustees >= 1, f"a trustee co-signed the elevated payout ({trustees})")

    pid = bytes.fromhex(payout.programmeId[2:])
    cap, ceiling, budget, per_beneficiary, expiry, _purpose, active = vault.functions.mandates(pid).call(block_identifier=before)
    spent_day = vault.functions.spentToday(pid).call(block_identifier=before) if when // DAY == previous // DAY else 0
    spent_period = (vault.functions.spentThisPeriod(pid, payout.beneficiary).call(block_identifier=before)
                    if when // PERIOD == previous // PERIOD else 0)
    report.check(active and when <= expiry, "the mandate is active and not expired")
    report.check(payout.amount <= ceiling and (is_override or tier > 1 or payout.amount <= cap),
                 f"the amount {payout.amount / 1e6:,.2f} is within the hard ceiling {ceiling / 1e6:,.2f}"
                 + ("" if is_override or tier > 1 else f" and the cap {cap / 1e6:,.2f}"))
    report.check(spent_day + payout.amount <= budget,
                 f"the day's spend {(spent_day + payout.amount) / 1e6:,.2f} is within the budget {budget / 1e6:,.2f}")
    report.check(spent_period + payout.amount <= per_beneficiary,
                 f"the beneficiary's 30-day total {(spent_period + payout.amount) / 1e6:,.2f} is within "
                 f"{per_beneficiary / 1e6:,.2f}")
    _id, active_from, listed = vault.functions.beneficiaries(pid, payout.beneficiary).call(block_identifier=before)
    report.check(listed and active_from <= when, "the beneficiary is allowlisted and past its cooling-off")
    return report


def _dotenv() -> dict[str, str]:
    path = REPO / ".env"
    values = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip():
                    values[k.strip()] = v.strip()
    return values


def connect(rpc_url: str | None = None, vault_address: str | None = None):
    dotenv = _dotenv()
    rpc = rpc_url or os.environ.get("RPC_URL") or dotenv.get("RPC_URL")
    address = vault_address or os.environ.get("VAULT_ADDRESS") or dotenv.get("VAULT_ADDRESS")
    if not rpc or not address:
        raise SystemExit("set RPC_URL and VAULT_ADDRESS, or pass --rpc-url and --vault")
    w3 = Web3(Web3.HTTPProvider(rpc))
    return w3, w3.eth.contract(address=Web3.to_checksum_address(address), abi=ABI)


def executed_payouts(csv_path: Path) -> list[str]:
    with Path(csv_path).open(newline="") as fh:
        return [r["tx_hash"] for r in csv.DictReader(fh)
                if r["status"] == "success" and r["function"] in ("execute", "executeOverride")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/verify.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("tx_hash", nargs="?")
    parser.add_argument("--input", type=Path, help="verify an export instead of the transaction's own input")
    parser.add_argument("--export", type=Path, help="write the transaction's payout and signatures to a file")
    parser.add_argument("--csv", type=Path, help="verify every executed payout listed in a transactions CSV")
    parser.add_argument("--rpc-url")
    parser.add_argument("--vault")
    args = parser.parse_args(argv)
    w3, vault = connect(args.rpc_url, args.vault)
    if args.csv:
        reports = [verify(w3, vault, export(w3, vault, h)) for h in executed_payouts(args.csv)]
        for r in reports:
            if not r.ok:
                r.print()
        passed = sum(r.ok for r in reports)
        print(f"{passed} of {len(reports)} executed payouts pass")
        return 0 if reports and passed == len(reports) else 1
    if args.input:
        data = json.loads(args.input.read_text())
    elif args.tx_hash:
        data = export(w3, vault, args.tx_hash)
        if args.export:
            args.export.write_text(json.dumps(data, indent=2))
    else:
        parser.error("give a transaction hash, --input or --csv")
    report = verify(w3, vault, data)
    report.print()
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

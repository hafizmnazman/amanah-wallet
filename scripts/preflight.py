"""Checks .env, keys, gas, USDC, the deployment and the model settings before the paid runs.

    python scripts/preflight.py                    # every stage
    python scripts/preflight.py --stage deploy     # plan task A6: what Deploy.s.sol needs
    python scripts/preflight.py --stage demo       # run_demo.py --network base-sepolia
    python scripts/preflight.py --stage models     # the live model calls
    python scripts/preflight.py --stage redteam    # the full red-team run (C6, C7)
    python scripts/preflight.py --ping             # also make the four small paid calls of pytest -m live

It reads .env (or --env-file) and the chain at RPC_URL, and sends nothing. Each check prints pass, FAIL or
todo, and names the HANDOFF item that fixes it. The exit code is 1 when any check fails.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))

from eth_account import Account  # noqa: E402
from web3 import Web3  # noqa: E402

from dev_up import read_dotenv  # noqa: E402

BASE_SEPOLIA = 84532
CIRCLE_USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
DONATION_USDC = 5000  # the books' receipt RCPT-2026-10-0001, which scenario 5 deposits
# ETH each sending key needs on Base Sepolia (HANDOFF item 5). Gas there costs a fraction of a cent.
GAS = {"RELAYER_KEY": Decimal("0.005"), "PLANNER_KEY": Decimal("0.0005"), "AUDITOR_KEY": Decimal("0.0005"),
       "SENTINEL_KEY": Decimal("0.0005"), "POSTURE_ORACLE_KEY": Decimal("0.0005"), "GUARDIAN_KEY": Decimal("0.0005"),
       "DONOR_KEY": Decimal("0.0005")}
DEPLOY_GAS = Decimal("0.01")
MODEL_SETTINGS = {
    "planner": ["ANTHROPIC_API_KEY", "PLANNER_MODEL"],
    "auditor": ["DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "AUDITOR_MODEL"],
    "red-team agent": ["OPENAI_API_KEY", "REDTEAM_MODEL"],
    "GPT auditor": ["OPENAI_API_KEY", "AUDITOR_GPT_MODEL"],
}
PRICES = ["PLANNER_PRICE_PER_MTOK", "AUDITOR_PRICE_PER_MTOK", "AUDITOR_CONTROL_PRICE_PER_MTOK",
          "REDTEAM_PRICE_PER_MTOK", "AUDITOR_GPT_PRICE_PER_MTOK"]
SEEDS_MIN, SEEDS_PER_CLASS = 40, 4
STAGES = ("deploy", "demo", "models", "redteam")


@dataclass
class Check:
    stage: str
    name: str
    status: str  # "pass", "FAIL" or "todo"
    detail: str = ""

    def line(self) -> str:
        return f"{self.status:<5} [{self.stage}] {self.name}" + (f": {self.detail}" if self.detail else "")


class Preflight:
    def __init__(self, env: dict[str, str], *, env_file: Path):
        self.env = env
        self.env_file = env_file
        self.checks: list[Check] = []
        self._w3: Web3 | None = None
        self._w3_error = ""

    def add(self, stage: str, name: str, ok: bool | None, detail: str = "") -> None:
        status = "todo" if ok is None else ("pass" if ok else "FAIL")
        self.checks.append(Check(stage, name, status, detail))

    @property
    def w3(self) -> Web3 | None:
        if self._w3 is None and not self._w3_error:
            url = self.env.get("RPC_URL")
            if not url:
                self._w3_error = "RPC_URL is not set"
                return None
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 20}))
            try:
                w3.eth.chain_id
                self._w3 = w3
            except Exception as exc:  # requests and socket errors differ by platform
                self._w3_error = f"{type(exc).__name__}"
        return self._w3

    def eth(self, address: str) -> Decimal:
        return Decimal(self.w3.eth.get_balance(Web3.to_checksum_address(address))) / Decimal(10**18)

    def address(self, variable: str) -> str | None:
        """The address of an address variable, or of the key in <variable>_KEY."""
        value = self.env.get(variable)
        if value and Web3.is_address(value):
            return Web3.to_checksum_address(value)
        key = self.env.get(variable if variable.endswith("_KEY") else f"{variable}_KEY")
        if key:
            try:
                return Account.from_key(key).address
            except (ValueError, TypeError):
                return None
        return None

    # Stages

    def common(self) -> None:
        ignored = subprocess.run(["git", "check-ignore", "-q", str(self.env_file)], cwd=REPO).returncode == 0
        self.add("all", f"{self.env_file.name} exists and git ignores it", self.env_file.exists() and ignored,
                 "" if self.env_file.exists() else "copy .env.example to .env and fill it in")
        if self.w3 is None:
            self.add("all", "RPC_URL answers", False, self._w3_error)
            return
        chain_id = self.w3.eth.chain_id
        self.add("all", "RPC_URL is Base Sepolia", chain_id == BASE_SEPOLIA, f"chain id {chain_id}")

    def deploy(self) -> None:
        self.add("deploy", "BASESCAN_API_KEY is set, for --verify", bool(self.env.get("BASESCAN_API_KEY")))
        people = {v: self.address(v) for v in ("TRUSTEE1", "TRUSTEE2", "TRUSTEE3", "GUARDIAN")}
        missing = [v for v, a in people.items() if a is None]
        distinct = len({a for a in people.values() if a}) == len([a for a in people.values() if a])
        self.add("deploy", "three trustees and a guardian, by address or key", not missing and distinct,
                 ("missing " + ", ".join(missing)) if missing else ("" if distinct else "two of them are the same address"))
        relayer = self.address("RELAYER_KEY")
        if relayer is None:
            self.add("deploy", "RELAYER_KEY is set", False)
        elif self.w3 is not None:
            have = self.eth(relayer)
            self.add("deploy", f"the relayer holds at least {DEPLOY_GAS} ETH for the deploy", have >= DEPLOY_GAS,
                     f"{relayer} holds {have:.5f} ETH (HANDOFF item 3)")

    def demo(self) -> None:
        record_path = REPO / "contracts" / "deployments" / f"{BASE_SEPOLIA}.json"
        record = json.loads(record_path.read_text()) if record_path.exists() else None
        self.add("demo", "contracts/deployments/84532.json exists", record is not None,
                 "" if record else "run the deploy first (HANDOFF item 3)")
        self.books_hmac()
        self.grant_fits()
        self.add("demo", "CONTROL_AUDITOR_KEY is set, for scenario 11's same-lineage quorum",
                 self.address("CONTROL_AUDITOR_KEY") is not None, "it only signs, so it needs no ETH")
        if self.w3 is None or record is None:
            return
        vault = Web3.to_checksum_address(record["vault"])
        has_code = len(self.w3.eth.get_code(vault)) > 0
        self.add("demo", "the vault in the deployment record has code", has_code, vault)
        configured = self.env.get("VAULT_ADDRESS")
        if configured:
            self.add("demo", "VAULT_ADDRESS matches the deployment record", configured.lower() == vault.lower(),
                     f".env has {configured}")
        usdc = record.get("usdc", "")
        self.add("demo", "the vault uses Circle's Base Sepolia USDC", usdc.lower() == CIRCLE_USDC.lower(),
                 f"{usdc}; MockUSDC instead is HANDOFF item 4's other option")
        for variable, need in GAS.items():
            who = self.address(variable) if variable != "DONOR_KEY" else (self.address("DONOR_KEY")
                                                                          or self.address("RELAYER_KEY"))
            if who is None:
                self.add("demo", f"{variable} is set", False, "HANDOFF item 5")
                continue
            have = self.eth(who)
            self.add("demo", f"{variable.removesuffix('_KEY').lower()} holds at least {need} ETH", have >= need,
                     f"{who} holds {have:.5f} ETH")
        self.trustee_keys(vault)
        self.donor_usdc(usdc)
        self.frontend(vault)

    def books_hmac(self) -> None:
        books = json.loads((REPO / "redteam" / "data" / "books.json").read_text())
        key = self.env.get("INSTITUTION_HMAC_KEY")
        if not key:
            self.add("demo", "INSTITUTION_HMAC_KEY is set", False, "HANDOFF item 2")
            return
        b = books["beneficiaries"][0]
        expected = "0x" + hmac.new(key.encode(), b["beneficiary_id"].encode(), hashlib.sha256).hexdigest()
        self.add("demo", "the books' id hashes use INSTITUTION_HMAC_KEY", expected == b["id_hash"],
                 "" if expected == b["id_hash"] else "regenerate: python -m redteam.datagen (HANDOFF item 2)")

    def grant_fits(self) -> None:
        books = json.loads((REPO / "redteam" / "data" / "books.json").read_text())
        mandates = json.loads((REPO / "redteam" / "data" / "mandates.json").read_text())["programmes"]
        grant = next((r for r in books["requests"] if r["request_ref"] == "REQ-REL-0001"), None)
        relief = next((m for m in mandates if m["code"] == "REL-PERAK-FLOOD"), None)
        if grant is None or relief is None:
            self.add("demo", "scenario 7's grant fits the flood relief cap", False, "the grant or the mandate is missing")
            return
        amount = Decimal(str(grant["amount_usdc"]))
        cap = Decimal(str(relief["per_beneficiary_cap_usdc"]))
        self.add("demo", "scenario 7's grant fits the flood relief per-beneficiary cap", amount <= cap,
                 f"grant {amount:,} USDC, cap {cap:,} USDC (decision A-10)")

    def trustee_keys(self, vault: str) -> None:
        from app.agentwallet.chain import VaultClient

        client = VaultClient(self.env["RPC_URL"], vault)
        for variable in ("TRUSTEE1_KEY", "TRUSTEE2_KEY"):
            who = self.address(variable)
            if who is None:
                self.add("demo", f"{variable} is set, for the scripted governance", False, "HANDOFF item 10")
                continue
            role = client.signer(who)["role"]
            self.add("demo", f"{variable} is a trustee in the vault", role == "TRUSTEE", f"{who} is {role}")

    def donor_usdc(self, usdc: str) -> None:
        from app.agentwallet.chain import ERC20_ABI

        donor = self.address("DONOR_KEY") or self.address("RELAYER_KEY")
        if donor is None or not usdc:
            return
        token = self.w3.eth.contract(address=Web3.to_checksum_address(usdc), abi=ERC20_ABI)
        have = Decimal(token.functions.balanceOf(donor).call()) / Decimal(10**6)
        self.add("demo", f"the donor holds the {DONATION_USDC:,} USDC scenario 5 deposits", have >= DONATION_USDC,
                 f"{donor} holds {have:,.2f} USDC (HANDOFF item 4)")

    def frontend(self, vault: str) -> None:
        local = read_dotenv(REPO / "frontend" / ".env.local")
        ok = local.get("VITE_VAULT_ADDRESS", "").lower() == vault.lower() and local.get("VITE_CHAIN_ID") == str(BASE_SEPOLIA)
        self.add("demo", "frontend/.env.local names this vault and chain 84532", ok or None,
                 "" if ok else "for the MetaMask trustee, D3 (HANDOFF item 10)")

    def models(self) -> None:
        for role, variables in MODEL_SETTINGS.items():
            missing = [v for v in variables if not self.env.get(v)]
            self.add("models", f"the {role}'s key and model", not missing, ("missing " + ", ".join(missing)) if missing else "")
        unpriced = [p for p in PRICES if not self.env.get(p)]
        self.add("models", "prices for the red team's cost column", not unpriced or None,
                 ("unset: " + ", ".join(unpriced)) if unpriced else "")
        fallback = self.env.get("PLANNER_REFUSAL_FALLBACK", "").lower()
        self.add("models", "PLANNER_REFUSAL_FALLBACK=off for red-team runs", fallback == "off" or None,
                 "" if fallback == "off" else "the protocol asks for it during red-team runs (HANDOFF item 7)")
        dry = self.env.get("AGENTWALLET_DRY_RUN", "0").lower() in ("1", "true", "yes")
        self.add("models", "AGENTWALLET_DRY_RUN is off", not dry, "it forces canned replies" if dry else "")

    def redteam(self) -> None:
        from redteam.cases import ATTACK_CLASSES, load_gallery

        protocol = (REPO / "redteam" / "protocol.md").read_text()
        markers = protocol.count("[[fill")
        self.add("redteam", "redteam/protocol.md is filled in", markers == 0, f"{markers} markers (HANDOFF item 9)")
        attacks = [c for c in load_gallery() if c.is_attack]
        per_class = {c: sum(case.case_class == c for case in attacks) for c in ATTACK_CLASSES}
        short = {c: n for c, n in per_class.items() if n < SEEDS_PER_CLASS}
        self.add("redteam", f"at least {SEEDS_MIN} reviewed seeds, {SEEDS_PER_CLASS} per class",
                 len(attacks) >= SEEDS_MIN and not short,
                 f"{len(attacks)} seeds; short: " + ", ".join(f"{c} {n}" for c, n in short.items()) if short
                 else f"{len(attacks)} seeds")
        self.add("redteam", "redteam/mutate.py exists (C3)", (REPO / "redteam" / "mutate.py").exists(),
                 "HANDOFF item 8")

    def ping(self) -> None:
        run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-m", "live"], cwd=REPO / "backend",
                             capture_output=True, text=True, env={**os.environ, **self.env})
        last = (run.stdout + run.stderr).strip().splitlines()[-1:] or ["no output"]
        self.add("models", "one small live call per model role (pytest -m live)", run.returncode == 0, last[0])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/preflight.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--stage", choices=STAGES, action="append", help="only these stages; repeatable")
    parser.add_argument("--env-file", type=Path, default=REPO / ".env")
    parser.add_argument("--ping", action="store_true", help="also make one small paid call per model role")
    args = parser.parse_args(argv)
    stages = args.stage or list(STAGES)
    p = Preflight(read_dotenv(args.env_file), env_file=args.env_file)
    p.common()
    for stage in stages:
        getattr(p, stage)()
    if args.ping:
        p.ping()
    for c in p.checks:
        print(c.line())
    failed = sum(c.status == "FAIL" for c in p.checks)
    print(f"{len(p.checks) - failed} of {len(p.checks)} checks pass or wait on a choice; {failed} fail")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

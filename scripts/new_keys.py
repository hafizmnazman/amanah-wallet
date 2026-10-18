"""Fills every empty signer key in .env with a new one, for the Base Sepolia test wallets (HANDOFF item 5).

    python scripts/new_keys.py                     # creates .env from .env.example when it is missing
    python scripts/new_keys.py --env-file other.env

A key that is already set is kept, so a second run changes nothing. INSTITUTION_HMAC_KEY gets 32 random
bytes as hex when it is empty. Keys go only into the file, which git must ignore, and are never printed:
the script prints each role's address, for the faucet, scripts/fund_keys.py and MetaMask. These are test
wallets for Base Sepolia and Anvil. Never send mainnet funds to them.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

from eth_account import Account

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from preflight import DEPLOY_GAS, GAS  # noqa: E402

# Every key a Base Sepolia run signs or sends with, in the order of docs/PATHS.md, and what each one does.
ROLES = {
    "RELAYER_KEY": "relayer: deploys and sends, no role",
    "PLANNER_KEY": "planner (Claude)",
    "AUDITOR_KEY": "auditor (Qwen)",
    "SENTINEL_KEY": "sentinel (rules)",
    "POSTURE_ORACLE_KEY": "posture oracle (red-team reports)",
    "TRUSTEE1_KEY": "trustee 1",
    "TRUSTEE2_KEY": "trustee 2",
    "TRUSTEE3_KEY": "trustee 3",
    "GUARDIAN_KEY": "guardian (pause)",
    "CONTROL_AUDITOR_KEY": "control auditor (Claude), scenario 11",
    "DONOR_KEY": "donor: scenario 5's deposit",
}
HMAC_VARIABLE = "INSTITUTION_HMAC_KEY"
LINE = re.compile(r"^(?P<name>[A-Z0-9_]+)=(?P<value>.*)$")


def fill(text: str) -> tuple[str, list[str]]:
    """The file with every empty key filled, and the names it filled. Set values and other lines stay as they are."""
    wanted = [*ROLES, HMAC_VARIABLE]
    seen: set[str] = set()
    filled: list[str] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        match = LINE.match(line.strip())
        if not match or match["name"] not in wanted:
            continue
        name = match["name"]
        seen.add(name)
        if match["value"].strip().strip('"').strip("'"):
            continue
        lines[i] = f"{name}={new_value(name)}"
        filled.append(name)
    missing = [name for name in wanted if name not in seen]
    if missing:
        lines += ["", "# Added by scripts/new_keys.py"]
        for name in missing:
            lines.append(f"{name}={new_value(name)}")
            filled.append(name)
    return "\n".join(lines) + "\n", filled


def new_value(name: str) -> str:
    if name == HMAC_VARIABLE:
        return secrets.token_hex(32)
    return "0x" + Account.create().key.hex().removeprefix("0x")


def values(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        match = LINE.match(line.strip())
        if match:
            out[match["name"]] = match["value"].strip().strip('"').strip("'")
    return out


def git_ignores(path: Path) -> bool:
    """True when git ignores the file, or when it lies outside the repository (a test's temporary .env)."""
    try:
        path.resolve().relative_to(REPO)
    except ValueError:
        return True
    return subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=REPO).returncode == 0


def eth_needed(name: str) -> str:
    if name == "RELAYER_KEY":
        return f"{DEPLOY_GAS} for the deploy, then {GAS[name]} (fund this one)"
    return f"{GAS[name]} (fund_keys.py sends it)" if name in GAS else "none, it only signs"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/new_keys.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", type=Path, default=REPO / ".env")
    args = parser.parse_args(argv)
    path: Path = args.env_file
    if not git_ignores(path):
        print(f"{path} is not ignored by git; refusing to write keys into it", file=sys.stderr)
        return 1
    text = path.read_text() if path.exists() else (REPO / ".env.example").read_text()
    text, filled = fill(text)
    path.write_text(text, newline="\n")
    os.chmod(path, 0o600)
    current = values(text)
    print(f"{path}: filled {len(filled)} of {len(ROLES) + 1} keys" + (f" ({', '.join(filled)})" if filled else ""))
    print()
    print(f"{'role':<38} {'variable':<20} {'address':<42}  ETH on Base Sepolia")
    for name, role in ROLES.items():
        print(f"{role:<38} {name:<20} {Account.from_key(current[name]).address:<42}  {eth_needed(name)}")
    print()
    print("Next: send about 0.03 Base Sepolia ETH to the relayer, then run python scripts/fund_keys.py --send.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

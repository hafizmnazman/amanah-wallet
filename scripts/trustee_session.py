"""Decision E-35: open and close the window in which a trustee signs a payout on Base Sepolia in MetaMask.

    python scripts/trustee_session.py raise     # the posture oracle raises the posture to 1
    python scripts/trustee_session.py status    # the posture and the last anchored report
    python scripts/trustee_session.py lower     # two trustees lower it to 0 again

With the posture at 1, the vault rates every payout elevated, so the next routine payout waits for a trustee's
co-signature (plan task D3; scenario 14 in the scripted demo). The raise is the operator's, for the demonstration:
the oracle anchors the sha256 of evidence/sepolia-trustee/demonstration.md, a statement that says so, and not a
red-team report. Lowering takes two trustee signatures, sent by the relayer, as the vault requires. Keys and
RPC_URL come from .env; transactions are recorded in evidence/sepolia-trustee/transactions.csv.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from dev_up import read_dotenv  # noqa: E402

from app.agentwallet.chain import TransactionLog, VaultClient, tagged  # noqa: E402

EVIDENCE = REPO / "evidence" / "sepolia-trustee"
STATEMENT = ("The security posture of the demo vault was raised to 1 by its operator on 20 October 2026, so that the next\n"
             "routine payout waits for a trustee's co-signature, for a trustee to sign one payout in MetaMask on Base Sepolia\n"
             "(decision E-35). It is not a red-team result: no report crossed a threshold. Two trustees lower it afterwards.\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/trustee_session.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("action", choices=("raise", "status", "lower"))
    args = parser.parse_args(argv)

    env = read_dotenv(REPO / ".env")
    deployment = json.loads((REPO / "contracts" / "deployments" / "84532.json").read_text())
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    client = VaultClient(env["RPC_URL"], deployment["vault"], env["RELAYER_KEY"],
                         tx_log=TransactionLog(EVIDENCE / "transactions.csv", "https://base-sepolia.blockscout.com",
                                               network="84532"))
    if client.chain_id != 84532:
        raise SystemExit("RPC_URL is not Base Sepolia")

    if args.action == "raise":
        statement = EVIDENCE / "demonstration.md"
        statement.write_text(STATEMENT)
        report_hash = "0x" + hashlib.sha256(STATEMENT.encode()).hexdigest()
        with tagged(scenario="D3", description="The operator raises the posture for the trustee demonstration",
                    expected="posture 1"):
            tx = client.raise_posture(1, report_hash, key=env["POSTURE_ORACLE_KEY"])
        print(f"posture raise: {tx.status} {tx.tx_hash}; anchored the statement's sha256 {report_hash}")
    elif args.action == "lower":
        with tagged(scenario="D3", description="Two trustees lower the posture after the demonstration",
                    expected="posture 0"):
            tx = client.governance("lowerPosture", (0,), [env["TRUSTEE1_KEY"], env["TRUSTEE2_KEY"]])
        print(f"posture lower: {tx.status} {tx.tx_hash}")
    print(f"posture is {client.posture()}; last anchored report {client.last_report_hash()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

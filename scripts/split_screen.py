"""The video's opening split screen (plan task E5): one attack message, two wallets, on a fresh Anvil.

    python scripts/split_screen.py                       # the demo's chairman message, dry-run planner
    python scripts/split_screen.py --live                # the planner model from .env
    python scripts/split_screen.py --message-file FILE   # another message; {wallet} becomes the attacker's wallet

Left, a typical agent wallet: the same planner model, holding a funded key alone, as red-team arm S1
measures. Whatever payout it proposes, it sends. Right, Amanah: the same message through the API, the
auditor, the sentinel and the vault. Both sides print what happened and the attacker's balance after.
The dry-run planner follows an explicit transfer request on purpose; it is not a model. With --live, the
planner may refuse, and the left side says so: pick a case the live S1 arm fell for
(redteam/results/final/results.jsonl, fooled.planner true) for the recording.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import textwrap
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from eth_account import Account  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.agentwallet import devchain  # noqa: E402
from app.agentwallet.api import create_app  # noqa: E402
from app.agentwallet.books import Books  # noqa: E402
from app.agentwallet.chain import ERC20_ABI, VaultClient  # noqa: E402
from app.agentwallet.config import Settings  # noqa: E402
from app.agentwallet.planner.propose import propose  # noqa: E402
from app.agentwallet.planner.service import PlannerService  # noqa: E402
from app.agentwallet.types import units_to_usdc, usdc_to_units  # noqa: E402
from dev_up import CHAIN_ONLY, read_dotenv  # noqa: E402
from run_demo import CHAIRMAN, OFFICER, UNLISTED  # noqa: E402

WALLET_FUNDS = "5000"  # what the typical wallet holds, as much as the demo's donor deposits
WIDTH = 58


def money(units: int) -> str:
    return as_usdc(units_to_usdc(units))


def as_usdc(amount) -> str:
    return f"{Decimal(str(amount)):,.2f} USDC"


def typical_wallet(chain, message: str, books: Books, usdc) -> dict:
    """The planner alone holds the key: every payout it proposes is sent as a plain USDC transfer."""
    key = chain.keys["planner"]
    account = Account.from_key(key)
    w3 = chain.w3
    w3.eth.wait_for_transaction_receipt(w3.eth.send_transaction(
        {"from": w3.eth.accounts[0], "to": usdc.address,
         "data": usdc.encode_abi("mint", [account.address, usdc_to_units(WALLET_FUNDS)])}))
    proposal = propose(message, books=books)
    lines, txs = [f"planner ({proposal.model}): " + (proposal.refusal or proposal.reply or "proposed a payout")], []
    for intent in proposal.intents:
        lines.append(f"planner: pay {as_usdc(intent.amount_usdc)} to {intent.wallet}")
        tx = usdc.functions.transfer(intent.wallet, usdc_to_units(intent.amount_usdc)).build_transaction(
            {"from": account.address, "nonce": w3.eth.get_transaction_count(account.address), "chainId": 31337})
        receipt = w3.eth.wait_for_transaction_receipt(
            w3.eth.send_raw_transaction(account.sign_transaction(tx).raw_transaction))
        txs.append("0x" + bytes(receipt["transactionHash"]).hex())
        lines.append(f"wallet: signed and sent it, tx {txs[-1][:18]}...")
    if not proposal.intents:
        lines.append("wallet: nothing to send")
    return {"lines": lines, "txs": txs}


def amanah(message: str, books: Books, client: VaultClient) -> dict:
    """The same message through the officer's API: plan, confirm, and the checkers and the vault decide."""
    api = TestClient(create_app(PlannerService(books=books, settings=Settings.from_env())))

    def post(path: str, body: dict) -> dict:
        r = api.post(path, json=body, headers=OFFICER)
        r.raise_for_status()
        return r.json()

    reply = post("/api/agent/chat", {"session_id": "split-screen", "message": message})
    card = reply.get("plan_card")
    if not card:
        return {"lines": [f"planner: {reply['reply'][:160]}", "nothing to confirm"], "txs": []}
    lines = [f"planner: pay {as_usdc(item['amount_usdc'])} to {item['wallet']}" for item in card["items"]]
    lines.append(f"tier preview: {card['tier_preview']}")
    before = len(client.tx_log.rows())
    results = post("/api/agent/confirm", {"session_id": "split-screen", "batch_id": card["batch_id"]})["results"]
    txs = []
    for r in results:
        for name, label in (("auditor", "auditor (Qwen)"), ("sentinel", "sentinel")):
            v = r["verdicts"][name]
            lines.append(f"{label}: {v['verdict']}" + (f", {', '.join(v['reasons'][:2])}" if v["verdict"] != "APPROVE" else ""))
        lines.append(f"result: {r['status']}" + (f", tx {r['tx_hash'][:18]}..." if r.get("tx_hash") else ""))
        if r.get("tx_hash"):
            txs.append(r["tx_hash"])
    anchors = [row["tx_hash"] for row in client.tx_log.rows()[before:] if row["function"] == "anchorDecision"]
    for tx in anchors:
        lines.append(f"refusal anchored on-chain, tx {tx[:18]}...")
    return {"lines": lines, "txs": txs + anchors}


def column(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        out += textwrap.wrap(line, WIDTH) or [""]
    return out


def show(message: str, left: dict, right: dict) -> None:
    head_l = ["A TYPICAL AGENT WALLET", "one model, the planner alone, holds the key (S1)"]
    head_r = ["AMANAH", "planner, Qwen auditor, sentinel, and the vault"]
    print("\nThe message, to both wallets:")
    for line in textwrap.wrap(message, 2 * WIDTH + 3):
        print(f"  {line}")
    print()
    rows_l = column(head_l) + ["=" * WIDTH] + column(left["lines"]) + [""] + column([left["balance"]])
    rows_r = column(head_r) + ["=" * WIDTH] + column(right["lines"]) + [""] + column([right["balance"]])
    for i in range(max(len(rows_l), len(rows_r))):
        a = rows_l[i] if i < len(rows_l) else ""
        b = rows_r[i] if i < len(rows_r) else ""
        print(f"{a:<{WIDTH}} | {b}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/split_screen.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--live", action="store_true", help="use the planner model from .env instead of dry-run")
    parser.add_argument("--message-file", type=Path, help="the attack message; {wallet} becomes the attacker's wallet")
    parser.add_argument("--json", type=Path, help="also write both sides to this file")
    args = parser.parse_args(argv)
    template = args.message_file.read_text().strip() if args.message_file else CHAIRMAN
    message = template.replace("{wallet}", UNLISTED)

    if args.live:
        os.environ.update({k: v for k, v in read_dotenv(REPO / ".env").items() if k not in CHAIN_ONLY})
    else:
        os.environ["AGENTWALLET_DRY_RUN"] = "1"
    state = Path(tempfile.mkdtemp(prefix="amanah-split-"))
    with devchain.anvil_fixture() as chain:
        os.environ.update({**chain.env(), "AGENTWALLET_CHECKERS": "inprocess", "AGENTWALLET_STATE_DIR": str(state),
                           "EVIDENCE_DIR": str(state / "evidence"), "EXPLORER_URL": "http://anvil.local",
                           "AUDITOR_ANCHOR": "1", "SENTINEL_ANCHOR": "1", "AGENTWALLET_QUEUE_RETRY": "0",
                           "AGENTWALLET_SCHEDULE": "0"})
        books = Books.load()
        os.environ.setdefault("AGENTWALLET_TODAY", books.as_of.isoformat())
        client = VaultClient.from_env()
        usdc = chain.w3.eth.contract(address=chain.w3.to_checksum_address(chain.usdc), abi=ERC20_ABI)

        left = typical_wallet(chain, message, books, usdc)
        left["balance"] = f"attacker's balance: {money(client.usdc_balance(UNLISTED))}"
        stolen = client.usdc_balance(UNLISTED)
        right = amanah(message, books, client)
        right["balance"] = f"attacker's balance from Amanah: {money(client.usdc_balance(UNLISTED) - stolen)}"
        show(message, left, right)
        if args.json:
            args.json.write_text(json.dumps({"message": message, "typical_wallet": left, "amanah": right}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

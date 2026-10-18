"""Read-only access to the operating books.

In this repository the books are redteam/data/books.json, written by lane C (format: shared/books.md).
When the agent wallet moves into Amanah's backend, this adapter is the one file that changes: the same
methods over Amanah's operating books models.
"""

from __future__ import annotations

import json
from datetime import date
from functools import cached_property
from pathlib import Path
from typing import Any

from eth_utils import to_checksum_address

from .config import REPO_ROOT, env
from .evidence import canonical, sha256_hex

ANCHOR_TABLES = {"programmes": "code", "beneficiaries": "beneficiary_ref", "payouts": "payout_ref",
                 "batches": "batch_ref", "requests": "request_ref", "notes": "note_ref", "donations": "receipt_ref"}


class IntegrityError(Exception):
    """A books record no longer matches its anchored hash."""


class Books:
    def __init__(self, data: dict, anchor: dict | None = None, path: Path | None = None):
        self.data = data
        self.anchor = anchor
        self.path = path

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Books":
        path = Path(path or env("BOOKS_PATH") or REPO_ROOT / "redteam" / "data" / "books.json")
        anchor_path = path.with_name("books_anchor.json")
        anchor = json.loads(anchor_path.read_text()) if anchor_path.exists() else None
        return cls(json.loads(path.read_text()), anchor, path)

    @property
    def as_of(self) -> date:
        return date.fromisoformat(self.data["generated"]["as_of"])

    # Programmes and funds

    def programmes(self) -> list[dict]:
        return self.data["programmes"]

    def programme(self, code: str) -> dict:
        for p in self.data["programmes"]:
            if p["code"] == code:
                return p
        raise KeyError(f"no programme {code}")

    def programme_by_id(self, programme_id: str) -> dict:
        for p in self.data["programmes"]:
            if p["programme_id"].lower() == programme_id.lower():
                return p
        raise KeyError(f"no programme with id {programme_id}")

    def fund_name(self, fund_code: str) -> str:
        return next(f["name"] for f in self.data["funds"] if f["fund_code"] == fund_code)

    # Beneficiaries

    @cached_property
    def _beneficiaries(self) -> dict[str, dict]:
        return {b["beneficiary_ref"]: b for b in self.data["beneficiaries"]}

    def beneficiary(self, ref: str) -> dict:
        return self._beneficiaries[ref]

    def beneficiaries(self, programme_code: str | None = None) -> list[dict]:
        return [b for b in self.data["beneficiaries"] if programme_code in (None, b["programme_code"])]

    def beneficiary_by_wallet(self, programme_code: str, wallet: str) -> dict | None:
        wallet = to_checksum_address(wallet)
        for b in self.beneficiaries(programme_code):
            if b["wallet"] == wallet:
                return b
        return None

    def beneficiary_by_household(self, household_ref: str) -> dict | None:
        return next((b for b in self.data["beneficiaries"] if b["household_ref"] == household_ref), None)

    def payouts_for(self, beneficiary_ref: str) -> list[dict]:
        """Past payouts, newest first: the books' history plus payouts executed since, from the ledger."""
        rows = [p for p in self.data["payouts"] if p["beneficiary_ref"] == beneficiary_ref]
        rows += [p for p in self.ledger() if p["beneficiary_ref"] == beneficiary_ref]
        return sorted(rows, key=lambda p: p["date"], reverse=True)

    # The runtime ledger: payouts this backend executed, so the books update themselves (plan section 3)

    @property
    def ledger_path(self) -> Path:
        state = Path(env("AGENTWALLET_STATE_DIR") or REPO_ROOT / "backend" / "var")
        return state / "ledger.jsonl"

    def ledger(self) -> list[dict]:
        if not self.ledger_path.exists():
            return []
        return [json.loads(line) for line in self.ledger_path.read_text().splitlines() if line.strip()]

    def record_payout(self, *, beneficiary_ref: str, programme_code: str, amount_usdc, tx_hash: str,
                      on: date | None = None) -> dict:
        """Appends an executed payout. Its anchor is the PayoutExecuted event at `tx_hash`, not books_anchor.json."""
        row = {"payout_ref": f"CHAIN-{tx_hash[:18]}", "beneficiary_ref": beneficiary_ref,
               "programme_code": programme_code, "amount_usdc": float(amount_usdc),
               "date": (on or date.today()).isoformat(), "batch_ref": None, "channel": "chain", "tx_hash": tx_hash}
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        return row

    def notes_for(self, beneficiary_ref: str) -> list[dict]:
        """Free text. The planner may read it; the auditor and the sentinel never get it."""
        return [n for n in self.data["notes"] if n["beneficiary_ref"] == beneficiary_ref]

    # Batches, requests, donations

    def batches(self, *, period: str | None = None, location: str | None = None) -> list[dict]:
        return [b for b in self.data["batches"]
                if period in (None, b["period"]) and (location is None or b["location"].lower() == location.lower())]

    def batch(self, batch_ref: str) -> dict:
        return next(b for b in self.data["batches"] if b["batch_ref"] == batch_ref)

    def batch_item_for(self, beneficiary_ref: str) -> dict | None:
        """The beneficiary's line in a batch of the books, with the batch's ref, or None."""
        for b in self.data["batches"]:
            for item in b["items"]:
                if item["beneficiary_ref"] == beneficiary_ref:
                    return {**item, "batch_ref": b["batch_ref"]}
        return None

    def requests(self) -> list[dict]:
        return self.data["requests"]

    def request(self, request_ref: str) -> dict:
        return next(r for r in self.data["requests"] if r["request_ref"] == request_ref)

    def request_for(self, beneficiary_ref: str) -> dict | None:
        return next((r for r in self.data["requests"] if r["beneficiary_ref"] == beneficiary_ref), None)

    def donations(self) -> list[dict]:
        return self.data["donations"]

    def scenario_ref(self, name: str) -> str:
        return self.data["scenario_refs"][name]

    # Integrity, the stand-in for Amanah's integrity check

    def record(self, table: str, ref: str) -> dict:
        key = ANCHOR_TABLES[table]
        return next(r for r in self.data[table] if r[key] == ref)

    def verify_record(self, table: str, ref: str) -> str:
        """Returns the record's sha256 if it matches books_anchor.json; raises IntegrityError otherwise."""
        digest = sha256_hex(canonical(self.record(table, ref)))
        if self.anchor is None:
            raise IntegrityError("no books anchor to check against")
        anchored = self.anchor["records"].get(f"{table}/{ref}")
        if anchored != digest:
            raise IntegrityError(f"{table}/{ref} does not match its anchored hash")
        return digest

    def summary_for_planner(self) -> dict[str, Any]:
        """What the planner sees of the books: programmes, batches and requests, never personal data."""
        return {
            "programmes": [{k: p[k] for k in ("code", "fund_code", "name", "cadence", "location", "cap_usdc",
                                              "hard_ceiling_usdc", "daily_budget_usdc", "per_beneficiary_cap_usdc")}
                           for p in self.programmes()],
            "funds": self.data["funds"],
            "batches": [{"batch_ref": b["batch_ref"], "programme_code": b["programme_code"], "period": b["period"],
                         "label": b["label"], "location": b["location"], "households": len(b["items"]),
                         "total_usdc": sum(i["amount_usdc"] for i in b["items"])} for b in self.batches()],
            "requests": [{k: r[k] for k in ("request_ref", "programme_code", "beneficiary_ref", "kind", "amount_usdc",
                                             "reason", "status")} for r in self.requests()],
            "households": [{k: b[k] for k in ("household_ref", "beneficiary_ref", "programme_code", "status")}
                           for b in self.data["beneficiaries"]],
        }

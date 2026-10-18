"""The evidence trail (plan section 3.5): a hash-chained action log and the transactions table.

Every record in evidence/action-log.jsonl carries the sha256 of the record before it, so an edit
anywhere breaks every later hash. At the end of a demo run the head hash is anchored on-chain with
anchorReport. evidence/transactions.csv lists every transaction with its scenario, status and block,
and is what GET /api/proof serves. The API, the auditor and the sentinel may run as separate processes
that share one evidence folder, so every append holds an exclusive lock on the file it writes.
"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

try:
    import fcntl
except ImportError:  # Windows: appends are kept in turn within one process only
    fcntl = None

GENESIS = "0" * 64
MALAYSIA = ZoneInfo("Asia/Kuala_Lumpur")
TRANSACTION_COLUMNS = ["scenario", "description", "expected", "tx_hash", "status", "block", "explorer_url",
                       "function", "error", "network", "ts"]


def canonical(obj: Any) -> str:
    """Sorted keys and no whitespace. The same form as redteam/datagen.py's books anchor."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def now_iso() -> str:
    return datetime.now(MALAYSIA).isoformat(timespec="seconds")


@contextlib.contextmanager
def _appending(path: Path, **open_args: Any):
    """Opens `path` for appending under an exclusive lock, released when the file closes. Without it, two
    processes could read the same last record and write two records with the same prev_hash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", **open_args) as fh:
        if fcntl is not None:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield fh
        fh.flush()


class ActionLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()

    def _last(self) -> dict | None:
        if not self.path.exists():
            return None
        last = None
        with self.path.open() as fh:
            for line in fh:
                if line.strip():
                    last = json.loads(line)
        return last

    def head(self) -> str:
        last = self._last()
        return last["hash"] if last else GENESIS

    def append(self, actor: str, lineage: str, event: str, **fields: Any) -> dict:
        """Writes one record. Optional fields from section 3.5: proposal_id, verdict, input_hash, model,
        tx_hash, status. None values are left out."""
        with self._lock, _appending(self.path) as fh:
            last = self._last()
            record = {"seq": (last["seq"] + 1) if last else 1, "ts": now_iso(), "actor": actor, "lineage": lineage,
                      "event": event, **{k: v for k, v in fields.items() if v is not None},
                      "prev_hash": last["hash"] if last else GENESIS}
            record["hash"] = sha256_hex(canonical(record))
            fh.write(canonical(record) + "\n")
            return record

    @staticmethod
    def verify(path: Path) -> tuple[bool, str]:
        """Recomputes the chain. Returns (True, head) or (False, the first problem found)."""
        prev = GENESIS
        expected_seq = 1
        with Path(path).open() as fh:
            for n, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                stated = record.pop("hash")
                if record.get("prev_hash") != prev:
                    return False, f"line {n}: prev_hash does not match the record before"
                if record.get("seq") != expected_seq:
                    return False, f"line {n}: seq {record.get('seq')} where {expected_seq} was expected"
                if sha256_hex(canonical(record)) != stated:
                    return False, f"line {n}: hash does not match the record"
                prev, expected_seq = stated, expected_seq + 1
        return True, prev


class TransactionLog:
    def __init__(self, path: Path, explorer_url: str = "https://sepolia.basescan.org", network: str = ""):
        self.path = Path(path)
        self.explorer_url = explorer_url.rstrip("/")
        self.network = network
        self._lock = threading.Lock()

    def append(self, tx_hash: str, status: str, block: int | None, *, scenario: str = "", description: str = "",
               expected: str = "", function: str = "", error: str = "") -> dict:
        row = {"scenario": scenario, "description": description, "expected": expected, "tx_hash": tx_hash,
               "status": status, "block": "" if block is None else block,
               "explorer_url": f"{self.explorer_url}/tx/{tx_hash}", "function": function, "error": error,
               "network": self.network, "ts": now_iso()}
        with self._lock, _appending(self.path, newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=TRANSACTION_COLUMNS)
            if fh.seek(0, os.SEEK_END) == 0:
                writer.writeheader()
            writer.writerow(row)
        return row

    def rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(newline="") as fh:
            return list(csv.DictReader(fh))

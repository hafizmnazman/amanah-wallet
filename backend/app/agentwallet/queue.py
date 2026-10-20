"""The fail-closed queue and trustee alerts (plan task B9), and the chain retry queue of plan task B3.

When a checker is unavailable or the chain cannot be reached, a payout is queued with the reason and what
is missing, and a trustee alert is written. Amanah's durable write queue is not in this repository, so
this SQLite store stands in for it; it survives restarts. A background task retries every
QUEUE_RETRY_SECONDS (default 60). Elevated payouts waiting for a trustee live here too.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from .evidence import now_iso

SCHEMA = """
create table if not exists queued (
    proposal_id text primary key, item text not null, reason text not null, missing text not null,
    queued_at text not null, attempts integer not null default 0, last_error text, status text not null
);
create table if not exists pending (
    proposal_id text primary key, item text not null, created_at text not null, status text not null,
    tx_hash text
);
create table if not exists results (
    proposal_id text primary key, result text not null, updated_at text not null
);
create table if not exists alerts (
    id integer primary key autoincrement, created_at text not null, kind text not null, proposal_id text,
    message text not null, read integer not null default 0
);
"""


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._db() as db:
            db.executescript(SCHEMA)

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    # Fail-closed queue

    def enqueue(self, proposal_id: str, item: dict, reason: str, missing: str) -> None:
        with self._lock, self._db() as db:
            db.execute("insert or replace into queued values (?, ?, ?, ?, ?, 0, null, 'queued')",
                       (proposal_id, json.dumps(item, default=str), reason, missing, now_iso()))
        self.alert("queued", proposal_id, f"Payout queued, {missing} missing: {reason}")

    def queued(self, status: str = "queued") -> list[dict]:
        with self._db() as db:
            rows = db.execute("select * from queued where status = ? order by queued_at", (status,)).fetchall()
        return [{**dict(r), "item": json.loads(r["item"])} for r in rows]

    def retried(self, proposal_id: str, *, done: bool, error: str | None = None, missing: str | None = None) -> None:
        with self._lock, self._db() as db:
            db.execute("update queued set attempts = attempts + 1, last_error = ?, status = ?, "
                       "missing = coalesce(?, missing) where proposal_id = ?",
                       (error, "done" if done else "queued", missing, proposal_id))
        if done:
            self.alert("drained", proposal_id, "Queued payout went through after a retry.")

    def refused(self, proposal_id: str, payout: str, reason: str) -> None:
        """A retry that a checker or the vault turned down: the payout leaves the queue unpaid, and the alert
        says so. `payout` names it, for example "150 USDC to ZKT-H01"."""
        with self._lock, self._db() as db:
            db.execute("update queued set attempts = attempts + 1, last_error = ?, status = 'refused' "
                       "where proposal_id = ?", (reason, proposal_id))
        self.alert("refused", proposal_id,
                   f"Queued payout of {payout} was refused on retry: {reason}. Nothing was paid.")

    # Elevated payouts waiting for a trustee

    def add_pending(self, proposal_id: str, item: dict) -> None:
        with self._lock, self._db() as db:
            db.execute("insert or replace into pending values (?, ?, ?, 'pending', null)",
                       (proposal_id, json.dumps(item, default=str), now_iso()))
        self.alert("trustee_needed", proposal_id, "An elevated payout needs a trustee's signature.")

    def pending(self, status: str = "pending") -> list[dict]:
        with self._db() as db:
            rows = db.execute("select * from pending where status = ? order by created_at", (status,)).fetchall()
        return [{**dict(r), "item": json.loads(r["item"])} for r in rows]

    def get_pending(self, proposal_id: str) -> dict | None:
        with self._db() as db:
            row = db.execute("select * from pending where proposal_id = ?", (proposal_id,)).fetchone()
        return {**dict(row), "item": json.loads(row["item"])} if row else None

    def update_pending(self, proposal_id: str, item: dict, status: str, tx_hash: str | None = None) -> None:
        with self._lock, self._db() as db:
            db.execute("update pending set item = ?, status = ?, tx_hash = ? where proposal_id = ?",
                       (json.dumps(item, default=str), status, tx_hash, proposal_id))

    # Latest outcome per payout, for the status route

    def record_result(self, result: dict) -> None:
        with self._lock, self._db() as db:
            db.execute("insert or replace into results values (?, ?, ?)",
                       (result["proposal_id"], json.dumps(result, default=str), now_iso()))

    def result(self, proposal_id: str) -> dict | None:
        with self._db() as db:
            row = db.execute("select result from results where proposal_id = ?", (proposal_id,)).fetchone()
        return json.loads(row["result"]) if row else None

    # Alerts

    def alert(self, kind: str, proposal_id: str | None, message: str) -> None:
        with self._lock, self._db() as db:
            db.execute("insert into alerts (created_at, kind, proposal_id, message) values (?, ?, ?, ?)",
                       (now_iso(), kind, proposal_id, message))

    def alerts(self, unread_only: bool = False) -> list[dict]:
        query = "select * from alerts" + (" where read = 0" if unread_only else "") + " order by id"
        with self._db() as db:
            return [dict(r) for r in db.execute(query).fetchall()]

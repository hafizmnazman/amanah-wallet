"""Recurring payouts (plan task B11): a scheduled batch is drafted as a plan card for the officer.

The job never confirms anything. The officer confirms the draft as any other plan, with
POST /api/agent/confirm and the draft's session id.

    python -m app.agentwallet.recurring [--today 2026-10-05]

A programme whose `schedule` in the books is `{"kind": "monthly", "day_of_month": N}` is due on day N of
each month, and on any later day of that month. The batch drafted is the programme's batch in the books
for that month (`period` YYYY-MM). Drafting needs no model call: the books name the batch.
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from .config import env, today as current_day

SESSION_PREFIX = "scheduled-"


def due(books, today: date | None = None) -> list[dict]:
    """The batches whose programme's schedule has come round this month."""
    today = today or current_day()
    period = today.strftime("%Y-%m")
    out = []
    for p in books.programmes():
        schedule = p.get("schedule") or {}
        if schedule.get("kind") != "monthly" or today.day < int(schedule["day_of_month"]):
            continue
        for b in books.batches():
            if b["programme_code"] == p["code"] and b["period"] == period:
                out.append({"programme_code": p["code"], "batch_ref": b["batch_ref"], "period": period})
    return out


def session_id(batch_ref: str) -> str:
    return SESSION_PREFIX + batch_ref


def draft_due(service, *, today: date | None = None, officer: str | None = None) -> list[dict]:
    """Drafts each due batch that has no open draft for the officer, and returns the new drafts."""
    officer = officer or env("SCHEDULE_OFFICER", "officer-1")
    drafted = []
    for item in due(service.books, today):
        sid = session_id(item["batch_ref"])
        card = service.draft(f"{officer}/{sid}", item["batch_ref"])
        if card is not None:
            drafted.append({**item, "session_id": sid, "officer": officer, "plan_card": card.model_dump(mode="json")})
    return drafted


def main(argv: list[str] | None = None) -> int:
    from .planner.service import PlannerService

    parser = argparse.ArgumentParser(prog="python -m app.agentwallet.recurring", description=__doc__.split("\n\n")[0])
    parser.add_argument("--today", type=date.fromisoformat)
    parser.add_argument("--officer")
    args = parser.parse_args(argv)
    drafted = draft_due(PlannerService(), today=args.today, officer=args.officer)
    print(json.dumps(drafted, indent=2, default=str) if drafted else "nothing is due")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

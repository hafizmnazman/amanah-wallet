"""The sentinel as its own service (plan task B4): POST /verdict on port 8102.

    SENTINEL_KEY=0x... uvicorn app.agentwallet.sentinel.service:app --port 8102

Features come from the books, read-only, and the batch the planner sends, so the sentinel works them out
itself rather than trusting the caller. With RPC_URL and VAULT_ADDRESS set, it also reads the household's
past payouts and today's spend from the vault (judge.py); no key is needed for that. A request may carry
`features`, as plan section 3.4 allows, but they are ignored: a caller's numbers never decide a verdict
(decision B-20). It signs only on APPROVE, with SENTINEL_KEY.
"""

from __future__ import annotations

import contextlib
import threading
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ..books import Books
from ..config import Settings, env
from ..evidence import ActionLog
from ..signer_service import batch_from_request, intent_from_request, respond
from ..types import VerdictRequest, VerdictResponse, units_to_usdc
from . import judge


class SentinelRequest(VerdictRequest):
    """Section 3.4, plus the rest of the batch and today's spend, both as numbers."""

    batch: list[dict[str, str]] | None = None
    spent_today: str | None = None  # base units, from the vault's spentToday


class Health(BaseModel):
    status: str
    service: str
    # The vault's payout history: "no chain", "reading", "ready" or "failed: <error>"; while reading, the
    # block it has reached and the head it reads to
    history: str = "no chain"
    history_block: int | None = None
    history_head: int | None = None


def warm(state: dict) -> None:
    """Reads the vault's payout history once at start, so that no verdict waits for it. On a provider that
    serves logs ten blocks at a time, a day of Base Sepolia blocks takes minutes."""
    try:
        chain = judge.chain_from_env()
        if chain is None:
            state["history"] = "no chain"
            return
        state["history"] = "reading"
        chain.payouts()
        state["history"] = "ready"
    except Exception as exc:  # a verdict still tries again, and fails closed if it cannot read either
        state["history"] = f"failed: {type(exc).__name__}"


def create_app(books: Books | None = None, log: ActionLog | None = None) -> FastAPI:
    state = {"books": books, "log": log, "history": "no chain"}

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        if env("SENTINEL_WARM", "1") != "0":
            threading.Thread(target=warm, args=(state,), daemon=True).start()
        yield

    app = FastAPI(title="Amanah sentinel", version="1", lifespan=lifespan)

    def get_books() -> Books:
        if state["books"] is None:
            state["books"] = Books.load()
        return state["books"]

    def get_log() -> ActionLog:
        if state["log"] is None:
            state["log"] = ActionLog(Settings.from_env().evidence_dir / "action-log.jsonl")
        return state["log"]

    @app.get("/health")
    def health() -> Health:
        reading = None
        with contextlib.suppress(Exception):
            chain = judge.chain_from_env()
            reading = chain.reading if chain is not None else None
        return Health(status="ok", service="sentinel", history=state["history"],
                      history_block=reading[0] if reading else None, history_head=reading[1] if reading else None)

    @app.post("/verdict")
    def verdict(req: SentinelRequest) -> VerdictResponse:
        books = get_books()
        try:
            payout, intent = intent_from_request(req, books)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        spent = units_to_usdc(int(req.spent_today)) if req.spent_today else Decimal(0)
        verdict = judge.judge(intent, books=books, batch=batch_from_request(req.batch, books), spent_today_usdc=spent)
        return respond("sentinel", "SENTINEL_KEY", verdict, payout, get_log(), tags=req.tags)

    return app


app = create_app()

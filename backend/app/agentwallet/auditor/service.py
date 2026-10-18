"""The auditor as its own service (plan task B5): POST /verdict on port 8101.

    AUDITOR_KEY=0x... uvicorn app.agentwallet.auditor.service:app --port 8101

It receives only the payout and the proposal id, never the chat. It builds its own case file from the
books, read-only, and signs only on APPROVE, with AUDITOR_KEY. A refusal is anchored on-chain with the
same key when RPC_URL and VAULT_ADDRESS are set, so trustees can cite it in an override.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from ..books import Books
from ..config import LINEAGE_QWEN, Settings
from ..evidence import ActionLog
from ..signer_service import intent_from_request, respond
from ..types import VerdictRequest, VerdictResponse
from .judge import audit


def create_app(books: Books | None = None, log: ActionLog | None = None) -> FastAPI:
    app = FastAPI(title="Amanah auditor", version="1")
    state = {"books": books, "log": log}

    def get_books() -> Books:
        if state["books"] is None:
            state["books"] = Books.load()
        return state["books"]

    def get_log() -> ActionLog:
        if state["log"] is None:
            state["log"] = ActionLog(Settings.from_env().evidence_dir / "action-log.jsonl")
        return state["log"]

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "auditor"}

    @app.post("/verdict")
    def verdict(req: VerdictRequest) -> VerdictResponse:
        books = get_books()
        try:
            payout, intent = intent_from_request(req, books)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return respond("auditor", "AUDITOR_KEY", audit(intent, books=books, lineage=LINEAGE_QWEN), payout, get_log())

    return app


app = create_app()

"""The HTTP API of plan section 3.3 (task B8), and the fail-closed queue's retry loop (task B9).

    uvicorn app.main:app --port 8000

Every route checks a role (`roles.py`). Errors are FastAPI's {"detail": "..."}, which the frontend shows.
Four routes are additions to section 3.3, listed in docs/api.md: GET /api/health, GET /api/alerts,
GET /api/agent/payouts/{proposal_id} (the status poll lane D asked for) and GET /api/agent/scheduled. Session ids are scoped to the
caller, so one user cannot confirm another user's plan by guessing its session id.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import logging
import secrets
from typing import Callable

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import posture
from .config import LINEAGE_CLAUDE, dry_run_forced, env, env_int
from .evidence import TransactionLog
from .planner.service import PlannerService
from .reader import read_document
from .roles import FINANCE_OFFICER, GUARDIAN, TRUSTEE, Identity, require
from .types import (ChatRequest, ChatResponse, ConfirmRequest, ConfirmResponse, CorrectRequest, CorrectResponse,
                    DocumentResponse, PayoutResult, PendingResponse, PostureResponse, ProofResponse, ProofRow,
                    QueueResponse, TrusteeSignRequest, TrusteeSignResponse)

LOG = logging.getLogger("amanah.api")
MAX_DOCUMENT_BYTES = 1_000_000
DEV_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"

officer = require(FINANCE_OFFICER)
trustee = require(TRUSTEE)
anyone = require()


def _detail(exc: Exception) -> str:
    return str(exc.args[0]) if exc.args else str(exc)


def _scoped(who: Identity, session_id: str) -> str:
    return f"{who.user}/{session_id}"


async def schedule_loop(get_service: Callable[[], PlannerService], seconds: int) -> None:
    """Plan task B11: drafts the books' scheduled batches for the officer, once at start and then every
    `seconds`. Nothing is confirmed here."""
    from . import recurring

    while True:
        try:
            drafted = await asyncio.to_thread(recurring.draft_due, get_service())
            for d in drafted:
                LOG.info("scheduled batch %s drafted for %s", d["batch_ref"], d["officer"])
        except Exception:  # a broken pass must not stop later ones
            LOG.exception("scheduled drafting failed")
        await asyncio.sleep(seconds)


async def retry_loop(get_service: Callable[[], PlannerService], seconds: int) -> None:
    """One pass over the fail-closed queue every `seconds`. A failed pass is logged and the loop goes on."""
    while True:
        await asyncio.sleep(seconds)
        try:
            drained = await asyncio.to_thread(get_service().retry_queue)
            if drained:
                LOG.info("queue retry: %d payouts went through", drained)
        except Exception:  # a broken pass must not stop later ones
            LOG.exception("queue retry failed")


def create_app(service: PlannerService | None = None) -> FastAPI:
    """The service is built on first use, so importing the app opens no chain connection."""
    state: dict[str, PlannerService | None] = {"service": service}

    def svc() -> PlannerService:
        if state["service"] is None:
            state["service"] = PlannerService()
        return state["service"]

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        tasks = []
        if env("AGENTWALLET_QUEUE_RETRY", "1") != "0":
            tasks.append(asyncio.create_task(retry_loop(svc, env_int("QUEUE_RETRY_SECONDS", 60))))
        if env("AGENTWALLET_SCHEDULE", "1") != "0":
            tasks.append(asyncio.create_task(schedule_loop(svc, env_int("SCHEDULE_SECONDS", 3600))))
        yield
        for task in tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="Amanah agent wallet", version="1", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=env("CORS_ORIGINS", DEV_ORIGINS).split(","),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Amanah-Role", "X-Amanah-User"])

    @app.get("/api/health")
    def health() -> dict:
        s = svc()
        return {"status": "ok", "chain": s.chain is not None, "dry_run": dry_run_forced(),
                "chain_id": s.settings.chain_id, "vault": s.settings.vault_address}

    # Finance officer

    @app.post("/api/agent/chat")
    def chat(req: ChatRequest, who: Identity = Depends(officer)) -> ChatResponse:
        # req.programme_code (the fund selector) is accepted but not used yet: the planner still asks which
        # batch is meant, which is a beat in the scripted demo.
        return svc().chat(_scoped(who, req.session_id), req.message, req.document_ids)

    @app.post("/api/agent/correct")
    def correct(req: CorrectRequest, who: Identity = Depends(officer)) -> CorrectResponse:
        try:
            return svc().correct(_scoped(who, req.session_id), req.batch_id, req.instruction)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=_detail(exc)) from exc

    @app.post("/api/agent/confirm")
    def confirm(req: ConfirmRequest, who: Identity = Depends(officer)) -> ConfirmResponse:
        try:
            return svc().confirm(_scoped(who, req.session_id), req.batch_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=_detail(exc)) from exc

    @app.post("/api/documents")
    def documents(file: UploadFile = File(...), who: Identity = Depends(officer)) -> DocumentResponse:
        raw = file.file.read(MAX_DOCUMENT_BYTES + 1)
        if len(raw) > MAX_DOCUMENT_BYTES:
            raise HTTPException(status_code=413, detail="Documents over 1 MB are not read.")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=415, detail="Only plain-text documents are read in this build.") from exc
        result = read_document(text)
        document_id = "DOC-" + secrets.token_hex(8)
        svc().record_document(document_id, {**result.fields.model_dump(mode="json"),
                                            "injection_flag": result.injection_flag})
        svc().log.append("reader", LINEAGE_CLAUDE, "document_read", model=result.model,
                         input_hash="0x" + hashlib.sha256(raw).hexdigest(),
                         status=("injection_flag: " + ", ".join(result.signals)) if result.injection_flag else "clean")
        return DocumentResponse(document_id=document_id, fields=result.fields, injection_flag=result.injection_flag)

    @app.get("/api/agent/scheduled")
    def scheduled(who: Identity = Depends(officer)) -> dict:
        """Plan task B11: the caller's drafted scheduled batches, waiting for confirmation."""
        return {"items": svc().open_drafts(f"{who.user}/")}

    @app.get("/api/agent/payouts/{proposal_id}")
    def payout(proposal_id: str, who: Identity = Depends(require(FINANCE_OFFICER, TRUSTEE))) -> PayoutResult:
        try:
            return svc().payout_status(proposal_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=_detail(exc)) from exc

    # Trustees

    @app.get("/api/agent/pending")
    def pending(who: Identity = Depends(trustee)) -> PendingResponse:
        return PendingResponse(items=svc().pending())

    @app.post("/api/agent/trustee-sign")
    def trustee_sign(req: TrusteeSignRequest, who: Identity = Depends(trustee)) -> TrusteeSignResponse:
        try:
            return svc().trustee_sign(req.proposal_id, req.signature)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=_detail(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=_detail(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"The signature cannot be read: {_detail(exc)}") from exc

    @app.get("/api/queue")
    def queue(who: Identity = Depends(trustee)) -> QueueResponse:
        return QueueResponse(items=svc().queue())

    @app.get("/api/alerts")
    def alerts(who: Identity = Depends(require(TRUSTEE, GUARDIAN))) -> dict:
        return {"items": svc().store.alerts()}

    # Anyone signed in

    @app.get("/api/proof")
    def proof(who: Identity = Depends(anyone)) -> ProofResponse:
        s = svc()
        rows = TransactionLog(s.settings.evidence_dir / "transactions.csv", s.settings.explorer_url).rows()
        return ProofResponse(rows=[ProofRow(scenario=r["scenario"], description=r["description"],
                                            expected=r["expected"], tx_hash=r["tx_hash"], status=r["status"],
                                            block=int(r["block"]) if r.get("block") else None,
                                            explorer_url=r["explorer_url"]) for r in rows])

    @app.get("/api/posture")
    def posture_level(who: Identity = Depends(anyone)) -> PostureResponse:
        try:
            return posture.status(svc().chain)
        except Exception as exc:  # web3 raises transport errors of several types
            raise HTTPException(status_code=503, detail=f"The vault cannot be read: {exc}") from exc

    return app

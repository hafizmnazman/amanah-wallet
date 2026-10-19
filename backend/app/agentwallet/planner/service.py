"""The planner service behind the API: the graph, the submission rules, trustee signing and queue retries."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .. import checkers, eip712, reporter
from ..books import Books
from ..chain import ChainError, ChainUnavailable, VaultClient
from ..config import Settings, env, planner_lineage
from ..evidence import ActionLog
from ..queue import Store
from ..types import (ChatResponse, Clarification, ConfirmResponse, CorrectResponse, Intent, PayoutResult,
                     PendingPayout, PlanCard, Payout, QueuedPayout, TrusteeSignResponse, Verdict, Verdicts)
from . import graph as planner_graph
from . import propose


@dataclass
class PlannerService:
    books: Books = field(default_factory=Books.load)
    settings: Settings = field(default_factory=Settings.from_env)
    chain: VaultClient | None = None
    store: Store | None = None
    log: ActionLog | None = None
    documents: dict[str, dict] = field(default_factory=dict)
    drafts: dict[str, str] = field(default_factory=dict)  # session key to the drafted batch id

    def __post_init__(self) -> None:
        if self.chain is None and self.settings.rpc_url and self.settings.vault_address:
            try:
                self.chain = VaultClient.from_env()
            except ChainUnavailable:
                self.chain = None
        self.store = self.store or Store(self.settings.state_dir / "agentwallet.db")
        self.log = self.log or ActionLog(self.settings.evidence_dir / "action-log.jsonl")
        self.graph = planner_graph.build(self)

    def _config(self, session_id: str) -> dict:
        return {"configurable": {"thread_id": session_id}}

    # Conversation

    def chat(self, session_id: str, message: str, document_ids: list[str] | None = None) -> ChatResponse:
        fields = [self.documents[d] for d in document_ids or [] if d in self.documents]
        state = self.graph.invoke({"session_id": session_id, "phase": "chat", "document_fields": fields,
                                   "conversation": [{"role": "user", "content": message}]}, self._config(session_id))
        return ChatResponse(reply=state["reply"],
                            plan_card=PlanCard.model_validate(state["plan_card"]) if state.get("plan_card") else None,
                            clarification=Clarification(**state["clarification"]) if state.get("clarification") else None)

    def draft(self, session_id: str, batch_ref: str) -> PlanCard | None:
        """Plan task B11: a plan card for a scheduled batch, with no model call, left for the officer to
        confirm. None when the session already has a plan."""
        if self.graph.get_state(self._config(session_id)).values.get("plan"):
            return None
        understanding = propose._blank("pay_batch", f"The scheduled batch {batch_ref} is ready for you to check.",
                                       batch_ref=batch_ref)
        state = self.graph.invoke({"session_id": session_id, "phase": "draft", "understanding": understanding,
                                   "conversation": []}, self._config(session_id))
        if not state.get("plan_card"):
            return None
        self.drafts[session_id] = state["plan_card"]["batch_id"]
        self.store.alert("plan_ready", None, f"Scheduled batch {batch_ref} is drafted for confirmation: "
                                             f"{state['plan_card']['total_usdc']} USDC.")
        self.log.append("planner", planner_lineage(), "scheduled_draft", status=state["plan_card"]["batch_id"])
        return PlanCard.model_validate(state["plan_card"])

    def open_drafts(self, prefix: str) -> list[dict]:
        """Drafted plans in sessions under `prefix` that nobody has confirmed yet."""
        out = []
        for key in list(self.drafts):
            if not key.startswith(prefix):
                continue
            values = self.graph.get_state(self._config(key)).values
            plan = values.get("plan")
            if plan and not plan.get("confirmed"):
                out.append({"session_id": key[len(prefix):], "plan_card": values["plan_card"]})
        return out

    def correct(self, session_id: str, batch_id: str, instruction: str) -> CorrectResponse:
        current = self.graph.get_state(self._config(session_id)).values
        if not current.get("plan") or current["plan"]["batch_id"] != batch_id:
            raise KeyError(f"no open plan {batch_id} in this session")
        state = self.graph.invoke({"phase": "correct", "instruction": instruction, "conversation": []},
                                  self._config(session_id))
        return CorrectResponse(reply=state["reply"], plan_card=PlanCard.model_validate(state["plan_card"]))

    def confirm(self, session_id: str, batch_id: str) -> ConfirmResponse:
        current = self.graph.get_state(self._config(session_id)).values
        plan = current.get("plan")
        if not plan or plan["batch_id"] != batch_id:
            raise KeyError(f"no open plan {batch_id} in this session")
        if plan.get("confirmed"):
            return ConfirmResponse(results=[PayoutResult.model_validate(r) for r in current.get("results", [])])
        state = self.graph.invoke({"phase": "confirm", "conversation": [{"role": "user", "content": "Confirm."}]},
                                  self._config(session_id))
        return ConfirmResponse(results=[PayoutResult.model_validate(r) for r in state["results"]])

    # Submission

    def submit_one(self, item: dict, *, enqueue: bool = True) -> dict:
        """Submits one checked payout and records its outcome for the status route."""
        result = self._submit_one(item, enqueue=enqueue)
        self.store.record_result(result)
        return result

    def _submit_one(self, item: dict, *, enqueue: bool) -> dict:
        intent = Intent.model_validate(item["intent"])
        payout = Payout.model_validate(item["payout"])
        verdicts = item["verdicts"]
        auditor, sentinel = verdicts["auditor"], verdicts["sentinel"]
        result = self._result(intent, payout, item, "queued")
        queue = self._queue if enqueue else self._queued_result
        if not item.get("planner_sig"):
            return queue(item, result, "the planner has no signing key", "chain")
        for name, v in (("auditor", auditor), ("sentinel", sentinel)):
            if v["verdict"] == "UNAVAILABLE":
                return queue(item, result, v["reasons"][0] if v["reasons"] else f"{name} unavailable", name)
        if "REJECT" in (auditor["verdict"], sentinel["verdict"]):
            return {**result, "status": "rejected", "reasons": auditor["reasons"] + sentinel["reasons"]}
        if "ESCALATE" in (auditor["verdict"], sentinel["verdict"]):
            return {**result, "status": "escalated", "reasons": auditor["reasons"] + sentinel["reasons"]}
        if self.chain is None:
            return queue(item, result, "no chain configured", "chain")
        sigs = [item["planner_sig"], auditor["signature"], sentinel["signature"]]
        try:
            tier = self.chain.tier_of(payout)
        except ChainError as exc:
            return {**result, "status": "rejected", "reasons": [f"The vault refuses it: {exc.name}."]}
        except ChainUnavailable as exc:
            return queue(item, result, str(exc), "chain")
        if tier == 2:
            decoded = reporter.decode(payout, self.books)
            self.store.add_pending(payout.proposalId, {**item, "sigs": sigs, "tier": tier, "decoded": decoded,
                                                      "summary": reporter.summary(decoded, tier)})
            self.log.append("planner", planner_lineage(), "pending_trustee", proposal_id=payout.proposalId, status="tier 2")
            return {**result, "status": "elevated_pending", "reasons": ["The vault rates it elevated: a trustee must co-sign."]}
        return self._execute(intent, payout, sigs, result)

    def _execute(self, intent: Intent, payout: Payout, sigs: list[str], result: dict, scenario: str = "") -> dict:
        try:
            tx = self.chain.execute(payout, sigs, expect_revert=True, scenario=scenario,
                                    description=f"payout to {intent.household_ref or intent.wallet}")
        except ChainUnavailable as exc:
            return self._queue({"intent": intent.model_dump(mode="json"), "payout": payout.model_dump(), "sigs": sigs},
                               result, str(exc), "chain")
        self.log.append("planner", planner_lineage(), "execute", proposal_id=payout.proposalId, tx_hash=tx.tx_hash,
                        status=tx.status)
        out = {**result, "tx_hash": tx.tx_hash, "explorer_url": f"{self.settings.explorer_url}/tx/{tx.tx_hash}"}
        if tx.status == "success":
            if intent.beneficiary_ref:
                self.books.record_payout(beneficiary_ref=intent.beneficiary_ref, programme_code=intent.programme_code,
                                         amount_usdc=intent.amount_usdc, tx_hash=tx.tx_hash)
            return {**out, "status": "paid"}
        return {**out, "status": "reverted", "reasons": [f"The vault reverted it: {tx.error}."]}

    def _queued_result(self, item: dict, result: dict, reason: str, missing: str) -> dict:
        return {**result, "status": "queued", "reasons": [reason]}

    def _queue(self, item: dict, result: dict, reason: str, missing: str) -> dict:
        self.store.enqueue(result["proposal_id"], item, reason, missing)
        self.log.append("planner", planner_lineage(), "queued", proposal_id=result["proposal_id"], status=missing)
        return {**result, "status": "queued", "reasons": [reason]}

    def _result(self, intent: Intent, payout: Payout, item: dict, status: str) -> dict:
        def verdict(v: dict | None) -> dict:
            if v is None:
                return Verdict(verdict="UNAVAILABLE").model_dump()
            return {"verdict": v["verdict"], "reasons": v["reasons"], "input_hash": v["input_hash"], "model": v["model"],
                    "lineage": v["lineage"], "signed": bool(v.get("signature"))}

        planner = {"verdict": "APPROVE", "reasons": ["Built from the books."] if intent.source == "books"
                   else ["Built from the conversation."], "input_hash": payout.evidenceHash,
                   "model": "planner", "lineage": planner_lineage(), "signed": bool(item.get("planner_sig"))}
        verdicts = item.get("verdicts", {})
        return {"proposal_id": payout.proposalId, "household_ref": intent.household_ref,
                "amount_usdc": str(intent.amount_usdc), "status": status, "tx_hash": None, "explorer_url": None,
                "verdicts": {"planner": planner, "auditor": verdict(verdicts.get("auditor")),
                             "sentinel": verdict(verdicts.get("sentinel"))},
                "reasons": []}

    # Trustees

    def pending(self) -> list[PendingPayout]:
        items = []
        for row in self.store.pending():
            item = row["item"]
            payout = Payout.model_validate(item["payout"])
            result = self._result(Intent.model_validate(item["intent"]), payout, item, "elevated_pending")
            items.append(PendingPayout(
                proposal_id=payout.proposalId, summary_text=item["summary"],
                typed_data=eip712.payout_typed_data(payout, chain_id=self.settings.chain_id,
                                                    vault=self.settings.vault_address),
                decoded_fields=item["decoded"], verdicts=Verdicts.model_validate(result["verdicts"]), tier=item["tier"]))
        return items

    def trustee_sign(self, proposal_id: str, signature: str) -> TrusteeSignResponse:
        row = self.store.get_pending(proposal_id)
        if row is None or row["status"] != "pending":
            raise KeyError(f"no payout {proposal_id} waits for a trustee")
        item = row["item"]
        payout = Payout.model_validate(item["payout"])
        try:
            signer = eip712.recover_payout(payout, signature, chain_id=self.settings.chain_id,
                                           vault=self.settings.vault_address)
        except Exception as exc:  # hex, length and curve errors each have their own type
            raise ValueError(f"not a 65-byte signature over this payout ({exc})") from exc
        record = self.chain.signer(signer) if self.chain is not None else {"role": "NONE", "active": False}
        if record["role"] != "TRUSTEE" or not record["active"]:
            raise PermissionError(f"{signer} is not an active trustee")
        intent = Intent.model_validate(item["intent"])
        result = self._execute(intent, payout, item["sigs"] + [signature], self._result(intent, payout, item, "paid"))
        self.store.update_pending(proposal_id, {**item, "trustee": signer}, result["status"], result.get("tx_hash"))
        self.store.record_result(result)
        self.log.append("trustee", "human", "trustee_sign", proposal_id=proposal_id, tx_hash=result.get("tx_hash"),
                        status=result["status"])
        return TrusteeSignResponse(tx_hash=result.get("tx_hash"), status=result["status"])

    def payout_status(self, proposal_id: str) -> PayoutResult:
        """The latest outcome of one payout: an elevated row turns to paid once a trustee signs."""
        result = self.store.result(proposal_id)
        if result is None:
            raise KeyError(f"no payout {proposal_id}")
        return PayoutResult.model_validate(result)

    # Fail-closed queue

    def queue(self) -> list[QueuedPayout]:
        return [QueuedPayout(proposal_id=r["proposal_id"], reason=r["reason"], queued_at=r["queued_at"],
                             missing=r["missing"]) for r in self.store.queued()]

    def retry_queue(self) -> int:
        """One pass over the queue: asks the missing checkers again or resubmits. Returns how many went through."""
        drained = 0
        for row in self.store.queued():
            item = row["item"]
            payout = Payout.model_validate(item["payout"])
            intent = Intent.model_validate(item["intent"])
            if row["missing"] in ("auditor", "sentinel") or "verdicts" not in item:
                verdicts = checkers.check(payout, intent, books=self.books, batch=[payout])
                item = {**item, "verdicts": {k: v.model_dump() for k, v in verdicts.items()}}
            outcome = self.submit_one(item, enqueue=False)
            if outcome["status"] == "queued":
                self.store.retried(row["proposal_id"], done=False, error=outcome["reasons"][0] if outcome["reasons"] else None)
            else:
                self.store.retried(row["proposal_id"], done=True)
                drained += 1
        return drained

    def record_document(self, document_id: str, fields: dict) -> None:
        self.documents[document_id] = fields

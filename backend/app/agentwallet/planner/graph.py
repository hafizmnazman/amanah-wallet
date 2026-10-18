"""The planner as a LangGraph graph (plan task B7).

One graph, four entry phases, state kept per session by a checkpointer:

    chat     understand -> plan                  a plan card, a clarifying question, or a reply
    draft    plan                                a plan card for a batch the books schedule (task B11)
    correct  correct (re-plans, same batch id)   an updated plan card
    confirm  sign -> check -> submit -> report   one result per payout

`understand` maps the request to a batch, a request or a payee. `plan` builds the card from the books, one
intent per household, amounts from the books. `sign` signs each intent with the planner's key. `check`
asks the auditor and the sentinel. `submit` executes routine payouts, stores elevated ones for a trustee,
and fails closed to the queue when a checker or the chain is unavailable. `report` writes the summary from
the decoded intents, not from the conversation. Every step is written to the evidence log.
"""

from __future__ import annotations

import operator
import re
import secrets
import time
from decimal import Decimal
from typing import Annotated, Any, TypedDict

from eth_utils import keccak
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from .. import checkers, eip712, reporter
from ..chain import ChainError, ChainUnavailable
from ..config import LINEAGE_CLAUDE, env
from ..evidence import canonical
from ..models import ModelBudgetExceeded, ModelUnavailable, get_model
from ..types import Intent, Payout, units_to_usdc, usdc_to_units
from . import propose


class PlannerState(TypedDict, total=False):
    session_id: str
    phase: str
    conversation: Annotated[list[dict], operator.add]
    document_fields: list[dict]
    understanding: dict
    plan: dict | None
    plan_card: dict | None
    clarification: dict | None
    instruction: str
    reply: str
    signed: list[dict]
    results: list[dict]


CORRECTION_SCHEMA = {
    "type": "object",
    "properties": {"remove_households": {"type": "array", "items": {"type": "string"}}, "reply": {"type": "string"}},
    "required": ["remove_households", "reply"],
    "additionalProperties": False,
}


def build(deps) -> Any:
    """`deps` carries books, chain (or None), store, log and settings; see service.PlannerService."""

    def log(event: str, **fields) -> None:
        deps.log.append("planner", LINEAGE_CLAUDE, event, **fields)

    # chat

    def understand(state: PlannerState) -> dict:
        try:
            u, reply = propose.understand(state["conversation"], books=deps.books,
                                          document_fields=state.get("document_fields"))
        except (ModelUnavailable, ModelBudgetExceeded) as exc:
            u, reply = propose._blank("chat", f"The planner is unavailable: {exc}"), None
        log("understand", input_hash=reply.input_hash if reply else None, model=reply.model if reply else None,
            status=u["action"])
        update = {"understanding": u, "reply": u["reply"], "clarification": None, "plan_card": None,
                  "conversation": [{"role": "assistant", "content": u["reply"]}]}
        if u["action"] == "clarify":
            update["clarification"] = {"question": u.get("question") or u["reply"], "options": u.get("options") or []}
        return update

    def plan(state: PlannerState) -> dict:
        intents, source = propose.resolve(state["understanding"], deps.books, strict_books_amounts=True)
        if not intents:
            return {"reply": "There is nothing in the books to pay for that request.", "plan": None}
        batch_id = f"{source['batch_ref']}-{secrets.token_hex(3)}"
        new_plan = {"batch_id": batch_id, "programme_code": source["programme_code"],
                    "intents": [i.model_dump(mode="json") for i in intents], "confirmed": False}
        card = plan_card(new_plan, state.get("document_fields"))
        log("plan", status=f"{len(intents)} intents, {card['total_usdc']} USDC, {card['tier_preview']}")
        reply = (f"{card['programme_name']}: {len(intents)} payout{'s' if len(intents) != 1 else ''}, "
                 f"{card['total_usdc']} USDC in all. Confirm to send them for the checks.")
        return {"plan": new_plan, "plan_card": card, "reply": reply,
                "conversation": [{"role": "assistant", "content": reply}]}

    def plan_card(p: dict, document_fields: list[dict] | None) -> dict:
        programme = deps.books.programme(p["programme_code"])
        intents = [Intent.model_validate(i) for i in p["intents"]]
        total = sum((i.amount_usdc for i in intents), Decimal(0))
        notes = []
        if any(i.source == "conversation" for i in intents):
            notes.append("At least one payee or amount comes from the conversation, not the books.")
        if any(d.get("injection_flag") for d in document_fields or []):
            notes.append("An uploaded document contains text aimed at the system; it was not followed.")
        return {"batch_id": p["batch_id"], "programme_code": programme["code"], "programme_name": programme["name"],
                "fund_name": deps.books.fund_name(programme["fund_code"]),
                "items": [{"household_ref": i.household_ref, "beneficiary_ref": i.beneficiary_ref, "wallet": i.wallet,
                           "amount_usdc": str(i.amount_usdc)} for i in intents],
                "total_usdc": str(total), "tier_preview": tier_preview(programme, intents), "notes": notes}

    def tier_preview(programme: dict, intents: list[Intent]) -> str:
        cap = Decimal(str(programme["cap_usdc"]))
        line = Decimal(str(programme["daily_budget_usdc"])) * Decimal("0.8")
        spent, posture = Decimal(0), 0
        if deps.chain is not None:
            try:
                spent = units_to_usdc(deps.chain.spent_today(programme["programme_id"]))
                posture = deps.chain.posture()
            except (ChainError, ChainUnavailable):
                pass
        running = spent
        for i in intents:
            running += i.amount_usdc
            if posture > 0 or i.amount_usdc > cap or running > line:
                return "elevated"
        return "routine"

    # correct

    def correct(state: PlannerState) -> dict:
        p = state.get("plan")
        if not p or p.get("confirmed"):
            return {"reply": "There is no open plan to correct."}
        instruction = state["instruction"]
        refs = [i["household_ref"] for i in p["intents"]]
        try:
            reply = get_model("planner").complete(
                propose.context(deps.books) + "\n\nThe open plan's households: " + ", ".join(r or "" for r in refs),
                state["conversation"] + [{"role": "user", "content": instruction}], schema=CORRECTION_SCHEMA,
                dry_run=lambda: offline_correction(instruction, refs))
            change = reply.data or {"remove_households": [], "reply": ""}
        except (ModelUnavailable, ModelBudgetExceeded):
            change = offline_correction(instruction, refs)
        remove = set(change["remove_households"])
        kept = [i for i in p["intents"] if i["household_ref"] not in remove]
        new_plan = {**p, "intents": kept}
        card = plan_card(new_plan, state.get("document_fields"))
        log("correct", status=f"removed {sorted(remove)}, {len(kept)} intents")
        text = change["reply"] or f"Updated: {len(kept)} households, {card['total_usdc']} USDC."
        return {"plan": new_plan, "plan_card": card, "reply": text,
                "conversation": [{"role": "user", "content": instruction}, {"role": "assistant", "content": text}]}

    # confirm

    def sign(state: PlannerState) -> dict:
        p = state["plan"]
        key = env("PLANNER_KEY")
        deadline = int(time.time()) + 3600
        if deps.chain is not None:
            try:
                deadline = deps.chain.w3.eth.get_block("latest")["timestamp"] + 3600
            except Exception:
                pass
        signed = []
        for raw in p["intents"]:
            intent = Intent.model_validate(raw)
            evidence = {"batch_id": p["batch_id"], "intent": raw, "books_record": _record_hash(intent)}
            payout = eip712.payout_from_intent(intent, deps.books, nonce=secrets.randbits(63), deadline=deadline,
                                               evidence_hash="0x" + keccak(text=canonical(evidence)).hex())
            sig = eip712.sign_payout(payout, key, chain_id=deps.settings.chain_id,
                                     vault=deps.settings.vault_address) if key else None
            log("sign", proposal_id=payout.proposalId, status="signed" if sig else "no planner key")
            signed.append({"intent": raw, "payout": payout.model_dump(), "planner_sig": sig})
        return {"signed": signed}

    def _record_hash(intent: Intent) -> str | None:
        if not intent.beneficiary_ref:
            return None
        try:
            return deps.books.verify_record("beneficiaries", intent.beneficiary_ref)
        except Exception:
            return None

    def check(state: PlannerState) -> dict:
        payouts = [Payout.model_validate(s["payout"]) for s in state["signed"]]
        spent = None
        if deps.chain is not None and payouts:
            try:
                spent = deps.chain.spent_today(payouts[0].programmeId)
            except (ChainError, ChainUnavailable):
                spent = None
        checked = []
        for s, payout in zip(state["signed"], payouts):
            verdicts = checkers.check(payout, Intent.model_validate(s["intent"]), books=deps.books, batch=payouts,
                                      spent_today=spent)
            for service, v in verdicts.items():
                if env("AGENTWALLET_CHECKERS", "http") == "inprocess":
                    deps.log.append(service, v.lineage, "verdict", proposal_id=payout.proposalId, verdict=v.verdict,
                                    input_hash=v.input_hash, model=v.model, tx_hash=v.anchor_tx)
            checked.append({**s, "verdicts": {k: v.model_dump() for k, v in verdicts.items()}})
        return {"signed": checked}

    def submit(state: PlannerState) -> dict:
        results = [deps.submit_one(item) for item in state["signed"]]
        return {"results": results, "plan": {**state["plan"], "confirmed": True}}

    def report(state: PlannerState) -> dict:
        counts: dict[str, int] = {}
        for r in state["results"]:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        words = ", ".join(f"{n} {status.replace('_', ' ')}" for status, n in sorted(counts.items()))
        log("report", status=words)
        text = f"Done: {words}."
        return {"reply": text, "conversation": [{"role": "assistant", "content": text}]}

    g = StateGraph(PlannerState)
    for name, fn in (("understand", understand), ("plan", plan), ("correct", correct), ("sign", sign),
                     ("check", check), ("submit", submit), ("report", report)):
        g.add_node(name, fn)
    g.add_conditional_edges(START, lambda s: {"chat": "understand", "draft": "plan", "correct": "correct",
                                              "confirm": "sign"}[s["phase"]],
                            ["understand", "plan", "correct", "sign"])
    g.add_conditional_edges("understand", lambda s: "plan" if s["understanding"]["action"].startswith("pay_") else END,
                            ["plan", END])
    g.add_edge("plan", END)
    g.add_edge("correct", END)
    g.add_edge("sign", "check")
    g.add_edge("check", "submit")
    g.add_edge("submit", "report")
    g.add_edge("report", END)
    return g.compile(checkpointer=InMemorySaver())


def offline_correction(instruction: str, household_refs: list[str]) -> dict:
    """The dry-run correction: "leave out household 12" removes the household whose number is 12."""
    numbers = {int(n) for n in re.findall(r"household\s*(?:ref\s*)?(?:[a-z]{3}-h)?(\d+)", instruction.lower())}
    remove = [r for r in household_refs if r and int(r.split("-H")[-1]) in numbers]
    reply = (f"Removed {', '.join(remove)}." if remove else "I did not find that household in the plan.")
    return {"remove_households": remove, "reply": reply}


def amount_units(intent_dict: dict) -> int:
    return usdc_to_units(intent_dict["amount_usdc"])

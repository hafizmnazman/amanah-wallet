"""The planner's understanding of a request, and its resolution into intents.

`understand` asks the planner model which action the officer wants (plan task B7's `understand` node).
`resolve` turns that action into intents from the books. In the product flow, amounts for registered
beneficiaries always come from the books (`strict_books_amounts=True`). `propose` is the planner alone,
with no checkers: red-team configuration S1. It keeps the model's own amounts by default, so S1 measures
what a typical single-model agent wallet would sign.
"""

from __future__ import annotations

import json
import re
import secrets
from decimal import Decimal

from .. import prompts
from ..config import planner_lineage
from ..models import ModelBudgetExceeded, ModelUnavailable, get_model
from ..reader import read_document
from ..types import Intent, Proposal

ACTIONS = ["pay_batch", "pay_request", "pay_beneficiary", "pay_wallet", "clarify", "refuse", "chat"]
SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ACTIONS},
        "batch_ref": {"type": ["string", "null"]},
        "request_ref": {"type": ["string", "null"]},
        "beneficiary_ref": {"type": ["string", "null"]},
        "wallet": {"type": ["string", "null"]},
        "programme_code": {"type": ["string", "null"]},
        "amount_usdc": {"type": ["number", "null"]},
        "question": {"type": ["string", "null"]},
        "options": {"type": "array", "items": {"type": "string"}},
        "reply": {"type": "string"},
    },
    "required": ["action", "batch_ref", "request_ref", "beneficiary_ref", "wallet", "programme_code", "amount_usdc",
                 "question", "options", "reply"],
    "additionalProperties": False,
}
WALLET = re.compile(r"0x[0-9a-fA-F]{40}")
AMOUNT = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:usdc|usd)\b", re.IGNORECASE)
CLARIFY_OPTIONS = ["Zakat monthly aid", "Flood relief"]


def context(books, *, document_fields: list[dict] | None = None, extra_notes: list[dict] | None = None) -> str:
    """The planner's view of the books: programmes, batches, requests and notes. Never personal data."""
    view = books.summary_for_planner()
    view["notes"] = [{"beneficiary_ref": n["beneficiary_ref"], "author": n["author"], "text": n["text"]}
                     for n in books.data["notes"]] + list(extra_notes or [])
    if document_fields:
        view["documents"] = [{"source": "untrusted upload, read by the quarantined reader", **d}
                             for d in document_fields]
    return prompts.load("planner") + "\n\nBooks summary (JSON):\n" + json.dumps(view, default=str)


def _blank(action: str, reply: str, **fields) -> dict:
    base = {k: None for k in SCHEMA["required"]}
    return {**base, "options": [], **fields, "action": action, "reply": reply}


def offline_understand(conversation: list[dict], books) -> dict:
    """The dry-run planner: keyword rules good enough for the scripted demo and the pipeline tests. It also
    follows explicit transfer requests, as a persuaded model might, so the checkers can be shown working."""
    text = conversation[-1]["content"].lower() if conversation else ""
    earlier = " ".join(m["content"].lower() for m in conversation[:-1] if m["role"] == "user")
    if re.search(r"\b(export|download|list)\b.*\b(identity|ic|address|phone|personal)\b", text):
        return _blank("refuse", "I cannot share personal data. I can offer the anonymised report of how each fund "
                                "was used.")
    if re.search(r"\b(new admin|administrator|add (?:my |this )?wallet|as a beneficiary|raise (?:the|its) cap)\b", text):
        return _blank("refuse", "Changes to beneficiaries, caps or signers need two trustees, not the agent.")
    wallet = WALLET.search(conversation[-1]["content"]) if conversation else None
    amount = AMOUNT.search(text)
    if wallet and amount:
        programme = "REL-PERAK-FLOOD" if "flood" in text else "ZKT-IPOH-FAKIR-M"
        return _blank("pay_wallet", "I have prepared that transfer for the checks.", wallet=wallet.group(0),
                      programme_code=programme, amount_usdc=float(amount.group(1).replace(",", "")))
    household = re.search(r"\b(?:household|student)\s+([a-z]{3}-h\d{2})\b", text)
    if household and "leave out" not in text:
        record = books.beneficiary_by_household(household.group(1).upper())
        if record:
            return _blank("pay_beneficiary", f"The payout for {record['household_ref']} is ready for the checks.",
                          beneficiary_ref=record["beneficiary_ref"],
                          amount_usdc=float(amount.group(1).replace(",", "")) if amount else None)
    if "emergency" in text or "grant" in text:
        return _blank("pay_request", "The emergency grant is ready for the checks.",
                      request_ref=books.scenario_ref("emergency_grant"))
    if "bursary" in text and ("late" in text or "edu-b04" in text or "edu-h04" in text):
        return _blank("pay_request", "The late bursary application is ready for the checks.",
                      request_ref=books.scenario_ref("override_case"))
    if "bursar" in text:
        return _blank("pay_batch", "Here are the second semester bursaries.", batch_ref="BATCH-2026-S2-EDU")
    if "monthly" in text or "zakat" in text or ("monthly" in earlier and "aid" in text):
        return _blank("pay_batch", "Here is October's monthly aid for Ipoh.",
                      batch_ref=books.scenario_ref("routine_batch"))
    if "flood" in text:
        return _blank("pay_batch", "Here is October's flood relief batch for Ipoh.", batch_ref="BATCH-2026-10-REL-IPOH")
    if "october" in text or "ipoh" in text:
        return _blank("clarify", "October has two batches for Ipoh.",
                      question="October has two batches for Ipoh: zakat monthly aid and flood relief. Which one?",
                      options=CLARIFY_OPTIONS)
    return _blank("chat", "I can plan payouts from the books: monthly aid, flood relief or bursaries.")


def understand(conversation: list[dict], *, books, document_fields: list[dict] | None = None,
               extra_notes: list[dict] | None = None):
    """Returns (understanding, model reply)."""
    model = get_model("planner")
    reply = model.complete(context(books, document_fields=document_fields, extra_notes=extra_notes), conversation,
                           schema=SCHEMA, dry_run=lambda: offline_understand(conversation, books))
    if reply.refused:
        return _blank("refuse", f"The planner model declined this request ({reply.refusal_category})."), reply
    data = reply.data or {}
    if data.get("action") not in ACTIONS:
        return _blank("chat", "I could not read that request. Please rephrase it."), reply
    return data, reply


def _proposal_id() -> str:
    return "0x" + secrets.token_hex(32)


def _beneficiary(books, ref: str | None) -> dict | None:
    """A beneficiary by its reference, or by its household's (ZKT-H05 for ZKT-B05); None when unknown."""
    if not ref:
        return None
    try:
        return books.beneficiary(ref)
    except KeyError:
        return books.beneficiary_by_household(ref.upper())


def resolve(understanding: dict, books, *, strict_books_amounts: bool = True) -> tuple[list[Intent], dict | None]:
    """Intents for a payable action, and the batch (or request) they came from. A reference the books do not
    have resolves to nothing, so a model that invents one gets "nothing to pay", not an error."""
    try:
        return _resolve(understanding, books, strict_books_amounts=strict_books_amounts)
    except (KeyError, StopIteration):
        return [], None


def _resolve(understanding: dict, books, *, strict_books_amounts: bool) -> tuple[list[Intent], dict | None]:
    action = understanding.get("action")
    if action == "pay_batch" and understanding.get("batch_ref"):
        batch = books.batch(understanding["batch_ref"])
        intents = []
        for item in batch["items"]:
            b = books.beneficiary(item["beneficiary_ref"])
            intents.append(Intent(programme_code=batch["programme_code"], beneficiary_ref=b["beneficiary_ref"],
                                  wallet=b["wallet"], amount_usdc=Decimal(str(item["amount_usdc"])),
                                  household_ref=item["household_ref"], proposal_id=_proposal_id()))
        return intents, {"batch_ref": batch["batch_ref"], "programme_code": batch["programme_code"]}
    if action == "pay_request" and understanding.get("request_ref"):
        r = books.request(understanding["request_ref"])
        b = books.beneficiary(r["beneficiary_ref"])
        intent = Intent(programme_code=r["programme_code"], beneficiary_ref=b["beneficiary_ref"], wallet=b["wallet"],
                        amount_usdc=Decimal(str(r["amount_usdc"])), household_ref=b["household_ref"],
                        proposal_id=_proposal_id())
        return [intent], {"batch_ref": r["request_ref"], "programme_code": r["programme_code"]}
    if action == "pay_beneficiary" and understanding.get("beneficiary_ref"):
        b = _beneficiary(books, understanding["beneficiary_ref"])
        if b is None:
            return [], None
        asked = understanding.get("amount_usdc")
        item = books.batch_item_for(b["beneficiary_ref"])
        books_amount = b.get("monthly_amount_usdc") or (item["amount_usdc"] if item else None)
        amount = books_amount if (strict_books_amounts and books_amount) or asked is None else asked
        if amount is None:
            return [], None
        intent = Intent(programme_code=b["programme_code"], beneficiary_ref=b["beneficiary_ref"], wallet=b["wallet"],
                        amount_usdc=Decimal(str(amount)), household_ref=b["household_ref"],
                        proposal_id=_proposal_id(), source="books" if amount == books_amount else "conversation")
        return [intent], {"batch_ref": f"ADHOC-{b['beneficiary_ref']}", "programme_code": b["programme_code"]}
    if action == "pay_wallet" and understanding.get("wallet") and understanding.get("amount_usdc"):
        code = understanding.get("programme_code") or "ZKT-IPOH-FAKIR-M"
        known = books.beneficiary_by_wallet(code, understanding["wallet"])
        intent = Intent(programme_code=code, beneficiary_ref=known["beneficiary_ref"] if known else None,
                        wallet=understanding["wallet"], amount_usdc=Decimal(str(understanding["amount_usdc"])),
                        household_ref=known["household_ref"] if known else None, proposal_id=_proposal_id(),
                        source="books" if known else "conversation")
        return [intent], {"batch_ref": "ADHOC-WALLET", "programme_code": code}
    return [], None


def propose(message: str, *, books, channel: str = "chat", document_text: str | None = None,
            note: dict | None = None, strict_books_amounts: bool = False) -> Proposal:
    """The planner alone, no checkers (red-team S1). Raw documents never reach the planner: only the
    quarantined reader's typed fields do. A `note` is free text stored in the books (channel "books")."""
    fields = None
    if document_text is not None:
        result = read_document(document_text)
        fields = [{**result.fields.model_dump(mode="json"), "injection_flag": result.injection_flag}]
    notes = [{"beneficiary_ref": note["beneficiary_ref"], "author": "beneficiary", "text": note["text"]}] if note else None
    try:
        understanding, reply = understand([{"role": "user", "content": message}], books=books, document_fields=fields,
                                          extra_notes=notes)
    except (ModelUnavailable, ModelBudgetExceeded) as exc:
        return Proposal(refusal=f"planner unavailable: {exc}", lineage=planner_lineage())
    intents, _ = resolve(understanding, books, strict_books_amounts=strict_books_amounts)
    action = understanding["action"]
    return Proposal(intents=intents,
                    refusal=understanding["reply"] if action == "refuse" else None,
                    clarification=understanding.get("question") if action == "clarify" else None,
                    reply=understanding["reply"], model=reply.model, lineage=reply.lineage, input_hash=reply.input_hash)

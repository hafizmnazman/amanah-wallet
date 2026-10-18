"""The quarantined reader (plan task B6): an untrusted document in, typed fields and an injection flag out.

The model call has no tools. Its reply is validated against ReaderFields and anything else is dropped.
Deterministic patterns set the injection flag whether or not a model is live, because a model can be
persuaded and a pattern cannot. Amounts from the reader are advisory: the planner always takes amounts
from the books.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from . import prompts
from .models import ModelUnavailable, get_model
from .types import ReaderFields

PATTERNS = {
    "system_prefix": r"\b(?:system|assistant|developer)\s*:",
    "ignore_instructions": r"\b(?:ignore|disregard|forget)\b[^.\n]{0,40}\b(?:instructions|rules|messages|checks)\b",
    "approval_command": r"\bapprove (?:this|the) (?:applicant|payout|payment|request|case)\b|\bpre-approved\b"
                        r"|\bmark (?:the|this) case as (?:verified|approved)\b",
    "payment_command": r"\b(?:pay|send|transfer)\s+(?:[\d,]+(?:\.\d+)?)\s*(?:usdc|usd|myr|rm)\b",
    "role_claim": r"\bi am the (?:new )?(?:system )?(?:admin|administrator|chairman|auditor|trustee|treasurer)\b",
    "checker_bypass": r"\b(?:do not|don't|never) (?:ask|tell|involve|notify) the (?:auditor|sentinel|trustees?)\b",
    "hidden_text": r"white text|font size\s*[01]\b|display\s*:\s*none|[​‌‍⁠]",
    "wallet_instruction": r"\b(?:add|whitelist|allowlist|register)\b[^.\n]{0,40}0x[0-9a-f]{6,}",
    "encoded_blob": r"\b[a-z0-9+/]{48,}={0,2}(?![a-z0-9+/])",
}
COMPILED = {name: re.compile(p, re.IGNORECASE) for name, p in PATTERNS.items()}

SCHEMA = {
    "type": "object",
    "properties": {
        "applicant_ref": {"type": ["string", "null"]},
        "requested_amount_usdc": {"type": ["number", "null"]},
        "programme_code": {"type": ["string", "null"]},
        "dates": {"type": "array", "items": {"type": "string"}},
        "free_text_present": {"type": "boolean"},
        "instructions_detected": {"type": "boolean"},
    },
    "required": ["applicant_ref", "requested_amount_usdc", "programme_code", "dates", "free_text_present",
                 "instructions_detected"],
    "additionalProperties": False,
}
PROGRAMME_BY_PREFIX = {"ZKT": "ZKT-IPOH-FAKIR-M", "REL": "REL-PERAK-FLOOD", "EDU": "EDU-BURSARY-S1"}
DATE = re.compile(r"\b\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|"
                  r"December) \d{4}\b|\b\d{4}-\d{2}-\d{2}\b")


@dataclass
class ReaderResult:
    fields: ReaderFields
    injection_flag: bool
    signals: list[str] = field(default_factory=list)
    model: str = ""
    input_hash: str = ""


def injection_signals(text: str) -> list[str]:
    return [name for name, pattern in COMPILED.items() if pattern.search(text)]


def _offline_fields(text: str) -> dict:
    ref = re.search(r"\b(ZKT|REL|EDU)-[HB]\d{2}\b", text)
    amount = re.search(r"([\d,]+(?:\.\d+)?)\s*USDC\b", text, re.IGNORECASE)
    return {
        "applicant_ref": ref.group(0) if ref else None,
        "requested_amount_usdc": float(amount.group(1).replace(",", "")) if amount else None,
        "programme_code": PROGRAMME_BY_PREFIX.get(ref.group(1)) if ref else None,
        "dates": DATE.findall(text),
        "free_text_present": len(text.split()) > 12,
        "instructions_detected": bool(injection_signals(text)),
    }


def read_document(text: str) -> ReaderResult:
    signals = injection_signals(text)
    model = get_model("reader")
    try:
        reply = model.complete(prompts.load("reader"), [{"role": "user", "content": text}], schema=SCHEMA,
                               dry_run=lambda: _offline_fields(text), max_tokens=2000)
    except ModelUnavailable:
        data, model_name, digest = _offline_fields(text), "reader unavailable: patterns only", ""
    else:
        data = reply.data or {}
        model_name, digest = reply.model, reply.input_hash
        if reply.refused:
            data = _offline_fields(text) | {"instructions_detected": True}
            signals.append("model_refused")
    try:
        fields = ReaderFields.model_validate(data)
    except ValidationError:
        fields = ReaderFields(free_text_present=True)
        signals.append("reply_outside_schema")
    if data.get("instructions_detected"):
        signals.append("model_flag")
    return ReaderResult(fields=fields, injection_flag=bool(signals), signals=sorted(set(signals)),
                        model=model_name, input_hash=digest)

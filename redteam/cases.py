"""Red-team cases: the format of plan section 3.6, validated with pydantic.

A case file under redteam/gallery/ holds a YAML list of cases. Seeds are hand-written; legitimate
payouts come from redteam/legit.py; mutations come from redteam/mutate.py.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

REDTEAM = Path(__file__).parent
REPO = REDTEAM.parent
GALLERY = REDTEAM / "gallery"
BOOKS_PATH = REDTEAM / "data" / "books.json"

CaseClass = Literal[
    "induced_transfer",
    "direct_injection",
    "document_injection",
    "stored_injection",
    "authority",
    "urgency",
    "encoded",
    "data_extraction",
    "privilege_escalation",
    "structuring",
    "legitimate",
]
ATTACK_CLASSES = [c for c in CaseClass.__args__ if c != "legitimate"]
PROGRAMMES = ("ZKT-IPOH-FAKIR-M", "REL-PERAK-FLOOD", "EDU-BURSARY-S1")
PERSONAL_FIELDS = ("name", "id_number", "address", "phone")


class Goal(BaseModel):
    """What success means for the attacker, or the payout a legitimate case expects."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["transfer", "extract"]
    beneficiary: str | None = None  # a wallet address
    beneficiary_ref: str | None = None  # a books reference, resolved to its wallet
    amount_usdc: Decimal | None = None  # transfer: the least the attacker wants, or the exact legitimate amount
    fields: list[Literal["name", "id_number", "address", "phone"]] = Field(default_factory=list)  # extract

    @model_validator(mode="after")
    def _shape(self) -> Goal:
        if self.kind == "transfer":
            if (self.beneficiary is None) == (self.beneficiary_ref is None):
                raise ValueError("a transfer goal names exactly one of beneficiary or beneficiary_ref")
            if self.amount_usdc is None or self.amount_usdc <= 0:
                raise ValueError("a transfer goal needs a positive amount_usdc")
        if self.kind == "extract" and not self.fields:
            raise ValueError("an extract goal lists the personal fields the attacker wants")
        return self


class Mutation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent: str
    transforms: list[str]
    provider: str  # "dryrun" or the model that wrote the variant


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    case_class: CaseClass = Field(alias="class")
    channel: Literal["chat", "document", "books"]
    payload: str
    goal: Goal
    expected: Literal["REJECT", "ESCALATE", "REVERT", "APPROVE"]
    target_programme: Literal["ZKT-IPOH-FAKIR-M", "REL-PERAK-FLOOD", "EDU-BURSARY-S1"]
    # For document and books cases: what the officer types. The payload is the document, or the note
    # stored in the books about `note_beneficiary_ref`.
    officer_message: str | None = None
    note_beneficiary_ref: str | None = None
    mutation: Mutation | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Case:
        legit = self.case_class == "legitimate"
        if legit != (self.expected == "APPROVE"):
            raise ValueError(f"{self.id}: legitimate cases expect APPROVE, attacks never do")
        if legit and self.goal.kind != "transfer":
            raise ValueError(f"{self.id}: a legitimate case is a transfer")
        if self.channel in ("document", "books") and not self.officer_message:
            raise ValueError(f"{self.id}: {self.channel} cases need officer_message")
        if self.channel == "books" and not self.note_beneficiary_ref:
            raise ValueError(f"{self.id}: books cases name note_beneficiary_ref")
        return self

    @property
    def is_attack(self) -> bool:
        return self.case_class != "legitimate"

    def dump(self) -> dict:
        return json.loads(self.model_dump_json(by_alias=True, exclude_none=True))


def load_books(path: Path = BOOKS_PATH) -> dict:
    return json.loads(Path(path).read_text())


def load_file(path: Path) -> list[Case]:
    raw = yaml.safe_load(Path(path).read_text()) or []
    return [Case.model_validate(item) for item in raw]


def load_gallery(include_mutated: bool = False, gallery: Path = GALLERY) -> list[Case]:
    """Every seed and legitimate case, plus the mutated set when asked. Ids must be unique."""
    files = sorted(gallery.glob("*.yaml"))
    if include_mutated:
        files += sorted((gallery / "mutated").glob("*.yaml"))
    cases = [c for f in files for c in load_file(f)]
    seen: set[str] = set()
    for c in cases:
        if c.id in seen:
            raise ValueError(f"duplicate case id {c.id}")
        seen.add(c.id)
    return cases


def resolve_wallet(goal: Goal, books: dict) -> str:
    if goal.beneficiary:
        return goal.beneficiary
    for b in books["beneficiaries"]:
        if b["beneficiary_ref"] == goal.beneficiary_ref:
            return b["wallet"]
    raise KeyError(f"unknown beneficiary_ref {goal.beneficiary_ref}")


def dataset_hash(cases: list[Case]) -> str:
    """sha256 over the cases' canonical JSON, in id order, for the run manifest."""
    body = json.dumps([c.dump() for c in sorted(cases, key=lambda c: c.id)], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def write_cases(path: Path, cases: list[Case], header: str) -> None:
    text = yaml.safe_dump([c.dump() for c in cases], sort_keys=False, allow_unicode=True, width=110)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(f"# {header}\n" + text)

"""Provider factory (plan task B1): one chat model per role, chosen from the environment.

| role            | lineage           | provider                                                    |
|-----------------|-------------------|-------------------------------------------------------------|
| planner         | anthropic/claude  | Anthropic API, or Bedrock when PLANNER_PROVIDER=bedrock      |
| reader          | anthropic/claude  | as the planner, READER_MODEL or PLANNER_MODEL                |
| reporter        | anthropic/claude  | as the planner, REPORTER_MODEL or PLANNER_MODEL              |
| auditor         | alibaba/qwen      | Model Studio's OpenAI-compatible endpoint; fails over only  |
|                 |                   | to AUDITOR_FALLBACK_MODEL on the same endpoint, never Claude |
| auditor_control | anthropic/claude  | the same-lineage control arm (red-team S2)                   |
| auditor_gpt     | openai/gpt        | OpenAI, AUDITOR_GPT_MODEL: a third lineage for the red team's |
|                 |                   | joint-failure matrix only, never a signer in the product     |
| redteam         | openai/gpt        | OpenAI; falls back to Groq (meta/llama)                      |

Model names always come from the environment; the code never hardcodes one. A role with no key, or
AGENTWALLET_DRY_RUN=1, answers from the caller's deterministic `dry_run` function instead, and the reply
says so. Every live call counts against DAILY_MODEL_CALL_CAP, the stand-in for Amanah's spending
control, and every reply carries the served model, its lineage and the sha256 of its input.
"""

from __future__ import annotations

import contextlib
import json
import threading
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from .config import LINEAGE_CLAUDE, LINEAGE_GPT, LINEAGE_QWEN, Settings, dry_run_forced, env
from .evidence import canonical, sha256_hex

DryRun = Callable[[], dict[str, Any]]


class ModelUnavailable(Exception):
    """Every provider for the role failed. Checkers turn this into UNAVAILABLE, so the planner fails closed."""


class ModelBudgetExceeded(Exception):
    """DAILY_MODEL_CALL_CAP was reached for today."""


@dataclass
class ModelReply:
    text: str
    data: dict[str, Any] | None
    model: str
    lineage: str
    input_hash: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    refused: bool = False
    refusal_category: str | None = None
    dry_run: bool = False


def price(role: str, model: str) -> tuple[float, float] | None:
    """USD per million input and output tokens, from <ROLE>_PRICE_PER_MTOK="in,out" in .env, copied from the
    provider's price list. No price table lives in the code, since it would have to name models."""
    override = env(f"{role.upper()}_PRICE_PER_MTOK")
    if not override:
        return None
    a, b = override.split(",")
    return float(a), float(b)


def cost(role: str, model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    p = price(role, model)
    if p is None or input_tokens is None or output_tokens is None:
        return None
    return round((input_tokens * p[0] + output_tokens * p[1]) / 1_000_000, 6)


_RECORDERS: list[list[ModelReply]] = []


@contextlib.contextmanager
def recording():
    """Collects every reply, live or dry-run, made inside the block: the red-team runner's latency and cost."""
    calls: list[ModelReply] = []
    _RECORDERS.append(calls)
    try:
        yield calls
    finally:
        _RECORDERS.remove(calls)


def _record(reply: ModelReply) -> ModelReply:
    for calls in _RECORDERS:
        calls.append(reply)
    return reply


class CallBudget:
    """Counts live model calls per day in <state>/model-calls.json and refuses past the daily cap."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.path = self.settings.state_dir / "model-calls.json"
        self._lock = threading.Lock()

    def used(self) -> int:
        """Live calls made today, against the cap."""
        counts = json.loads(self.path.read_text()) if self.path.exists() else {}
        return sum(counts.get(date.today().isoformat(), {}).values())

    def take(self, role: str) -> None:
        with self._lock:
            today = date.today().isoformat()
            counts = json.loads(self.path.read_text()) if self.path.exists() else {}
            day = counts.setdefault(today, {})
            if sum(day.values()) >= self.settings.daily_model_call_cap:
                raise ModelBudgetExceeded(f"{self.settings.daily_model_call_cap} model calls already made today")
            day[role] = day.get(role, 0) + 1
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({today: day}, indent=2))


def input_hash(system: str, messages: list[dict], schema: dict | None) -> str:
    return "0x" + sha256_hex(canonical({"system": system, "messages": messages, "schema": schema}))


ROLE_LINEAGE = {"planner": LINEAGE_CLAUDE, "reader": LINEAGE_CLAUDE, "reporter": LINEAGE_CLAUDE,
                "auditor": LINEAGE_QWEN, "auditor_control": LINEAGE_CLAUDE, "auditor_gpt": LINEAGE_GPT,
                "redteam": LINEAGE_GPT}


class ChatModel:
    """One role's model. `complete` returns a ModelReply; with `schema`, `data` holds the parsed JSON."""

    def __init__(self, role: str, budget: CallBudget | None = None):
        if role not in ROLE_LINEAGE:
            raise ValueError(f"unknown role {role}")
        self.role = role
        self.lineage = ROLE_LINEAGE[role]
        self.budget = budget
        self._providers: list | None = None

    def providers(self) -> list:
        """Live providers in failover order; empty means dry-run."""
        if self._providers is None:
            self._providers = [] if dry_run_forced() else _live_providers(self.role)
        return self._providers

    @property
    def live(self) -> bool:
        return bool(self.providers())

    def complete(self, system: str, messages: list[dict], *, schema: dict | None = None,
                 dry_run: DryRun | None = None, max_tokens: int = 16000) -> ModelReply:
        digest = input_hash(system, messages, schema)
        started = time.monotonic()
        if not self.live:
            if dry_run is None:
                raise ModelUnavailable(f"no live provider for {self.role} and no dry-run reply")
            data = dry_run()
            return _record(ModelReply(json.dumps(data), data, f"dry-run:{self.role}", self.lineage, digest,
                                      int((time.monotonic() - started) * 1000), dry_run=True))
        (self.budget or CallBudget()).take(self.role)
        errors = []
        for provider in self.providers():
            try:
                reply = provider.complete(system, messages, schema=schema, max_tokens=max_tokens)
            except ModelUnavailable as exc:
                errors.append(f"{provider.model}: {exc}")
                continue
            reply.input_hash = digest
            reply.latency_ms = int((time.monotonic() - started) * 1000)
            reply.cost_usd = cost(self.role, reply.model, reply.input_tokens, reply.output_tokens)
            return _record(reply)
        raise ModelUnavailable("; ".join(errors))


def _live_providers(role: str) -> list:
    if role in ("planner", "reader", "reporter", "auditor_control"):
        model = env(f"{role.upper()}_MODEL") or env("PLANNER_MODEL")
        if role == "auditor_control":
            model = env("AUDITOR_CONTROL_MODEL") or env("PLANNER_MODEL")
        if not model:
            return []
        if env("PLANNER_PROVIDER", "anthropic") == "bedrock" and env("AWS_REGION"):
            from .providers.anthropic_chat import ClaudeChat

            return [ClaudeChat(model, lineage=LINEAGE_CLAUDE, bedrock_region=env("AWS_REGION"), role=role)]
        if not env("ANTHROPIC_API_KEY"):
            return []
        from .providers.anthropic_chat import ClaudeChat

        return [ClaudeChat(model, lineage=LINEAGE_CLAUDE, role=role)]

    from .providers.openai_chat import OpenAICompatibleChat

    if role == "auditor":
        key, base = env("DASHSCOPE_API_KEY"), env("DASHSCOPE_BASE_URL")
        models = [m for m in (env("AUDITOR_MODEL"), env("AUDITOR_FALLBACK_MODEL")) if m]
        if not (key and base and models):
            return []
        return [OpenAICompatibleChat(m, lineage=LINEAGE_QWEN, api_key=key, base_url=base, temperature=0)
                for m in models]

    if role == "auditor_gpt":
        if not (env("OPENAI_API_KEY") and env("AUDITOR_GPT_MODEL")):
            return []
        return [OpenAICompatibleChat(env("AUDITOR_GPT_MODEL"), lineage=LINEAGE_GPT, api_key=env("OPENAI_API_KEY"),
                                     base_url=None, temperature=0)]

    providers = []  # redteam
    if env("OPENAI_API_KEY") and env("REDTEAM_MODEL"):
        providers.append(OpenAICompatibleChat(env("REDTEAM_MODEL"), lineage=LINEAGE_GPT,
                                              api_key=env("OPENAI_API_KEY"), base_url=None, temperature=1))
    if env("GROQ_API_KEY") and env("REDTEAM_FALLBACK_MODEL"):
        providers.append(OpenAICompatibleChat(env("REDTEAM_FALLBACK_MODEL"), lineage="meta/llama",
                                              api_key=env("GROQ_API_KEY"), base_url=env("GROQ_BASE_URL"),
                                              temperature=1))
    return providers


_MODELS: dict[str, ChatModel] = {}


def get_model(role: str) -> ChatModel:
    if role not in _MODELS:
        _MODELS[role] = ChatModel(role)
    return _MODELS[role]


def reset_models() -> None:
    """Forgets cached providers, for tests that change the environment."""
    _MODELS.clear()

"""Claude through the official `anthropic` SDK: the first-party API, or Amazon Bedrock's Mantle client.

JSON replies use structured outputs (`output_config.format`). Thinking is left to the model's default
(adaptive on current models). `temperature` is never sent: current Claude models reject it. Effort comes
from <ROLE>_EFFORT, default "high". On the first-party API, models that support it get server-side refusal
fallbacks (`fallbacks: "default"`); set PLANNER_REFUSAL_FALLBACK=off to turn that off, for example to keep
red-team measurements on one model. The reply always names the model that actually served it.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic

from ..config import env
from ..models import ModelReply, ModelUnavailable

FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Models that accept fallbacks: "default" on the first-party API. Haiku 5.5 has no server-side fallback.
FALLBACK_MODELS = ("claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5")


class ClaudeChat:
    def __init__(self, model: str, *, lineage: str, bedrock_region: str | None = None, role: str = "planner"):
        self.model = model
        self.lineage = lineage
        self.role = role
        self.bedrock = bedrock_region is not None
        if self.bedrock:
            self.client = anthropic.AnthropicBedrockMantle(aws_region=bedrock_region, timeout=180.0)
        else:
            self.client = anthropic.Anthropic(timeout=180.0)

    def _fallbacks(self) -> bool:
        return (not self.bedrock and self.model in FALLBACK_MODELS
                and env("PLANNER_REFUSAL_FALLBACK", "default") != "off")

    def complete(self, system: str, messages: list[dict], *, schema: dict | None = None,
                 max_tokens: int = 16000) -> ModelReply:
        output_config: dict[str, Any] = {"effort": env(f"{self.role.upper()}_EFFORT", "high")}
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        request = {"model": self.model, "max_tokens": max_tokens, "system": system, "messages": messages,
                   "output_config": output_config}
        try:
            if self._fallbacks():
                response = self.client.beta.messages.create(**request, betas=[FALLBACK_BETA], fallbacks="default")
            else:
                response = self.client.messages.create(**request)
        except anthropic.RateLimitError as exc:
            raise ModelUnavailable(f"rate limited: {exc}") from exc
        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500:
                raise ModelUnavailable(f"server error {exc.status_code}") from exc
            raise
        except anthropic.APIConnectionError as exc:
            raise ModelUnavailable(f"connection error: {exc}") from exc

        usage = response.usage
        reply = ModelReply(text="", data=None, model=response.model, lineage=self.lineage, input_hash="",
                           latency_ms=0, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)
        if response.stop_reason == "refusal":
            reply.refused = True
            details = getattr(response, "stop_details", None)
            reply.refusal_category = getattr(details, "category", None) if details else None
            return reply
        reply.text = next((b.text for b in response.content if b.type == "text"), "")
        if schema is not None and reply.text:
            reply.data = json.loads(reply.text)
        return reply

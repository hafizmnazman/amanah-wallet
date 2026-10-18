"""Claude through the official `anthropic` SDK: the first-party API, or Amazon Bedrock's Mantle client.

JSON replies use structured outputs (`output_config.format`). Thinking is left to the model's default
(adaptive on current models). `temperature` is never sent: current Claude models reject it. Effort comes
from <ROLE>_EFFORT, default "high". On the first-party API, requests ask for server-side refusal fallbacks
(`fallbacks: "default"`). A model that does not take them answers 400; the client then asks again without
them and stops asking for that model. Set PLANNER_REFUSAL_FALLBACK=off to turn fallbacks off, for example
to keep red-team measurements on one model. The reply always names the model that actually served it.
"""

from __future__ import annotations

from typing import Any

import anthropic

from ..config import env
from ..models import ModelReply, ModelUnavailable, parse_json

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ClaudeChat:
    def __init__(self, model: str, *, lineage: str, bedrock_region: str | None = None, role: str = "planner"):
        self.model = model
        self.lineage = lineage
        self.role = role
        self.bedrock = bedrock_region is not None
        self.fallbacks_supported = True
        if self.bedrock:
            self.client = anthropic.AnthropicBedrockMantle(aws_region=bedrock_region, timeout=180.0)
        else:
            self.client = anthropic.Anthropic(timeout=180.0)

    def _fallbacks(self) -> bool:
        return not self.bedrock and self.fallbacks_supported and env("PLANNER_REFUSAL_FALLBACK", "default") != "off"

    def _create(self, request: dict) -> Any:
        if self._fallbacks():
            try:
                return self.client.beta.messages.create(**request, betas=[FALLBACK_BETA], fallbacks="default")
            except anthropic.BadRequestError as exc:
                if "fallback" not in str(exc).lower():
                    raise
                self.fallbacks_supported = False
        return self.client.messages.create(**request)

    def complete(self, system: str, messages: list[dict], *, schema: dict | None = None,
                 max_tokens: int = 16000) -> ModelReply:
        output_config: dict[str, Any] = {"effort": env(f"{self.role.upper()}_EFFORT", "high")}
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        request = {"model": self.model, "max_tokens": max_tokens, "system": system, "messages": messages,
                   "output_config": output_config}
        try:
            response = self._create(request)
        except anthropic.RateLimitError as exc:
            raise ModelUnavailable(f"rate limited: {exc}") from exc
        except anthropic.APIStatusError as exc:
            # A 4xx here is a configuration problem (key, model name, parameter). Failing closed with the
            # reason keeps the payout queued or the auditor escalating, instead of an error mid-request.
            raise ModelUnavailable(f"API error {exc.status_code}: {exc.message}") from exc
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
        if schema is not None and reply.text and response.stop_reason != "max_tokens":
            reply.data = parse_json(reply.text)
        return reply

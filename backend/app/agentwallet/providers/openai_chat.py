"""Non-Claude lineages through the official `openai` SDK and OpenAI-compatible endpoints: Qwen on Alibaba
Cloud Model Studio (the auditor), GPT on OpenAI and Llama on Groq (the red-team agent)."""

from __future__ import annotations

import json

import openai

from ..models import ModelReply, ModelUnavailable, parse_json


class OpenAICompatibleChat:
    def __init__(self, model: str, *, lineage: str, api_key: str, base_url: str | None, temperature: float):
        self.model = model
        self.lineage = lineage
        self.temperature = temperature
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=120.0, max_retries=2)

    def complete(self, system: str, messages: list[dict], *, schema: dict | None = None,
                 max_tokens: int = 16000) -> ModelReply:
        chat = [{"role": "system", "content": system}] + messages
        if schema is not None:
            # json_object is the widest-supported JSON mode on compatible endpoints; the caller validates
            # the reply against its schema, and the schema is restated in the system message.
            chat[0] = {"role": "system", "content": system + "\n\nReply with one JSON object matching this "
                                                              "JSON Schema:\n" + json.dumps(schema)}
        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=chat, temperature=self.temperature, max_tokens=max_tokens,
                response_format={"type": "json_object"} if schema is not None else openai.NOT_GIVEN,
            )
        except (openai.APIConnectionError, openai.APITimeoutError, openai.RateLimitError) as exc:
            raise ModelUnavailable(str(exc)) from exc
        except openai.APIStatusError as exc:
            raise ModelUnavailable(f"API error {exc.status_code}: {exc.message}") from exc
        text = response.choices[0].message.content or ""
        usage = response.usage
        truncated = response.choices[0].finish_reason == "length"
        return ModelReply(text=text, data=parse_json(text) if schema is not None and text and not truncated else None,
                          model=response.model or self.model, lineage=self.lineage, input_hash="", latency_ms=0,
                          input_tokens=getattr(usage, "prompt_tokens", None),
                          output_tokens=getattr(usage, "completion_tokens", None))

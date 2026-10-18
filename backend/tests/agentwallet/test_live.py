"""Plan task B1: one live smoke test per provider, skipped unless its key and model are in the environment.

Each test makes one small paid call. Load the keys first, for example:

    set -a; . ../.env; set +a; python -m pytest -m live
"""

import os

import pytest

from app.agentwallet import models

pytestmark = pytest.mark.live
SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"],
          "additionalProperties": False}
ASK = [{"role": "user", "content": 'Reply with the JSON object {"ok": true} and nothing else.'}]


def needs(*names):
    missing = [n for n in names if not os.environ.get(n)]
    return pytest.mark.skipif(bool(missing), reason=f"set {', '.join(missing)} to run")


@pytest.fixture(autouse=True)
def live_models(monkeypatch, tmp_path):
    monkeypatch.delenv("AGENTWALLET_DRY_RUN", raising=False)
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path))
    models.reset_models()
    yield
    models.reset_models()


def check(role, lineage):
    m = models.get_model(role)
    assert m.live
    reply = m.complete("You are a test endpoint. Answer in JSON.", ASK, schema=SCHEMA, max_tokens=2000)
    assert not reply.dry_run and reply.data == {"ok": True}, reply.text
    assert reply.lineage == lineage and reply.model and reply.input_hash
    return reply


@needs("ANTHROPIC_API_KEY", "PLANNER_MODEL")
def test_planner_answers_live():
    check("planner", "anthropic/claude")


@needs("DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "AUDITOR_MODEL")
def test_auditor_answers_live():
    check("auditor", "alibaba/qwen")


@needs("OPENAI_API_KEY", "REDTEAM_MODEL")
def test_redteam_model_answers_live():
    check("redteam", "openai/gpt")


@needs("OPENAI_API_KEY", "AUDITOR_GPT_MODEL")
def test_gpt_auditor_answers_live():
    check("auditor_gpt", "openai/gpt")

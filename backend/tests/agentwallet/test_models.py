"""Plan task B1: each role picks its provider from the environment; dry-run answers offline."""

import pytest

from app.agentwallet import models
from app.agentwallet.config import Settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for name in ("ANTHROPIC_API_KEY", "PLANNER_MODEL", "DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL", "AUDITOR_MODEL",
                 "AUDITOR_FALLBACK_MODEL", "OPENAI_API_KEY", "REDTEAM_MODEL", "GROQ_API_KEY", "REDTEAM_FALLBACK_MODEL",
                 "PLANNER_PROVIDER", "AWS_REGION", "AGENTWALLET_DRY_RUN", "AUDITOR_GPT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path))
    models.reset_models()
    yield
    models.reset_models()


def test_without_keys_every_role_is_dry_run_and_says_so():
    for role in ("planner", "reader", "reporter", "auditor", "auditor_control", "auditor_gpt", "redteam"):
        m = models.get_model(role)
        assert not m.live
        reply = m.complete("system", [{"role": "user", "content": "hi"}], schema={"type": "object"},
                           dry_run=lambda: {"ok": True})
        assert reply.dry_run and reply.data == {"ok": True} and reply.model == f"dry-run:{role}"
    assert models.get_model("auditor").lineage == "alibaba/qwen"
    assert models.get_model("auditor_control").lineage == "anthropic/claude"
    assert models.get_model("auditor_gpt").lineage == "openai/gpt"


def test_a_role_without_a_dry_run_reply_is_unavailable():
    with pytest.raises(models.ModelUnavailable):
        models.get_model("planner").complete("s", [{"role": "user", "content": "x"}])


def test_input_hash_is_stable_and_input_sensitive():
    a = models.input_hash("s", [{"role": "user", "content": "x"}], None)
    assert a == models.input_hash("s", [{"role": "user", "content": "x"}], None)
    assert a != models.input_hash("s", [{"role": "user", "content": "y"}], None)


def test_keys_select_live_providers_in_failover_order(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    monkeypatch.setenv("PLANNER_MODEL", "planner-model-from-env")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-not-a-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "http://127.0.0.1:9/compatible-mode/v1")
    monkeypatch.setenv("AUDITOR_MODEL", "qwen-primary")
    monkeypatch.setenv("AUDITOR_FALLBACK_MODEL", "qwen-fallback")
    models.reset_models()
    assert [p.model for p in models.get_model("planner").providers()] == ["planner-model-from-env"]
    auditor = models.get_model("auditor").providers()
    assert [p.model for p in auditor] == ["qwen-primary", "qwen-fallback"]
    assert all(p.lineage == "alibaba/qwen" for p in auditor)
    monkeypatch.setenv("AGENTWALLET_DRY_RUN", "1")
    models.reset_models()
    assert not models.get_model("planner").live


def test_auditor_failover_ends_unavailable_when_every_endpoint_is_down(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-not-a-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("AUDITOR_MODEL", "qwen-primary")
    models.reset_models()
    m = models.get_model("auditor")
    for p in m.providers():
        p.client = p.client.with_options(max_retries=0, timeout=2)
    with pytest.raises(models.ModelUnavailable):
        m.complete("s", [{"role": "user", "content": "x"}], schema={"type": "object"})


def test_daily_call_cap(monkeypatch, tmp_path):
    monkeypatch.setenv("DAILY_MODEL_CALL_CAP", "2")
    budget = models.CallBudget(Settings.from_env())
    budget.take("planner")
    budget.take("auditor")
    with pytest.raises(models.ModelBudgetExceeded):
        budget.take("planner")


def test_cost_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv("AUDITOR_PRICE_PER_MTOK", raising=False)
    assert models.cost("auditor", "qwen-x", 1000, 1000) is None
    monkeypatch.setenv("AUDITOR_PRICE_PER_MTOK", "0.5,1.5")
    assert models.cost("auditor", "qwen-x", 1_000_000, 1_000_000) == 2.0
    monkeypatch.setenv("PLANNER_PRICE_PER_MTOK", "4,20")
    assert models.cost("planner", "planner-model-from-env", 1_000_000, 100_000) == 6.0


def test_recording_collects_replies_and_the_budget_counts_live_calls(monkeypatch):
    with models.recording() as calls:
        models.get_model("auditor").complete("s", [{"role": "user", "content": "x"}], dry_run=lambda: {"ok": 1})
    assert [c.model for c in calls] == ["dry-run:auditor"]
    budget = models.CallBudget(Settings.from_env())
    assert budget.used() == 0
    budget.take("planner")
    assert budget.used() == 1


class _Fake:
    """Stands in for an SDK client: every attribute leads to `create`, which returns the canned response."""

    def __init__(self, response):
        self.response = response

    def __getattr__(self, name):
        return self

    def create(self, **kwargs):
        return self.response


def _claude_reply(text, stop_reason="end_turn"):
    block = type("Block", (), {"type": "text", "text": text})()
    usage = type("Usage", (), {"input_tokens": 10, "output_tokens": 5})()
    return type("Message", (), {"content": [block], "stop_reason": stop_reason, "model": "fake", "usage": usage})()


def _openai_reply(text, finish_reason="stop"):
    message = type("Msg", (), {"content": text})()
    choice = type("Choice", (), {"message": message, "finish_reason": finish_reason})()
    usage = type("Usage", (), {"prompt_tokens": 10, "completion_tokens": 5})()
    return type("Completion", (), {"choices": [choice], "model": "fake", "usage": usage})()


@pytest.mark.parametrize("text, stop, data", [
    ('{"ok": true}', "end_turn", {"ok": True}),
    ('{"action": "pay', "max_tokens", None),
    ("not json at all", "end_turn", None),
    ("[1, 2]", "end_turn", None),
])
def test_a_cut_off_or_malformed_claude_reply_has_no_data(monkeypatch, text, stop, data):
    from app.agentwallet.providers.anthropic_chat import ClaudeChat

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-key")
    monkeypatch.setenv("PLANNER_REFUSAL_FALLBACK", "off")
    chat = ClaudeChat("planner-model-from-env", lineage="anthropic/claude")
    chat.client = _Fake(_claude_reply(text, stop))
    assert chat.complete("s", [{"role": "user", "content": "x"}], schema={"type": "object"}).data == data


@pytest.mark.parametrize("text, finish, data", [
    ('{"verdict": "APPROVE"}', "stop", {"verdict": "APPROVE"}),
    ('{"verdict": "APP', "length", None),
    ("I think it is fine.", "stop", None),
])
def test_a_cut_off_or_malformed_qwen_reply_has_no_data(text, finish, data):
    from app.agentwallet.providers.openai_chat import OpenAICompatibleChat

    chat = OpenAICompatibleChat("qwen-primary", lineage="alibaba/qwen", api_key="test-not-a-key", base_url=None,
                                temperature=0)
    chat.client = _Fake(_openai_reply(text, finish))
    assert chat.complete("s", [{"role": "user", "content": "x"}], schema={"type": "object"}).data == data


def test_an_api_error_fails_closed_with_its_reason(monkeypatch):
    import httpx
    import openai

    from app.agentwallet.providers.openai_chat import OpenAICompatibleChat

    chat = OpenAICompatibleChat("qwen-primary", lineage="alibaba/qwen", api_key="test-not-a-key", base_url=None,
                                temperature=0)

    class Refusing(_Fake):
        def create(self, **kwargs):
            request = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
            raise openai.BadRequestError("model not found", response=httpx.Response(400, request=request), body=None)

    chat.client = Refusing(None)
    with pytest.raises(models.ModelUnavailable, match="400"):
        chat.complete("s", [{"role": "user", "content": "x"}], schema={"type": "object"})

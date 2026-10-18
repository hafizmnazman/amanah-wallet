"""Shared settings for the red-team tests: dry-run models, temporary state, and no chain unless asked."""

import pytest

import redteam.run  # noqa: F401  (puts lane B's package on the path)

from app.agentwallet import models  # noqa: E402

CHAIN_VARIABLES = ("RPC_URL", "VAULT_ADDRESS", "PLANNER_KEY", "AUDITOR_KEY", "SENTINEL_KEY", "RELAYER_KEY",
                   "POSTURE_ORACLE_KEY", "ANTHROPIC_API_KEY", "DASHSCOPE_API_KEY", "OPENAI_API_KEY")


@pytest.fixture
def offline(monkeypatch, tmp_path):
    for name in CHAIN_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AGENTWALLET_DRY_RUN", "1")
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("AGENTWALLET_TODAY", "2026-10-18")
    models.reset_models()
    yield tmp_path
    models.reset_models()



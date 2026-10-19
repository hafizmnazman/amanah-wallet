"""Scenario 2's signers: the planner and scenario 11's same-lineage control always share one model family."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))


def test_the_control_auditor_shares_the_planner_s_family_whichever_family_plans(monkeypatch):
    import run_demo

    monkeypatch.delenv("PLANNER_PROVIDER", raising=False)
    lineages = {name: lineage for name, _role, lineage, _view in run_demo.signers()}
    assert lineages["planner"] == lineages["control_auditor"] == "anthropic/claude"
    assert lineages["auditor"] == "alibaba/qwen"
    assert run_demo.family_name(lineages["planner"]) == "Claude"

    monkeypatch.setenv("PLANNER_PROVIDER", "openai")
    monkeypatch.setenv("PLANNER_LINEAGE", "moonshot/kimi")
    lineages = {name: lineage for name, _role, lineage, _view in run_demo.signers()}
    assert lineages["planner"] == lineages["control_auditor"] == "moonshot/kimi"
    assert lineages["auditor"] == "alibaba/qwen"
    assert run_demo.family_name(lineages["planner"]) == "Kimi"

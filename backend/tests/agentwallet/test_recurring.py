"""Plan task B11: the books' schedule makes the job draft a plan card, and only the officer confirms it."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.agentwallet import models, recurring
from app.agentwallet.api import create_app
from app.agentwallet.books import Books
from app.agentwallet.config import Settings
from app.agentwallet.planner.service import PlannerService

OFFICER = {"X-Amanah-Role": "finance_officer", "X-Amanah-User": "officer-1"}


@pytest.fixture
def service(monkeypatch, tmp_path):
    for name in ("RPC_URL", "VAULT_ADDRESS", "PLANNER_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AGENTWALLET_DRY_RUN", "1")
    monkeypatch.setenv("AGENTWALLET_CHECKERS", "inprocess")
    monkeypatch.setenv("AGENTWALLET_QUEUE_RETRY", "0")
    monkeypatch.setenv("AGENTWALLET_SCHEDULE", "0")
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("AGENTWALLET_TODAY", "2026-10-18")
    models.reset_models()
    return PlannerService(books=Books.load(), settings=Settings.from_env())


def test_a_monthly_programme_is_due_from_its_day_of_the_month():
    books = Books.load()
    assert recurring.due(books, date(2026, 10, 4)) == []
    [item] = recurring.due(books, date(2026, 10, 5))
    assert item == {"programme_code": "ZKT-IPOH-FAKIR-M", "batch_ref": "BATCH-2026-10-ZKT-MONTHLY", "period": "2026-10"}
    assert recurring.due(books, date(2026, 10, 31)) == [item]
    assert recurring.due(books, date(2026, 11, 6)) == []  # the books have no November batch yet


def test_the_job_drafts_a_plan_card_once_and_confirms_nothing(service):
    [draft] = recurring.draft_due(service, today=date(2026, 10, 5))
    card = draft["plan_card"]
    assert draft["session_id"] == "scheduled-BATCH-2026-10-ZKT-MONTHLY" and draft["officer"] == "officer-1"
    assert len(card["items"]) == 12 and card["total_usdc"] == "1810" and card["programme_code"] == "ZKT-IPOH-FAKIR-M"
    assert recurring.draft_due(service, today=date(2026, 10, 6)) == []
    values = service.graph.get_state(service._config(f"officer-1/{draft['session_id']}")).values
    assert not values.get("results") and values["plan"]["confirmed"] is False and service.queue() == []
    assert any(a["kind"] == "plan_ready" for a in service.store.alerts())


def test_the_officer_sees_the_draft_and_confirms_it(service):
    recurring.draft_due(service, today=date(2026, 10, 5))
    with TestClient(create_app(service)) as api:
        [item] = api.get("/api/agent/scheduled", headers=OFFICER).json()["items"]
        other = {**OFFICER, "X-Amanah-User": "officer-2"}
        assert api.get("/api/agent/scheduled", headers=other).json()["items"] == []
        results = api.post("/api/agent/confirm", headers=OFFICER,
                           json={"session_id": item["session_id"], "batch_id": item["plan_card"]["batch_id"]})
        assert results.status_code == 200 and len(results.json()["results"]) == 12
        assert api.get("/api/agent/scheduled", headers=OFFICER).json()["items"] == []

"""How the planner reaches the checkers over HTTP: a checker that does not answer is UNAVAILABLE with the
reason the officer's screen parses, "<service> unavailable: <the HTTP client's error>", and CHECKER_TIMEOUT
bounds the wait."""

import re
import secrets
from decimal import Decimal

import httpx
import pytest

from app.agentwallet import checkers, eip712
from app.agentwallet.books import Books
from app.agentwallet.types import Intent

BOOKS = Books.load()
# frontend/src/lib/rules.ts reads the reason with this pattern
UNAVAILABLE = re.compile(r"^(\w+) unavailable: (\w+)$")


def payout_and_intent():
    b = BOOKS.beneficiary("ZKT-B01")
    intent = Intent(programme_code=b["programme_code"], beneficiary_ref="ZKT-B01", wallet=b["wallet"],
                    amount_usdc=Decimal("150"), household_ref=b["household_ref"],
                    proposal_id="0x" + secrets.token_hex(32))
    payout = eip712.payout_from_intent(intent, BOOKS, nonce=7, deadline=2_000_000_000, evidence_hash="0x" + "00" * 32)
    return payout, intent


@pytest.fixture
def over_http(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTWALLET_CHECKERS", "http")
    monkeypatch.setenv("AUDITOR_URL", "http://auditor.invalid")
    monkeypatch.setenv("SENTINEL_URL", "http://sentinel.invalid/")
    monkeypatch.setenv("AGENTWALLET_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("CHECKER_TIMEOUT", raising=False)


def answer_with(monkeypatch, reply):
    """Every POST to a checker records its URL and timeout, then raises `reply` or returns it."""
    calls = []

    def post(url, *, json, timeout):
        calls.append((url, timeout))
        request = httpx.Request("POST", url)
        if isinstance(reply, type) and issubclass(reply, Exception):
            raise reply("no answer", request=request)
        return httpx.Response(reply[0], json=reply[1], request=request)

    monkeypatch.setattr(httpx, "post", post)
    return calls


@pytest.mark.parametrize("setting, seconds", [("7", 7.0), (None, 60.0)])
def test_a_timed_out_checker_is_unavailable_with_the_reason_the_screen_reads(over_http, monkeypatch, setting, seconds):
    if setting:
        monkeypatch.setenv("CHECKER_TIMEOUT", setting)
    calls = answer_with(monkeypatch, httpx.ReadTimeout)
    payout, intent = payout_and_intent()
    verdicts = checkers.check(payout, intent, books=BOOKS, batch=[payout])
    auditor, sentinel = verdicts["auditor"], verdicts["sentinel"]
    assert (auditor.verdict, auditor.reasons) == ("UNAVAILABLE", ["auditor unavailable: ReadTimeout"])
    assert (sentinel.verdict, sentinel.reasons) == ("UNAVAILABLE", ["sentinel unavailable: ReadTimeout"])
    assert auditor.signature is None and sentinel.signature is None
    assert UNAVAILABLE.match(auditor.reasons[0]).groups() == ("auditor", "ReadTimeout")
    assert sorted(calls) == [("http://auditor.invalid/verdict", seconds), ("http://sentinel.invalid/verdict", seconds)]


@pytest.mark.parametrize("reply, error", [
    (httpx.ConnectError, "ConnectError"),
    ((503, {"detail": "starting"}), "HTTPStatusError"),
    ((200, {"verdict": "MAYBE"}), "ValidationError"),
])
def test_every_failed_call_names_its_error_in_the_same_shape(over_http, monkeypatch, reply, error):
    answer_with(monkeypatch, reply)
    payout, intent = payout_and_intent()
    [reason] = checkers.check(payout, intent, books=BOOKS, batch=[payout], only=("auditor",))["auditor"].reasons
    assert reason == f"auditor unavailable: {error}" and UNAVAILABLE.match(reason)

"""How the planner reaches the auditor and the sentinel.

By default over HTTP, POST /verdict on AUDITOR_URL and SENTINEL_URL (plan section 3.4), so each checker
runs as its own service with its own key. AGENTWALLET_CHECKERS=inprocess runs both in the planner's
process with keys from the same environment: for tests and quick local runs only, since it gives up the
separation of keys. A checker that cannot be reached answers UNAVAILABLE, and the planner fails closed.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import httpx

from .config import Settings, env
from .types import Intent, Payout, VerdictRequest, VerdictResponse


def _unavailable(service: str, why: str) -> VerdictResponse:
    lineage = "alibaba/qwen" if service == "auditor" else "symbolic/rules"
    return VerdictResponse(verdict="UNAVAILABLE", reasons=[f"{service} unavailable: {why}"], input_hash="",
                           model="none", lineage=lineage)


def _http(url: str, service: str, body: dict) -> VerdictResponse:
    try:
        r = httpx.post(f"{url.rstrip('/')}/verdict", json=body, timeout=float(env("CHECKER_TIMEOUT", "60")))
        r.raise_for_status()
        return VerdictResponse.model_validate(r.json())
    except (httpx.HTTPError, ValueError) as exc:
        return _unavailable(service, type(exc).__name__)


def _inprocess(service: str, body: dict, books) -> VerdictResponse:
    from .signer_service import batch_from_request, intent_from_request, respond

    req = VerdictRequest.model_validate({k: v for k, v in body.items() if k in VerdictRequest.model_fields})
    payout, intent = intent_from_request(req, books)
    if service == "auditor":
        from .auditor.judge import audit

        verdict = audit(intent, books=books)
        return respond("auditor", "AUDITOR_KEY", verdict, payout, None)
    from decimal import Decimal

    from .sentinel.judge import judge
    from .types import units_to_usdc

    spent = units_to_usdc(int(body["spent_today"])) if body.get("spent_today") else Decimal(0)
    verdict = judge(intent, books=books, batch=batch_from_request(body.get("batch"), books), spent_today_usdc=spent)
    return respond("sentinel", "SENTINEL_KEY", verdict, payout, None)


def check(payout: Payout, intent: Intent, *, books, batch: list[Payout], spent_today: int | None = None,
          only: tuple[str, ...] = ("auditor", "sentinel")) -> dict[str, VerdictResponse]:
    """Asks both checkers in parallel. The auditor gets the payout and nothing else; the sentinel also gets
    the batch and today's spend, as numbers."""
    from .chain import current_tags

    base = {"payout": payout.as_strings(), "proposal_id": payout.proposalId, "programme_code": intent.programme_code,
            "tags": current_tags() or None}
    bodies = {"auditor": base,
              "sentinel": {**base, "batch": [p.as_strings() for p in batch],
                           "spent_today": str(spent_today) if spent_today is not None else None}}
    settings = Settings.from_env()
    urls = {"auditor": settings.auditor_url, "sentinel": settings.sentinel_url}
    inprocess = env("AGENTWALLET_CHECKERS", "http") == "inprocess"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {s: pool.submit(_inprocess, s, bodies[s], books) if inprocess else pool.submit(_http, urls[s], s, bodies[s])
                   for s in only}
        return {s: f.result() for s, f in futures.items()}

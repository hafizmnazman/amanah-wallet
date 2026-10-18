"""What the auditor and the sentinel services share (plan section 3.4): turning a POST /verdict payload into
an intent, signing on APPROVE with the service's own key, and anchoring a refusal with that same key.

Each service loads only its own key: AUDITOR_KEY or SENTINEL_KEY. Anchoring needs RPC_URL and
VAULT_ADDRESS, and is on unless <SERVICE>_ANCHOR=0.
"""

from __future__ import annotations

from eth_utils import to_checksum_address

from . import eip712
from .config import env, env_int
from .evidence import ActionLog
from .types import Intent, Payout, Verdict, VerdictRequest, VerdictResponse, units_to_usdc


def intent_from_request(req: VerdictRequest, books) -> tuple[Payout, Intent]:
    payout = Payout.from_strings(req.payout)
    programme = books.programme_by_id(payout.programmeId)
    if programme["code"] != req.programme_code:
        raise ValueError("programme_code does not match the payout's programmeId")
    record = books.beneficiary_by_wallet(programme["code"], payout.beneficiary)
    intent = Intent(programme_code=programme["code"], beneficiary_ref=record["beneficiary_ref"] if record else None,
                    wallet=to_checksum_address(payout.beneficiary), amount_usdc=units_to_usdc(payout.amount),
                    household_ref=record["household_ref"] if record else None, proposal_id=payout.proposalId,
                    source="books" if record else "conversation")
    return payout, intent


def batch_from_request(batch: list[dict[str, str]] | None, books) -> list[Intent] | None:
    if not batch:
        return None
    result = []
    for raw in batch:
        p = Payout.from_strings(raw)
        programme = books.programme_by_id(p.programmeId)
        result.append(Intent(programme_code=programme["code"], wallet=to_checksum_address(p.beneficiary),
                             amount_usdc=units_to_usdc(p.amount), proposal_id=p.proposalId))
    return result


def respond(service: str, key_variable: str, verdict: Verdict, payout: Payout, log: ActionLog | None,
            tags: dict | None = None) -> VerdictResponse:
    """Signs an APPROVE, or anchors a REJECT or ESCALATE, with the service's own key. `tags` label the anchor's
    row in the evidence table, as the caller's tagged() would in one process."""
    response = VerdictResponse(verdict=verdict.verdict, reasons=verdict.reasons, input_hash=verdict.input_hash,
                               model=verdict.model, lineage=verdict.lineage)
    key = env(key_variable)
    chain_id = env_int("CHAIN_ID", 84532)
    vault = env("VAULT_ADDRESS")
    if verdict.verdict == "APPROVE" and key and vault:
        response.signature = eip712.sign_payout(payout, key, chain_id=chain_id, vault=vault)
    elif verdict.verdict in ("REJECT", "ESCALATE") and key and vault and env("RPC_URL") \
            and env(f"{service.upper()}_ANCHOR", "1") != "0":
        from .chain import safe_tags, tagged

        with tagged(**safe_tags(tags)):
            response.anchor_id, response.anchor_tx = _anchor(payout, verdict, key)
    if log is not None:
        log.append(service, verdict.lineage, "verdict", proposal_id=payout.proposalId, verdict=verdict.verdict,
                   input_hash=verdict.input_hash, model=verdict.model, tx_hash=response.anchor_tx)
    return response


def _anchor(payout: Payout, verdict: Verdict, key: str) -> tuple[str | None, str | None]:
    from .chain import ChainError, ChainUnavailable, VaultClient

    try:
        client = VaultClient.from_env(relayer_key=key)
        result, anchor_id = client.anchor_decision(payout.proposalId, verdict.verdict, payout.evidenceHash, key=key,
                                                   description=f"{verdict.model} {verdict.verdict}")
        return anchor_id, result.tx_hash
    except (ChainError, ChainUnavailable):
        return None, None

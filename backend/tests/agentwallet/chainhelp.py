"""Paying through the vault in tests, as the planner would, without writing the backend's ledger."""

from __future__ import annotations

import secrets
from decimal import Decimal

from app.agentwallet import eip712
from app.agentwallet.chain import VaultClient
from app.agentwallet.types import Intent


def pay_on_chain(chain, books, ref: str, amount: str) -> str:
    """Pays a household with the three machine signatures and returns the transaction hash."""
    b = books.beneficiary(ref)
    intent = Intent(programme_code=b["programme_code"], beneficiary_ref=ref, wallet=b["wallet"],
                    amount_usdc=Decimal(amount), household_ref=b["household_ref"],
                    proposal_id="0x" + secrets.token_hex(32))
    vault = VaultClient(chain.rpc_url, chain.vault, chain.keys["relayer"])
    deadline = vault.w3.eth.get_block("latest")["timestamp"] + 3600
    payout = eip712.payout_from_intent(intent, books, nonce=secrets.randbits(63), deadline=deadline,
                                       evidence_hash="0x" + secrets.token_hex(32))
    sigs = [eip712.sign_payout(payout, chain.keys[s], chain_id=vault.chain_id, vault=vault.address)
            for s in ("planner", "auditor", "sentinel")]
    result = vault.execute(payout, sigs)
    assert result.status == "success"
    return result.tx_hash

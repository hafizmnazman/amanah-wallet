"""Plan task B3: against the Anvil fixture, a routine payout executes and a forced payout to an unlisted
wallet returns a mined, reverted hash."""

import secrets
from decimal import Decimal

import pytest

from app.agentwallet import eip712
from app.agentwallet.chain import ChainError, VaultClient, tagged
from app.agentwallet.evidence import TransactionLog
from app.agentwallet.types import Intent, usdc_to_units

pytestmark = pytest.mark.anvil


def client(chain, tmp_path) -> VaultClient:
    return VaultClient(chain.rpc_url, chain.vault, chain.keys["relayer"],
                       tx_log=TransactionLog(tmp_path / "transactions.csv", network="anvil"))


def signed_payout(chain, vault, beneficiary_ref: str, amount: str, signers=("planner", "auditor", "sentinel"),
                  wallet: str | None = None):
    b = chain.books.beneficiary(beneficiary_ref)
    intent = Intent(programme_code=b["programme_code"], beneficiary_ref=beneficiary_ref, wallet=wallet or b["wallet"],
                    amount_usdc=Decimal(amount), household_ref=b["household_ref"],
                    proposal_id="0x" + secrets.token_hex(32))
    deadline = vault.w3.eth.get_block("latest")["timestamp"] + 3600
    payout = eip712.payout_from_intent(intent, chain.books, nonce=secrets.randbits(63), deadline=deadline,
                                       evidence_hash="0x" + secrets.token_hex(32))
    sigs = [eip712.sign_payout(payout, chain.keys[s], chain_id=vault.chain_id, vault=vault.address) for s in signers]
    return payout, sigs


def test_routine_payout_executes_and_is_logged(local_chain, tmp_path):
    vault = client(local_chain, tmp_path)
    payout, sigs = signed_payout(local_chain, vault, "ZKT-B02", "150")
    assert vault.tier_of(payout) == 1
    before = vault.usdc_balance(payout.beneficiary)
    result = vault.execute(payout, sigs, scenario="6", description="routine payout", expected="paid")
    assert result.status == "success" and result.block
    assert vault.usdc_balance(payout.beneficiary) - before == usdc_to_units("150")
    assert any(e["event"] == "PayoutExecuted" and e["tier"] == 1 for e in result.events)
    assert vault.tx_log.rows()[-1]["status"] == "success"


def test_forced_payout_to_an_unlisted_wallet_is_mined_and_reverted(local_chain, tmp_path):
    vault = client(local_chain, tmp_path)
    payout, sigs = signed_payout(local_chain, vault, "ZKT-B03", "150", wallet="0x" + secrets.token_hex(20))
    with pytest.raises(ChainError) as refused:
        vault.execute(payout, sigs)
    assert refused.value.name == "NotAllowlisted"
    result = vault.execute(payout, sigs, expect_revert=True, scenario="10", expected="reverted")
    assert result.status == "reverted" and result.error == "NotAllowlisted" and result.block
    assert vault.tx_log.rows()[-1]["error"] == "NotAllowlisted"


def test_tier_reads_and_hard_limits(local_chain, tmp_path):
    vault = client(local_chain, tmp_path)
    above_cap, _ = signed_payout(local_chain, vault, "REL-B05", "450")
    assert vault.tier_of(above_cap) == 2
    too_much, _ = signed_payout(local_chain, vault, "REL-B05", "601")
    with pytest.raises(ChainError) as refused:
        vault.tier_of(too_much)
    assert refused.value.name == "BeneficiaryCapExceeded"


def test_checker_anchors_its_own_refusal(local_chain, tmp_path):
    vault = client(local_chain, tmp_path)
    proposal = "0x" + secrets.token_hex(32)
    result, anchor_id = vault.anchor_decision(proposal, "REJECT", "0x" + secrets.token_hex(32),
                                              key=local_chain.keys["auditor"], scenario="8")
    assert result.status == "success" and anchor_id
    decision = vault.decision(anchor_id)
    assert decision["verdict"] == "REJECT" and decision["proposal_id"] == proposal


def test_governance_needs_trustees(local_chain, tmp_path):
    vault = client(local_chain, tmp_path)
    pid = local_chain.programmes["ZKT-IPOH-FAKIR-M"]
    wallet = "0x" + secrets.token_hex(20)
    params = (pid, wallet, "0x" + secrets.token_hex(32))
    refused = vault.governance("addBeneficiary", params, [local_chain.keys["planner"]], expect_revert=True,
                               sender_key=local_chain.keys["planner"], scenario="12")
    assert refused.status == "reverted" and refused.error == "NotTrustee"
    added = vault.governance("addBeneficiary", params, [local_chain.keys["trustee1"], local_chain.keys["trustee2"]])
    assert added.status == "success"
    assert vault.beneficiary(pid, wallet)["active"]


def test_signer_registry_reads(local_chain, tmp_path):
    vault = client(local_chain, tmp_path)
    from eth_account import Account

    planner = vault.signer(Account.from_key(local_chain.keys["planner"]).address)
    assert planner["role"] == "PLANNER" and planner["active"]
    assert planner["lineage"] == eip712.label("anthropic/claude")


def test_tagged_block_labels_every_transaction(local_chain, tmp_path):
    vault = client(local_chain, tmp_path)
    payout, sigs = signed_payout(local_chain, vault, "ZKT-B04", "150", wallet="0x" + secrets.token_hex(20))
    with tagged(scenario="10", expected="reverted", description="forced payout"):
        vault.execute(payout, sigs, expect_revert=True)
        vault.anchor_decision(payout.proposalId, "REJECT", "0x" + secrets.token_hex(32), key=local_chain.keys["auditor"],
                              description="auditor REJECT")
    vault.anchor_decision("0x" + secrets.token_hex(32), "REJECT", "0x" + secrets.token_hex(32),
                          key=local_chain.keys["auditor"])
    rows = vault.tx_log.rows()
    assert [(r["scenario"], r["expected"]) for r in rows] == [("10", "reverted"), ("10", "reverted"), ("", "")]
    assert [r["description"] for r in rows[:2]] == ["forced payout", "auditor REJECT"]

"""Plan task B2: Python produces the same digests and signatures as the contract (shared/vectors.json)."""

import json

import pytest
from eth_account import Account
from eth_utils import keccak

from app.agentwallet import eip712
from app.agentwallet.config import REPO_ROOT
from app.agentwallet.types import Payout

VECTORS = json.loads((REPO_ROOT / "shared" / "vectors.json").read_text())
CHAIN = VECTORS["domain"]["chainId"]
VAULT = VECTORS["domain"]["verifyingContract"]


def key(label: str) -> str:
    return "0x" + keccak(text=label).hex()


def vector_payout() -> Payout:
    m = VECTORS["payout"]["message"]
    return Payout(proposalId=m["proposalId"], programmeId=m["programmeId"], beneficiary=m["beneficiary"],
                  amount=int(m["amount"]), evidenceHash=m["evidenceHash"], nonce=int(m["nonce"]),
                  deadline=int(m["deadline"]))


def test_domain_separator_and_type_hashes_match_the_contract():
    assert "0x" + eip712.domain_separator(CHAIN, VAULT).hex() == VECTORS["domainSeparator"]
    assert "0x" + eip712.type_hash("Payout").hex() == VECTORS["typeHashes"]["Payout"]
    assert "0x" + eip712.type_hash("Governance").hex() == VECTORS["typeHashes"]["Governance"]


def test_payout_digest_signature_and_recovery_match_the_vector():
    p = vector_payout()
    assert "0x" + eip712.payout_digest(p, chain_id=CHAIN, vault=VAULT).hex() == VECTORS["payout"]["digest"]
    signature = eip712.sign_payout(p, key(VECTORS["payout"]["signerKeyLabel"]), chain_id=CHAIN, vault=VAULT)
    assert signature == VECTORS["payout"]["signature"]
    assert eip712.recover_payout(p, signature, chain_id=CHAIN, vault=VAULT) == VECTORS["payout"]["signer"]


@pytest.mark.parametrize("action", ["lowerPosture", "registerSigner", "setSignerActive", "setMandate",
                                    "addBeneficiary", "unpause"])
def test_governance_params_digest_and_signature_match_the_vector(action):
    g = VECTORS["governance"][action]
    auditor = Account.from_key(key("amanah.vector.auditor")).address
    wallet = Account.from_key(key("amanah.vector.beneficiary")).address
    pid = "0x" + keccak(text="amanah.vector.programme").hex()
    m = VECTORS["governance"]["setMandateMandate"]
    mandate = (int(m["cap"]), int(m["hardCeiling"]), int(m["dailyBudget"]), int(m["perBeneficiaryCap"]),
               int(m["expiry"]), m["purposeHash"], m["active"])
    params = {
        "lowerPosture": (0,),
        "registerSigner": (auditor, 2, eip712.label("alibaba/qwen"), eip712.label("casefile")),
        "setSignerActive": (auditor, False),
        "setMandate": (pid, mandate),
        "addBeneficiary": (pid, wallet, "0x" + keccak(text="amanah.vector.idHash").hex()),
        "unpause": (),
    }[action]
    ph = eip712.params_hash(action, *params)
    assert ph == g["paramsHash"]
    n, d = int(g["govNonce"]), int(g["deadline"])
    assert "0x" + eip712.governance_digest(action, ph, n, d, chain_id=CHAIN, vault=VAULT).hex() == g["digest"]
    sig = eip712.sign_governance(action, ph, n, d, key(g["signerKeyLabel"]), chain_id=CHAIN, vault=VAULT)
    assert sig == g["signature"]
    assert eip712.recover_governance(action, ph, n, d, sig, chain_id=CHAIN, vault=VAULT) == g["signer"]


def test_typed_data_carries_strings_and_the_live_domain():
    td = eip712.payout_typed_data(vector_payout(), chain_id=31337, vault=VAULT)
    assert td["primaryType"] == "Payout"
    assert td["domain"]["chainId"] == 31337
    assert td["message"]["amount"] == "150000000"
    assert [f["name"] for f in td["types"]["Payout"]][0] == "proposalId"


def test_a_signature_does_not_carry_over_to_another_chain():
    p = vector_payout()
    signature = eip712.sign_payout(p, key("amanah.vector.planner"), chain_id=CHAIN, vault=VAULT)
    assert eip712.recover_payout(p, signature, chain_id=31337, vault=VAULT) != VECTORS["payout"]["signer"]

"""The preflight: what it reports with no .env, the HMAC check, and every demo check against a live Anvil."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import preflight  # noqa: E402
from app.agentwallet import devchain  # noqa: E402


def run(env: dict, tmp_path: Path, *stages: str) -> dict[str, preflight.Check]:
    env_file = tmp_path / ".env"
    env_file.write_text("".join(f"{k}={v}\n" for k, v in env.items()))
    p = preflight.Preflight(env, env_file=env_file)
    p.common()
    for stage in stages:
        getattr(p, stage)()
    return {c.name: c for c in p.checks}


def test_with_no_settings_each_stage_names_what_is_missing(tmp_path):
    checks = run({}, tmp_path, *preflight.STAGES)
    assert checks["RPC_URL answers"].status == "FAIL"
    assert checks["BASESCAN_API_KEY is set, for --verify"].status == "FAIL"
    assert checks["three trustees and a guardian, by address or key"].detail.startswith("missing TRUSTEE1")
    assert checks["the planner's key and model"].detail == "missing ANTHROPIC_API_KEY, PLANNER_MODEL"
    assert checks["redteam/mutate.py exists (C3)"].status == "FAIL"
    assert checks["prices for the red team's cost column"].status == "todo"


def test_the_hmac_check_tells_the_development_key_from_the_real_one(tmp_path):
    from redteam.datagen import DEV_HMAC_KEY

    assert run({"INSTITUTION_HMAC_KEY": DEV_HMAC_KEY}, tmp_path, "demo")[
        "the books' id hashes use INSTITUTION_HMAC_KEY"].status == "pass"
    other = run({"INSTITUTION_HMAC_KEY": "another key"}, tmp_path, "demo")
    assert other["the books' id hashes use INSTITUTION_HMAC_KEY"].status == "FAIL"


@pytest.mark.skipif(not devchain.available(), reason="anvil and forge are needed")
def test_every_demo_check_against_the_anvil_fixture(monkeypatch, tmp_path):
    with devchain.anvil_fixture() as chain:
        monkeypatch.setattr(preflight, "BASE_SEPOLIA", 31337)  # contracts/deployments/31337.json is the fixture's
        monkeypatch.setattr(preflight, "CIRCLE_USDC", chain.usdc)
        env = {**chain.env(), "DONOR_KEY": chain.keys["relayer"], "BASESCAN_API_KEY": "x"}
        env.pop("VAULT_ADDRESS")
        usdc = chain.w3.eth.contract(address=chain.w3.to_checksum_address(chain.usdc), abi=preflight_erc20())
        relayer = chain.w3.eth.accounts[0]
        chain.w3.eth.wait_for_transaction_receipt(usdc.functions.mint(relayer, 5_000 * 10**6).transact({"from": relayer}))
        checks = run(env, tmp_path, "deploy", "demo")
    assert checks["RPC_URL is Base Sepolia"].detail == "chain id 31337"
    for name in ("the vault in the deployment record has code", "the vault uses Circle's Base Sepolia USDC",
                 "relayer holds at least 0.005 ETH", "TRUSTEE1_KEY is a trustee in the vault",
                 "TRUSTEE2_KEY is a trustee in the vault", "the donor holds the 5,000 USDC scenario 5 deposits",
                 "three trustees and a guardian, by address or key"):
        assert checks[name].status == "pass", (name, checks[name].detail)


def preflight_erc20():
    from app.agentwallet.chain import ERC20_ABI

    return ERC20_ABI

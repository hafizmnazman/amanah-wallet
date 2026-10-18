"""The test-wallet tools: new_keys.py fills only empty keys and never prints one; fund_keys.py tops up on Anvil."""

import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import fund_keys  # noqa: E402
import new_keys  # noqa: E402
import preflight  # noqa: E402
from app.agentwallet import devchain  # noqa: E402
from eth_account import Account  # noqa: E402
from web3 import Web3  # noqa: E402

EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"


def test_every_role_gets_a_distinct_key_and_set_values_stay(tmp_path, capsys):
    env_file = tmp_path / ".env"
    kept = devchain.anvil_key(5)
    env_file.write_text(EXAMPLE.read_text().replace("TRUSTEE1_KEY=", f"TRUSTEE1_KEY={kept}"))
    assert new_keys.main(["--env-file", str(env_file)]) == 0
    values = new_keys.values(env_file.read_text())
    keys = [values[name] for name in new_keys.ROLES]
    assert len(set(keys)) == len(keys)
    assert values["TRUSTEE1_KEY"] == kept
    assert all(Account.from_key(k) for k in keys)
    assert len(bytes.fromhex(values["INSTITUTION_HMAC_KEY"])) == 32
    assert env_file.stat().st_mode & 0o077 == 0
    out = capsys.readouterr().out
    assert all(k.removeprefix("0x") not in out for k in [*keys, values["INSTITUTION_HMAC_KEY"]])
    assert Account.from_key(values["DONOR_KEY"]).address in out


def test_a_second_run_changes_nothing(tmp_path):
    env_file = tmp_path / ".env"
    new_keys.main(["--env-file", str(env_file)])
    first = env_file.read_text()
    new_keys.main(["--env-file", str(env_file)])
    assert env_file.read_text() == first
    assert first.count("DONOR_KEY=") == 1


def test_it_refuses_a_file_git_would_commit():
    assert new_keys.main(["--env-file", str(new_keys.REPO / "README.md")]) == 1


@pytest.mark.skipif(not devchain.available(), reason="anvil is needed")
def test_fund_keys_tops_up_each_sending_key_and_keeps_the_relayers_reserve(tmp_path):
    port = devchain.free_port()
    anvil = subprocess.Popen(["anvil", "--port", str(port), "--silent"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    try:
        rpc = f"http://127.0.0.1:{port}"
        w3 = Web3(Web3.HTTPProvider(rpc))
        for _ in range(100):
            try:
                w3.eth.chain_id
                break
            except Exception:  # not listening yet
                time.sleep(0.1)
        env_file = tmp_path / ".env"
        env_file.write_text(f"RPC_URL={rpc}\nRELAYER_KEY={devchain.anvil_key(0)}\n")
        new_keys.main(["--env-file", str(env_file)])  # keeps the funded relayer, fills the rest
        assert fund_keys.main(["--env-file", str(env_file)]) == 0  # a dry run sends nothing
        env = new_keys.values(env_file.read_text())
        donor = Account.from_key(env["DONOR_KEY"]).address
        assert w3.eth.get_balance(donor) == 0
        assert fund_keys.main(["--env-file", str(env_file), "--send"]) == 0
        for variable, need in preflight.GAS.items():
            assert w3.eth.get_balance(Account.from_key(env[variable]).address) >= int(need * 10**18)
        assert w3.eth.get_balance(Account.from_key(env["TRUSTEE1_KEY"]).address) == 0  # trustees only sign
        assert fund_keys.main(["--env-file", str(env_file), "--send"]) == 0  # nothing left to send
    finally:
        anvil.terminate()
        anvil.wait(timeout=10)


def test_fund_keys_stops_when_the_relayer_is_short(tmp_path, monkeypatch, capsys):
    class Eth:
        chain_id = preflight.BASE_SEPOLIA

        def get_balance(self, address):
            return 0  # every key empty, the relayer included

    class W3:
        eth = Eth()

    monkeypatch.setattr(fund_keys, "connect", lambda url: W3())
    env_file = tmp_path / ".env"
    env_file.write_text("RPC_URL=http://unused\n")
    new_keys.main(["--env-file", str(env_file)])
    capsys.readouterr()
    assert fund_keys.main(["--env-file", str(env_file), "--send"]) == 1
    assert "short" in capsys.readouterr().err

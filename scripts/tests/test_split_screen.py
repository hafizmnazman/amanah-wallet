"""The video's opening: on a fresh Anvil, the planner alone pays the attacker and Amanah moves nothing."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.agentwallet import devchain  # noqa: E402


@pytest.mark.skipif(not devchain.available(), reason="anvil and forge are needed")
def test_one_message_two_wallets(monkeypatch, tmp_path, capsys):
    import split_screen

    for name in ("AGENTWALLET_TODAY", "RPC_URL", "VAULT_ADDRESS", "AUDITOR_URL", "SENTINEL_URL"):
        monkeypatch.delenv(name, raising=False)
    out = tmp_path / "split.json"
    monkeypatch.setattr(split_screen.os, "environ", dict(split_screen.os.environ))
    assert split_screen.main(["--json", str(out)]) == 0
    result = json.loads(out.read_text())
    assert result["typical_wallet"]["balance"] == "attacker's balance: 2,000.00 USDC"
    assert result["amanah"]["balance"] == "attacker's balance from Amanah: 0.00 USDC"
    assert any(line.startswith("auditor (Qwen): REJECT") for line in result["amanah"]["lines"])
    assert sum(line.startswith("refusal anchored on-chain") for line in result["amanah"]["lines"]) == 2
    assert "A TYPICAL AGENT WALLET" in capsys.readouterr().out

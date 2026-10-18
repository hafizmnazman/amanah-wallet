"""Settings from the environment. An empty variable, as left by .env.example, counts as unset."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value else default


def env_int(name: str, default: int) -> int:
    value = env(name)
    return int(value) if value else default


def dry_run_forced() -> bool:
    """AGENTWALLET_DRY_RUN=1 forces canned model replies even when keys are present (tests, demos offline)."""
    return env("AGENTWALLET_DRY_RUN", "0").lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Settings:
    chain_id: int
    rpc_url: str | None
    vault_address: str | None
    usdc_address: str | None
    explorer_url: str
    books_path: Path
    evidence_dir: Path
    state_dir: Path
    auditor_url: str
    sentinel_url: str
    daily_model_call_cap: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            chain_id=env_int("CHAIN_ID", 84532),
            rpc_url=env("RPC_URL"),
            vault_address=env("VAULT_ADDRESS"),
            usdc_address=env("USDC_ADDRESS"),
            explorer_url=env("EXPLORER_URL", "https://sepolia.basescan.org"),
            books_path=Path(env("BOOKS_PATH", str(REPO_ROOT / "redteam" / "data" / "books.json"))),
            evidence_dir=Path(env("EVIDENCE_DIR", str(REPO_ROOT / "evidence"))),
            state_dir=Path(env("AGENTWALLET_STATE_DIR", str(REPO_ROOT / "backend" / "var"))),
            auditor_url=env("AUDITOR_URL", "http://127.0.0.1:8101"),
            sentinel_url=env("SENTINEL_URL", "http://127.0.0.1:8102"),
            daily_model_call_cap=env_int("DAILY_MODEL_CALL_CAP", 2000),
        )


# Lineage and evidence-view labels, plan section 1. contracts/src/AmanahLabels.sol holds the same strings.
LINEAGE_CLAUDE = "anthropic/claude"
LINEAGE_QWEN = "alibaba/qwen"
LINEAGE_GPT = "openai/gpt"
LINEAGE_RULES = "symbolic/rules"
LINEAGE_HUMAN = "human"

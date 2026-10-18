"""Prompts for the new agents, one file each, as CLAUDE.md asks. The audit agents' fingerprinted prompts
from Amanah (ec02406645ee3f2c) are not here and are not changed."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).parent


@lru_cache
def load(name: str) -> str:
    return (HERE / f"{name}.md").read_text()


def fingerprint(name: str) -> str:
    """The first 16 hex characters of the prompt's sha256, for run manifests."""
    return hashlib.sha256(load(name).encode()).hexdigest()[:16]

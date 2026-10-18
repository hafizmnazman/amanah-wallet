"""Statistics for the red-team report (plan task C5), from the standard library only.

Wilson score intervals for rates, the exact McNemar test for paired configurations, and Holm's step-down
correction across the protocol's planned comparisons (redteam/protocol.md).
"""

from __future__ import annotations

import math
from statistics import median

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    """The 95% Wilson score interval for k successes in n trials; None when n is 0."""
    if n == 0:
        return None
    p = k / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value. b and c are the discordant pairs: cases where only the first
    configuration failed to stop the attack, and cases where only the second did."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2**n
    return min(1.0, 2 * tail)


def holm(p_values: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values, monotone in rank, capped at 1."""
    ordered = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[name] = running
    return adjusted


def median_or_none(values: list[float]) -> float | None:
    values = [v for v in values if v is not None]
    return median(values) if values else None

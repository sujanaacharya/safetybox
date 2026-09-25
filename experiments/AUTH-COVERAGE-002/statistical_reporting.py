"""Frozen supplemental statistical procedures for AUTH-COVERAGE-002.

The metric contract remains the canonical source for point estimates.  This
module implements the exact and dependence-aware sensitivity intervals that
the preregistered protocol requires in addition to those point estimates.
"""

from __future__ import annotations

import hashlib
import math
import random
from collections import defaultdict
from collections.abc import Iterable, Sequence

CONFIDENCE = 0.95
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED_DOMAIN = "AUTH-COVERAGE-002-CLUSTER-BOOTSTRAP@1"


def _binomial_cdf(k: int, n: int, probability: float) -> float:
    """Return P[X <= k] for X~Binomial(n, probability), stably."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if probability <= 0.0:
        return 1.0
    if probability >= 1.0:
        return 0.0
    logs = [
        math.lgamma(n + 1)
        - math.lgamma(index + 1)
        - math.lgamma(n - index + 1)
        + index * math.log(probability)
        + (n - index) * math.log1p(-probability)
        for index in range(k + 1)
    ]
    maximum = max(logs)
    return min(1.0, math.exp(maximum) * math.fsum(math.exp(item - maximum) for item in logs))


def _bisect_decreasing_cdf(k: int, n: int, target: float) -> float:
    low, high = 0.0, 1.0
    for _ in range(80):
        midpoint = (low + high) / 2.0
        if _binomial_cdf(k, n, midpoint) > target:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2.0


def clopper_pearson(
    successes: int, trials: int, confidence: float = CONFIDENCE
) -> tuple[float, float]:
    """Return the two-sided exact Clopper-Pearson interval."""
    if trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("require 0 <= successes <= trials and trials > 0")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between zero and one")
    alpha = 1.0 - confidence
    lower = (
        0.0 if successes == 0 else _bisect_decreasing_cdf(successes - 1, trials, 1.0 - alpha / 2.0)
    )
    upper = 1.0 if successes == trials else _bisect_decreasing_cdf(successes, trials, alpha / 2.0)
    return lower, upper


def exact_zero_error_upper_bound(trials: int, confidence: float = CONFIDENCE) -> float:
    """Return the exact one-sided upper bound for an observed zero-error rate."""
    if trials <= 0:
        raise ValueError("trials must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between zero and one")
    return 1.0 - (1.0 - confidence) ** (1.0 / trials)


def clustered_accuracy_interval(
    observations: Iterable[tuple[str, bool]],
    *,
    seed_label: str,
    confidence: float = CONFIDENCE,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> tuple[float, float]:
    """Percentile bootstrap accuracy while resampling whole dependency clusters."""
    if not 0.0 < confidence < 1.0 or replicates <= 0 or not seed_label:
        raise ValueError("invalid bootstrap configuration")
    clusters: dict[str, list[bool]] = defaultdict(list)
    for cluster_id, correct in observations:
        if not cluster_id:
            raise ValueError("cluster identifiers must be nonempty")
        clusters[cluster_id].append(bool(correct))
    ordered: Sequence[tuple[bool, ...]] = tuple(tuple(clusters[key]) for key in sorted(clusters))
    if not ordered:
        raise ValueError("at least one observation is required")
    seed = int.from_bytes(
        hashlib.sha256(f"{BOOTSTRAP_SEED_DOMAIN}:{seed_label}".encode()).digest(), "big"
    )
    generator = random.Random(seed)
    estimates: list[float] = []
    for _ in range(replicates):
        sample = [ordered[generator.randrange(len(ordered))] for _ in ordered]
        correct = sum(sum(cluster) for cluster in sample)
        total = sum(len(cluster) for cluster in sample)
        estimates.append(correct / total)
    estimates.sort()
    tail = (1.0 - confidence) / 2.0
    low_index = max(0, math.floor(tail * replicates))
    high_index = min(replicates - 1, math.ceil((1.0 - tail) * replicates) - 1)
    return estimates[low_index], estimates[high_index]
